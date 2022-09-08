"""Definition of cascade protocol implementation.

This module provides an implementation of the cascade protocol for error correction.
The protocol must be provided with a lower-layer protocol for key generation, such as BB84.
Also included in this module are a function to pair protocol instances (required before the start of transmission) and the message type used by the protocol.
"""

import math
from enum import Enum, auto
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..topology.node import QKDNode

from numpy import random

from ..message import Message
from ..protocol import StackProtocol
from ..utils import log

def pair_cascade_protocols(sender: "Cascade", receiver: "Cascade") -> None:
    """Method to pair cascade protocol instance.

    Args:
        sender (Cascade): cascade protocol on node sending qubits (Alice).
        receiver (Cascade): cascade protocol on node receiving qubits (Bob).
    """

    sender.another = receiver
    receiver.another = sender
    sender.role = 0
    receiver.role = 1


class CascadeMsgType(Enum):
    """Defines possible message types for cascade."""

    KEY = auto()
    PARAMS = auto()
    CHECKSUMS = auto()
    SEND_FOR_BINARY = auto()
    RECEIVE_FOR_BINARY = auto()
    GENERATE_KEY = auto()
    KEY_IS_VALID = auto()


class CascadeMessage(Message):
    """Message used by cascade protocols.

    This message contains all information passed between cascade protocol instances.
    Messages of different types contain different information.

    Attributes:
        msg_type (CascadeMsgType): defines the message type.
        receiver (str): name of destination protocol instance.
        key (int): initial key sent to establish parameters (if `msg_type == KEY`).
        k (int): cascade parameter (if `msg_type == PARAMS`).
        keylen (int): length of keys to request from BB84 (if `msg_type == PARAMS or GENERATE_KEY`).
        frame_num (int): number of keys to request (if `msg_type == PARAMS or GENERATE_KEY`).
        run_time (int): runtime for BB84 (if `msg_type == PARAMS or GENERATE_KEY`).
        key_id (int): key being processed  (if `msg_type == CHECKSUMS or SEND_FOR_BINARY or RECEIVE_FOR_BINARY or KEY_IS_VALID`).
        checksums (int): checksum results (if `msg_type == CHECKSUMS`).
        pass_id (int): pass number (if `msg_type == SEND_FOR_BINARY or RECEIVE_FOR_BINARY`).
        block_id (int): block number (if `msg_type == SEND_FOR_BINARY or RECEIVE_FOR_BINARY`).
        start (int): starting position in key (if `msg_type == SEND_FOR_BINARY or RECEIVE_FOR_BINARY`).
        end (int): ending position in key (if `msg_type == SEND_FOR_BINARY or RECEIVE_FOR_BINARY`).
        checksum (int): checksum result (if `msg_type == RECEIVE_FOR_BINARY`).
    """

    def __init__(self, msg_type: Enum, receiver: str, **kwargs):
        super().__init__(msg_type, receiver)
        self.protocol_type = Cascade
        if msg_type is CascadeMsgType.KEY:
            self.key = kwargs["key"]
        elif msg_type is CascadeMsgType.PARAMS:
            self.k = kwargs["k"]
            self.keylen = kwargs["keylen"]
            self.frame_num = kwargs["frame_num"]
            self.run_time = kwargs["run_time"]
        elif msg_type is CascadeMsgType.CHECKSUMS:
            self.key_id = kwargs["key_id"]
            self.checksums = kwargs["checksums"]
        elif msg_type is CascadeMsgType.SEND_FOR_BINARY:
            self.key_id = kwargs["key_id"]
            self.pass_id = kwargs["pass_id"]
            self.block_id = kwargs["block_id"]
            self.start = kwargs["start"]
            self.end = kwargs["end"]
        elif msg_type is CascadeMsgType.RECEIVE_FOR_BINARY:
            self.key_id = kwargs["key_id"]
            self.pass_id = kwargs["pass_id"]
            self.block_id = kwargs["block_id"]
            self.start = kwargs["start"]
            self.end = kwargs["end"]
            self.checksum = kwargs["checksum"]
        elif msg_type is CascadeMsgType.GENERATE_KEY:
            self.keylen = kwargs["keylen"]
            self.frame_num = kwargs["frame_num"]
            self.run_time = kwargs["run_time"]
        elif msg_type == CascadeMsgType.KEY_IS_VALID:
            self.key_id = kwargs["key_id"]
        else:
            raise Exception("Invalid cascade message type {}".format(msg_type))


