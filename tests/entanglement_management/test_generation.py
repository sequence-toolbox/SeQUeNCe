import numpy as np

from sequence.components.bsm import *
from sequence.components.memory import MemoryArray
from sequence.components.optical_channel import *
from sequence.kernel.timeline import Timeline
from sequence.entanglement_management.generation import *
from sequence.topology.node import Node


class ResourceManager:
    def __init__(self):
        self.log = []

    def update(self, protocol, memory, state):
        self.log.append((memory, state))


class FakeRouter(Node):
    def __init__(self, name, tl, **kwargs):
        super().__init__(name, tl)
        self.resource_manager = ResourceManager()
        self.memory_array = None

    def init(self):
        self.memory_array.add_receiver(self)

    def get(self, photon, **kwargs):
        dst = kwargs["dst"]
        self.send_qubit(dst, photon)


class FakeBSMNode(Node):
    def __init__(self, name, tl, **kwargs):
        super().__init__(name, tl)
        self.msg_log = []

    def receive_message(self, src: str, msg: "Message"):
        self.msg_log.append((self.timeline.now(), src, msg))
        super().receive_message(src, msg)

    def receive_qubit(self, src: str, qubit):
        self.bsm.get(qubit)


def test_generation_message():
    msg = EntanglementGenerationMessage(GenerationMsgType.NEGOTIATE, "alice", qc_delay=1)

    assert msg.receiver == "alice"
    assert msg.msg_type == GenerationMsgType.NEGOTIATE
    assert msg.qc_delay == 1


def test_generation_receive_message():
    tl = Timeline()
    node = Node("e1", tl)
    m0 = FakeBSMNode("m1", tl)
    qc = QuantumChannel("qc_nodem1", tl, 0, 1e3)
    qc.frequency = 1e12
    qc.set_ends(node, m0.name)
    node.memory_array = MemoryArray("memory", tl)
    node.assign_cchannel(ClassicalChannel("cc", tl, 0, delay=1), "m1")

    eg = EntanglementGenerationA(node, "EG", middle="m1", other="e2", memory=node.memory_array[0])
    eg.qc_delay = 1

    # negotiate message
    msg = EntanglementGenerationMessage(GenerationMsgType.NEGOTIATE_ACK, "EG", emit_time=0)
    eg.received_message("e2", msg)
    assert eg.expected_time == 1
    assert len(tl.events.data) == 2  # two excites, flip state, end time


def test_generation_pop():
    class DumbBSM():
        def __init__(self):
            self.resolution = 1

    class DumbNode():
        def __init__(self):
            self.name = "none"
            self.protocols = []
            self.messages = []
            self.bsm = DumbBSM()

        def send_message(self, destination, message):
            self.messages.append([destination, message])

    m0 = DumbNode()

    middle = EntanglementGenerationB(m0, "middle", others=["e0", "e1"])

    # BSM result
    middle.bsm_update(m0.bsm, {'info_type': "BSM_res", 'res': 0, 'time': 100})
    assert len(m0.messages) == 2
    assert m0.messages[0][0] == "e0"
    assert m0.messages[1][0] == "e1"
    assert m0.messages[0][1].msg_type == m0.messages[1][1].msg_type == GenerationMsgType.MEAS_RES


