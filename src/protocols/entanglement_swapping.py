from abc import ABC, abstractmethod
from typing import List
from numpy.random import random
from math import ceil, sqrt

from sequence import topology
from sequence import timeline
from sequence import encoding
from sequence.topology import Node
from sequence.process import Process
from sequence.event import Event


class EntanglementSwapping(Protocol):
    '''
    Node will execute entanglement swapping protocol will when there are
    memories that are entangled with memories on node remote1 and remote2
    SWAP_RES message is composed by:
        1. Type of message: SWAP_RES
        2. Influenced memory of receiver: integer
        3. Fidelity after entanglement swap : float
        4. Entangled node after entanglement swap : str
        5. Entangled memory after entanglement swap: integer
    ASSUMPTION:
        1. The name of node is not null string
    '''
    def __init__(self, own: Node, remote1: str, remote2: str, known_nodes):
        Protocol.__init__(self, own)
        self.remote1 = remote1
        self.remote2 = remote2
        # self.waiting_memo1(2) stores memories that entangled with remote1(2)
        self.waiting_memo1 = []
        self.waiting_memo2 = []
        self.waiting_swap_res = {}
        self.known_nodes = known_nodes
        self.rsvp_name = ''
        self.valid_memories = set()

    def init(self):
        pass

    def set_valid_memories(self, memories):
        self.valid_memories = memories

    def push(self, **kwargs):
        self._push(**kwargs)

    def _pop(self, **kwargs):
        super()._pop(**kwargs)

    def pop(self, **kwargs): # memory_index: int, another_node: str:
        if "info_type" in kwargs:
            return

        memory_index = kwargs["memory_index"]
        another_node = kwargs["another_node"]
        if memory_index not in self.valid_memories:
            return False

        if another_node == self.remote1:
            self.waiting_memo1.append(memory_index)
        elif another_node == self.remote2:
            self.waiting_memo2.append(memory_index)
        elif another_node in self.known_nodes:
            self.waiting_swap_res[memory_index] = another_node
        else:
            self._pop(memory_index=memory_index, another_node=another_node)

        while self.waiting_memo1 and self.waiting_memo2:
            memo1 = self.waiting_memo1.pop()
            memo2 = self.waiting_memo2.pop()
            self.swap(memo1, memo2)
            self._push(index=memo1)
            self._push(index=memo2)

    def swap(self, memo_id1: int, memo_id2: int):
        memo1 = self.own.components["MemoryArray"][memo_id1]
        memo2 = self.own.components["MemoryArray"][memo_id2]

        suc_prob = self.success_probability()
        fidelity = 0
        if random() < suc_prob:
            fidelity = self.updated_fidelity(memo1.fidelity, memo2.fidelity)

        another_node_id1 = memo1.entangled_memory['node_id']
        another_memo_id1 = memo1.entangled_memory['memo_id']
        another_node_id2 = memo2.entangled_memory['node_id']
        another_memo_id2 = memo2.entangled_memory['memo_id']
        msg = self.rsvp_name + " EntanglementSwapping SWAP_RES %d %f %s %d" % (another_memo_id1,
                                                             fidelity,
                                                             another_node_id2,
                                                             another_memo_id2)
        self.own.send_message(dst=another_node_id1, msg=msg, priority=3)
        msg = self.rsvp_name + " EntanglementSwapping SWAP_RES %d %f %s %d" % (another_memo_id2,
                                                             fidelity,
                                                             another_node_id1,
                                                             another_memo_id1)
        self.own.send_message(dst=another_node_id2, msg=msg, priority=3)

    def received_message(self, src: str, msg: List[str]):
        if src not in self.known_nodes:
            return False
        type_index = 0
        msg_type = msg[type_index]
        if msg_type == "SWAP_RES":
            memo_id = int(msg[type_index + 1])
            fidelity = float(msg[type_index + 2])
            another_node = msg[type_index + 3]
            another_memo = int(msg[type_index + 4])

            self.waiting_swap_res.pop(memo_id)

            memory = self.own.components["MemoryArray"][memo_id]
            if fidelity == 0:
                self._push(index=memo_id)
            else:
                memory.fidelity = fidelity
                memory.entangled_memory['node_id'] = another_node
                memory.entangled_memory['memo_id'] = another_memo
                self._pop(memory_index=memo_id, another_node=another_node)
        else:
            raise Exception("Entanglement swapping protocol "
                            "receives unkown type of message: "
                            "%s" % str(msg))

        return True

    def __str__(self):
        return "EntanglementSwapping: remote1: %s;  remote2: %s; known_nodes: %s" % (self.remote1, self.remote2, self.known_nodes)

    @staticmethod
    def success_probability() -> float:
        '''
        A simple model for BSM success probability
        '''
        return 0.93

    @staticmethod
    def updated_fidelity(f1: float, f2: float) -> float:
        '''
        A simple model updating fidelity of entanglement
        '''
        return (f1 + f2) / 2 * 0.95

