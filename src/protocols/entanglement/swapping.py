from typing import Set

from numpy.random import random

from ..message import Message
from ..protocol import Protocol
from ...topology.node import Node


class EntanglementSwappingMessage(Message):
    def __init__(self, msg_type: str, **kwargs):
        self.msg_type = msg_type
        self.owner_type = type(EntanglementSwapping(None, None, None, None))
        if self.msg_type == "SWAP_RES":
            self.local_memo = kwargs.get("local_memo")
            self.fidelity = kwargs.get("fidelity")
            self.remote_node = kwargs.get("remote_node")
            self.remote_memo = kwargs.get("remote_memo")
        else:
            raise Exception("Entanglement swapping protocol create unkown type of message: %s" % str(msg_type))

    def __str__(self):
        if self.msg_type == "SWAP_RES":
            return "EntanglementSwappingMessage: msg_type: %s; local_memo: %d; fidelity: %.2f; remote_node: %s; remote_memo: %d; " % (
                self.msg_type, self.local_memo, self.fidelity, self.remote_node, self.remote_memo)


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
        if own is None:
            # to create dummy object with none parameters
            return
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

    def set_valid_memories(self, memories: Set):
        self.valid_memories = memories

    def push(self, **kwargs):
        self._push(**kwargs)

    def pop(self, **kwargs):  # memory_index: int, another_node: str:
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

        return True

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
        msg = EntanglementSwappingMessage("SWAP_RES", local_memo=another_memo_id1, fidelity=fidelity,
                                          remote_node=another_node_id2, remote_memo=another_memo_id2)
        # msg = self.rsvp_name + " EntanglementSwapping SWAP_RES %d %f %s %d" % (another_memo_id1,
        #                                                                        fidelity,
        #                                                                        another_node_id2,
        #                                                                        another_memo_id2)
        self.own.send_message(dst=another_node_id1, msg=msg, priority=3)
        # msg = self.rsvp_name + " EntanglementSwapping SWAP_RES %d %f %s %d" % (another_memo_id2,
        #                                                                        fidelity,
        #                                                                        another_node_id1,
        #                                                                        another_memo_id1)
        msg = EntanglementSwappingMessage("SWAP_RES", local_memo=another_memo_id2, fidelity=fidelity,
                                          remote_node=another_node_id1, remote_memo=another_memo_id1)
        self.own.send_message(dst=another_node_id2, msg=msg, priority=3)

    def received_message(self, src: str, msg: EntanglementSwappingMessage):
        if src not in self.known_nodes:
            return False
        if msg.msg_type == "SWAP_RES":
            memo_id = msg.local_memo
            fidelity = msg.fidelity
            another_node = msg.remote_node
            another_memo = msg.remote_memo

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
        return "EntanglementSwapping: remote1: %s;  remote2: %s; known_nodes: %s" % (
            self.remote1, self.remote2, self.known_nodes)

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