def test_generation_expire():
    class DumbBSM:
        def __init__(self):
            pass

        def get(self, qubit):
            pass

    tl = Timeline(1e12)
    e0 = FakeRouter("e0", tl)
    e1 = FakeRouter("e1", tl)
    m0 = FakeBSMNode("m0", tl)

    qc0 = QuantumChannel("qc_e0m0", tl, 0, 1e3)
    qc1 = QuantumChannel("qc_e1m0", tl, 0, 1e3)
    qc0.set_ends(e0, m0.name)
    qc1.set_ends(e1, m0.name)

    for src in [e0, e1, m0]:
        for dst in [e0, e1, m0]:
            if src.name != dst.name:
                cc = ClassicalChannel("cc_%s_%s" % (src.name, dst.name), tl,
                                      1e3, delay=4e11)
                cc.set_ends(src, dst.name)

    e0.memory_array = MemoryArray("e0mem", tl, coherence_time=1)
    e1.memory_array = MemoryArray("e1mem", tl, coherence_time=1)
    e0.memory_array.owner = e0
    e1.memory_array.owner = e1
    m0.bsm = DumbBSM()

    tl.init()

    protocol0 = EntanglementGenerationA(e0, "e0prot", middle="m0", other="e1", memory=e0.memory_array[0])
    protocol1 = EntanglementGenerationA(e1, "e1prot", middle="m0", other="e0", memory=e1.memory_array[0])
    e0.protocols.append(protocol0)
    e1.protocols.append(protocol1)
    protocol0.set_others(protocol1.name, e1.name, [e1.memory_array[0].name])
    protocol1.set_others(protocol0.name, e0.name, [e0.memory_array[0].name])

    for p in [protocol0, protocol1]:
        process = Process(p, "start", [])
        event = Event(0, process)
        tl.schedule(event)

    tl.init()
    tl.run()

    assert e0.memory_array[0].expiration_event.time > 1e12


def test_generation_run():
    NUM_TESTS = 100

    tl = Timeline()

    e0 = FakeRouter("e0", tl)
    m0 = FakeBSMNode("m0", tl)
    e1 = FakeRouter("e1", tl)
    e0.set_seed(0)
    m0.set_seed(1)
    e1.set_seed(2)

    # add connections
    qc0 = QuantumChannel("qc_e0m0", tl, 0, 1e3)
    qc1 = QuantumChannel("qc_e1m0", tl, 0, 1e3)
    qc0.set_ends(e0, m0.name)
    qc1.set_ends(e1, m0.name)

    for src in [e0, e1, m0]:
        for dst in [e0, e1, m0]:
            if src.name != dst.name:
                cc = ClassicalChannel("cc_%s_%s" % (src.name, dst.name), tl,
                                      1e3, delay=1e9)
                cc.set_ends(src, dst.name)

    # add hardware
    e0.memory_array = MemoryArray("e0.memory_array", tl, num_memories=NUM_TESTS)
    e0.memory_array.owner = e0
    e1.memory_array = MemoryArray("e1.memory_array", tl, num_memories=NUM_TESTS)
    e1.memory_array.owner = e1
    detectors = [{"efficiency": 1, "count_rate": 1e11}] * 2
    m0.bsm = make_bsm("m0.bsm", tl, encoding_type="single_atom", detectors=detectors)
    m0.bsm.owner = m0

    # add middle protocol
    eg_m0 = EntanglementGenerationB(m0, "eg_m0", others=["e0", "e1"])
    m0.bsm.attach(eg_m0)

    tl.init()

    protocols_e0 = []
    protocols_e1 = []

    for i in range(NUM_TESTS):
        name0, name1 = [f"eg_e{j}[{i}]" for j in range(2)]
        protocol0 = EntanglementGenerationA(e0, name0, middle="m0", other="e1", memory=e0.memory_array[i])
        e0.protocols.append(protocol0)
        protocols_e0.append(protocol0)
        protocol1 = EntanglementGenerationA(e1, name1, middle="m0", other="e0", memory=e1.memory_array[i])
        e1.protocols.append(protocol1)
        protocols_e1.append(protocol1)
        protocol0.set_others(protocol1.name, e1.name, [e1.memory_array[i].name])
        protocol1.set_others(protocol0.name, e0.name, [e0.memory_array[i].name])

        for protocol in [protocols_e0[i], protocols_e1[i]]:
            process = Process(protocol, "start", [])
            event = Event(i * 1e12, process)
            tl.schedule(event)

    tl.run()

    assert len(e0.resource_manager.log) == NUM_TESTS
    assert len(e1.resource_manager.log) == NUM_TESTS
    empty_count = 0
    for i in range(NUM_TESTS):
        if e0.resource_manager.log[i][1] == "RAW":
            empty_count += 1
        else:
            assert e0.resource_manager.log[i][1] == "ENTANGLED"
            memory0 = e0.resource_manager.log[i][0]
            memory1 = e1.resource_manager.log[i][0]
            assert memory0.fidelity == memory0.raw_fidelity
            assert memory1.fidelity == memory1.raw_fidelity
            assert memory0.entangled_memory["node_id"] == e1.name
            assert memory1.entangled_memory["node_id"] == e0.name

    ratio = empty_count / NUM_TESTS
    assert abs(ratio - 0.5) < 0.1
    

