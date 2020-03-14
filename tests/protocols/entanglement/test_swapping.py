import numpy
import pytest
from sequence.components.memory import MemoryArray
from sequence.components.optical_channel import ClassicalChannel
from sequence.kernel.timeline import Timeline
from sequence.protocols.entanglement.swapping import *
from sequence.topology.node import Node

numpy.random.seed(0)


def test_entanglement_swapping_message():
    import pytest
    from sequence.protocols.entanglement.swapping import EntanglementSwappingMessage, EntanglementSwapping

    # __init__ function
    msg = EntanglementSwappingMessage("SWAP_RES", local_memo=1, fidelity=0.9, remote_node="a1", remote_memo=2)
    assert msg.owner_type == type(EntanglementSwapping(None, None, None, None)) \
           and (msg.msg_type == "SWAP_RES") and (msg.local_memo == 1) \
           and (msg.fidelity == 0.9) and (msg.remote_node == "a1") and (msg.remote_memo == 2)
    with pytest.raises(Exception):
        EntanglementSwappingMessage("error")

    # __str__ function
    assert ('%s' % msg) == "EntanglementSwappingMessage: " \
                           "msg_type: SWAP_RES; local_memo: 1; fidelity: 0.90; " \
                           "remote_node: a1; remote_memo: 2; "


def test_EntanglementSwapping_init():
    tl = Timeline()
    a1 = Node("a1", tl)

    es = EntanglementSwapping(a1, 'a0', 'a2', ['a0', 'a2'])
    assert es.remote1 == 'a0' and es.remote2 == 'a2' and es.known_nodes == ['a0', 'a2']

    es.init()
    assert True


def test_EntanglementSwapping_set_valid_memories():
    tl = Timeline()
    a1 = Node("a1", tl)
    es = EntanglementSwapping(a1, 'a0', 'a2', ['a0', 'a2'])
    memories = set(range(10))
    es.set_valid_memories(memories)
    assert True


def test_EntanglementSwapping_push():
    class Child1():
        def __init__(self):
            pass

        def push(self, **kwargs):
            assert (str(kwargs) == "{'a': 1, 'b': 2, 'c': 3}")

    tl = Timeline()
    a1 = Node("a1", tl)
    es = EntanglementSwapping(a1, 'a0', 'a2', ['a0', 'a2'])
    memories = set(range(10))
    es.set_valid_memories(memories)
    es.lower_protocols.append(Child1())
    es.push(a=1, b=2, c=3)
    es.lower_protocols.pop()


def test_EntanglementSwapping_pop():
    class Parent():
        def __init__(self):
            self.last_pop = None

        def pop(self, **kwargs):
            self.last_pop = [kwargs["memory_index"], kwargs["another_node"]]

        def get_res(self):
            res = self.last_pop
            self.last_pop = None
            return res

    class Child2():
        def __init__(self):
            self.push_log = []

        def push(self, **kwargs):
            self.push_log.append(kwargs["index"])

    tl = Timeline()

    a0 = Node("a0", tl)
    a1 = Node("a1", tl)
    a2 = Node("a2", tl)

    es = EntanglementSwapping(a1, 'a0', 'a2', ['a0', 'a2', 'a100'])
    memories = set(range(10))
    es.set_valid_memories(memories)
    ma = MemoryArray("ma", tl, num_memories=10, memory_params={})
    a1.assign_component(ma, "MemoryArray")
    cc1 = ClassicalChannel("a0-a1", tl, 2e-4, 1e3)
    cc1.set_ends(a0, a1)

    cc2 = ClassicalChannel("a1-a2", tl, 2e4, 1e3)
    cc2.set_ends(a1, a2)

    parent = Parent()
    child = Child2()
    es.upper_protocols.append(parent)
    es.lower_protocols.append(child)
    args = [[10, 'a0'], [0, 'a5'],
            [0, 'a0'], [1, 'a2'],
            [2, 'a0'], [3, 'a0'],
            [8, 'a100']]
    # res = [(return, self.waiting_memo1, self.waiting_memo2, self.waiting_swap_res, upper pop, lower push)]
    results = [(False, [], [], {}, None, []), (True, [], [], {}, [0, 'a5'], []),
               (True, [0], [], {}, None, []), (True, [], [], {}, None, [0, 1]),
               (True, [2], [], {}, None, [0, 1]), (True, [2, 3], [], {}, None, [0, 1]),
               (True, [2, 3], [], {8: 'a100'}, None, [0, 1])]
    for arg, res in zip(args, results):
        if arg[0] < len(es.own.components["MemoryArray"]):
            es.own.components["MemoryArray"][arg[0]].entangled_memory["node_id"] = arg[1]
        assert es.pop(memory_index=arg[0], another_node=arg[1]) is res[0]
        assert es.waiting_memo1 == res[1]
        assert es.waiting_memo2 == res[2]
        assert es.waiting_swap_res == res[3]
        assert parent.get_res() == res[4]
        assert child.push_log == res[5]


