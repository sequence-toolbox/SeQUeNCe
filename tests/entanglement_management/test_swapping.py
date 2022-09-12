import numpy
import pytest
from sequence.components.memory import Memory
from sequence.components.optical_channel import ClassicalChannel
from sequence.kernel.timeline import Timeline
from sequence.entanglement_management.swapping import *
from sequence.topology.node import Node


class ResourceManager:
    def __init__(self):
        self.log = []

    def update(self, protocol, memory, state):
        self.log.append((memory, state))
        if state == "RAW":
            memory.reset()


class FakeNode(Node):
    def __init__(self, name, tl, **kwargs):
        Node.__init__(self, name, tl)
        self.msg_log = []
        self.resource_manager = ResourceManager()

    def receive_message(self, src: str, msg: "Message"):
        self.msg_log.append((self.timeline.now(), src, msg))
        for protocol in self.protocols:
            if protocol.name == msg.receiver:
                protocol.received_message(src, msg)


phi_plus = [0.5 ** 0.5, 0, 0, 0.5 ** 0.5]
phi_minus = [0.5 ** 0.5, 0, 0, -(0.5 ** 0.5)]
psi_plus = [0, 0.5 ** 0.5, 0.5 ** 0.5, 0]
psi_minus = [0, 0.5 ** 0.5, -(0.5 ** 0.5), 0]


def correct_order(state, keys):
    if keys[0] > keys[1]:
        return numpy.array([[1, 0, 0, 0],
                            [0, 0, 1, 0],
                            [0, 1, 0, 0],
                            [0, 0, 0, 1]]) @ state
    else:
        return state


def config_three_nodes_network(state1, state2, seed_index):
    tl = Timeline()
    a1 = FakeNode("a1", tl)
    a2 = FakeNode("a2", tl)
    a3 = FakeNode("a3", tl)
    a1.set_seed(3 * seed_index)
    a2.set_seed(3 * seed_index + 1)
    a3.set_seed(3 * seed_index + 2)
    cc0 = ClassicalChannel("a2-a1", tl, 0, 1e5)
    cc1 = ClassicalChannel("a2-a3", tl, 0, 1e5)
    cc0.set_ends(a2, a1.name)
    cc1.set_ends(a2, a3.name)
    tl.init()

    memory_names = ["a1.0", "a2.0", "a2.1", "a3.0"]
    memories = [Memory(name, tl, 1, 0, 1, 1, 500) for name in memory_names]
    for memory in memories:
        memory.fidelity = 1
    memo1, memo2, memo3, memo4 = memories

    memo1.entangled_memory = {'node_id': 'a2', 'memo_id': memo2.name}
    memo2.entangled_memory = {'node_id': 'a1', 'memo_id': memo1.name}
    memo3.entangled_memory = {'node_id': 'a3', 'memo_id': memo4.name}
    memo4.entangled_memory = {'node_id': 'a2', 'memo_id': memo3.name}

    tl.quantum_manager.set([memo1.qstate_key, memo2.qstate_key], state1)
    tl.quantum_manager.set([memo3.qstate_key, memo4.qstate_key], state2)
    return tl, [a1, a2, a3], memories


def create_scenario(state1, state2, seed_index):
    tl, nodes, memories = config_three_nodes_network(state1, state2, seed_index)
    a1, a2, a3 = nodes
    memo1, memo2, memo3, memo4 = memories

    es1 = EntanglementSwappingB(a1, "a1.ESb0", memo1)
    a1.protocols.append(es1)
    es2 = EntanglementSwappingA(a2, "a2.ESa0", memo2, memo3)
    a2.protocols.append(es2)
    es3 = EntanglementSwappingB(a3, "a3.ESb1", memo4)
    a3.protocols.append(es3)

    es1.set_others(es2.name, a2.name, [memo2.name, memo3.name])
    es3.set_others(es2.name, a2.name, [memo2.name, memo3.name])
    es2.set_others(es1.name, a1.name, [memo1.name])
    es2.set_others(es3.name, a3.name, [memo4.name])

    es2.start()

    tl.run()

    ket1, ket2, ket3, ket4 = map(tl.quantum_manager.get,
                                 [memo1.qstate_key, memo2.qstate_key,
                                  memo3.qstate_key, memo4.qstate_key])

    assert id(ket1) == id(ket4)
    assert id(ket2) != id(ket3)
    assert len(ket1.keys) == 2
    assert memo1.qstate_key in ket1.keys
    assert memo4.qstate_key in ket1.keys
    assert len(ket2.keys) == 1

    assert memo2.entangled_memory == {'node_id': None, 'memo_id': None}
    assert memo3.entangled_memory == {'node_id': None, 'memo_id': None}
    assert memo1.entangled_memory["node_id"] == "a3"
    assert memo4.entangled_memory["node_id"] == "a1"
    assert a1.resource_manager.log[-1] == (memo1, "ENTANGLED")
    assert a3.resource_manager.log[-1] == (memo4, "ENTANGLED")
    return ket1, ket2, ket3, ket4, a3


