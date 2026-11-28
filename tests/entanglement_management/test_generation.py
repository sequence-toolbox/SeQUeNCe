import numpy as np
import pytest

from sequence.constants import (BARRET_KOK, BELL_DIAGONAL_STATE_FORMALISM, KET_VECTOR_FORMALISM, 
                                SECOND, SINGLE_HERALDED, SINGLE_HERALDED_SURROGATE)
from sequence.components.bsm import *
from sequence.components.memory import MemoryArray
from sequence.components.optical_channel import *
from sequence.kernel.timeline import Timeline
from sequence.kernel.quantum_manager import QuantumManager
from sequence.entanglement_management.generation import (
    BarretKokA, BarretKokB,
    EntanglementGenerationA, EntanglementGenerationB,
    EntanglementGenerationMessage,
    GenerationMsgType,
    SingleHeraldedA, SingleHeraldedB,
    SingleHeraldedASurrogate,
)

from sequence.topology.node import Node
from sequence.utils.miscellaneous import set_type_and_formalism


class FakeReservation:
    def __init__(self, path):
        self.path = path


class FakeRule:
    def __init__(self, path):
        self.reservation = FakeReservation(path)


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
    msg = EntanglementGenerationMessage(GenerationMsgType.NEGOTIATE, "alice", protocol_type=BARRET_KOK, qc_delay=1)

    assert msg.receiver == "alice"
    assert msg.msg_type == GenerationMsgType.NEGOTIATE
    assert msg.qc_delay == 1


def test_generation_protocol_registry_and_factory_selection():
    old_formalism = QuantumManager.get_active_formalism()

    try:
        protocols_a = set(EntanglementGenerationA.list_protocols())
        protocols_b = set(EntanglementGenerationB.list_protocols())

        assert {BARRET_KOK, SINGLE_HERALDED}.issubset(protocols_a)
        assert {BARRET_KOK, SINGLE_HERALDED}.issubset(protocols_b)

        QuantumManager.set_global_manager_formalism(KET_VECTOR_FORMALISM)
        EntanglementGenerationA.set_global_type(BARRET_KOK)
        EntanglementGenerationB.set_global_type(BARRET_KOK)
        tl = Timeline()
        router = Node("e0", tl)
        router.memory_array = MemoryArray("e0.memory_array", tl, num_memories=1)
        bsm_node = FakeBSMNode("m0", tl)

        protocol_a = EntanglementGenerationA.create(router, "eg_e0", middle="m0", other="e1", 
                                                    memory=router.memory_array[0])
        protocol_b = EntanglementGenerationB.create(bsm_node, "eg_m0", others=["e0", "e1"])

        assert isinstance(protocol_a, BarretKokA)
        assert isinstance(protocol_b, BarretKokB)

        QuantumManager.set_global_manager_formalism(BELL_DIAGONAL_STATE_FORMALISM)
        EntanglementGenerationA.set_global_type(SINGLE_HERALDED)
        EntanglementGenerationB.set_global_type(SINGLE_HERALDED)
        tl = Timeline()
        router = Node("e0", tl)
        router.memory_array = MemoryArray("e0.memory_array", tl, num_memories=1)
        bsm_node = FakeBSMNode("m0", tl)

        protocol_a = EntanglementGenerationA.create(router, "eg_e0", middle="m0", other="e1", 
                                                    memory=router.memory_array[0])
        protocol_b = EntanglementGenerationB.create(bsm_node, "eg_m0", others=["e0", "e1"])

        assert isinstance(protocol_a, SingleHeraldedA)
        assert isinstance(protocol_b, SingleHeraldedB)
    finally:
        EntanglementGenerationA.set_global_type(BARRET_KOK)
        EntanglementGenerationB.set_global_type(BARRET_KOK)
        QuantumManager.set_global_manager_formalism(old_formalism)


def test_single_heralded_generation_requires_bell_diagonal_formalism():
    old_formalism = QuantumManager.get_active_formalism()

    try:
        QuantumManager.set_global_manager_formalism(KET_VECTOR_FORMALISM)
        EntanglementGenerationA.set_global_type(SINGLE_HERALDED)
        tl = Timeline()
        router = Node("e0", tl)
        router.memory_array = MemoryArray("e0.memory_array", tl, num_memories=1)

        with pytest.raises(AssertionError, match="supports Bell diagonal state formalism"):
            EntanglementGenerationA.create(router, "eg_e0", middle="m0", other="e1", memory=router.memory_array[0])
    finally:
        EntanglementGenerationA.set_global_type(BARRET_KOK)
        QuantumManager.set_global_manager_formalism(old_formalism)


