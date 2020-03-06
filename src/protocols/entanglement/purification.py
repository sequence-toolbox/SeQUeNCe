from typing import List

from numpy.random import random

from ..message import Message
from ..protocol import Protocol


class BBPSSWMessage(Message):
    def __init__(self, msg_type, **kwargs):
        self.msg_type = msg_type
        self.owner_type = type(BBPSSW(None, 0))
        if self.msg_type == "PING":
            self.index = kwargs["index"]
            self.kept_memo_r = kwargs["kept_memo_r"]
            self.meas_memo_r = kwargs["meas_memo_r"]
            self.kept_memo_s = kwargs["kept_memo_s"]
            self.meas_memo_s = kwargs["meas_memo_s"]
        elif self.msg_type == "PONG":
            self.index = kwargs["index"]
            self.fidelity = kwargs["fidelity"]
            self.kept_memo_r = kwargs["kept_memo_r"]
            self.meas_memo_r = kwargs["meas_memo_r"]
        else:
            raise Exception("BBPSSW protocol create unkown type of message: %s" % str(msg_type))

    def __str__(self):
        if self.msg_type == "PING":
            return "BBPSSW Message: msg_type: %s; round #: %d; kept memo id (receiver): %d; " \
                   "measured memo id (receiver): %d; kept memo id (sender): %d; measured memo id (sender): %d;" \
                   % (self.msg_type, self.index, self.kept_memo_r, self.meas_memo_r, self.kept_memo_s, self.meas_memo_s)
        elif self.msg_type == "PONG":
            return "BBPSSW Message: msg_type: %s; round #: %d; kept memo id (receiver): %d; " \
                   "measured memo id (receiver): %d; fidelity: %.2f" \
                   % (self.msg_type, self.index, self.kept_memo_r, self.meas_memo_r, self.fidelity)


