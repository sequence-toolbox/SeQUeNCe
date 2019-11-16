from abc import ABC, abstractmethod
from typing import List
from random import random

from topology import Node


class Protocol(ABC):

    def __init__(self, own: Node):
        self.upper_protocols = []
        self.lower_protocols = []
        self.own = own

    @abstractmethod
    def pop(self):
        '''
        information generated in current protocol is poped to
        all its parents protocols
        '''
        pass

    @abstractmethod
    def push(self):
        '''
        information generated in current protocol is pushed to
        all its child protocols
        '''
        pass

    @abstractmethod
    def received_message(self, src: str, msg: List[str]):
        '''
        receive classical message from another node
        '''
        pass


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
        Protocol.__init__(self, own)
        self.threshold = threshold
        # self.purified_list :
        #   the index number present the number of operated purification
        self.purified_list = []
        # self.waiting_list:
        # { round of purification : [ set( [ kept memory, measured memory ] ) }
        self.waiting_list = {}

    def pop(self, memory_index: int, another_node: str):
        if len(self.purified_list) == 0:
            self.purified_list.append([])

        local_memory = self.own.components['MemoryArray']
        cur_fidelity = local_memory[memory_index].fidelity

        if cur_fidelity < self.threshold:
            self.purified_list[0].append(memory_index)
        else:
            self._pop(memory_index=memory_index, another_node=another_node)

        if len(self.purified_list[0]) > 1 and self.own.name > another_node:
            self.start_round(0, another_node)

    def start_round(self, round_id, another_node):
        local_memory = self.own.components['MemoryArray']
        if round_id not in self.waiting_list:
            self.waiting_list[round_id] = set()
        kept_memo = self.purified_list[round_id].pop()
        measured_memo = self.purified_list[round_id].pop()
        assert (local_memory[kept_memo].fidelity ==
                local_memory[measured_memo].fidelity)
        assert (local_memory[kept_memo].fidelity > 0.5)

        another_kept_memo = local_memory.entangled_memories[kept_memo]
        another_measured_memo = local_memory.entangled_memories[measured_memo]
        self.waiting_list[round_id].add((kept_memo, measured_memo))

        msg = "BBPSSW PING %d %d %d %d %d" % (round_id,
                                              another_kept_memo,
                                              another_measured_memo,
                                              kept_memo,
                                              measured_memo)
        # WARN: wait change of Node.send_message function
        self.own.send_message(dst=another_node, msg=msg)

    def push(self):
        pass

    def _push(self, **kwargs):
        for child in self.lower_protocols:
            child.push(**kwargs)

    def _pop(self, **kwargs):
        for parent in self.upper_protocols:
            parent.pop(**kwargs)
        return

    def received_message(self, src: str, msg: List[str]):
        # WARN: wait change of Node.receive_message
        # WARN: assume protocol name is discarded from msg list
        type_index = 0
        msg_type = msg[type_index]
        if msg_type == "PING":
            round_id = int(msg[type_index+1])
            kept_memo = int(msg[type_index+2])
            measured_memo = int(msg[type_index+3])
            fidelity = self.purification(round_id, kept_memo, measured_memo)

            reply = "BBPSSW PONG %d %f %s %s" % (round_id,
                                                 fidelity,
                                                 msg[type_index+4],
                                                 msg[type_index+5])
            # WARN: wait change of Node.send_message function
            self.own.send_message(dst=src, msg=reply)

            if fidelity >= self.threshold:
                self._pop(memory_index=kept_memo, another_node=src)
                self.purified_list[round_id+1].remove(kept_memo)
        elif msg_type == "PONG":
            round_id = int(msg[type_index+1])
            fidelity = float(msg[type_index+2])
            kept_memo = int(msg[type_index+3])
            measured_memo = int(msg[type_index+4])
            self.update(round_id, fidelity, kept_memo, measured_memo)
            if fidelity >= self.threshold:
                self._pop(memory_index=kept_memo, another_node=src)
            if (round_id+1 < len(self.purified_list) and
                    len(self.purified_list[round_id+1]) > 1):
                self.start_round(round_id+1, src)
        else:
            raise Exception("BBPSSW protocol receives"
                            "unkown type of message: %s" % str(msg))

    def purification(self,
                     round_id: int,
                     kept_memo: int,
                     measured_memo: int) -> float:

        local_memory = self.own.components['MemoryArray']
        assert (local_memory[kept_memo].fidelity ==
                local_memory[measured_memo].fidelity)
        assert (local_memory[kept_memo].fidelity > 0.5)
        self.purified_list[round_id].remove(kept_memo)
        self.purified_list[round_id].remove(measured_memo)

        fidelity = local_memory[kept_memo].fidelity
        suc_prob = self.success_probability(fidelity)
        if random() < suc_prob:
            fidelity = round(self.improved_fidelity(fidelity), 6)
            local_memory[kept_memo].fidelity = fidelity

            if len(self.purified_list) <= round_id + 1:
                self.purified_list.append([])
            self.purified_list[round_id+1].append(kept_memo)
        else:
            fidelity = 0
            local_memory[kept_memo].fidelity = fidelity
            local_memory.entangled_memories[kept_memo] = -1
            self._push(memory_index=kept_memo)

        local_memory[measured_memo].fidelity = 0
        local_memory.entangled_memories[measured_memo] = -1
        self._push(memory_index=measured_memo)
        return fidelity

    def update(self,
               round_id: int,
               fidelity: float,
               kept_memo: int,
               measured_memo: int):

        local_memory = self.own.components['MemoryArray']
        self.waiting_list[round_id].remove((kept_memo, measured_memo))

        local_memory[kept_memo].fidelity = fidelity
        if fidelity == 0:
            local_memory.entangled_memories[kept_memo] = -1
            self._push(memory_index=kept_memo)
        elif fidelity < self.threshold:
            if len(self.purified_list) <= round_id + 1:
                self.purified_list.append([])
            self.purified_list[round_id+1].append(kept_memo)

        local_memory[measured_memo].fidelity = 0
        local_memory.entangled_memories[measured_memo] = -1
        self._push(memory_index=measured_memo)

    @staticmethod
    def success_probability(F: float) -> float:
        '''
        F is the fidelity of entanglement
        Formula comes from Dur and Briegel (2007) page 14
        '''
        return F**2 + 2*F*(1-F)/3 + 5*((1-F)/3)**2

    @staticmethod
    def improved_fidelity(F: float) -> float:
        '''
        F is the fidelity of entanglement
        Formula comes from Dur and Briegel (2007) formula (18) page 14
        '''
        return (F**2 + ((1-F)/3)**2) / (F**2 + 2*F*(1-F)/3 + 5*((1-F)/3)**2)