def test_generation_receive_message():
    tl = Timeline()
    node = Node("e1", tl)
    m0 = FakeBSMNode("m1", tl)
    qc = QuantumChannel("qc_nodem1", tl, 0, 1e3)
    qc.frequency = SECOND
    qc.set_ends(node, m0.name)
    node.memory_array = MemoryArray("memory", tl)
    node.assign_cchannel(ClassicalChannel("cc", tl, 0, delay=1), "m1")

    eg = EntanglementGenerationA.create(node, "EG", middle="m1", other="e2", memory=node.memory_array[0])
    eg.qc_delay = 1

    # negotiate message
    msg = EntanglementGenerationMessage(GenerationMsgType.NEGOTIATE_ACK, "EG", protocol_type=BARRET_KOK, emit_time=0)
    eg.received_message("e2", msg)
    assert eg.expected_time == 1
    assert len(tl.events.data) == 2  # two excites, flip state, end time


def test_generation_pop():
    class DumbBSM():
        def __init__(self):
            self.resolution = 1
            self.encoding = "single_atom"

    class DumbNode():
        def __init__(self):
            self.name = "none"
            self.protocols = []
            self.messages = []
            self.bsm = DumbBSM()

        def send_message(self, destination, message):
            self.messages.append([destination, message])

    m0 = DumbNode()

    middle = EntanglementGenerationB.create(m0, "middle", others=["e0", "e1"])

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

    tl = Timeline(SECOND)
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

    protocol0 = EntanglementGenerationA.create(e0, "e0prot", middle="m0", other="e1", memory=e0.memory_array[0])
    protocol1 = EntanglementGenerationA.create(e1, "e1prot", middle="m0", other="e0", memory=e1.memory_array[0])
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

    assert e0.memory_array[0].expiration_event.time > SECOND


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
                cc = ClassicalChannel("cc_%s_%s" % (src.name, dst.name), tl, 1e3, delay=1e9)
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
    eg_m0 = EntanglementGenerationB.create(m0, "eg_m0", others=["e0", "e1"])
    m0.bsm.attach(eg_m0)

    tl.init()

    protocols_e0 = []
    protocols_e1 = []

    for i in range(NUM_TESTS):
        name0, name1 = [f"eg_e{j}[{i}]" for j in range(2)]
        protocol0 = EntanglementGenerationA.create(e0, name0, middle="m0", other="e1", memory=e0.memory_array[i])
        e0.protocols.append(protocol0)
        protocols_e0.append(protocol0)
        protocol1 = EntanglementGenerationA.create(e1, name1, middle="m0", other="e0", memory=e1.memory_array[i])
        e1.protocols.append(protocol1)
        protocols_e1.append(protocol1)
        protocol0.set_others(protocol1.name, e1.name, [e1.memory_array[i].name])
        protocol1.set_others(protocol0.name, e0.name, [e0.memory_array[i].name])

        for protocol in [protocols_e0[i], protocols_e1[i]]:
            process = Process(protocol, "start", [])
            event = Event(i * SECOND, process)
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
                cc = ClassicalChannel("cc_%s%s" % (n1.name, n2.name), tl, 1e3, delay=1e9)
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
    eg_m0 = EntanglementGenerationB.create(m0, "eg_m0", others=["e0", "e1"])
    m0.bsm.attach(eg_m0)

    tl.init()

    protocols_e0 = []
    protocols_e1 = []

    for i in range(NUM_TESTS):
        name0 = "eg_e0[{}]".format(i)
        name1 = "eg_e1[{}]".format(i)
        protocol0 = EntanglementGenerationA.create(e0, name0, middle="m0", other="e1", memory=e0.memory_array[i])
        e0.protocols.append(protocol0)
        protocols_e0.append(protocol0)
        protocol1 = EntanglementGenerationA.create(e1, name1, middle="m0", other="e0", memory=e1.memory_array[i])
        e1.protocols.append(protocol1)
        protocols_e1.append(protocol1)
        protocol0.set_others(protocol1.name, e1.name, [e1.memory_array[i].name])
        protocol1.set_others(protocol0.name, e0.name, [e0.memory_array[i].name])

        process = Process(protocols_e0[i], "start", [])
        event = Event(i * SECOND, process)
        tl.schedule(event)
        process = Process(protocols_e1[i], "start", [])
        event = Event(i * SECOND, process)
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


