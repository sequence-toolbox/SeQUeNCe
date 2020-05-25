import math

from numpy import random

from ..message import Message
from ..protocol import *
from ...kernel.event import Event
from ...kernel.process import Process


def pair_cascade_protocols(sender: "Cascade", receiver: "BB84") -> None:
    sender.another = receiver
    receiver.another = sender
    sender.role = 0
    receiver.role = 1

    if sender.lower_protocols == []:
        sender.lower_protocols.append(sender.own.sifting_protocol)
        sender.own.sifting_protocol.upper_protocols.append(sender)

    if receiver.lower_protocols == []:
        receiver.lower_protocols.append(receiver.own.sifting_protocol)
        receiver.own.sifting_protocol.upper_protocols.append(receiver)


class CascadeMessage(Message):
    def __init__(self, msg_type: str, receiver: str, **kwargs):
        super().__init__(msg_type, receiver)
        self.owner_type = Cascade
        if msg_type == "key":
            self.key = kwargs["key"]
        elif msg_type == "params":
            self.k = kwargs["k"]
            self.keylen = kwargs["keylen"]
            self.frame_num = kwargs["frame_num"]
            self.run_time = kwargs["run_time"]
        elif msg_type == "checksums":
            self.key_id = kwargs["key_id"]
            self.checksums = kwargs["checksums"]
        elif msg_type == "start_for_binary":
            self.key_id = kwargs["key_id"]
            self.pass_id = kwargs["pass_id"]
            self.block_id = kwargs["block_id"]
            self.start = kwargs["start"]
            self.end = kwargs["end"]
        elif msg_type == "receive_for_binary":
            self.key_id = kwargs["key_id"]
            self.pass_id = kwargs["pass_id"]
            self.block_id = kwargs["block_id"]
            self.start = kwargs["start"]
            self.end = kwargs["end"]
            self.checksum = kwargs["checksum"]
        elif msg_type == "generate_key":
            self.keylen = kwargs["keylen"]
            self.frame_num = kwargs["frame_num"]
            self.run_time = kwargs["run_time"]
        elif msg_type == "key_is_valid":
            self.key_id = kwargs["key_id"]
        else:
            raise Exception("Invalid cascade message type" + msg_type)


