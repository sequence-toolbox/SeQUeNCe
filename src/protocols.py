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

    def _push(self, **kwargs):
        for child in self.lower_protocols:
            child.push(**kwargs)

    def _pop(self, **kwargs):
        for parent in self.upper_protocols:
            parent.pop(**kwargs)
        return


class EntanglementGeneration(Protocol):

    def __init__(self, own, parent_protocols=[], child_protocols=[]):
        Protocol.__init__(own, parent_protocols, child_protocols)

        self.alice_name = ""
        self.bob_name = ""
        self.charlie_name = ""
        self.is_charlie = False
        self.node = None

        self.start_time = 0
        self.quantum_delay = [0, 0]  # Alice, Bob
        self.classical_delay = [0, 0]  # Alice, Bob

    def pop(self):
        pass

    def push(self):
        pass

    def assign_node(self, node):
        self.node = node
        if self.is_charlie:
            self.classical_delay[0] = node.cchannels.get(self.alice_name).delay
            self.classical_delay[1] = node.cchannels.get(self.bob_name).delay

            qchannel_a = node.qchannels.get(self.alice_name)
            qchannel_b = node.qchannels.get(self.bob_name)
            self.quantum_delay[0] = int(round(qchannel_a.distance / qchannel_a.light_speed))
            self.quantum_delay[1] = int(round(qchannel_b.distance / qchannel_b.light_speed))

    def start(self):
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
        # self.purified_lists :
        # { node name : [ [index of memories after round i purificaiton] ]
        self.purified_lists = {}
        # self.waiting_list:
        # { round of purification : [ set( [ kept memory, measured memory ] ) }
        self.waiting_list = {}

    def pop(self, memory_index: int, another_node: str):
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

    def start_round(self, round_id, another_node):
        local_memory = self.own.components['MemoryArray']
        purified_list = self.purified_lists[another_node]
        if round_id not in self.waiting_list:
            self.waiting_list[round_id] = set()
        kept_memo = purified_list[round_id].pop()
        measured_memo = purified_list[round_id].pop()
        assert (local_memory[kept_memo].fidelity ==
                local_memory[measured_memo].fidelity)
        assert (local_memory[kept_memo].fidelity > 0.5)

        another_kept_memo = local_memory[kept_memo].entangled_memory['memo_id']
        another_measured_memo = local_memory[measured_memo].entangled_memory['memo_id']
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

    def received_message(self, src: str, msg: List[str]):
        purified_list = self.purified_lists[src]
        # WARN: wait change of Node.receive_message
        # WARN: assume protocol name is discarded from msg list
        type_index = 0
        msg_type = msg[type_index]
        if msg_type == "PING":
            round_id = int(msg[type_index+1])
            kept_memo = int(msg[type_index+2])
            measured_memo = int(msg[type_index+3])
            fidelity = self.purification(round_id, kept_memo,
                                         measured_memo, purified_list)

            reply = "BBPSSW PONG %d %f %s %s" % (round_id,
                                                 fidelity,
                                                 msg[type_index+4],
                                                 msg[type_index+5])
            # WARN: wait change of Node.send_message function
            self.own.send_message(dst=src, msg=reply)

            if fidelity >= self.threshold:
                self._pop(memory_index=kept_memo, another_node=src)
                purified_list[round_id+1].remove(kept_memo)
        elif msg_type == "PONG":
            round_id = int(msg[type_index+1])
            fidelity = float(msg[type_index+2])
            kept_memo = int(msg[type_index+3])
            measured_memo = int(msg[type_index+4])
            self.update(round_id, fidelity, kept_memo,
                        measured_memo, purified_list)
            if fidelity >= self.threshold:
                self._pop(memory_index=kept_memo, another_node=src)
            if (round_id+1 < len(purified_list) and
                    len(purified_list[round_id+1]) > 1):
                self.start_round(round_id+1, src)
        else:
            raise Exception("BBPSSW protocol receives"
                            "unkown type of message: %s" % str(msg))

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
            purified_list[round_id+1].append(kept_memo)
        else:
            fidelity = 0
            local_memory[kept_memo].fidelity = fidelity
            local_memory[kept_memo].entangled_memory['node_id'] = None
            local_memory[kept_memo].entangled_memory['memo_id'] = None
            self._push(memory_index=kept_memo)

        local_memory[measured_memo].fidelity = 0
        local_memory[measured_memo].entangled_memory['node_id'] = None
        local_memory[measured_memo].entangled_memory['memo_id'] = None
        self._push(memory_index=measured_memo)
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
            self._push(memory_index=kept_memo)
        elif fidelity < self.threshold:
            if len(purified_list) <= round_id + 1:
                purified_list.append([])
            purified_list[round_id+1].append(kept_memo)

        local_memory[measured_memo].fidelity = 0
        local_memory[measured_memo].entangled_memory['node_id'] = None
        local_memory[measured_memo].entangled_memory['memo_id'] = None
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

    # dummy protocol for distribution of direct transmission
    class DummyParent(Protocol):

        def __init__(self, own):
            Protocol.__init__(self, own)
            self.another = ''
            self.counter = 100
            self.multi_nodes = False

        def pop(self, memory_index, another):
            for parent in self.upper_protocols:
                parent.pop(memory_index, another)

        def push(self, **kwargs):
            memory_index = kwargs.get("memory_index")
            local_memory = self.own.components['MemoryArray']
            local_memory[memory_index].fidelity = 0.6
            if self.multi_nodes:
                if self.own.name > self.another and memory_index < 20:
                    local_memory[memory_index].entangled_memory['memo_id'] = memory_index + 20
                elif self.own.name < self.another and memory_index >= 20:
                    local_memory[memory_index].entangled_memory['memo_id'] = memory_index - 20
                else:
                    return
            else:
                local_memory[memory_index].entangled_memory['memo_id'] = memory_index
            local_memory[memory_index].entangled_memory['node_id'] = self.another
            process = Process(self, 'pop', [memory_index, self.another])
            event = Event(self.counter*1e9, process)
            self.own.timeline.schedule(event)
            self.counter += 1

        def received_message(self, src, msg):
            pass

    def two_nodes_test():
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
            alice_memo_array[i].entangled_memory = {'node_id': 'bob', 'memo_id': i}
            bob_memo_array[i].entangled_memory = {'node_id': 'alice', 'memo_id': i}
            e = Event(i*(1e5), Process(dummyA, "pop", [i, "bob"]))
            tl.schedule(e)
            e = Event(i*(1e5), Process(dummyB, "pop", [i, "alice"]))
            tl.schedule(e)

        # start simulation
        tl.init()
        tl.run()

        def print_memory(memoryArray):
            for i, memory in enumerate(memoryArray):
                print(i, memoryArray[i].entangled_memory, memory.fidelity)

        print('alice memory')
        print_memory(alice_memo_array)
        print('bob memory')
        print_memory(bob_memo_array)

    def multi_nodes_test(n: int):
        # create timeline
        tl = timeline.Timeline()

        # create nodes
        nodes = []
        for i in range(n):
            node = topology.Node("node %d" % i, tl)
            nodes.append(node)

        # create classical channel
        for i in range(n-1):
            cc = topology.ClassicalChannel("cc1", tl, distance=1e3, delay=1e5)
            cc.add_end(nodes[i])
            cc.add_end(nodes[i+1])
            nodes[i].assign_cchannel(cc)
            nodes[i+1].assign_cchannel(cc)

        # create memories on nodes
        NUM_MEMORY = 40
        memory_params = {"fidelity": 0.6}
        for node in nodes:
            memory = topology.MemoryArray("%s memory array" % node.name,
                                          tl, num_memories=NUM_MEMORY,
                                          memory_params=memory_params)
            node.components['MemoryArray'] = memory

        # create protocol stack
        dummys = []
        for i, node in enumerate(nodes):
            bbpssw = BBPSSW(node, threshold=0.9)
            if i > 0:
                dummy = DummyParent(node)
                dummy.multi_nodes = True
                dummy.another = "node %d" % (i-1)
                dummy.upper_protocols.append(bbpssw)
                bbpssw.lower_protocols.append(dummy)
                node.protocols.append(dummy)
                dummys.append(dummy)
            if i < len(nodes)-1:
                dummy = DummyParent(node)
                dummy.multi_nodes = True
                dummy.another = "node %d" % (i+1)
                dummy.upper_protocols.append(bbpssw)
                bbpssw.lower_protocols.append(dummy)
                node.protocols.append(dummy)
                dummys.append(dummy)

            node.protocols.append(bbpssw)

        # create entanglement
        for i in range(n-1):
            memo1 = nodes[i].components['MemoryArray']
            memo2 = nodes[i+1].components['MemoryArray']
            for j in range(int(NUM_MEMORY/2)):
                memo1[j+int(NUM_MEMORY/2)].entangled_memory = {'node_id': 'node %d' % (i+1), 'memo_id': j}
                memo2[j].entangled_memory = {'node_id': 'node %d' % i, 'memo_id': j+int(NUM_MEMORY/2)}

        # schedule events
        counter = 0
        for i in range(0, len(dummys), 2):
            dummy1 = dummys[i]
            dummy2 = dummys[i+1]
            for j in range(int(NUM_MEMORY/2)):
                e = Event(counter*(1e5), Process(dummy1, "pop", [j+int(NUM_MEMORY/2), dummy2.own.name]))
                tl.schedule(e)
                e = Event(counter*(1e5), Process(dummy2, "pop", [j, dummy1.own.name]))
                tl.schedule(e)
                counter += 1

        # start simulation
        tl.init()
        tl.run()

        def print_memory(memoryArray):
            for i, memory in enumerate(memoryArray):
                print(i, memoryArray[i].entangled_memory, memory.fidelity)

        for node in nodes:
            memory = node.components['MemoryArray']
            print(node.name)
            print_memory(memory)

    # two_nodes_test()
    multi_nodes_test(3)