class Cascade(StackProtocol):
    """Implementation of cascade error correction protocol.

    The cascade protocol uses checksums to determine if there are errors in a generated key and pinpoint the errors.
    The protocol exists in 3 states:

    0. initialization step of protocol
    1. generating block
    2. end

    Attributes:
        own (QuantumRouter): node that protocol instance is attached to.
        name (str): label for protocol instance.
        w (int): cascade parameter.
        role (int): differentiates "alice" and "bob" protocols.
        secure_params (int): security parameter.
        another (Cascade): reference to paired cascade protocol.
        state (int): current state of protocol.
        keylen (int): lenght of keys to generate.
        frame_len (int): length of frame to use to generate keys.
        frame_num (int): frame number.
        run_time (int): time to run protocol.
        bits (List[int]): bits to operate on (received from BB84).
        t1 (int): cascade parameter.
        t2 (int): cascade parameter.
        k1 (int): cascade parameter.
        checksum_tables (List[List[int]]): lists of generated checksums.
        another_checksums (List[List[int]]): checksums of paired protocol.
        index_to_block_id_lists (List): store block ids.
        block_id_to_index_lists (List): store index ids.
        time_cost (int): time penalty for key generation.
        setup_time (int): time of cascade protocol setup.
        start_time (int): time to start generating corrected keys.
        end_time (int): time to stop generating keys.
        valid_keys (List[int]): list of keys generated.
        throughput (float): protocol throughput in bits/s.
        error_bit_rate (float): rate of errors in finished keys.
        latency (int): average latency of generated keys.
        disclosed_bits_counter (int): counts revealed bits.
        privacy_throughput (int): throughput of not revealed bits.
    """

    def __init__(self, own: "QKDNode", name: str, w=4, role=-1, secure_params=100):
        """Constructor for cascade class.

        Args:
            own (QKDNode): node protocol instance is attached to.
            name (str): name of protocol instance.

        Keyword Args:
            w (int): parameter for cascade protocol (default 4).
            role (int): 0/1 role for protocol, differentiates Alice/Bob instances (default -1).
            secure_params (int): security parameter (default 100).
        """

        super().__init__(own, name)

        self.w = w
        self.role = role  # 0 for sender, 1 for receiver
        self.secure_params = secure_params

        self.another = None
        self.state = 0

        self.keylen = None
        self.frame_len = 10240
        self.frame_num = None
        self.run_time = None
        self.bits = []
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

        # metrics
        self.valid_keys = []
        self.throughput = None  # bits/sec
        self.error_bit_rate = None
        self.latency = None  # the average latency
        self.disclosed_bits_counter = 0
        self.privacy_throughput = None

    def push(self, keylen: int, frame_num=math.inf, run_time=math.inf) -> None:
        """Method to receive key generation events.

        Defers to `generate_key` method.
        """

        self.generate_key(keylen, frame_num, run_time)

    def pop(self, info: int) -> None:
        """Function called by BB84 when it creates a key.

        Args:
            info (int): key received.
        """

        log.logger.debug(self.name + ' state={} get_key_from_BB84, key={}'.format(self.state, info))
        self.bits.append(info)
        self.t1.append(self.own.timeline.now())
        self.t2.append(-1)

        if self.state == 1:
            self.create_checksum_table()
        
        if self.state == 0 and self.role == 1:
            message = CascadeMessage(CascadeMsgType.KEY, self.another.name, key=self.bits[0])
            self.send_by_cc(message)

        elif self.state == 1 and self.role == 0:
            message = CascadeMessage(CascadeMsgType.CHECKSUMS, self.another.name,
                                     key_id=len(self.checksum_tables)-1, checksums=self.checksum_tables[-1])
            self.send_by_cc(message)

    def received_message(self, src: str, msg: "Message") -> None:
        """Method to receive messages from other protocol instance.

        Different messages will cause different actions.

        Args:
            src (str): name of node that sent the message.
            msg (Message): message received.
        """

        if msg.msg_type is CascadeMsgType.KEY:
            """
            Sender receive key from receiver to measure the error rate of key
            Calculate self.k by error rate
            Send self.k and keylen to receiver
            """
            key = msg.key

            log.logger.debug(self.name + ' state={} receive_key, key={}'.format(self.state, key))

            @lru_cache(maxsize=128)
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

            @lru_cache(maxsize=128)
            def get_diff_bit_num(key1, key2):
                val = key1 ^ key2
                counter = 0
                i = 0
                while val >> i:
                    if (val >> i) & 1:
                        counter += 1
                    i += 1
                return counter

            p = get_diff_bit_num(key, self.bits[0]) / 10000
            # avoid p==0, which will cause k1 to an infinite large number
            if p == 0:
                p = 0.0001
            self.k1 = get_k1(p, 0, 10000)
            self.state = 1

            message = CascadeMessage(CascadeMsgType.PARAMS, self.another.name,
                                     k=self.k1, keylen=self.keylen, frame_num=self.frame_num,
                                     run_time=self.run_time)
            self.send_by_cc(message)

        elif msg.msg_type is CascadeMsgType.PARAMS:
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

            log.logger.debug(self.name + ' state={} receive_params with params={}'.format(self.state, [self.k1, self.keylen, self.frame_num]))
            if self.role == 0:
                raise Exception("Cascade protocol sender '{}' got params message".format(self.name))

            # Schedule a key generation event for Cascade sender
            message = CascadeMessage(CascadeMsgType.GENERATE_KEY, self.another.name,
                                     keylen=self.keylen, frame_num=self.frame_num, run_time=self.run_time)
            self.send_by_cc(message)

        elif msg.msg_type is CascadeMsgType.CHECKSUMS:
            key_id = msg.key_id
            checksums = msg.checksums

            log.logger.debug(self.name + ' state={} receive_checksums'.format(self.state))

            while len(self.another_checksums) <= key_id:
                self.another_checksums.append(None)
            self.another_checksums[key_id] = checksums
            self.check_checksum(key_id)

        elif msg.msg_type is CascadeMsgType.SEND_FOR_BINARY:
            """
            Sender sends checksum of block[start:end] in pass_id pass
            """
            key_id = msg.key_id
            pass_id = msg.pass_id
            block_id = msg.block_id
            start = msg.start
            end = msg.end

            log.logger.debug(self.name + ' state={} send_for_binary, params={}'.format(self.state, [pass_id, block_id, start, end]))

            checksum = 0
            block_id_to_index = self.block_id_to_index_lists[key_id]
            for pos in block_id_to_index[pass_id][block_id][start:end]:
                checksum ^= ((self.bits[key_id] >> pos) & 1)

            message = CascadeMessage(CascadeMsgType.RECEIVE_FOR_BINARY, self.another.name,
                                     key_id=key_id, pass_id=pass_id, block_id=block_id,
                                     start=start, end=end, checksum=checksum)
            self.send_by_cc(message)

        elif msg.msg_type is CascadeMsgType.RECEIVE_FOR_BINARY:
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

            log.logger.debug(self.name + ' state={} receive_for_binary, params={}'.format(self.state, [key_id, pass_id, block_id, start, end, checksum]))

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
                    log.logger.debug(self.name + ' state={} ::: flip at {}'.format(self.state, pos))
                    # update checksum_table
                    for _pass in range(1, len(checksum_table)):
                        _block = index_to_block_id[_pass][pos]
                        checksum_table[_pass][_block] ^= 1

                    if not self.check_checksum(key_id):
                        return

                else:
                    self.interactive_binary_search(key_id, pass_id, block_id, start, end)

        elif msg.msg_type is CascadeMsgType.GENERATE_KEY:
            keylen = msg.keylen
            frame_num = msg.frame_num
            run_time = msg.run_time
            self.generate_key(keylen, frame_num, run_time)

        elif msg.msg_type is CascadeMsgType.KEY_IS_VALID:
            key_id = msg.key_id

            for i in range(int(self.frame_len / self.keylen)):
                self.valid_keys.append((self.bits[key_id] >> (i*self.keylen)) & ((1 << self.keylen)-1))
                if self.frame_num > 0:
                    log.logger.info(self.name + ' state={} got valid key'.format(self.state))
                    self._pop(key=self.valid_keys[-1])
                    self.frame_num -= 1

            self.t2[key_id] = self.own.timeline.now()
            self.performance_measure()

    def generate_key(self, keylen: int, frame_num=math.inf, run_time=math.inf) -> None:
        """Method to start key generation.

        The process for generating keys is:

        1. Generate 10000 bits key to measure error rate at 0 pass
        2. Generate keylen bits key at 1st pass

        Args:
            keylen (int): length of key to generate.
            frame_num (int): number of keys to generate (default inf).
            run_time (int): max simulation time allowed for key generation (default inf).
        """

        log.logger.info(self.name + ' state={} generate_key, keylen={}, keynum={}'.format(self.state, keylen, frame_num))
        if self.role == 1:
            raise Exception(
                "Cascase.generate_key() called on receiver '{}'".format(self.name))

        if self.state == 0:
            log.logger.debug(self.name + ' generate_key with state 0')
            self.setup_time = self.own.timeline.now()
            self.keylen = keylen
            self.frame_num = frame_num
            self.run_time = run_time
            self._push(length=10000, key_num=1)

        else:
            self.start_time = self.own.timeline.now()
            self.end_time = self.start_time + self.run_time
            log.logger.debug(self.name + ' generate_key with state ' + str(self.state))
            self._push(length=self.frame_len, key_num=self.frame_num, run_time=self.run_time)

    def create_checksum_table(self) -> None:
        """Method to create checksum tables.

        Initialize checksum_table, index_to_block_id, and block_id_to_index after get key from BB84.

        Side Effects:
            Will modify `index_to_block_id_lists`, `block_id_to_index_lists`,  and `checksum_tables` attributes.
        """

        # create index_to_block_id
        log.logger.debug(self.name + ' state={} create_checksum_table'.format(self.state))
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
   
    def check_checksum(self, key_id: int) -> bool:
        """Method to check a checksum.

        Args:
            key_id (int): key id to check checksums for.

        Side Effects:
            May return keys to upper protocol.
            WILL send a KEY_IS_VALID method to other cascade protocols.
        """

        log.logger.debug(self.name + ' state={} check_checksum'.format(self.state))
        cur_key = key_id
        another_checksum = self.another_checksums[cur_key]
        block_id_to_index = self.block_id_to_index_lists[cur_key]
        for _pass in range(1, len(another_checksum)):
            for _block in range(len(another_checksum[_pass])):
                if self.checksum_tables[cur_key][_pass][_block] != self.another_checksums[cur_key][_pass][_block]:
                    log.logger.debug(self.name + ' state={} two checksums are different'.format(self.state, [cur_key, _pass, _block]))
                    block_size = len(block_id_to_index[_pass][_block])
                    self.interactive_binary_search(cur_key, _pass, _block, 0, block_size)
                    return False

        for i in range(int(self.frame_len / self.keylen)):
            self.valid_keys.append((self.bits[key_id] >> (i*self.keylen)) & ((1 << self.keylen)-1))
            if self.frame_num > 0:
                log.logger.info(self.name + ' state={} got_valid_key'.format(self.state))
                self._pop(key=self.valid_keys[-1])
                self.frame_num -= 1

        if self.role == 0:
            self.t2[key_id] = self.own.timeline.now()
        self.performance_measure()

        message = CascadeMessage(CascadeMsgType.KEY_IS_VALID, self.another.name, key_id=key_id)
        self.send_by_cc(message)

        return True

    def end_cascade(self):
        """Method to end cascade protocol."""

        self.state = 2
    
    def interactive_binary_search(self, key_id: int, pass_id: int, block_id: int, start: int, end: int) -> None:
        """Method to search for errors in key.

        Split block[start:end] to block[start:(start+end)/2], block[(start+end)/2,end].
        Ask checksums of subblock from sender.

        Args:
            key_id (int): id of key to check.
            pass_id (int): id of pass to check.
            block_id (int): id of block to check.
            start (int): index to start checking at.
            end (int): index to stop checking at.

        Side Effects:
            Will send SEND_FOR_BINARY messages to other protocol.
        """

        log.logger.debug(self.name + ' state={} interactive_binary_search, params={}'.format(
            self.state, [key_id, pass_id, block_id, start, end]))

        # first half checksum
        message = CascadeMessage(CascadeMsgType.SEND_FOR_BINARY, self.another.name,
                                 key_id=key_id, pass_id=pass_id, block_id=block_id,
                                 start=start, end=int((end+start) / 2))
        self.send_by_cc(message)

        # last half checksum
        message = CascadeMessage(CascadeMsgType.SEND_FOR_BINARY, self.another.name,
                                 key_id=key_id, pass_id=pass_id, block_id=block_id,
                                 start=int((end+start) / 2), end=end)
        self.send_by_cc(message)

    def send_by_cc(self, message: "CascadeMessage") -> None:
        """Method to send classical messages."""

        if self.own.timeline.now() > self.end_time and self.state != 2:
            self.end_cascade()
            self.another.end_cascade()
            return

        self.own.send_message(self.another.own.name, message)

    def performance_measure(self) -> None:
        """Method to record performance metrics."""

        # record metrics
        if self.role == 0:
            self.latency = 0
            counter = 0
            for i in range(len(self.t1)):
                if self.t2[i] != -1:
                    self.latency += self.t2[i]-self.t1[i]
                    counter += 1
            if counter > 0:
                self.latency /= counter
            else:
                self.latency = None
            self.another.latency = self.latency

        if self.own.timeline.now() - self.start_time:
            self.throughput = 1e12 * len(self.valid_keys) * self.keylen / (self.own.timeline.now() - self.start_time)
            self.privacy_throughput = 1e12 * (len(self.valid_keys) * self.keylen - int(len(self.valid_keys)/40) * self.secure_params - self.disclosed_bits_counter) / (self.own.timeline.now() - self.start_time)

        counter = 0
        for j in range(min(len(self.valid_keys), len(self.another.valid_keys))):
            i = 0
            val = self.valid_keys[j] ^ self.another.valid_keys[j]
            while val >> i:
                if (val >> i) & 1 == 1:
                    counter += 1
                i += 1

        if len(self.valid_keys) > 1:
            self.error_bit_rate = counter / (self.keylen * (len(self.valid_keys)))
        else:
            self.error_bit_rate = 0
        self.time_cost = self.end_time - self.start_time