def test_single_heralded_surrogate():
    old_type = EntanglementGenerationA.get_global_type()
    old_formalism = QuantumManager.get_active_formalism()

    NUM_TESTS = 100
    FIDELITY = 0.75
    try:
        SingleHeraldedASurrogate.surrogates = {}
        set_type_and_formalism(SINGLE_HERALDED_SURROGATE, BELL_DIAGONAL_STATE_FORMALISM)
        tl = Timeline()
        e0 = FakeRouter("e0", tl)
        m0 = FakeBSMNode("m0", tl)
        e1 = FakeRouter("e1", tl)
        e0.set_seed(0)
        m0.set_seed(1)
        e1.set_seed(2)
        # Use the hardware names expected by the surrogate.
        for node in (e0, e1):
            qc = QuantumChannel(f"qc-{node.name}-m0", tl, 0, 1e3)
            qc.set_ends(node, m0.name)
        for src in (e0, e1, m0):
            for dst in (e0, e1, m0):
                if src.name != dst.name:
                    cc = ClassicalChannel(f"cc-{src.name}-{dst.name}", tl, 1e3, delay=1e9)
                    cc.set_ends(src, dst.name)

        for node in (e0, e1):
            node.memory_array = MemoryArray(f"{node.name}.memory_array", tl, efficiency=0.5, 
                                            fidelity=FIDELITY, num_memories=NUM_TESTS)
            node.memory_array.owner = node
        detectors = [{"efficiency": 1, "count_rate": 1e11}] * 2
        m0.bsm = SingleHeraldedBSM("m0.BSM", tl, detectors=detectors)
        m0.bsm.owner = m0
        eg_m0 = EntanglementGenerationB.create(m0, "eg_m0", others=["e0", "e1"])
        m0.bsm.attach(eg_m0)

        tl.init()
        # initiate the surrogate
        SingleHeraldedASurrogate.set_surrogate_parameter_from_timeline(tl)

        for i in range(NUM_TESTS):
            protocol0 = EntanglementGenerationA.create(e0, f"EGA.{e0.memory_array[i].name}", middle="m0", other="e1",
                                                       memory=e0.memory_array[i])
            protocol1 = EntanglementGenerationA.create(e1, f"EGA.{e1.memory_array[i].name}", middle="m0", other="e0", 
                                                       memory=e1.memory_array[i])
            for protocol in (protocol0, protocol1):
                assert isinstance(protocol, SingleHeraldedASurrogate)
                protocol.rule = FakeRule(["e0", "e1"])
                protocol.owner.protocols.append(protocol)
            protocol0.set_others(protocol1.name, e1.name, [e1.memory_array[i].name])
            protocol1.set_others(protocol0.name, e0.name, [e0.memory_array[i].name])
            assert protocol1.surrogate_parameter_is_set()
            assert protocol1.surrogate is not None
            for protocol in (protocol0, protocol1):
                process = Process(protocol, "start", [])
                event = Event(i * SECOND, process)
                tl.schedule(event)

        tl.run()

        assert len(e0.resource_manager.log) == NUM_TESTS
        assert len(e1.resource_manager.log) == NUM_TESTS
        for i in range(NUM_TESTS):
            for node, remote in ((e0, e1), (e1, e0)):
                memory, state = node.resource_manager.log[i]
                assert state == "ENTANGLED"
                assert memory.fidelity == FIDELITY
                assert memory.entangled_memory["node_id"] == remote.name
                assert memory.entangled_memory["memo_id"] == remote.memory_array[i].name
            memory0, memory1 = e0.memory_array[i], e1.memory_array[i]
            state0 = tl.quantum_manager.get(memory0.qstate_key)
            assert state0 is tl.quantum_manager.get(memory1.qstate_key)
            assert np.allclose(state0.state, [FIDELITY] + [(1 - FIDELITY) / 3] * 3)
        assert m0.msg_log == []
    finally:
        set_type_and_formalism(old_type, old_formalism)
