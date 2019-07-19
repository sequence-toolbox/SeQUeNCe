from entity import Entity
from process import Process
from event import Event
from numpy import random
import math


class Cascade(Entity):
    def log(self, info):
        if self.logflag:
            print(self.timeline.now(), self.name, self.state, info)

    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.w = kwargs.get("w", 4)
        self.bb84 = kwargs.get("bb84", None)
        # for sender role==0; for receiver role==1
        self.role = kwargs.get("role", None)
        self.another = None
        self.state = 0
        self.keylen = None
        self.key_num = None
        self.run_time = None
        self.bits = []
        self.valid_keys = []
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
        self.throughput = None # bit/(timeline time unit)
        self.error_bit_rate = None
        self.latency = None
        """
        state of protocol:
            0: initialization step of protocol
            1: generating block
            2: end
        """

    def assign_cchannel(self, cchanel):
        self.cchanel = cchanel

    def generate_key(self, keylen, key_num=math.inf, run_time=math.inf):
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
            self.key_num = key_num
            self.run_time = run_time
            self.bb84.generate_key(10000, key_num = 1)
        else:
            self.start_time = self.timeline.now()
            self.end_time = self.start_time + self.run_time
            self.log('generate_key with state ' + str(self.state))
            self.bb84.generate_key(10240, self.key_num, self.run_time)

    def get_key_from_BB84(self, key):
        """
        Function called by BB84 when it creates a key
        """
        self.log('get_key_from_BB84, key= ' + str(key))
        self.bits.append(key)

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
                if (val>>i)&1 == 1:
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
                for i in range(self.keylen):
                    index_to_block_relation.append(int(i / block_size))
            else:
                # if block_size/2 has been greater than key length, more pass
                # will not fix error bit
                if block_size / 2 >= self.keylen:
                    break

                random.seed(pass_id)
                bit_order = list(range(self.keylen))
                random.shuffle(bit_order)
                for i in range(self.keylen):
                    index_to_block_relation.append(int(bit_order[i] / block_size))

            index_to_block_id.append(index_to_block_relation)
        self.index_to_block_id_lists.append(index_to_block_id)

        # create block_id_to_index
        block_id_to_index = [[]]
        for pass_id in range(1, self.w + 1):
            block_to_index_relation = []
            block_size = self.k1 * (2**(pass_id - 1))
            block_num = math.ceil(self.keylen / block_size)
            for _ in range(block_num):
                block_to_index_relation.append([None] * block_size)

            if pass_id == 1:
                for i in range(self.keylen):
                    block_to_index_relation[int(i / block_size)][i % block_size] = i
            else:
                random.seed(pass_id)
                bit_order = list(range(self.keylen))
                random.shuffle(bit_order)
                for i in range(self.keylen):
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
            block_num = math.ceil(self.keylen / block_size)
            checksum_table.append([0] * block_num)
            for i in range(self.keylen):
                block_id = index_to_block_id[pass_id][i]
                checksum_table[pass_id][block_id] ^= ((self.bits[-1] >> i) & 1)
        self.checksum_tables.append(checksum_table)

    def send_params(self):
        """
        Schedule a receive paramters event
        """
        self.log('send_params'+str([self.k1, self.keylen, self.key_num, self.run_time]))
        process = Process(self.another, "receive_params", [self.k1, self.keylen, self.key_num, self.run_time])
        self.send_by_cc(process)

    def receive_params(self, k, keylen, key_num, run_time):
        """
        Receiver receive k, keylen from sender
        """
        self.log('receive_params with params= ' + str([k, keylen]))
        if self.role == 0:
            raise Exception(
                "Cascade protocol type is sender (type==0); sender cannot receive parameters from receiver")

        self.k1 = k
        self.keylen = keylen
        self.key_num = key_num
        self.run_time = run_time
        self.start_time = self.timeline.now()
        self.end_time = self.start_time+self.run_time
        self.state = 1

        # Schedule a key generation event for Cascade sender
        process = Process(self.another, "generate_key", [self.keylen, self.key_num, self.run_time])
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
            self.valid_keys.append( (self.bits[key_id]>>(i*256)) & ((1<<256)-1) )

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
            self.valid_keys.append( (self.bits[key_id]>>(i*256)) & ((1<<256)-1) )
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

                    if not self.check_checksum(key_id): break
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
        '''
        if not process.activation in self.tmp:
            self.tmp[process.activation] = 0
        self.tmp[process.activation]+=1
        '''

    def performance_measure(self):
        if self.latency is None:
            self.latency = self.timeline.now() - self.start_time

        if self.timeline.now() - self.start_time:
            self.throughput = 1e12 * len(self.valid_keys) * self.keylen / (self.timeline.now() - self.start_time)
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
    import topology
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