def test_EntanglementSwapping_received_message():
    class Parent():
        def __init__(self):
            self.last_pop = None

        def pop(self, **kwargs):
            self.last_pop = [kwargs["memory_index"], kwargs["another_node"]]

        def get_res(self):
            res = self.last_pop
            self.last_pop = None
            return res

    class Child2():
        def __init__(self):
            self.push_log = []

        def push(self, **kwargs):
            self.push_log.append(kwargs["index"])

    tl = Timeline()

    a1 = Node("a1", tl)

    es = EntanglementSwapping(a1, 'a0', 'a2', ['a0', 'a2'])
    memories = set(range(10))
    es.set_valid_memories(memories)
    ma = MemoryArray("ma", tl, num_memories=10, memory_params={})
    a1.assign_component(ma, "MemoryArray")

    parent = Parent()
    child = Child2()
    es.upper_protocols.append(parent)
    es.lower_protocols.append(child)

    # test 1: unknown msg type
    args = [["a0", "UNKNOWN", 1, 0.1, "a2", 2]]
    results = []
    for arg, res in zip(args, results):
        src = arg[0]
        msg = EntanglementSwappingMessage(msg_type=arg[1], local_memo=arg[2], fidelity=arg[3],
                                          remote_node=arg[4], remote_memo=arg[5])
        with pytest.raises(Exception):
            es.received_message(src, msg)

    # test 2: unknown node
    args = [["a100", "SWAP_RES", 1, 0.1, "a2", 2]]
    results = [[False]]
    for arg, res in zip(args, results):
        src = arg[0]
        msg = EntanglementSwappingMessage(msg_type=arg[1], local_memo=arg[2], fidelity=arg[3],
                                          remote_node=arg[4], remote_memo=arg[5])
        assert es.received_message(src, msg) is res[0]

    # test 3: success swap (fidelity > 0)
    args = [["a0", "SWAP_RES", 1, 0.9, "a2", 2]]
    results = [[True, 0.9, "a2", 2, [1, "a2"]]]
    for arg, res in zip(args, results):
        src = arg[0]
        msg = EntanglementSwappingMessage(msg_type=arg[1], local_memo=arg[2], fidelity=arg[3],
                                          remote_node=arg[4], remote_memo=arg[5])
        es.waiting_swap_res[arg[2]] = src
        assert es.received_message(src, msg) is res[0]
        memo = ma[arg[2]]
        assert memo.fidelity == res[1] and memo.entangled_memory["node_id"] == res[2] \
               and memo.entangled_memory["memo_id"] == res[3]
        assert parent.get_res() == res[4]

    # test 4: fail swap (fidelity == 0)
    args = [["a0", "SWAP_RES", 1, 0, "a2", 2]]
    results = [[True, 0, [1]]]
    for arg, res in zip(args, results):
        src = arg[0]
        msg = EntanglementSwappingMessage(msg_type=arg[1], local_memo=arg[2], fidelity=arg[3],
                                          remote_node=arg[4], remote_memo=arg[5])
        es.waiting_swap_res[arg[2]] = src
        assert es.received_message(src, msg) is res[0]
        assert child.push_log == res[2]