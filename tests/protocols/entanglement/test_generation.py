import numpy
import pytest

from sequence.protocols.entanglement.generation import *
from sequence.kernel.timeline import Timeline
from sequence.components.optical_channel import ClassicalChannel
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

    node0 = Node("e0", tl)
    node1 = Node("e1", tl)
    node2 = Node("e2", tl)
    
    generation = EntanglementGeneration(node1, others=["e0","e2"], middles=["m0","m1"])
    generation.debug = True

    # unknown message

    # unknown node
    msg = EntanglementGenerationMessage("EXPIRE", mem_num=10)
    assert generation.received_message("e3", msg) is False

    # expire
    msg = EntanglementGenerationMessage("EXPIRE", mem_num=10)
    assert generation.received_message("e0", msg) is True
    assert generation.add_list[0] == [10]


