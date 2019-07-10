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
        self.role = kwargs.get("role", None)
        self.another = None
        self.state = 0
        self.keylen = 0
        self.key = None
        self.k = 0
        self.checksum_table = [[]]
        self.another_checksum = [[]]
        self.index_to_block_id = [[]]
        self.block_id_to_index = [[]]
        self.logflag = False
        """
        state of protocol:
            0: initialization step of protocol
            1: 1st pass of protocol
        """

    def assign_cchannel(self, cchanel):
        self.cchanel = cchanel
        if cchanel.end_1.name == self.name:
            self.another = cchanel.end_2
        else:
            self.another = cchanel.end_1

    def generate_key(self, keylen):
        self.log('generate_key, keylen='+str(keylen))
        if self.role==1:
            raise Exception("Cascade protocol type is receiver (type==1); receiver cannot generate key")

        if self.state == 0:
            self.log('generate_key with state 0')
            self.keylen = keylen
            self.bb84.generate_key(10000)
        else:
            self.log('generate_key with state '+str(self.state))
            self.bb84.generate_key(self.keylen)

    def get_key_from_BB84(self, key):
        self.log('get_key_from_BB84, key= ' + str(key))
        self.key = key

        if self.state == 1:
            self.create_checksum_table()
        if self.state == 0 and self.role == 1:
            self.send_key()
        elif self.state == 1 and self.role == 0:
            self.send_checksum(self.state, 0)

    def send_key(self):
        # Schedule a receive key event
        self.log('send_key')
        process = Process(self.another, "receive_key", [self.key])
        self.send_by_cc(process)

    def receive_key(self, key):
        self.log('receive_key, key='+str(key))
        def get_diff_bit_num(key1, key2):
            key1 = bin(key1)[2:].zfill(10000)
            key2 = bin(key2)[2:].zfill(10000)
            counter = 0
            for i in range(10000):
                if key1[i] != key2[i]:
                    counter+=1
            return counter

        def get_k1(p, lower, upper):
            while lower<=upper:
                k1 = int((lower+upper)/2)
                if (k1*p-(1-(1-2*p)**k1)/2) < (-(math.log(1/2)/2)) :
                    lower = k1+1
                elif (k1*p-(1-(1-2*p)**k1)/2) > (-(math.log(1/2)/2)) :
                    upper = k1-1
                else:
                    return k1

            return lower-1

        p = get_diff_bit_num(key, self.key)/10000
        # avoid p==0, which will cause k1 to an infinite large number
        if p==0:
            p = 0.0001
        self.k = get_k1(p, 0, 10000)
        self.send_params()
        self.state = 1

    def create_checksum_table(self):
        # initialize checksum_table, index_to_block_id, and block_id_to_index after get key from bb84
        # create index_to_block_id
        self.log('create_checksum_table')
        for pass_id in range(1,self.w+1):
            index_to_block_relation = []
            block_size = self.k*(2**(pass_id-1))

            if pass_id==1:
                for i in range(self.keylen):
                    index_to_block_relation.append(int(i/self.k))
            else:
                # if block_size/2 has been greater than key length, more pass will not fix error bit
                if block_size/2 >= self.keylen:
                    break

                random.seed(pass_id)
                bit_order = list(range(self.keylen))
                random.shuffle(bit_order)
                for i in range(self.keylen):
                    index_to_block_relation.append(int(bit_order[i]/block_size))

            self.index_to_block_id.append(index_to_block_relation)

        # create block_id_to_index
        for pass_id in range(1,self.w+1):
            block_to_index_relation = []
            block_size = self.k*(2**(pass_id-1))
            block_num = math.ceil(self.keylen/block_size)
            for _ in range(block_num):
                block_to_index_relation.append([None]*block_size)

            if pass_id == 1:
                for i in range(self.keylen):
                    block_to_index_relation[int(i/block_size)][i%block_size] = i
            else:
                random.seed(pass_id)
                bit_order = list(range(self.keylen))
                random.shuffle(bit_order)
                for i in range(self.keylen):
                    bit_pos = bit_order[i]
                    block_to_index_relation[int(bit_pos/block_size)][bit_pos%block_size] = i
            # pop extra element in the last block
            while block_to_index_relation[-1][-1] is None:
                block_to_index_relation[-1].pop()

            self.block_id_to_index.append(block_to_index_relation)

        # create checksum_table
        for pass_id in range(1,len(self.index_to_block_id)):
            block_size = self.k*(2**(pass_id-1))
            block_num = math.ceil(self.keylen/block_size)
            self.checksum_table.append([0]*block_num)
            for i in range(self.keylen):
                block_id = self.index_to_block_id[pass_id][i]
                self.checksum_table[pass_id][block_id] ^= ((self.key>>i) & 1)

    def send_params(self):
        self.log('send_params')
        # Schedule a receive paramters event
        process = Process(self.another, "receive_params", [self.k, self.keylen])
        self.send_by_cc(process)

    def receive_params(self, k, keylen):
        self.log('receive_params with k0= ' + str([k, keylen]))
        if self.role==0:
            raise Exception("Cascade protocol type is sender (type==0); sender cannot receive parameters from receiver")

        self.k = k
        self.keylen = keylen
        self.state = 1

        # Schedule a key generation event for Cascade sender
        process = Process(self.another, "generate_key", [self.keylen])
        self.send_by_cc(process)

    def send_checksum(self, pass_id, block_id):
        self.log('send_checksum params= '+str([pass_id, block_id]))
        if pass_id > self.state:
            self.state+=1
        if self.state>=len(self.checksum_table):
            return

        process = Process(self.another, "receive_checksum", [pass_id, block_id, self.checksum_table[pass_id][block_id]])
        self.send_by_cc(process)

    def receive_checksum(self, pass_id, block_id, checksum):
        self.log('receive_checksum params= '+str([pass_id, block_id, checksum]))
        if pass_id == len(self.another_checksum):
            self.another_checksum.append([])
        self.another_checksum[pass_id].append(checksum)

        if len(self.another_checksum[pass_id]) != block_id+1:
            raise Exception(self.name + ".receive_checksum does not receive checksum in order")

        if self.checksum_table[pass_id][block_id] == checksum:
            self.log('two checksums are same')
            process = None
            if block_id+1 < len(self.checksum_table[pass_id]):
                process = Process(self.another, "send_checksum", [pass_id, block_id+1])
            elif pass_id+1 < len(self.checksum_table):
                process = Process(self.another, "send_checksum", [pass_id+1, 0])
                self.state+=1
            if not process is None:
                self.send_by_cc(process)
        else:
            self.log('two checksums are different')
            block_size = len(self.block_id_to_index[pass_id][block_id])
            self.interactive_binary_search(pass_id, block_id, 0, block_size)

    def send_for_binary(self, pass_id, block_id, start, end):
        self.log('send_for_binary, params' + str([pass_id, block_id, start, end]))
        checksum = 0
        for pos in self.block_id_to_index[pass_id][block_id][start:end]:
            checksum ^= ((self.key>>pos) & 1)

        process = Process(self.another, "receive_for_binary", [pass_id, block_id, start, end, checksum])
        self.send_by_cc(process)

    def receive_for_binary(self, pass_id, block_id, start, end, checksum):
        self.log('receive_for_binary, params= '+str([pass_id, block_id, start, end, checksum]))
        def flip_bit_at_pos(val, pos):
            """
            flip one bit of integer val at pos (right bit with lower position)
            """
            return (((val>>pos)^1)<<pos) + (((1<<pos)-1) & val)

        _checksum = 0
        for pos in self.block_id_to_index[pass_id][block_id][start:end]:
            _checksum ^= ((self.key>>pos) & 1)

        if checksum != _checksum:
            if end-start==1:
                pos = self.block_id_to_index[pass_id][block_id][start]
                self.key = flip_bit_at_pos(self.key, pos)
                self.log("::: flip at "+str(pos))
                # update checksum_table
                for _pass in range(1, len(self.checksum_table)):
                    _block = self.index_to_block_id[_pass][pos]
                    self.checksum_table[_pass][_block] ^= 1

                if self.state == 1:
                    # for 1st pass, just continue send checksums
                    process = None
                    if block_id+1 < len(self.checksum_table[pass_id]):
                        process = Process(self.another, "send_checksum", [pass_id, block_id+1])
                    elif pass_id+1 < len(self.checksum_table):
                        process = Process(self.another, "send_checksum", [pass_id+1, 0])
                        self.state+=1
                    if not process is None:
                        self.send_by_cc(process)
                else:
                    # if all of error in previous pass are fixed, continue send checksum
                    if not self.correct_error_in_previous(pass_id, block_id, pos):
                        process = None
                        if block_id+1 < len(self.checksum_table[pass_id]):
                            process = Process(self.another, "send_checksum", [pass_id, block_id+1])
                        elif pass_id+1 < len(self.checksum_table):
                            process = Process(self.another, "send_checksum", [pass_id+1, 0])
                            self.state+=1
                        if not process is None:
                            self.send_by_cc(process)
            else:
                self.interactive_binary_search(pass_id, block_id, start, end)

    def interactive_binary_search(self, pass_id, block_id, start, end):
        self.log('interactive_binary_search, params= ' + str([pass_id, block_id, start, end]))
        # first half checksum
        process = Process(self.another, "send_for_binary", [pass_id, block_id, start, int((end+start)/2)])
        self.send_by_cc(process)
        # last half checksum
        process = Process(self.another, "send_for_binary", [pass_id, block_id, int((end+start)/2), end])
        self.send_by_cc(process)

    def correct_error_in_previous(self, pass_id, block_id, pos):
        # for i-th pass, correct error in blocks of previous pass
        self.log('correct_error_in_previous, params= ' + str([pass_id, block_id, pos]))
        for _pass in range(1, pass_id):
            _block = self.index_to_block_id[_pass][pos]
            if self.checksum_table[_pass][_block] != self.another_checksum[_pass][_block]:
                block_size = len(self.block_id_to_index[pass_id][block_id])
                self.interactive_binary_search(pass_id, block_id, 0, block_size)
                return True
        return False

    def send_by_cc(self, process):
        """
        Schedule an event after delay time
        """
        future_time = self.timeline.now() + self.cchanel.delay
        event = Event(future_time, process)
        self.timeline.schedule(event)

    def init():
        pass


