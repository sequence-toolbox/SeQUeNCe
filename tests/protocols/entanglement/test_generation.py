from sequence.components.memory import MemoryArray
from sequence.components.optical_channel import QuantumChannel
from sequence.kernel.timeline import Timeline
from sequence.protocols.entanglement.generation import EntanglementGeneration, EntanglementGenerationMessage
from sequence.topology.node import *


def test_generation_message():
    msg = EntanglementGenerationMessage("EXPIRE", mem_num=10)

    assert msg.msg_type == "EXPIRE"
    assert msg.owner_type == type(EntanglementGeneration(None))
    assert msg.mem_num == 10

def test_generation_init_func():
    # TODO: add BSM, quantum channels
    tl = Timeline()
    node = QuantumRepeater("e1", tl)
    node.eg.middles = ["m0", "m1"]
    node.eg.others = ["e0", "e2"]

    node.init()

    # test set_params
    assert len(node.eg.memory_indices) == 2
    # test automatic generation of memory destinations
    assert len(node.eg.memory_destinations) == 10
    # test internal memory management construction
    assert len(node.eg.memory_indices[0]) == 10
    assert len(node.eg.memory_indices[1]) == 0

def test_generation_receive_message():
    tl = Timeline()
    node = QuantumRepeater("e1", tl)
    node.eg.middles = ["m0", "m1"]
    node.eg.others = ["e0", "e2"]

    node.init()

    # unknown message

    # unknown node
    msg = EntanglementGenerationMessage("EXPIRE", mem_num=10)
    assert node.eg.received_message("e3", msg) is False

    # expire message
    msg = EntanglementGenerationMessage("EXPIRE", mem_num=10)
    assert node.eg.received_message("e0", msg) is True
    assert node.eg.add_list[0] == [10]

def test_generation_push():
    tl = Timeline()

    node = QuantumRepeater("e0", tl)
    node.eg.middles = ["m0"]
    node.eg.others = ["e1"]

    node.init()

    node.eg.push(index=0)

    assert node.eg.add_list[0] == [0]

def test_generation_pop():
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


