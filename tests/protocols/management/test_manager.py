from sequence.protocols.management.manager import ResourceManager
from sequence.protocols.management.ruleset import *
from sequence.kernel.timeline import Timeline
from sequence.topology.node import *
from sequence.components.memory import *


action_counter = 0
def fake_action(memories):
    memories[0].fidelity = 0


def test_load():
    tl = Timeline()
    node = Node("node", tl)
    node.memory_array = MemoryArray("ma", tl)
    manager = ResourceManager(node)

    rule = Rule(0, fake_action, True)
    manager.load(rule)
    
    assert node.memory_array[0].fidelity == 0

def test_update():
    assert True

def test_received_message():
    assert True