def test_generation_fidelity_ket():
    NUM_TESTS = 100
    FIDELITY = 0.75

    tl = Timeline()

    e0 = FakeRouter("e0", tl)
    m0 = FakeBSMNode("m0", tl)
    e1 = FakeRouter("e1", tl)
    e0.set_seed(0)
    m0.set_seed(1)
    e1.set_seed(2)

    # add connections
    qc0 = QuantumChannel("qc_e0m0", tl, 0, 1e3)
    qc1 = QuantumChannel("qc_e1m0", tl, 0, 1e3)
    qc0.set_ends(e0, m0.name)
    qc1.set_ends(e1, m0.name)

    for n1 in [e0, e1, m0]:
        for n2 in [e0, e1, m0]:
            if n1 != n2:
                cc = ClassicalChannel("cc_%s%s" % (n1.name, n2.name), tl, 1e3,
                                      delay=1e9)
                cc.set_ends(n1, n2.name)

    # add hardware
    e0.memory_array = MemoryArray("e0.memory_array", tl, fidelity=FIDELITY, num_memories=NUM_TESTS)
    e0.memory_array.owner = e0
    e1.memory_array = MemoryArray("e1.memory_array", tl, fidelity=FIDELITY, num_memories=NUM_TESTS)
    e1.memory_array.owner = e1
    detectors = [{"efficiency": 1, "count_rate": 1e11}] * 2
    m0.bsm = make_bsm("m0.bsm", tl, encoding_type="single_atom", detectors=detectors)
    m0.bsm.owner = m0

    # add middle protocol
    eg_m0 = EntanglementGenerationB(m0, "eg_m0", others=["e0", "e1"])
    m0.bsm.attach(eg_m0)

    tl.init()

    protocols_e0 = []
    protocols_e1 = []

    for i in range(NUM_TESTS):
        name0 = "eg_e0[{}]".format(i)
        name1 = "eg_e1[{}]".format(i)
        protocol0 = EntanglementGenerationA(e0, name0, middle="m0", other="e1", memory=e0.memory_array[i])
        e0.protocols.append(protocol0)
        protocols_e0.append(protocol0)
        protocol1 = EntanglementGenerationA(e1, name1, middle="m0", other="e0", memory=e1.memory_array[i])
        e1.protocols.append(protocol1)
        protocols_e1.append(protocol1)
        protocol0.set_others(protocol1.name, e1.name, [e1.memory_array[i].name])
        protocol1.set_others(protocol0.name, e0.name, [e0.memory_array[i].name])

        process = Process(protocols_e0[i], "start", [])
        event = Event(i * 1e12, process)
        tl.schedule(event)
        process = Process(protocols_e1[i], "start", [])
        event = Event(i * 1e12, process)
        tl.schedule(event)

    tl.init()
    tl.run()

    desired = np.array([complex(np.sqrt(1 / 2)), complex(0),
                        complex(0), complex(np.sqrt(1 / 2))])
    correct = 0
    total = 0
    for mem in e0.memory_array:
        if mem.fidelity > 0:
            total += 1
            mem_state = tl.quantum_manager.get(mem.qstate_key).state
            if np.array_equal(desired, mem_state):
                correct += 1

    assert total > 0, "More trials needed; insufficient successes"
    ratio = correct / total
    assert abs(ratio - FIDELITY) < 0.1

