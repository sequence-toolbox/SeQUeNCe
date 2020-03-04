import math

from numpy import random

from ...kernel.entity import Entity
from ...kernel.event import Event
from ...kernel.process import Process


class Cascade(Entity):
    def log(self, info):
        if self.logflag:
            print(self.timeline.now(), self.name, self.state, info)

    def __init__(self, name, timeline, **kwargs):
        # TODO: now we assume key length is 256 bits
        Entity.__init__(self, name, timeline)
        self.w = kwargs.get("w", 4)
        self.bb84 = kwargs.get("bb84", None)
        # for sender role==0; for receiver role==1
        self.role = kwargs.get("role", None)
        self.secure_params = kwargs.get("secure_params", 100)
        self.another = None
        self.state = 0
        self.keylen = None
        self.frame_len = 10240
        self.frame_num = None
        self.run_time = None
        self.bits = []
        self.valid_keys = []
        self.t1 = []
        self.t2 = []
        self.k1 = 0
        self.checksum_tables = [[]]
        self.another_checksums = [[]]
        self.index_to_block_id_lists = [[]]
        self.block_id_to_index_lists = [[]]
        self.logflag = False
        #self.tmp = {}
        self.time_cost = None
        self.setup_time = None
        self.start_time = None
        self.end_time = math.inf
        self.throughput = None # bits/sec
        self.error_bit_rate = None
        self.latency = None # the average latency
        self.disclosed_bits_counter = 0
        self.privacy_throughput = None

        """
        state of protocol:
            0: initialization step of protocol
            1: generating block
            2: end
        """

    def assign_cchannel(self, cchanel):
        self.cchanel = cchanel

    def generate_key(self, keylen, frame_num=math.inf, run_time=math.inf):
        """
        Generate 10000 bits key to measure error rate at 0 pass
        Generate keylen bits key at 1st pass
        """
        self.log('generate_key, keylen=' + str(keylen))
        if self.role == 1:
            raise Exception(
                "Cascade protocol type is receiver (type==1); receiver cannot generate key")

        if self.state == 0:
            self.log('generate_key with state 0')
            self.setup_time = self.timeline.now()
            self.keylen = keylen
            self.frame_num = frame_num
            self.run_time = run_time
            self.bb84.generate_key(10000, key_num = 1)
        else:
            self.start_time = self.timeline.now()
            self.end_time = self.start_time + self.run_time
            self.log('generate_key with state ' + str(self.state))
            self.bb84.generate_key(self.frame_len, self.frame_num, self.run_time)

    def get_key_from_BB84(self, key):
        """
        Function called by BB84 when it creates a key
        """
        self.log('get_key_from_BB84, key= ' + str(key))
        self.bits.append(key)
        self.t1.append(self.timeline.now())
        self.t2.append(-1)

        if self.state == 1:
            self.create_checksum_table()
        if self.state == 0 and self.role == 1:
            self.send_key()
        elif self.state == 1 and self.role == 0:
            self.send_checksums()

    def send_key(self):
        """
        Schedule a receive key event
        """
        self.log('send_key')
        process = Process(self.another, "receive_key", [self.bits[0]])
        self.send_by_cc(process)

    def receive_key(self, key):
        """
        Sender receive key from receiver to measure the error rate of key
        Calculate self.k by error rate
        Send self.k and keylen to receiver
        """
        self.log('receive_key, key=' + str(key))

        def get_k1(p, lower, upper):
            while lower <= upper:
                k1 = int((lower + upper) / 2)
                if (k1 * p - (1 - (1 - 2 * p)**k1) / 2) < (-(math.log(1 / 2) / 2)):
                    lower = k1 + 1
                elif (k1 * p - (1 - (1 - 2 * p)**k1) / 2) > (-(math.log(1 / 2) / 2)):
                    upper = k1 - 1
                else:
                    return k1

            return lower - 1

        def get_diff_bit_num(key1, key2):
            val = key1^key2
            counter = 0
            i = 0
            while val>>i:
                if (val>>i)&1:
                    counter += 1
                i+=1
            return counter

        p = get_diff_bit_num(key, self.bits[0]) / 10000
        # avoid p==0, which will cause k1 to an infinite large number
        if p == 0:
            p = 0.0001
        self.k1 = get_k1(p, 0, 10000)
        self.send_params()
        self.state = 1

    def create_checksum_table(self):
        """
        initialize checksum_table, index_to_block_id, and block_id_to_index after get key from bb84
        """
        # create index_to_block_id
        self.log('create_checksum_table')
        index_to_block_id = [[]]
        for pass_id in range(1, self.w + 1):
            index_to_block_relation = []
            block_size = self.k1 * (2**(pass_id - 1))

            if pass_id == 1:
                for i in range(self.frame_len):
                    index_to_block_relation.append(int(i / block_size))
            else:
                # if block_size/2 has been greater than key length, more pass
                # will not fix error bit
                if block_size / 2 >= self.frame_len:
                    break

                random.seed(pass_id)
                bit_order = list(range(self.frame_len))
                random.shuffle(bit_order)
                for i in range(self.frame_len):
                    index_to_block_relation.append(int(bit_order[i] / block_size))

            index_to_block_id.append(index_to_block_relation)
        self.index_to_block_id_lists.append(index_to_block_id)

        # create block_id_to_index
        block_id_to_index = [[]]
        for pass_id in range(1, self.w + 1):
            block_to_index_relation = []
            block_size = self.k1 * (2**(pass_id - 1))
            block_num = math.ceil(self.frame_len / block_size)
            for _ in range(block_num):
                block_to_index_relation.append([None] * block_size)

            if pass_id == 1:
                for i in range(self.frame_len):
                    block_to_index_relation[int(i / block_size)][i % block_size] = i
            else:
                random.seed(pass_id)
                bit_order = list(range(self.frame_len))
                random.shuffle(bit_order)
                for i in range(self.frame_len):
                    bit_pos = bit_order[i]
                    block_to_index_relation[int(bit_pos / block_size)][bit_pos % block_size] = i
            # pop extra element in the last block
            while block_to_index_relation[-1][-1] is None:
                block_to_index_relation[-1].pop()

            block_id_to_index.append(block_to_index_relation)
        self.block_id_to_index_lists.append(block_id_to_index)

        # create checksum_table
        checksum_table = [[]]
        for pass_id in range(1, len(index_to_block_id)):
            block_size = self.k1 * (2**(pass_id - 1))
            block_num = math.ceil(self.frame_len / block_size)
            checksum_table.append([0] * block_num)
            for i in range(self.frame_len):
                block_id = index_to_block_id[pass_id][i]
                checksum_table[pass_id][block_id] ^= ((self.bits[-1] >> i) & 1)
        self.checksum_tables.append(checksum_table)

    def send_params(self):
        """
        Schedule a receive paramters event
        """
        self.log('send_params'+str([self.k1, self.keylen, self.frame_num, self.run_time]))
        process = Process(self.another, "receive_params", [self.k1, self.keylen, self.frame_num, self.run_time])
        self.send_by_cc(process)

    def receive_params(self, k, keylen, frame_num, run_time):
        """
        Receiver receive k, keylen from sender
        """
        self.log('receive_params with params= ' + str([k, keylen]))
        if self.role == 0:
            raise Exception(
                "Cascade protocol type is sender (type==0); sender cannot receive parameters from receiver")

        self.k1 = k
        self.keylen = keylen
        self.frame_num = frame_num
        self.run_time = run_time
        self.start_time = self.timeline.now()
        self.end_time = self.start_time+self.run_time
        self.state = 1

        # Schedule a key generation event for Cascade sender
        process = Process(self.another, "generate_key", [self.keylen, self.frame_num, self.run_time])
        self.send_by_cc(process)

    def send_checksums(self):
        """
        Sender send all checksums to receiver
        """
        self.log("send_checksums "+str(len(self.checksum_tables)))
        if self.role == 1:
            raise Exception(
                "Cascade protocol type is receiver (type==1); receiver cannot send checksums to sender")
        self.state = 1
        process = Process(self.another, "receive_checksums", [len(self.checksum_tables)-1, self.checksum_tables[-1]])
        self.send_by_cc(process)

    def receive_checksums(self, key_id, checksums):
        self.log("receive_checksums ")
        while len(self.another_checksums) <= key_id:
            self.another_checksums.append(None)
        self.another_checksums[key_id] = checksums
        self.check_checksum(key_id)

    def check_checksum(self, key_id):
        self.log("check_checksum")
        cur_key = key_id
        another_checksum = self.another_checksums[cur_key]
        block_id_to_index = self.block_id_to_index_lists[cur_key]
        for _pass in range(1,len(another_checksum)):
            for _block in range(len(another_checksum[_pass])):
                if self.checksum_tables[cur_key][_pass][_block] != self.another_checksums[cur_key][_pass][_block]:
                    self.log('two checksums are different'+str([cur_key,_pass,_block]))
                    block_size = len(block_id_to_index[_pass][_block])
                    self.interactive_binary_search(cur_key, _pass, _block, 0, block_size)
                    return False

        for i in range(40):
            self.valid_keys.append( (self.bits[key_id]>>(i*self.keylen)) & ((1<<self.keylen)-1) )

        if self.role == 0: self.t2[key_id] = self.timeline.now()
        self.performance_measure()

        process = Process(self.another, "key_is_valid", [key_id])
        self.send_by_cc(process)

        return True

    def end_cascade(self):
        """
        """
        self.state = 2

    def key_is_valid(self, key_id):
        for i in range(40):
            self.valid_keys.append( (self.bits[key_id]>>(i*self.keylen)) & ((1<<self.keylen)-1) )
        self.t2[key_id] = self.timeline.now()
        self.performance_measure()

    def send_for_binary(self, key_id, pass_id, block_id, start, end):
        """
        Sender sends checksum of block[start:end] in pass_id pass
        """
        self.log('send_for_binary, params' + str([pass_id, block_id, start, end]))
        checksum = 0
        block_id_to_index = self.block_id_to_index_lists[key_id]
        for pos in block_id_to_index[pass_id][block_id][start:end]:
            checksum ^= ((self.bits[key_id] >> pos) & 1)

        process = Process(self.another, "receive_for_binary", [key_id, pass_id, block_id, start, end, checksum])
        self.send_by_cc(process)

    def receive_for_binary(self, key_id, pass_id, block_id, start, end, checksum):
        """
        Receiver receive checksum of block[start:end] in pass_id pass
        If checksums are different, continue interactive_binary_search
        """
        self.log('receive_for_binary, params= ' + str([key_id, pass_id, block_id, start, end, checksum]))

        def flip_bit_at_pos(val, pos):
            """
            flip one bit of integer val at pos (right bit with lower position)
            """
            self.disclosed_bits_counter += 1
            self.another.disclosed_bits_counter += 1
            return (((val >> pos) ^ 1) << pos) + (((1 << pos) - 1) & val)

        _checksum = 0
        block_id_to_index = self.block_id_to_index_lists[key_id]
        index_to_block_id = self.index_to_block_id_lists[key_id]
        checksum_table = self.checksum_tables[key_id]
        key = self.bits[key_id]
        for pos in block_id_to_index[pass_id][block_id][start:end]:
            _checksum ^= ((key >> pos) & 1)

        if checksum != _checksum:
            if end - start == 1:
                pos = block_id_to_index[pass_id][block_id][start]
                self.bits[key_id] = flip_bit_at_pos(key, pos)
                self.log("::: flip at " + str(pos))
                # update checksum_table
                for _pass in range(1, len(checksum_table)):
                    _block = index_to_block_id[_pass][pos]
                    checksum_table[_pass][_block] ^= 1

                if not self.check_checksum(key_id): return

            else:
                self.interactive_binary_search(key_id, pass_id, block_id, start, end)

    def interactive_binary_search(self, key_id, pass_id, block_id, start, end):
        """
        Split block[start:end] to block[start:(start+end)/2], block[(start+end)/2,end]
        Ask checksums of subblock from sender
        """
        self.log('interactive_binary_search, params= ' + str([key_id, pass_id, block_id, start, end]))
        # first half checksum
        process = Process(self.another, "send_for_binary", [key_id, pass_id, block_id, start, int((end + start) / 2)])
        self.send_by_cc(process)
        # last half checksum
        process = Process(self.another, "send_for_binary", [key_id, pass_id, block_id, int((end + start) / 2), end])
        self.send_by_cc(process)

    def send_by_cc(self, process):
        """
        Schedule an event after delay time
        """

        if self.timeline.now() > self.end_time and self.state!=2:
            self.end_cascade()
            self.another.end_cascade()
            return

        future_time = self.timeline.now() + self.cchanel.delay
        event = Event(future_time, process)
        self.timeline.schedule(event)

    def performance_measure(self):
        if self.role == 0:
            self.latency = 0
            counter = 0
            for i in range(len(self.t1)):
                if self.t2[i] != -1:
                    self.latency+=self.t2[i]-self.t1[i]
                    counter+=1
            if counter>0: self.latency /= counter
            else: self.latency = None
            self.another.latency = self.latency

        if self.timeline.now() - self.start_time:
            self.throughput = 1e12 * len(self.valid_keys) * self.keylen / (self.timeline.now() - self.start_time)
            self.privacy_throughput = 1e12 * (len(self.valid_keys) * (self.keylen) - int(len(self.valid_keys)/40) * self.secure_params - self.disclosed_bits_counter) / (self.timeline.now() - self.start_time)

        counter = 0
        for j in range(min(len(self.valid_keys), len(self.another.valid_keys))):
            i = 0
            val = self.valid_keys[j] ^ self.another.valid_keys[j]
            while val>>i:
                if (val>>i)&1 == 1:
                    counter += 1
                i+=1

        if len(self.valid_keys) > 1:
            self.error_bit_rate = counter / (self.keylen * (len(self.valid_keys)))
        else:
            self.error_bit_rate = 0
        self.time_cost = self.end_time - self.start_time

    def init():
        pass


