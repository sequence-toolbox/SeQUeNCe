import numpy
from sequence.components.memory import MemoryArray, AtomMemory
from sequence.components.optical_channel import *
from sequence.components.bsm import *
from sequence.kernel.timeline import Timeline
from sequence.protocols.entanglement.generation import *
from sequence.topology.node import Node


class ResourceManager():
    def __init__(self):
        self.log = []

    def update(self, memory, state):
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
    msg = EntanglementGenerationMessage("NEGOTIATE", "alice", qc_delay=1)

    assert msg.receiver == "alice"
    assert msg.msg_type == "NEGOTIATE"
    assert msg.qc_delay == 1


def test_generation_init_func():
    tl = Timeline()
    node = Node("e1", tl)
    node.memory_array = MemoryArray("", tl)
    eg = EntanglementGenerationA(node, "EG", middle="m1", other="e2", other_protocol="e1")

    eg.init()

    assert type(eg.memory) == AtomMemory


def test_generation_receive_message():
    tl = Timeline()
    node = Node("e1", tl)
    node.memory_array = MemoryArray("", tl)
    node.assign_cchannel(ClassicalChannel("", tl, 0, 0, delay=1), "m1")

    eg = EntanglementGenerationA(node, "EG", middle="m1", other="e2", other_protocol="e1")
    eg.qc_delay = 1
    eg.init()

    # unknown node
    msg = EntanglementGenerationMessage("NEGOTIATE_ACK", "EG", emit_time=1)
    assert eg.received_message("e3", msg) is False

    # negotiate message
    msg = EntanglementGenerationMessage("NEGOTIATE_ACK", "EG", emit_time=1)
    assert eg.received_message("e2", msg) is True
    assert eg.expected_time == 2
    assert len(tl.events.data) == 2 # excite and next start time


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

    middle = EntanglementGenerationB(m0, "middle", others=["e0","e1"], other_protocols=["eg0", "eg1"])

    # BSM result
    middle.pop("BSM_res", res=0)
    
    assert len(m0.messages) == 2
    assert m0.messages[0][0] == "e0"
    assert m0.messages[1][0] == "e1"
    assert m0.messages[0][1].msg_type == m0.messages[1][1].msg_type == "MEAS_RES"


def test_generation_run():
    numpy.random.seed(2)
    NUM_TESTS = 1 

    tl = Timeline()

    e0 = FakeNode("e0", tl)
    m0 = FakeNode("m0", tl)
    e1 = FakeNode("e1", tl)

    # add connections
    cc = ClassicalChannel("cc_e0m0", tl, 0, 1e3)
    cc.set_ends(e0, m0)
    cc = ClassicalChannel("cc_e1m0", tl, 0, 1e3)
    cc.set_ends(e1, m0)
    cc = ClassicalChannel("cc_e0e1", tl, 0, 1e3)
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
    eg_m0 = EntanglementGenerationB(m0, "eg_m0", others=["e0", "e1"], other_protocols=["eg_e0", "eg_e1"])
    m0.bsm.upper_protocols.append(eg_m0)

    tl.init()

    for i in range(NUM_TESTS):
        eg_e0 = EntanglementGenerationA(e0, "eg_e0", middle="m0", other="e1", other_protocol="eg_e1", memory_index=i, another_index=i)
        eg_e0.primary = True
        eg_e0.debug = True
        eg_e1 = EntanglementGenerationA(e1, "eg_e1", middle="m0", other="e0", other_protocol="eg_e0", memory_index=i, another_index=i)

        process = Process(eg_e0, "init", [])
        event = Event(i * 1e12, process)
        tl.schedule(event)
        process = Process(eg_e1, "init", [])
        event = Event(i * 1e12, process)
        tl.schedule(event)

        process = Process(eg_e0, "start", [])
        event = Event(i * 1e12 + 1, process)
        tl.schedule(event)
        process = Process(eg_e1, "start", [])
        event = Event(i * 1e12 + 1, process)
        tl.schedule(event)

    tl.run()

    for i in range(NUM_TESTS):
        print(e0.resource_manager.log[i][1])