def test_phi_plus_phi_plus():
    """
    phi+ phi+
     0b0
     [0.35355339+0.j 0.        +0.j 0.        +0.j 0.35355339+0.j]
     0b1
     [0.35355339+0.j 0.        +0.j 0.        +0.j 0.35355339+0.j]
     0b10
     [0.35355339+0.j 0.        +0.j 0.        +0.j 0.35355339+0.j]
     0b11
     [0.35355339+0.j 0.        +0.j 0.        +0.j 0.35355339+0.j]
    """

    for i in range(400):
        k1, k2, k3, k4, a3 = create_scenario(phi_plus, phi_plus, i)

        state = correct_order(k1.state, k1.keys)
        assert numpy.array_equal(state, phi_plus)


def test_phi_plus_phi_minus():
    """
    phi+ phi-
     0b0
     [ 0.35355339+0.j  0.        +0.j  0.        +0.j -0.35355339+0.j]
     0b1
     [-0.35355339+0.j  0.        +0.j  0.        +0.j  0.35355339+0.j]
     0b10
     [ 0.35355339+0.j  0.        +0.j  0.        +0.j -0.35355339+0.j]
     0b11
     [-0.35355339+0.j  0.        +0.j  0.        +0.j  0.35355339+0.j]
    """

    for i in range(200):
        k1, k2, k3, k4, a3 = create_scenario(phi_plus, phi_minus, i)
        state = correct_order(k1.state, k1.keys)
        if a3.msg_log[0][2].meas_res == [0, 0]:
            assert numpy.array_equal(state, phi_minus)
        elif a3.msg_log[0][2].meas_res == [0, 1]:
            assert numpy.array_equal(state, [-(0.5 ** 0.5), 0, 0, 0.5 ** 0.5])
        elif a3.msg_log[0][2].meas_res == [1, 0]:
            assert numpy.array_equal(state, phi_minus)
        else:
            assert numpy.array_equal(state, [-(0.5 ** 0.5), 0, 0, 0.5 ** 0.5])


def test_phi_plus_psi_plus():
    """
    phi+ psi+
     0b0
     [0.        +0.j 0.35355339+0.j 0.35355339+0.j 0.        +0.j]
     0b1
     [0.        +0.j 0.35355339+0.j 0.35355339+0.j 0.        +0.j]
     0b10
     [ 0.        +0.j -0.35355339+0.j -0.35355339+0.j  0.        +0.j]
     0b11
     [ 0.        +0.j -0.35355339+0.j -0.35355339+0.j  0.        +0.j]
    """

    for i in range(200):
        k1, k2, k3, k4, a3 = create_scenario(phi_plus, psi_plus, i)
        state = correct_order(k1.state, k1.keys)
        if a3.msg_log[0][2].meas_res == [0, 0]:
            assert numpy.array_equal(state, psi_plus)
        elif a3.msg_log[0][2].meas_res == [0, 1]:
            assert numpy.array_equal(state, psi_plus)
        elif a3.msg_log[0][2].meas_res == [1, 0]:
            assert numpy.array_equal(state, [0, -(0.5 ** 0.5), -(0.5 ** 0.5), 0])
        else:
            assert numpy.array_equal(state, [0, -(0.5 ** 0.5), -(0.5 ** 0.5), 0])