class Cascade(StackProtocol):
    def __init__(self, own: "QKDNode", name: str, **kwargs):
        super().__init__(own, name)

        self.w = kwargs.get("w", 4)
        self.role = kwargs.get("role", 1)  # 0 for sender, 1 for receiver
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
        self.time_cost = None
        self.setup_time = None
        self.start_time = None
        self.end_time = math.inf

        # used for debugging purposes (prints out cascade process)
        self.logflag = False

        # metrics
        self.throughput = None  # bits/sec
        self.error_bit_rate = None
        self.latency = None  # the average latency
        self.disclosed_bits_counter = 0
        self.privacy_throughput = None

        """
        state of protocol:
            0: initialization step of protocol
            1: generating block
            2: end
        """

    def init(self) -> None:
        pass

    def log(self, info) -> None:
        if self.logflag:
            print(self.own.timeline.now(), self.name, self.state, info)

    def push(self, keylen: int, frame_num=math.inf, run_time=math.inf) -> None:
        self.generate_key(keylen, frame_num, run_time)

    def pop(self, msg: int) -> None:
        """
        Function called by BB84 when it creates a key
        """
        self.log('get_key_from_BB84, key= ' + str(msg))
        self.bits.append(msg)
        self.t1.append(self.own.timeline.now())
        self.t2.append(-1)

        if self.state == 1:
            self.create_checksum_table()
        
        if self.state == 0 and self.role == 1:
            message = CascadeMessage("key", self.another.name, key=self.bits[0])
            self.send_by_cc(message)

        elif self.state == 1 and self.role == 0:
            message = CascadeMessage("checksums", self.another.name,
                                     key_id=len(self.checksum_tables)-1, checksums=self.checksum_tables[-1])
            self.send_by_cc(message)

    def received_message(self, src: str, msg: "Message") -> None:
        if msg.msg_type == "key":
            """
            Sender receive key from receiver to measure the error rate of key
            Calculate self.k by error rate
            Send self.k and keylen to receiver
            """
            key = msg.key

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
            self.state = 1

            message = CascadeMessage("params", self.another.name,
                                     k=self.k1, keylen=self.keylen, frame_num=self.frame_num,
                                     run_time=self.run_time)
            self.send_by_cc(message)

        elif msg.msg_type == "params":
            """
            Receiver receive k, keylen from sender
            """ 
            self.k1 = msg.k
            self.keylen = msg.keylen
            self.frame_num = msg.frame_num
            self.run_time = msg.run_time
            self.start_time = self.own.timeline.now()
            self.end_time = self.start_time + self.run_time
            self.state = 1

            self.log('receive_params with params= ' + str([self.k1, self.keylen]))
            if self.role == 0:
                raise Exception("Cascade protocol sender '{}' got params message".format(self.name))

            # Schedule a key generation event for Cascade sender
            message = CascadeMessage("generate_key", self.another.name,
                                     keylen=self.keylen, frame_num=self.frame_num, run_time=self.run_time)
            self.send_by_cc(message)

        elif msg.msg_type == "checksums":
            key_id = msg.key_id
            checksums = msg.checksums

            self.log("receive_checksums")

            while len(self.another_checksums) <= key_id:
                self.another_checksums.append(None)
            self.another_checksums[key_id] = checksums
            self.check_checksum(key_id)

        elif msg.msg_type == "send_for_binary":
            """
            Sender sends checksum of block[start:end] in pass_id pass
            """
            key_id = msg.key_id
            pass_id = msg.pass_id
            block_id = msg.block_id
            start = msg.start
            end = msg.end

            self.log('send_for_binary, params' + str([pass_id, block_id, start, end]))

            checksum = 0
            block_id_to_index = self.block_id_to_index_lists[key_id]
            for pos in block_id_to_index[pass_id][block_id][start:end]:
                checksum ^= ((self.bits[key_id] >> pos) & 1)

            message = CascadeMessage("receive_for_binary", self.another.name,
                                     key_id=key_id, pass_id=pass_id, block_id=block_id,
                                     start=start, end=end, checksum=checksum)
            self.send_by_cc(message)

        elif msg.msg_type == "receive_for_binary":
            """
            Receiver receive checksum of block[start:end] in pass_id pass
            If checksums are different, continue interactive_binary_search
            """
            key_id = msg.key_id
            pass_id = msg.pass_id
            block_id = msg.block_id
            start = msg.start
            end = msg.end
            checksum = msg.checksum

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

        elif msg.msg_type == "generate_key":
            keylen = msg.keylen
            frame_num = msg.frame_num
            run_time = msg.run_time
            self.generate_key(keylen, frame_num, run_time)

        elif msg.msg_type == "key_is_valid":
            key_id = msg.key_id
            self.key_is_valid(key_id)

    def generate_key(self, keylen: int, frame_num=math.inf, run_time=math.inf) -> None:
        """
        Generate 10000 bits key to measure error rate at 0 pass
        Generate keylen bits key at 1st pass
        """
        self.log('generate_key, keylen=' + str(keylen))
        if self.role == 1:
            raise Exception(
                "Cascase.generate_key() called on receiver '{}'".format(self.name))

        if self.state == 0:
            self.log('generate_key with state 0')
            self.setup_time = self.own.timeline.now()
            self.keylen = keylen
            self.frame_num = frame_num
            self.run_time = run_time
            self._push(length=10000, key_num=1)

        else:
            self.start_time = self.own.timeline.now()
            self.end_time = self.start_time + self.run_time
            self.log('generate_key with state ' + str(self.state))
            self._push(length=keylen, key_num=frame_num, run_time=run_time)

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

        # for i in range(self.frame_num): 
        #     self.valid_keys.append( (self.bits[key_id]>>(i*self.keylen)) & ((1<<self.keylen)-1) )
        self.valid_keys.append(self.bits[key_id] & ((1 << self.keylen) - 1))

        if self.role == 0: self.t2[key_id] = self.own.timeline.now()
        self.performance_measure()

        message = CascadeMessage("key_is_valid", self.another.name, key_id=key_id)
        self.send_by_cc(message)

        return True

    def end_cascade(self):
        """
        end cascade protocol
        """
        self.state = 2

    def key_is_valid(self, key_id):
        # for i in range(self.frame_num):
        #     self.valid_keys.append( (self.bits[key_id]>>(i*self.keylen)) & ((1<<self.keylen)-1) )
        self.valid_keys.append(self.bits[key_id] & ((1 << self.keylen) - 1))
        self.t2[key_id] = self.own.timeline.now()
        self.performance_measure()
    
    def interactive_binary_search(self, key_id, pass_id, block_id, start, end):
        """
        Split block[start:end] to block[start:(start+end)/2], block[(start+end)/2,end]
        Ask checksums of subblock from sender
        """
        self.log('interactive_binary_search, params= ' + str([key_id, pass_id, block_id, start, end]))

        # first half checksum
        message = CascadeMessage("send_for_binary", self.another.name,
                                 key_id=key_id, pass_id=pass_id, block_id=block_id,
                                 start=start, end=int((end+start) / 2))
        self.send_by_cc(message)

        # last half checksum
        message = CascadeMessage("send_for_binary", self.another.name,
                                 key_id=key_id, pass_id=pass_id, block_id=block_id,
                                 start=int((end+start) / 2), end=end)
        self.send_by_cc(message)

    def send_by_cc(self, message):
        if self.own.timeline.now() > self.end_time and self.state != 2:
            self.end_cascade()
            self.another.end_cascade()
            return

        self.own.send_message(self.another.own.name, message)

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

        if self.own.timeline.now() - self.start_time:
            self.throughput = 1e12 * len(self.valid_keys) * self.keylen / (self.own.timeline.now() - self.start_time)
            self.privacy_throughput = 1e12 * (len(self.valid_keys) * (self.keylen) - int(len(self.valid_keys)/40) * self.secure_params - self.disclosed_bits_counter) / (self.own.timeline.now() - self.start_time)

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