if __name__ == "__main__":
    from timeline import Timeline

    '''
    from BB84 import BB84

    random.seed(1)
    tl = Timeline()  # stop time is 10 seconds

    qc = topology.QuantumChannel("qc", tl, distance=10)
    cc = topology.ClassicalChannel("cc", tl, distance=10)
    cc.delay = 5*10**9 # 5ms delay

    # Alice
    ls = topology.LightSource("alice.lightsource", tl,
                              frequency=80000000, mean_photon_num=0.1, direct_receiver=qc)
    components = {"lightsource": ls, "cchannel": cc, "qchannel": qc}

    alice = topology.Node("alice", tl, components=components)
    qc.set_sender(ls)
    cc.add_end(alice)

    # Bob
    detectors = [{"dark_count": 1, "time_resolution": 1},
                 {"dark_count": 1, "time_resolution": 1}]
    splitter = {}
    qsd = topology.QSDetector("bob.qsdetector", tl, detectors=detectors, splitter=splitter)
    components = {"detector": qsd, "cchannel": cc, "qchannel": qc}

    bob = topology.Node("bob", tl, components=components)
    qc.set_receiver(qsd)
    cc.add_end(bob)

    tl.entities.append(alice)
    tl.entities.append(bob)

    # BB84
    bba = BB84("bba", tl, role=0)
    bbb = BB84("bbb", tl, role=1)
    bba.assign_node(alice)
    bbb.assign_node(bob)
    bba.another = bbb
    bbb.another = bba
    alice.protocol = bba
    bob.protocol = bbb

    # Parent
    cascade_a = Cascade("cascade_a", tl, bb84=bba, role=0)
    cascade_b = Cascade("cascade_b", tl, bb84=bbb, role=1)
    cascade_a.assign_cchannel(cc)
    cascade_b.assign_cchannel(cc)
    cascade_a.another = cascade_b
    cascade_b.another = cascade_a
    bba.add_parent(cascade_a)
    bbb.add_parent(cascade_b)

    p = Process(cascade_a, 'generate_key', [256,math.inf,60*10**12])
    tl.schedule(Event(0, p))
    tl.run()

    print("throughput: ",cascade_a.throughput*10**12, " bit/sec")
    print("error rate:", cascade_a.error_bit_rate)
    print("time cost=", cascade_a.time_cost)
    print("latency = ", cascade_a.latency/(10**12))
    print("key per second = ", (cascade_a.cur_key / cascade_a.run_time * 10**12))
    #print(cascade_a.tmp)
    #print(cascade_b.tmp)
    print(tl.now())
    '''
    class BB84(Entity):
        def __init__(self, name, timeline, **kwargs):
            Entity.__init__(self, name, timeline)
            self.keys = kwargs.get("keys")
            self.parent = None
            self.another = None

        def assign_parent(self, parent):
            self.parent = parent

        def assign_another(self, another):
            self.another = another

        def generate_key(self, keylen, key_num=math.inf, run_time=math.inf):
            self.parent.get_key_from_BB84(self.keys.pop())
            self.another.parent.get_key_from_BB84(self.another.keys.pop())

        def init():
            pass

    class CChannel(Entity):
        def log(self, info):
            print(self.timeline.now(), self.name, info)

        def __init__(self, name, timeline, **kwargs):
            Entity.__init__(self, name, timeline)
            self.delay = kwargs.get("delay")
            self.end_1 = kwargs.get("end_1")
            self.end_2 = kwargs.get("end_2")

        def init():
            pass

    def add_error(key):
        pass

    a = 1251429359572206134487023313361775985077099188278612257719341591315811285159249892989796805204078554722091135112981560561404281978885282828573479669916043148911272356583799875017815539789369776358063690797981940595724335366267849520088636018613507155845773155704732058238887985325864880716498801977023726694136647266350836645283234870541121097579449014641515113615896552061187001408739406923159836241545315908769151169281219747957019328446693170486926588146350789970536041927372343850025990041217308770534374624402597195493428854027787945656507113688822918290748085103853429078784405162176769371639616558160928541550301301330514027683224061982502325159360294325293370521075904565775176049478685640512663130796466631300752509085121611152237608661699338345364114013085955529704992854757453081867549390308669902701769738252161603030870515100855071490509129789703426368815871928691725285495683953532492828117412191982340842169944430411244042349647787719959101255796257663974330043035890952883069528380244735866280708625919448456428238481509155462080959427251566539785198400485850937291099007264439796785740037320459152439967354424929137531118293507316699681685274707557761391750016095285426088984393499459652078635445127118391620552186535844261795240686129902037407472712770645450666261672147829024833464603210903162509582470757018458398150025701165274416400857717504308098367470242716205980981534873158128033138566575695605175398067392923413454337142197749034432101756927235433882513676594514364745921296769850737070876340115895600729704679665033223421962896824367267766754438800157582280904946177081159055634497576724090802550005236638458301810151325907962092222354250837844525150697632901400476733154353896886449193251954971311260763801075891335181503940008385613249688837750623093387191059145740077060553339271992658971906345703564347943758239078696344540843677752494305617368951763658713257872279362401282272298794103673893287680976361537740533728073286566748167039274805707339065396339876769997111271415550777831162511340643007122086107785774152164837096105398638850908563097385825080966320106029528256489806623122772388487889341582551436663355972784784258500736995201733007272714735178136495674220447789219823621875615489435962115283602991140316659326702541909505937113064436065929178071538916682666851064412232255616880388938818729472363193359425808589179870564327843846138166320250689453830604326605294967028136082292395579077673413607275386931944075897164528462429023229595195528042102543153084976105982633173808511458367867052620079605396605611851630215967760982818727196804636799481459229546759069573155626200775029689945597246444759711119662635089655675467317169063141134575891616983087075028857311816940432445722307233113469362444026618557399461547028299621567186226043699629460739150126196051754613117352496615496931216722736974656159111772563590664098721608984492172149780762196213967835402912539931314586155967491945900940589547429947617824719698797019739588746333603060237575385682562434817044716978519170673714274915757285536719344220739219890441023444023107365662311

    b = 1251429359828681560343878946849322658106649332518941716942532055097170143295897681654812760004853557683628697132738338542519773170288123958613482163801283944861538806218746178058064474387295386418714933242903374742974967807013917347596896638226093807006748740733960051638799297758134902374869219899026976645541345340910379465879653458002420334877320451261674849033342223996037136813344376733047009874981499823160481829796714160846539785488212024923186455529327892644421883706718880294350755849407713001121509785623507445014607771372949778132949462090267218144436906147086587904560070127851001670906749543314460929020760768185205502801100835216265731455883405780894952834277244781883484102689684833068653329293977024216550859739757674557119926900976746003794874933289518603813581130780828454530899696858103680060457742633228844913641838466177295646671747791216072128629326232568624326674185471618511125709875617989601845218029731382680294773774360979123771407882610587002755321582046739087806412228958433009217065973483224309798484304780333992029080007414723013544714680793083531106766517092414386978860092921396943276570500214039832608985509509508351535224554592596523460094137250222786885158139616107168528104329362161304575471644792916766772228222720783403979575135180416540991821473839560397750359129871191219565538955381314382609313822610510229524544112199620286915306988036955895834034707041174930061650017554069586394988698016956428033782650505525706258650612728315602362699051993556275591910984303759530247349148261106538974101102019665888760763069682931349894893058782452037034420150913284376103160605008253652078247626132567957927624404976177794787679080293562274468568424191854567371063725314643972936101582878863741318680239374528097793682514604947190269076078421024672217691624700860175522393278220512345878978299996207681444661783051859329211135026458439730354504502823896753326517297543462236595674516868823846341061540426099505955770028292343572466625790357989293439398480625657763883004341310270026852629817433700352088992755724659680056298203645576031178930413064427580966324701165166782443990985603997701868077448507955253193084693727545871224200116283896896537158029032275514252748384299897733234317814635296218567998790046716531983416468859929888444636452006581986828885618252752364592392465522061102109222075203095612415545404811590666845865398549105746389622505016356241105815959894062567160196268102911529246648846294360981063256819437912809644933099203037586430497341622200675992998913471353154199793239741180517306832690397987672311353815895964399372829603599065003345488310670871621221844634388980107046260303180650690697675221704527552329453915231751557900703983498874221552332835628597237495223454387813808979286814859514716823683339136719282465352804058347442388914423100760767118389569880345478957066421622142767524776966011314028658867639643519067591161670707170933406276565590881364580885954819880580022286087679377356962243569047151944598397683976039618352721117209082327344938346294253653231583338930894740543277081866240108716347856597653027843687

    t = Timeline()
    bb84_1 = BB84("bb84_1", t, keys=[(1 << 140) - 1, a, (1 << 138) - 1])
    cascade_1 = Cascade("cascade_1", t, bb84=bb84_1, role=0)
    bb84_1.assign_parent(cascade_1)
    bb84_2 = BB84("bb84_2", t, keys=[0, b, 0])
    cascade_2 = Cascade("cascade_2", t, bb84=bb84_2, role=1)
    cascade_1.another = cascade_2
    cascade_2.another = cascade_1
    bb84_2.assign_parent(cascade_2)
    bb84_1.assign_another(bb84_2)
    bb84_2.assign_another(bb84_1)
    cchanel = CChannel(
        "cchannel",
        t,
        end_1=cascade_1,
        end_2=cascade_2,
        delay=5)
    cascade_1.assign_cchannel(cchanel)
    cascade_2.assign_cchannel(cchanel)
    cascade_1.logflag = True
    cascade_2.logflag = True

    random.seed(2)
    p = Process(cascade_1, 'generate_key', [256])
    t.schedule(Event(0, p))
    p = Process(bb84_1, 'generate_key', [256])
    t.schedule(Event(20, p))
    t.run()
    print(t.now())
    print(cascade_1.latency)
    print(cascade_1.t1)
    print(cascade_1.t2)
    print(cascade_1.throughput)
    print(cascade_1.privacy_throughput)

