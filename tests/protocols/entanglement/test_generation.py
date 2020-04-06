from sequence.components.memory import MemoryArray, AtomMemory
from sequence.components.optical_channel import *
from sequence.kernel.timeline import Timeline
from sequence.protocols.entanglement.generation import *
from sequence.topology.node import Node


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


def test_generation_push():
    return
    tl = Timeline()

    node = QuantumRepeater("e0", tl)
    node.eg.middles = ["m0"]
    node.eg.others = ["e1"]

    node.init()

    node.eg.push(index=0)

    assert node.eg.add_list[0] == [0]

def test_generation_pop():
    return
    class DumbMemory():
        def __init__(self):
            self.entangled_memory = {"memo_id": 0}

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

    e0 = DumbNode()
    m0 = DumbNode()

    end = EntanglementGeneration(e0, others=["e0"], middles=["m0"])
    end.set_params()
    end.memory_destinations = ["m0"]
    end.memory_array = [DumbMemory()]
    middle = EntanglementGeneration(m0, others=["e0","e1"])

    # BSM result
    middle.pop("BSM_res", res=0)
    
    assert len(m0.messages) == 2
    assert m0.messages[0][0] == "e0"
    assert m0.messages[1][0] == "e1"
    assert m0.messages[0][1].msg_type == m0.messages[1][1].msg_type == "MEAS_RES"

    # expire with memory index
    end.memory_indices[0] = [0]
    end.memory_stage[0] = [0]
    end.pop("expired_memory", index=0)
    
    assert end.memory_stage[0][0] == -1

    # expire without memory index
    end.memory_indices[0] = []
    end.memory_stage[0] = []
    end.pop("expired_memory", index=0)

    assert end.add_list[0][0] == 0
    assert len(e0.messages) == 1
    assert e0.messages[0][0] == "e0"
    assert e0.messages[0][1].msg_type == "EXPIRE"