def test_phi_plus_psi_minus():
    """
    phi+ psi-
     0b0
     [ 0.        +0.j  0.35355339+0.j -0.35355339+0.j  0.        +0.j]
     0b1
     [ 0.        +0.j -0.35355339+0.j  0.35355339+0.j  0.        +0.j]
     0b10
     [ 0.        +0.j -0.35355339+0.j  0.35355339+0.j  0.        +0.j]
     0b11
     [ 0.        +0.j  0.35355339+0.j -0.35355339+0.j  0.        +0.j]
    """

    for i in range(200):
        k1, k2, k3, k4, a3 = create_scenario(phi_plus, psi_minus, i)
        state = correct_order(k1.state, k1.keys)
        if a3.msg_log[0][2].meas_res == [0, 0]:
            assert numpy.array_equal(state, psi_minus)
        elif a3.msg_log[0][2].meas_res == [0, 1]:
            assert numpy.array_equal(state, [0, -(0.5 ** 0.5), (0.5 ** 0.5), 0])
        elif a3.msg_log[0][2].meas_res == [1, 0]:
            assert numpy.array_equal(state, [0, -(0.5 ** 0.5), (0.5 ** 0.5), 0])
        else:
            assert numpy.array_equal(state, psi_minus)


def test_phi_minus_phi_plus():
    """
    phi- phi+
     0b0
     [ 0.35355339+0.j  0.        +0.j  0.        +0.j -0.35355339+0.j]
     0b1
     [ 0.35355339+0.j  0.        +0.j  0.        +0.j -0.35355339+0.j]
     0b10
     [ 0.35355339+0.j  0.        +0.j  0.        +0.j -0.35355339+0.j]
     0b11
     [ 0.35355339+0.j  0.        +0.j  0.        +0.j -0.35355339+0.j]
    """

    for i in range(200):
        k1, k2, k3, k4, a3 = create_scenario(phi_minus, phi_plus, i)
        state = correct_order(k1.state, k1.keys)
        assert numpy.array_equal(state, phi_minus)


def test_phi_minus_phi_minus():
    """
    phi- phi-
     0b0
     [0.35355339+0.j 0.        +0.j 0.        +0.j 0.35355339+0.j]
     0b1
     [-0.35355339+0.j  0.        +0.j  0.        +0.j -0.35355339+0.j]
     0b10
     [0.35355339+0.j 0.        +0.j 0.        +0.j 0.35355339+0.j]
     0b11
     [-0.35355339+0.j  0.        +0.j  0.        +0.j -0.35355339+0.j]
    """

    for i in range(200):
        k1, k2, k3, k4, a3 = create_scenario(phi_minus, phi_minus, i)
        state = correct_order(k1.state, k1.keys)
        if a3.msg_log[0][2].meas_res == [0, 0]:
            assert numpy.array_equal(state, phi_plus)
        elif a3.msg_log[0][2].meas_res == [0, 1]:
            assert numpy.array_equal(state, [-(0.5 ** 0.5), 0, 0, -(0.5 ** 0.5)])
        elif a3.msg_log[0][2].meas_res == [1, 0]:
            assert numpy.array_equal(state, phi_plus)
        else:
            assert numpy.array_equal(state, [-(0.5 ** 0.5), 0, 0, -(0.5 ** 0.5)])


def test_phi_minus_psi_plus():
    """
    phi- psi+
     0b0
     [ 0.        +0.j  0.35355339+0.j -0.35355339+0.j  0.        +0.j]
     0b1
     [ 0.        +0.j  0.35355339+0.j -0.35355339+0.j  0.        +0.j]
     0b10
     [ 0.        +0.j -0.35355339+0.j  0.35355339+0.j  0.        +0.j]
     0b11
     [ 0.        +0.j -0.35355339+0.j  0.35355339+0.j  0.        +0.j]
    """

    for i in range(200):
        k1, k2, k3, k4, a3 = create_scenario(phi_minus, psi_plus, i)
        state = correct_order(k1.state, k1.keys)
        if a3.msg_log[0][2].meas_res == [0, 0]:
            assert numpy.array_equal(state, psi_minus)
        elif a3.msg_log[0][2].meas_res == [0, 1]:
            assert numpy.array_equal(state, psi_minus)
        elif a3.msg_log[0][2].meas_res == [1, 0]:
            assert numpy.array_equal(state, [0, -(0.5 ** 0.5), (0.5 ** 0.5), 0])
        else:
            assert numpy.array_equal(state, [0, -(0.5 ** 0.5), (0.5 ** 0.5), 0])