if __name__ == "__main__":
    import topology
    import timeline
    from sequence.process import Process
    from sequence.event import Event
    from random import seed

    # two nodes case
    # multiple nodes case
    seed(1)

    # create timeline
    tl = timeline.Timeline()

    # create nodes alice and bob
    alice = topology.Node("alice", tl)
    bob = topology.Node("bob", tl)

    # create classical channel
    cc = topology.ClassicalChannel("cc", tl, distance=1e3, delay=1e5)
    cc.add_end(alice)
    cc.add_end(bob)
    alice.assign_cchannel(cc)
    bob.assign_cchannel(cc)

    # create memories on nodes
    NUM_MEMORY = 20
    sample_memory = topology.Memory("", tl, fidelity=0.6)
    alice_memo_array = topology.MemoryArray("alice memory array",
                                            tl, num_memories=NUM_MEMORY,
                                            sample_memory=sample_memory)
    bob_memo_array = topology.MemoryArray("bob memory array",
                                          tl, num_memories=NUM_MEMORY,
                                          sample_memory=sample_memory)
    alice.components['MemoryArray'] = alice_memo_array
    bob.components['MemoryArray'] = bob_memo_array

    # dummy protocol for distribution of direct transmission
    class DummyParent(Protocol):

        def __init__(self, own):
            Protocol.__init__(self, own)
            self.another = ''
            self.counter = 100

        def pop(self, memory_index, another):
            for parent in self.upper_protocols:
                parent.pop(memory_index, another)

        def push(self, **kwargs):
            memory_index = kwargs.get("memory_index")
            local_memory = self.own.components['MemoryArray']
            local_memory[memory_index].fidelity = 0.6
            local_memory.entangled_memories[memory_index] = memory_index
            process = Process(self, 'pop', [memory_index, self.another])
            event = Event(self.counter*1e9, process)
            self.own.timeline.schedule(event)
            self.counter += 1

        def received_message(self, src, msg):
            pass

    # create alice protocol stack
    dummyA = DummyParent(alice)
    dummyA.another = 'bob'
    bbpsswA = BBPSSW(alice, threshold=0.9)
    dummyA.upper_protocols.append(bbpsswA)
    bbpsswA.lower_protocols.append(dummyA)
    alice.protocols.append(dummyA)
    alice.protocols.append(bbpsswA)

    # create bob protocol stack
    dummyB = DummyParent(bob)
    dummyB.another = 'alice'
    bbpsswB = BBPSSW(bob, threshold=0.9)
    dummyB.upper_protocols.append(bbpsswB)
    bbpsswB.lower_protocols.append(dummyB)
    bob.protocols.append(dummyB)
    bob.protocols.append(bbpsswB)

    # schedule events
    for i in range(NUM_MEMORY):
        alice_memo_array.entangled_memories[i] = i
        bob_memo_array.entangled_memories[i] = i
        e = Event(i*(1e5), Process(dummyA, "pop", [i, "bob"]))
        tl.schedule(e)
        e = Event(i*(1e5), Process(dummyB, "pop", [i, "alice"]))
        tl.schedule(e)

    # start simulation
    tl.init()
    tl.run()

    def print_memory(memoryArray):
        for i, memory in enumerate(memoryArray):
            print(i, memoryArray.entangled_memories[i], memory.fidelity)

    print('alice memory')
    print_memory(alice_memo_array)
    print('bob memory')
    print_memory(bob_memo_array)
