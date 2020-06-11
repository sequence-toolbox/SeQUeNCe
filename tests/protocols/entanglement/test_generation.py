from sequence.components.bsm import *
from sequence.components.memory import MemoryArray
from sequence.components.optical_channel import *
from sequence.kernel.timeline import Timeline
from sequence.protocols.entanglement.generation import *
from sequence.topology.node import Node


class ResourceManager():
    def __init__(self):
        self.log = []

    def update(self, protocol, memory, state):
        self.log.append((memory, state))


class FakeNode(Node):
    def __init__(self, name, tl, **kwargs):
        Node.__init__(self, name, tl)
        self.msg_log = []
        self.resource_manager = ResourceManager()

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
    m0 = FakeNode("m1", tl)
    qc = QuantumChannel("qc_nodem1", tl, 0, 1e3)
    qc.set_ends(node, m0)
    node.memory_array = MemoryArray("", tl)
    node.assign_cchannel(ClassicalChannel("", tl, 0, delay=1), "m1")

    eg = EntanglementGenerationA(node, "EG", middle="m1", other="e2", memory=node.memory_array[0])
    eg.qc_delay = 1

    # negotiate message
    msg = EntanglementGenerationMessage(GenerationMsgType.NEGOTIATE_ACK, "EG", emit_time=0)
    assert eg.received_message("e2", msg) is True
    assert eg.expected_time == 1
    assert len(tl.events.data) == 2  # excite and next start time


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
    middle.pop("BSM_res", res=0)
    
    assert len(m0.messages) == 2
    assert m0.messages[0][0] == "e0"
    assert m0.messages[1][0] == "e1"
    assert m0.messages[0][1].msg_type == m0.messages[1][1].msg_type == GenerationMsgType.MEAS_RES


def test_generation_expire():
    class DumbBSM():
        def __init__(self):
            pass

        def get(self, qubit):
            pass

    tl = Timeline(1e12)
    e0 = Node("e0", tl)
    e1 = Node("e1", tl)
    m0 = FakeNode("m0", tl)

    qc0 = QuantumChannel("qc_e0m0", tl, 0, 1e3)
    qc1 = QuantumChannel("qc_e1m0", tl, 0, 1e3)
    qc0.set_ends(e0, m0)
    qc1.set_ends(e1, m0)
    cc0 = ClassicalChannel("cc_e0m0", tl, 1e3, delay=1e12)
    cc1 = ClassicalChannel("cc_e1m0", tl, 1e3, delay=1e12)
    cc2 = ClassicalChannel("cc_e0e1", tl, 2e3, delay=1e9)
    cc0.set_ends(e0, m0)
    cc1.set_ends(e1, m0)
    cc2.set_ends(e0, e1)

    e0.memory_array = MemoryArray("e0mem", tl, coherence_time=1)
    e1.memory_array = MemoryArray("e1mem", tl, coherence_time=1)
    e0.memory_array.owner = e0
    e1.memory_array.owner = e1
    m0.bsm = DumbBSM()

    tl.init()

    protocol0 = EntanglementGenerationA(e0, "e0prot", middle="m0", other="e1", memory=e0.memory_array[0])
    protocol1 = EntanglementGenerationA(e1, "e1prot", middle="m0", other="e0", memory=e1.memory_array[0])
    protocol0.primary = True
    e0.protocols.append(protocol0)
    e1.protocols.append(protocol1)
    protocol0.set_others(protocol1)
    protocol1.set_others(protocol0)

    process = Process(protocol0, "start", [])
    event = Event(0, process)
    tl.schedule(event)
    process = Process(protocol1, "start", [])
    event = Event(0, process)
    tl.schedule(event)

    tl.run()

    assert e0.memory_array[0].expiration_event.time > 1e12


def test_generation_run():
    numpy.random.seed(0)
    NUM_TESTS = 200

    tl = Timeline()

    e0 = FakeNode("e0", tl)
    m0 = FakeNode("m0", tl)
    e1 = FakeNode("e1", tl)

    # add connections
    cc = ClassicalChannel("cc_e0m0", tl, 1e3)
    cc.set_ends(e0, m0)
    cc = ClassicalChannel("cc_e1m0", tl, 1e3)
    cc.set_ends(e1, m0)
    cc = ClassicalChannel("cc_e0e1", tl, 1e3)
    cc.set_ends(e0, e1)
    qc = QuantumChannel("qc_e0m0", tl, 0, 1e3)
    qc.set_ends(e0, m0)
    qc = QuantumChannel("qc_e1m0", tl, 0, 1e3)
    qc.set_ends(e1, m0)

    # add hardware
    e0.memory_array = MemoryArray("e0.memory_array", tl, num_memories=NUM_TESTS)
    e0.memory_array.owner = e0
    e1.memory_array = MemoryArray("e1.memory_array", tl, num_memories=NUM_TESTS)
    e1.memory_array.owner = e1
    detectors = [{"efficiency": 1}] * 2
    m0.bsm = make_bsm("m0.bsm", tl, encoding_type="single_atom", detectors=detectors)

    # add middle protocol
    eg_m0 = EntanglementGenerationB(m0, "eg_m0", others=["e0", "e1"])
    m0.bsm.upper_protocols.append(eg_m0)

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
        protocol0.set_others(protocol1)
        protocol1.set_others(protocol0)

        process = Process(protocols_e0[i], "start", [])
        event = Event(i * 1e12, process)
        tl.schedule(event)
        process = Process(protocols_e1[i], "start", [])
        event = Event(i * 1e12, process)
        tl.schedule(event)

    tl.run()

    empty_count = 0
    for i in range(NUM_TESTS):
        if e0.resource_manager.log[i][1] == "RAW":
            empty_count += 1

    ratio = empty_count / NUM_TESTS
    assert abs(ratio - 0.5) < 0.1