def test_phi_minus_psi_minus():
    """
    phi- psi-
     0b0
     [0.        +0.j 0.35355339+0.j 0.35355339+0.j 0.        +0.j]
     0b1
     [ 0.        +0.j -0.35355339+0.j -0.35355339+0.j  0.        +0.j]
     0b10
     [ 0.        +0.j -0.35355339+0.j -0.35355339+0.j  0.        +0.j]
     0b11
     [0.        +0.j 0.35355339+0.j 0.35355339+0.j 0.        +0.j]
    """

    for i in range(200):
        k1, k2, k3, k4, a3 = create_scenario(phi_minus, psi_minus, i)
        state = correct_order(k1.state, k1.keys)
        if a3.msg_log[0][2].meas_res == [0, 0]:
            assert numpy.array_equal(state, psi_plus)
        elif a3.msg_log[0][2].meas_res == [0, 1]:
            assert numpy.array_equal(state, [0, -(0.5 ** 0.5), -(0.5 ** 0.5), 0])
        elif a3.msg_log[0][2].meas_res == [1, 0]:
            assert numpy.array_equal(state, [0, -(0.5 ** 0.5), -(0.5 ** 0.5), 0])
        else:
            assert numpy.array_equal(state, psi_plus)


def test_psi_plus_phi_plus():
    """
    psi+ phi+
     0b0
     [0.        +0.j 0.35355339+0.j 0.35355339+0.j 0.        +0.j]
     0b1
     [0.        +0.j 0.35355339+0.j 0.35355339+0.j 0.        +0.j]
     0b10
     [0.        +0.j 0.35355339+0.j 0.35355339+0.j 0.        +0.j]
     0b11
     [0.        +0.j 0.35355339+0.j 0.35355339+0.j 0.        +0.j]
    """

    for i in range(200):
        k1, k2, k3, k4, a3 = create_scenario(psi_plus, phi_plus, i)
        state = correct_order(k1.state, k1.keys)
        assert numpy.array_equal(state, psi_plus)


def test_psi_plus_phi_minus():
    """
    psi+ phi-
     0b0
     [ 0.        +0.j -0.35355339+0.j  0.35355339+0.j  0.        +0.j]
     0b1
     [ 0.        +0.j  0.35355339+0.j -0.35355339+0.j  0.        +0.j]
     0b10
     [ 0.        +0.j -0.35355339+0.j  0.35355339+0.j  0.        +0.j]
     0b11
     [ 0.        +0.j  0.35355339+0.j -0.35355339+0.j  0.        +0.j]
    """

    for i in range(200):
        k1, k2, k3, k4, a3 = create_scenario(psi_plus, phi_minus, i)
        state = correct_order(k1.state, k1.keys)
        if a3.msg_log[0][2].meas_res == [0, 0]:
            assert numpy.array_equal(state, [0, -(0.5 ** 0.5), (0.5 ** 0.5), 0])
        elif a3.msg_log[0][2].meas_res == [0, 1]:
            assert numpy.array_equal(state, psi_minus)
        elif a3.msg_log[0][2].meas_res == [1, 0]:
            assert numpy.array_equal(state, [0, -(0.5 ** 0.5), (0.5 ** 0.5), 0])
        else:
            assert numpy.array_equal(state, psi_minus)


def test_psi_plus_psi_plus():
    """
    psi+ psi+
     0b0
     [0.35355339+0.j 0.        +0.j 0.        +0.j 0.35355339+0.j]
     0b1
     [0.35355339+0.j 0.        +0.j 0.        +0.j 0.35355339+0.j]
     0b10
     [-0.35355339+0.j  0.        +0.j  0.        +0.j -0.35355339+0.j]
     0b11
     [-0.35355339+0.j  0.        +0.j  0.        +0.j -0.35355339+0.j]
    """

    for i in range(200):
        k1, k2, k3, k4, a3 = create_scenario(psi_plus, psi_plus, i)
        state = correct_order(k1.state, k1.keys)
        if a3.msg_log[0][2].meas_res == [0, 0]:
            assert numpy.array_equal(state, phi_plus)
        elif a3.msg_log[0][2].meas_res == [0, 1]:
            assert numpy.array_equal(state, phi_plus)
        elif a3.msg_log[0][2].meas_res == [1, 0]:
            assert numpy.array_equal(state, [-(0.5 ** 0.5), 0, 0, -(0.5 ** 0.5)])
        else:
            assert numpy.array_equal(state, [-(0.5 ** 0.5), 0, 0, -(0.5 ** 0.5)])


