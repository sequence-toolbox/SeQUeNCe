import numpy
import pytest

from sequence.protocols.entanglement.generation import *
from sequence.kernel.timeline import Timeline
from sequence.components.optical_channel import *
from sequence.components.memory import MemoryArray
from sequence.topology.node import Node

def test_message():
    msg = EntanglementGenerationMessage("EXPIRE", mem_num=10)

    assert msg.msg_type == "EXPIRE"
    assert msg.owner_type == type(EntanglementGeneration(None))
    assert msg.mem_num == 10

def test_generation_init():
    tl = Timeline()
    node = Node("e1", tl)

    generation = EntanglementGeneration(node, others=["e0","e2"], middles=["m0","m1"])

    assert len(generation.qc_delays) == 2
    assert len(generation.memory_indices) == 2

def test_generation_init_func():
    # TODO: add BSM, quantum channels
    tl = Timeline()
    node = Node("e1", tl)
    memo_array = MemoryArray("array", tl)
    node.assign_component(memo_array, "MemoryArray")

    generation = EntanglementGeneration(node, others=["e0","e2"], middles=["m0","m1"])
    generation.debug = True
    generation.init()

    assert generation.frequencies == [1, 1]

def test_message():
    tl = Timeline()

    node = Node("e1", tl)
    
    generation = EntanglementGeneration(node, others=["e0","e2"], middles=["m0","m1"])
    generation.debug = True

    # unknown message

    # unknown node
    msg = EntanglementGenerationMessage("EXPIRE", mem_num=10)
    assert generation.received_message("e3", msg) is False

    # expire message
    msg = EntanglementGenerationMessage("EXPIRE", mem_num=10)
    assert generation.received_message("e0", msg) is True
    assert generation.add_list[0] == [10]

def test_push():
    tl = Timeline()

    node = Node("e1", tl)
    qc = QuantumChannel("dummy_qc", tl, attenuation=0, distance=1)
    memo_array = MemoryArray("array", tl, num_memories=10, memory_params={})
    memo_array[0].direct_receiver = qc

    generation = EntanglementGeneration(node, others=["e0","e2"], middles=["m0","m1"])
    generation.debug = True
    generation.invert_map = {qc: "m0"}
    generation.memory_array = memo_array

    generation.push(index=0)

    assert generation.add_list[0] == [0]

def test_pop():
    class DumbNode():
        def __init__(self):
            self.name = "none"
            self.protocols = []
            self.messages = []
            self.components = {}

        def send_message(self, destination, message):
            self.messages.append([destination, message])

    class DumbBSM():
        def __init__(self):
            self.resolution = 1

    tl = Timeline()

    e1 = DumbNode()
    m0 = DumbNode()

    qc = QuantumChannel("dummy_qc", tl, attenuation=0, distance=1)
    memo_array = MemoryArray("array", tl, num_memories=10, memory_params={})
    memo_array[0].direct_receiver = qc
    bsm = DumbBSM()
    m0.components = {"BSM": bsm}

    generation = EntanglementGeneration(e1, others=["e0","e2"], middles=["m0","m1"])
    generation.debug = True
    generation.invert_map = {qc: "m0"}
    generation.memory_array = memo_array

    middle = EntanglementGeneration(m0, others=["e0","e1"])

    # BSM result
    middle.pop("BSM_res", res=0)
    
    assert len(m0.messages) == 2
    assert m0.messages[0][0] == "e0"
    assert m0.messages[1][0] == "e1"
    assert m0.messages[0][1].msg_type == m0.messages[1][1].msg_type == "MEAS_RES"

    # expire with memory index
    generation.memory_indices[0] = [0]
    generation.memory_stage[0] = [0]
    generation.pop("expired_memory", index=0)
    
    assert generation.memory_stage[0][0] == -1

    # expire without memory index
    generation.memory_indices[0] = []
    generation.memory_stage[0] = []
    generation.pop("expired_memory", index=0)

    assert generation.add_list[0][0] == 0
    assert len(e1.messages) == 1
    assert e1.messages[0][0] == "e0"
    assert e1.messages[0][1].msg_type == "EXPIRE"