if __name__ == "__main__":
    from timeline import Timeline

    class BB84(Entity):
        def log(self, info):
            print(self.timeline.now(), self.name, info)

        def __init__(self, name, timeline, **kwargs):
            Entity.__init__(self, name, timeline)
            self.keys = kwargs.get("keys")
            self.parent = None
            self.another = None


        def assign_parent(self, parent):
            self.parent = parent

        def assign_another(self,another):
            self.another = another

        def generate_key(self, keylen):
            self.log("generate_key, params = "+str(keylen))
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

    t = Timeline()
    bb84_1 = BB84("bb84_1", t, keys=[(1<<75)+1, (1<<100)-1])
    cascade_1 = Cascade("cascade_1", t, bb84=bb84_1, role=0)
    bb84_1.assign_parent(cascade_1)
    bb84_2 = BB84("bb84_2", t, keys=[0,0])
    cascade_2 = Cascade("cascade_2", t, bb84=bb84_2, role=1)
    bb84_2.assign_parent(cascade_2)
    bb84_1.assign_another(bb84_2)
    bb84_2.assign_another(bb84_1)
    cchanel = CChannel("cchannel", t, end_1=cascade_1, end_2=cascade_2, delay=5)
    cascade_1.assign_cchannel(cchanel)
    cascade_2.assign_cchannel(cchanel)
    cascade_1.logflag = True
    cascade_2.logflag = True

    p = Process(cascade_1, 'generate_key', [200])
    t.schedule(Event(0,p))
    t.run()
    counter = 0
    for i in range(200):
        if (cascade_2.key>>i & 1) != (cascade_1.key>>i & 1):
            counter+=1
    print("diff bit number:",counter)
    print("key1=",cascade_1.key)
    print("key2=",cascade_2.key)