class BBPSSW(Protocol):
    '''
    BBPSSW use PING, PONG message to exchange classical information
    PING message is composed by five parts:
        1. Type of message: PING
        2. The index number of operated purification: integer
        3. Memory id of kept memory on message receiver: integer
        4. Memory id of measured memory on message receiver: integer
        5. Memory id of kept memory on message sender: integer
        6. Memory id of measured memory on message sender: integer
    PONG message is composed by four parts:
        1. Type of message: PONG
        2. The index number of operated purification: integer
        3. Fidelity after purification: float
        4. Memory id of kept memory on message receiver: integer
        5. Memory id of measured memory on message receiver: integer
    ASSUMPTION:
        1. Two nodes receive poped message from bottom layer before receive
           PING / PONG message
        2. Classical message
        3. nodes have different name
    '''

    def __init__(self, own, threshold):
        if own is None:
            # to create dummy object with none parameters
            return
        Protocol.__init__(self, own)
        self.threshold = threshold
        # self.purified_lists :
        # { node name : [ [index of memories after round i purificaiton] ]
        self.purified_lists = {}
        # self.waiting_list:
        # { round of purification : [ set( [ kept memory, measured memory ] ) }
        self.waiting_list = {}
        self.rsvp_name = ''
        self.valid_memories = set()

    def init(self):
        pass

    def set_valid_memories(self, memories):
        self.valid_memories = memories

    def pop(self, **kwargs):
        if "info_type" in kwargs:
            return
        memory_index = kwargs["memory_index"]
        another_node = kwargs["another_node"]
        if memory_index not in self.valid_memories:
            return False

        if another_node not in self.purified_lists:
            self.purified_lists[another_node] = []
        purified_list = self.purified_lists[another_node]
        if len(purified_list) == 0:
            purified_list.append([])

        local_memory = self.own.components['MemoryArray']
        cur_fidelity = local_memory[memory_index].fidelity

        if cur_fidelity < self.threshold:
            purified_list[0].append(memory_index)
        else:
            self._pop(memory_index=memory_index, another_node=another_node)

        if len(purified_list[0]) > 1 and self.own.name > another_node:
            self.start_round(0, another_node)

        return True

    def start_round(self, round_id, another_node):
        local_memory = self.own.components['MemoryArray']
        purified_list = self.purified_lists[another_node]
        if round_id not in self.waiting_list:
            self.waiting_list[round_id] = set()
        kept_memo = purified_list[round_id].pop()
        measured_memo = purified_list[round_id].pop()
        assert (local_memory[kept_memo].fidelity == local_memory[measured_memo].fidelity)
        assert (local_memory[kept_memo].fidelity > 0.5)

        another_kept_memo = local_memory[kept_memo].entangled_memory['memo_id']
        another_measured_memo = local_memory[measured_memo].entangled_memory['memo_id']
        self.waiting_list[round_id].add((kept_memo, measured_memo))

        msg = BBPSSWMessage("PING", index=round_id, kept_memo_r=another_kept_memo,
                            meas_memo_r=another_measured_memo, kept_memo_s=kept_memo,
                            meas_memo_s=measured_memo)

        # WARN: wait change of Node.send_message function
        self.own.send_message(dst=another_node, msg=msg, priority=2)

    def push(self, **kwargs):
        self._push(**kwargs)

    def received_message(self, src: str, msg: Message):
        if src not in self.purified_lists:
            return False
        purified_list = self.purified_lists[src]
        # WARN: wait change of Node.receive_message
        if msg.msg_type == "PING":
            round_id = msg.index
            kept_memo = msg.kept_memo_r
            measured_memo = msg.meas_memo_r
            if not (len(purified_list) > round_id and
                    kept_memo in purified_list[round_id] and
                    measured_memo in purified_list[round_id]):
                return False
            fidelity = self.purification(round_id, kept_memo,
                                         measured_memo, purified_list)

            reply = BBPSSWMessage("PONG", index=round_id, fidelity=fidelity,
                                  kept_memo_r=msg.kept_memo_s, meas_memo_r=msg.meas_memo_s)

            # WARN: wait change of Node.send_message function
            self.own.send_message(dst=src, msg=reply, priority=2)

            if fidelity >= self.threshold:
                self._pop(memory_index=kept_memo, another_node=src)
                purified_list[round_id + 1].remove(kept_memo)
        elif msg.msg_type == "PONG":
            round_id = msg.index
            fidelity = msg.fidelity
            kept_memo = msg.kept_memo_r
            measured_memo = msg.meas_memo_r
            if round_id not in self.waiting_list or (kept_memo, measured_memo) not in self.waiting_list[round_id]:
                return False

            self.update(round_id, fidelity, kept_memo,
                        measured_memo, purified_list)
            if fidelity >= self.threshold:
                self._pop(memory_index=kept_memo, another_node=src)
            if (round_id + 1 < len(purified_list) and len(purified_list[round_id + 1]) > 1):
                self.start_round(round_id + 1, src)
        else:
            raise Exception("BBPSSW protocol receives"
                            "unkown type of message: %s" % str(msg))

        return True

    def purification(self,
                     round_id: int,
                     kept_memo: int,
                     measured_memo: int,
                     purified_list: List[List[int]]) -> float:

        local_memory = self.own.components['MemoryArray']

        assert (local_memory[kept_memo].fidelity ==
                local_memory[measured_memo].fidelity)
        assert (local_memory[kept_memo].fidelity > 0.5)
        purified_list[round_id].remove(kept_memo)
        purified_list[round_id].remove(measured_memo)

        fidelity = local_memory[kept_memo].fidelity
        suc_prob = self.success_probability(fidelity)
        if random() < suc_prob:
            fidelity = round(self.improved_fidelity(fidelity), 6)
            local_memory[kept_memo].fidelity = fidelity

            if len(purified_list) <= round_id + 1:
                purified_list.append([])
            purified_list[round_id + 1].append(kept_memo)
        else:
            fidelity = 0
            local_memory[kept_memo].fidelity = fidelity
            local_memory[kept_memo].entangled_memory['node_id'] = None
            local_memory[kept_memo].entangled_memory['memo_id'] = None
            self._push(index=kept_memo)

        local_memory[measured_memo].fidelity = 0
        local_memory[measured_memo].entangled_memory['node_id'] = None
        local_memory[measured_memo].entangled_memory['memo_id'] = None
        self._push(index=measured_memo)
        return fidelity

    def update(self, round_id: int,
               fidelity: float, kept_memo: int,
               measured_memo: int, purified_list):

        local_memory = self.own.components['MemoryArray']
        self.waiting_list[round_id].remove((kept_memo, measured_memo))

        local_memory[kept_memo].fidelity = fidelity
        if fidelity == 0:
            local_memory[kept_memo].entangled_memory['node_id'] = None
            local_memory[kept_memo].entangled_memory['memo_id'] = None
            self._push(index=kept_memo)
        elif fidelity < self.threshold:
            if len(purified_list) <= round_id + 1:
                purified_list.append([])
            purified_list[round_id + 1].append(kept_memo)

        local_memory[measured_memo].fidelity = 0
        local_memory[measured_memo].entangled_memory['node_id'] = None
        local_memory[measured_memo].entangled_memory['memo_id'] = None
        self._push(index=measured_memo)

    @staticmethod
    def success_probability(F: float) -> float:
        '''
        F is the fidelity of entanglement
        Formula comes from Dur and Briegel (2007) page 14
        '''
        return F**2 + 2 * F * (1 - F) / 3 + 5 * ((1 - F) / 3)**2

    @staticmethod
    def improved_fidelity(F: float) -> float:
        '''
        F is the fidelity of entanglement
        Formula comes from Dur and Briegel (2007) formula (18) page 14
        '''
        return (F**2 + ((1 - F) / 3)**2) / (F**2 + 2 * F * (1 - F) / 3 + 5 * ((1 - F) / 3)**2)