def test_psi_plus_psi_minus():
    """
    psi+ psi-
     0b0
     [-0.35355339+0.j  0.        +0.j  0.        +0.j  0.35355339+0.j]
     0b1
     [ 0.35355339+0.j  0.        +0.j  0.        +0.j -0.35355339+0.j]
     0b10
     [ 0.35355339+0.j  0.        +0.j  0.        +0.j -0.35355339+0.j]
     0b11
     [-0.35355339+0.j  0.        +0.j  0.        +0.j  0.35355339+0.j]
    """

    for i in range(200):
        k1, k2, k3, k4, a3 = create_scenario(psi_plus, psi_minus, i)
        state = correct_order(k1.state, k1.keys)
        if a3.msg_log[0][2].meas_res == [0, 0]:
            assert numpy.array_equal(state, [-(0.5 ** 0.5), 0, 0, (0.5 ** 0.5)])
        elif a3.msg_log[0][2].meas_res == [0, 1]:
            assert numpy.array_equal(state, phi_minus)
        elif a3.msg_log[0][2].meas_res == [1, 0]:
            assert numpy.array_equal(state, phi_minus)
        else:
            assert numpy.array_equal(state, [-(0.5 ** 0.5), 0, 0, (0.5 ** 0.5)])


def test_psi_minus_phi_plus():
    """
    psi- phi+
     0b0
     [ 0.        +0.j  0.35355339+0.j -0.35355339+0.j  0.        +0.j]
     0b1
     [ 0.        +0.j  0.35355339+0.j -0.35355339+0.j  0.        +0.j]
     0b10
     [ 0.        +0.j  0.35355339+0.j -0.35355339+0.j  0.        +0.j]
     0b11
     [ 0.        +0.j  0.35355339+0.j -0.35355339+0.j  0.        +0.j]
    """

    for i in range(200):
        k1, k2, k3, k4, a3 = create_scenario(psi_minus, phi_plus, i)
        state = correct_order(k1.state, k1.keys)
        assert numpy.array_equal(state, psi_minus)


def test_psi_minus_phi_minus():
    """
    psi- phi-
     0b0
     [ 0.        +0.j -0.35355339+0.j -0.35355339+0.j  0.        +0.j]
     0b1
     [0.        +0.j 0.35355339+0.j 0.35355339+0.j 0.        +0.j]
     0b10
     [ 0.        +0.j -0.35355339+0.j -0.35355339+0.j  0.        +0.j]
     0b11
     [0.        +0.j 0.35355339+0.j 0.35355339+0.j 0.        +0.j]
    """

    for i in range(200):
        k1, k2, k3, k4, a3 = create_scenario(psi_minus, phi_minus, i)
        state = correct_order(k1.state, k1.keys)
        if a3.msg_log[0][2].meas_res == [0, 0]:
            assert numpy.array_equal(state, [0, -(0.5 ** 0.5), -(0.5 ** 0.5), 0])
        elif a3.msg_log[0][2].meas_res == [0, 1]:
            assert numpy.array_equal(state, psi_plus)
        elif a3.msg_log[0][2].meas_res == [1, 0]:
            assert numpy.array_equal(state, [0, -(0.5 ** 0.5), -(0.5 ** 0.5), 0])
        else:
            assert numpy.array_equal(state, psi_plus)


def test_psi_minus_psi_plus():
    """
    psi- psi+
     0b0
     [ 0.35355339+0.j  0.        +0.j  0.        +0.j -0.35355339+0.j]
     0b1
     [ 0.35355339+0.j  0.        +0.j  0.        +0.j -0.35355339+0.j]
     0b10
     [-0.35355339+0.j  0.        +0.j  0.        +0.j  0.35355339+0.j]
     0b11
     [-0.35355339+0.j  0.        +0.j  0.        +0.j  0.35355339+0.j]
    """

    for i in range(200):
        k1, k2, k3, k4, a3 = create_scenario(psi_minus, psi_plus, i)
        state = correct_order(k1.state, k1.keys)
        if a3.msg_log[0][2].meas_res == [0, 0]:
            assert numpy.array_equal(state, phi_minus)
        elif a3.msg_log[0][2].meas_res == [0, 1]:
            assert numpy.array_equal(state, phi_minus)
        elif a3.msg_log[0][2].meas_res == [1, 0]:
            assert numpy.array_equal(state, [-(0.5 ** 0.5), 0, 0, (0.5 ** 0.5)])
        else:
            assert numpy.array_equal(state, [-(0.5 ** 0.5), 0, 0, (0.5 ** 0.5)])


