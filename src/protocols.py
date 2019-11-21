from abc import ABC, abstractmethod
from typing import List
from random import random
import re

from sequence import topology
from sequence import timeline
from sequence import encoding
from sequence.topology import Node
from sequence.process import Process
from sequence.event import Event


class Protocol(ABC):
    def __init__(self, own: Node):
        self.upper_protocols = []
        self.lower_protocols = []
        self.own = own

    @abstractmethod
    def pop(self, *args):
        '''
        information generated in current protocol is popped to
        all its parents protocols
        '''
        pass

    @abstractmethod
    def push(self, *args):
        '''
        information generated in current protocol is pushed to
        all its child protocols
        '''
        pass

    def _push(self, *args):
        for child in self.lower_protocols:
            child.push(*args)

    def _pop(self, *args):
        for parent in self.upper_protocols:
            parent.pop(*args)
        return

    @abstractmethod
    def received_message(self, src: str, msg: List[str]):
        '''
        receive classical message from another node
        '''
        pass


class EntanglementGeneration(Protocol):
    '''
    Procedure:
    1. Nodes that are not a middle (charlie) node send data to middle
    2. Middle node uses data to schedule end nodes to send photons from memory
    3. Middle node performs BSM when photons arrive
    4. Middle node broadcasts results of entanglement to end node
    5. End nodes store result and pop information to parent node
    '''
    def __init__(self, own, is_middle=False, **kwargs):
        Protocol.__init__(self, own)
        self.is_middle = is_middle
        # properties below used for middle node
        self.end_nodes = kwargs.get("end_nodes", [])
        self.classical_delays = [-1, -1]
        self.quantum_delays = [-1, -1]
        self.num_memories = [-1, -1]
        self.frequencies = [-1, -1]
        self.start_time = -1

        # keep track of which memory arrays we're trying to entangle
        if len(self.end_nodes) == 2:
            mem_0 = self.end_nodes[0].components["MemoryArray"]
            mem_1 = self.end_nodes[1].components["MemoryArray"]
            mem_0.set_entanglement_partner(mem_1)
            mem_1.set_entanglement_partner(mem_0)

    def pop(self, start=False):
        # used to start protocol
        if self.is_middle and start:
            self.classical_delays = [-1, -1]
            self.quantum_delays = [-1, -1]
            self.num_memories = [-1, -1]
            self.frequencies = [-1, -1]
            message = "EntanglementGeneration send_data"
            for node in self.end_nodes:
                self.own.send_message(node.name, message)

    def push(self, _):
        # redo entanglement with this memory
        pass

    def end_photons(self):
        bsm_res = self.own.components["BSM"].get_bsm_res()
        message_0 = "EntanglementGeneration receive_bsm {} {}".format(self.end_nodes[1].name, bsm_res)
        message_1 = "EntanglementGeneration receive_bsm {} {}".format(self.end_nodes[0].name, bsm_res)
        self.own.send_message(self.end_nodes[0].name, message_0)
        self.own.send_message(self.end_nodes[1].name, message_1)

    def received_message(self, src: str, msg: List[str]):
        msg_type = msg[0]

        if msg_type == "send_data":
            classical_delay = int(round(self.own.cchannels[src].delay))
            qchannel = self.own.qchannels[src]
            quantum_delay = int(round(qchannel.distance / qchannel.light_speed))
            num_memories = len(self.own.components["MemoryArray"])
            frequency = self.own.components["MemoryArray"].frequency

            message = "EntanglementGeneration receive_data {} {} {} {}".format(classical_delay, 
                                                                               quantum_delay,
                                                                               num_memories,
                                                                               frequency)
            self.own.send_message(src, message)

        elif msg_type == "receive_data":
            if self.end_nodes[0].name == src:
                index = 0
            else:
                index = 1

            self.classical_delays[index] = int(msg[1])
            self.quantum_delays[index] = int(msg[2])
            self.num_memories[index] = int(msg[3])
            self.frequencies[index] = int(msg[4])

            # check if we have both sets of information
            if -1 not in self.classical_delays:
                # use frequency to determine read rate
                assert self.frequencies[0] == self.frequencies[1]
                start_time_0 = self.own.timeline.now() + max(self.classical_delays)\
                                                       + max(self.quantum_delays[1] - self.quantum_delays[0], 0)
                start_time_1 = self.own.timeline.now() + max(self.classical_delays)\
                                                       + max(self.quantum_delays[0] - self.quantum_delays[1], 0)
                # add some extra delay to the start time for jitter
                message_0 = "EntanglementGeneration send_photons {}".format(start_time_0)
                message_1 = "EntanglementGeneration send_photons {}".format(start_time_1)
                self.own.send_message(self.end_nodes[0].name, message_0)
                self.own.send_message(self.end_nodes[1].name, message_1)

                light_time = int(round(min(self.num_memories) / self.frequencies[0] * 1e12))
                self.start_time = self.own.timeline.now() + max(self.classical_delays) + max(self.quantum_delays)
                process_time = self.start_time + light_time
                process = Process(self, "end_photons", [])
                event = Event(process_time, process)
                self.own.timeline.schedule(event)

        elif msg_type == "send_photons":
            start_time = int(msg[1])
            process = Process(self.own.components["MemoryArray"], "write", [])
            event = Event(start_time, process)
            self.own.timeline.schedule(event)

        elif msg_type == "receive_bsm":
            other_node = msg[1]
            msg = msg[2:]

            # parse bsm result
            times_and_bits = []
            if msg[0] != "[]":
                for val in msg:
                    times_and_bits.append(int(re.sub("[],[]", "", val)))
            bsm_res = []
            bsm_single = []
            for i, val in enumerate(times_and_bits):
                bsm_single.append(val)
                if i % 2:
                    bsm_res.append(bsm_single)
                    bsm_single = []

            for res in bsm_res:
                # calculate index
                i = int(round((res[0] - self.start_time) * self.frequencies[0] * 1e-12))

                # record entanglement
                self.own.components["MemoryArray"][i].entangled_memory["node_id"] = other_node
                self.own.components["MemoryArray"][i].entangled_memory["memo_id"] = i

                # send to entanglement purification
                self._pop(i, other_node)

        else:
            raise Exception("unknown message of type '{}' received by EntanglementGeneration on node '{}'"
                            .format(msg_type, self.own.name))


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

    def pop(self, memory_index=0, another_node=""):
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
        print("{}: {}".format(kept_memo, local_memory[kept_memo].fidelity))
        print("{}: {}".format(measured_memo, local_memory[measured_memo].fidelity))
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
            self._push(kept_memo)

        local_memory[measured_memo].fidelity = 0
        local_memory[measured_memo].entangled_memory['node_id'] = None
        local_memory[measured_memo].entangled_memory['memo_id'] = None
        self._push(measured_memo)
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
        self._push(measured_memo)

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

    def three_nodes_test():
        # create timeline
        tl = timeline.Timeline()

        # create nodes alice, bob, charlie
        alice = topology.Node("alice", tl)
        bob = topology.Node("bob", tl)
        charlie = topology.Node("charlie", tl)

        # create classical channels
        cc1 = topology.ClassicalChannel("cc1", tl, distance=1e3, delay=1e5)
        cc2 = topology.ClassicalChannel("cc2", tl, distance=1e3, delay=1e5)
        cc3 = topology.ClassicalChannel("cc3", tl, distance=1e3, delay=1e5)
        cc1.add_end(alice)
        cc1.add_end(charlie)
        cc2.add_end(bob)
        cc2.add_end(charlie)
        cc3.add_end(alice)
        cc3.add_end(bob)
        alice.assign_cchannel(cc1)
        charlie.assign_cchannel(cc1)
        bob.assign_cchannel(cc2)
        charlie.assign_cchannel(cc2)
        alice.assign_cchannel(cc3)
        bob.assign_cchannel(cc3)

        # create quantum channels
        qc1 = topology.QuantumChannel("qc1", tl, distance=1e3)
        qc2 = topology.QuantumChannel("qc2", tl, distance=1e3)
        alice.qchannels = {"charlie": qc1}
        bob.qchannels = {"charlie": qc2}

        # create memories on nodes
        NUM_MEMORY = 100
        memory_params_alice = {"fidelity": 0.6, "direct_receiver": qc1}
        memory_params_bob = {"fidelity": 0.6, "direct_receiver": qc2}
        alice_memo_array = topology.MemoryArray("alice memory array",
                                                tl, num_memories=NUM_MEMORY,
                                                memory_params=memory_params_alice)
        bob_memo_array = topology.MemoryArray("bob memory array",
                                              tl, num_memories=NUM_MEMORY,
                                              memory_params=memory_params_bob)
        alice.components['MemoryArray'] = alice_memo_array
        bob.components['MemoryArray'] = bob_memo_array
        qc1.set_sender(alice_memo_array)
        qc2.set_sender(bob_memo_array)

        # create BSM
        detectors = [{"efficiency": 0.7, "dark_count": 100, "time_resolution": 150, "count_rate": 25000000}] * 2
        bsm = topology.BSM("charlie bsm", tl, encoding_type=encoding.ensemble, detectors=detectors)
        charlie.components['BSM'] = bsm
        qc1.set_receiver(bsm)
        qc2.set_receiver(bsm)

        # create alice protocol stack
        egA = EntanglementGeneration(alice)
        bbpsswA = BBPSSW(alice, threshold=0.9)
        egA.upper_protocols.append(bbpsswA)
        bbpsswA.lower_protocols.append(egA)
        alice.protocols.append(egA)
        alice.protocols.append(bbpsswA)

        # create bob protocol stack
        egB = EntanglementGeneration(bob)
        bbpsswB = BBPSSW(bob, threshold=0.9)
        egB.upper_protocols.append(bbpsswB)
        bbpsswB.lower_protocols.append(egB)
        bob.protocols.append(egB)
        bob.protocols.append(bbpsswB)

        # create charlie protocol stack
        egC = EntanglementGeneration(charlie, is_middle=True, end_nodes=[alice, bob])
        charlie.protocols.append(egC)

        # schedule events
        process = Process(egC, "pop", [True])
        event = Event(0, process)
        tl.schedule(event)

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

    three_nodes_test()
    # multi_nodes_test(3)