def test_psi_minus_psi_minus():
    """
    psi- psi-
     0b0
     [-0.35355339+0.j  0.        +0.j  0.        +0.j -0.35355339+0.j]
     0b1
     [0.35355339+0.j 0.        +0.j 0.        +0.j 0.35355339+0.j]
     0b10
     [0.35355339+0.j 0.        +0.j 0.        +0.j 0.35355339+0.j]
     0b11
     [-0.35355339+0.j  0.        +0.j  0.        +0.j -0.35355339+0.j]
    """

    for i in range(200):
        k1, k2, k3, k4, a3 = create_scenario(psi_minus, psi_minus, i)
        state = correct_order(k1.state, k1.keys)
        if a3.msg_log[0][2].meas_res == [0, 0]:
            assert numpy.array_equal(state, [-(0.5 ** 0.5), 0, 0, -(0.5 ** 0.5)])
        elif a3.msg_log[0][2].meas_res == [0, 1]:
            assert numpy.array_equal(state, phi_plus)
        elif a3.msg_log[0][2].meas_res == [1, 0]:
            assert numpy.array_equal(state, phi_plus)
        else:
            assert numpy.array_equal(state, [-(0.5 ** 0.5), 0, 0, -(0.5 ** 0.5)])


def test_EntanglementSwappingMessage():
    # __init__ function
    msg = EntanglementSwappingMessage(SwappingMsgType.SWAP_RES, "receiver", fidelity=0.9, remote_node="a1",
                                      remote_memo=2)
    assert msg.msg_type == SwappingMsgType.SWAP_RES
    assert msg.receiver == "receiver"
    assert msg.fidelity == 0.9
    assert msg.remote_node == "a1"
    assert msg.remote_memo == 2
    with pytest.raises(Exception):
        EntanglementSwappingMessage("error")


def test_EntanglementSwapping():
    counter1 = counter2 = 0

    for i in range(1000):
        tl, nodes, memories = config_three_nodes_network(phi_plus, phi_plus, i)
        a1, a2, a3 = nodes
        memo1, memo2, memo3, memo4 = memories

        es1 = EntanglementSwappingB(a1, "a1.ESb%d" % i, memo1)
        a1.protocols.append(es1)
        es2 = EntanglementSwappingA(a2, "a2.ESa%d" % i, memo2, memo3, success_prob=0.2)
        a2.protocols.append(es2)
        es3 = EntanglementSwappingB(a3, "a3.ESb%d" % i, memo4)
        a3.protocols.append(es3)

        es1.set_others(es2.name, a2.name, [memo2.name, memo3.name])
        es3.set_others(es2.name, a2.name, [memo2.name, memo3.name])
        es2.set_others(es1.name, a1.name, [memo1.name])
        es2.set_others(es3.name, a3.name, [memo4.name])

        es2.start()

        assert memo2.fidelity == memo3.fidelity == 0
        assert memo1.entangled_memory["node_id"] == memo4.entangled_memory["node_id"] == "a2"
        assert memo2.entangled_memory["node_id"] == memo3.entangled_memory["node_id"] == None
        assert memo2.entangled_memory["memo_id"] == memo3.entangled_memory["memo_id"] == None
        assert a2.resource_manager.log[-2] == (memo2, "RAW")
        assert a2.resource_manager.log[-1] == (memo3, "RAW")

        tl.run()

        if es2.is_success:
            counter1 += 1
            assert memo1.entangled_memory["node_id"] == "a3"
            assert memo4.entangled_memory["node_id"] == "a1"
            assert memo1.fidelity == memo4.fidelity <= memo1.raw_fidelity
            assert a1.resource_manager.log[-1] == (memo1, "ENTANGLED")
            assert a3.resource_manager.log[-1] == (memo4, "ENTANGLED")
        else:
            counter2 += 1
            assert memo1.entangled_memory["node_id"] == None
            assert memo4.entangled_memory["node_id"] == None
            assert memo1.fidelity == memo4.fidelity == 0
            assert a1.resource_manager.log[-1] == (memo1, "RAW")
            assert a3.resource_manager.log[-1] == (memo4, "RAW")

    assert abs((counter1 / (counter1 + counter2)) - 0.2) < 0.1
