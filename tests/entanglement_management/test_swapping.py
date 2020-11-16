import numpy
import pytest
from sequence.components.memory import Memory
from sequence.components.optical_channel import ClassicalChannel
from sequence.kernel.timeline import Timeline
from sequence.entanglement_management.swapping import *
from sequence.topology.node import Node

numpy.random.seed(0)


class ResourceManager():
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
        return numpy.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]]) @ state
    else:
        return state


def create_scenario(state1, state2, seed):
    tl = Timeline()
    tl.seed(seed)
    a1 = FakeNode("a1", tl)
    a2 = FakeNode("a2", tl)
    a3 = FakeNode("a3", tl)
    cc0 = ClassicalChannel("a2-a1", tl, 0, 1e5)
    cc1 = ClassicalChannel("a2-a3", tl, 0, 1e5)
    cc0.set_ends(a2, a1)
    cc1.set_ends(a2, a3)
    tl.init()

    memo1 = Memory("a1.0", timeline=tl, fidelity=0.9, frequency=0, efficiency=1, coherence_time=1, wavelength=500)
    memo2 = Memory("a2.0", tl, 0.9, 0, 1, 1, 500)
    memo3 = Memory("a2.1", tl, 0.9, 0, 1, 1, 500)
    memo4 = Memory("a3.0", tl, 0.9, 0, 1, 1, 500)

    memo1.fidelity = memo2.fidelity = memo3.fidelity = memo4.fidelity = 1
    memo1.entangled_memory = {'node_id': 'a2', 'memo_id': memo2.name}
    memo2.entangled_memory = {'node_id': 'a1', 'memo_id': memo1.name}
    memo3.entangled_memory = {'node_id': 'a3', 'memo_id': memo4.name}
    memo4.entangled_memory = {'node_id': 'a2', 'memo_id': memo3.name}

    tl.quantum_manager.set([memo1.qstate_key, memo2.qstate_key], state1)
    tl.quantum_manager.set([memo3.qstate_key, memo4.qstate_key], state2)

    es1 = EntanglementSwappingB(a1, "a1.ESb0", memo1)
    a1.protocols.append(es1)
    es2 = EntanglementSwappingA(a2, "a2.ESa0", memo2, memo3)
    a2.protocols.append(es2)
    es3 = EntanglementSwappingB(a3, "a3.ESb1", memo4)
    a3.protocols.append(es3)

    es1.set_others(es2)
    es3.set_others(es2)
    es2.set_others(es1)
    es2.set_others(es3)

    es2.start()

    tl.run()

    ket1, ket2, ket3, ket4 = map(tl.quantum_manager.get,
                                 [memo1.qstate_key, memo2.qstate_key, memo3.qstate_key, memo4.qstate_key])

    assert id(ket1) == id(ket4)
    assert id(ket2) != id(ket3)
    assert len(ket1.keys) == 2 and memo1.qstate_key in ket1.keys and memo4.qstate_key in ket1.keys
    assert len(ket2.keys) == 1

    assert memo2.entangled_memory == memo3.entangled_memory == {'node_id': None, 'memo_id': None}
    assert memo1.entangled_memory["node_id"] == "a3" and memo4.entangled_memory["node_id"] == "a1"
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
    tl = Timeline()
    a1 = FakeNode("a1", tl)
    a2 = FakeNode("a2", tl)
    a3 = FakeNode("a3", tl)
    cc0 = ClassicalChannel("a2-a1", tl, 0, 1e5)
    cc1 = ClassicalChannel("a2-a3", tl, 0, 1e5)
    cc0.set_ends(a2, a1)
    cc1.set_ends(a2, a3)
    tl.init()
    counter1 = counter2 = 0

    for i in range(1000):
        memo1 = Memory("a1.%d" % i, timeline=tl, fidelity=0.9, frequency=0, efficiency=1, coherence_time=1,
                       wavelength=500)
        memo2 = Memory("a2.%d" % i, tl, 0.9, 0, 1, 1, 500)
        memo3 = Memory("a2.%d" % i, tl, 0.9, 0, 1, 1, 500)
        memo4 = Memory("a3.%d" % i, tl, 0.9, 0, 1, 1, 500)

        memo1.entangled_memory["node_id"] = "a2"
        memo1.entangled_memory["memo_id"] = memo2.name
        memo1.fidelity = 0.9
        memo2.entangled_memory["node_id"] = "a1"
        memo2.entangled_memory["memo_id"] = memo1.name
        memo2.fidelity = 0.9
        memo3.entangled_memory["node_id"] = "a3"
        memo3.entangled_memory["memo_id"] = memo4.name
        memo3.fidelity = 0.9
        memo4.entangled_memory["node_id"] = "a2"
        memo4.entangled_memory["memo_id"] = memo3.name
        memo4.fidelity = 0.9

        es1 = EntanglementSwappingB(a1, "a1.ESb%d" % i, memo1)
        a1.protocols.append(es1)
        es2 = EntanglementSwappingA(a2, "a2.ESa%d" % i, memo2, memo3, success_prob=0.2)
        a2.protocols.append(es2)
        es3 = EntanglementSwappingB(a3, "a3.ESb%d" % i, memo4)
        a3.protocols.append(es3)

        es1.set_others(es2)
        es3.set_others(es2)
        es2.set_others(es1)
        es2.set_others(es3)

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
            assert memo1.entangled_memory["node_id"] == "a3" and memo4.entangled_memory["node_id"] == "a1"
            assert memo1.fidelity == memo4.fidelity <= memo1.raw_fidelity
            assert a1.resource_manager.log[-1] == (memo1, "ENTANGLED")
            assert a3.resource_manager.log[-1] == (memo4, "ENTANGLED")
        else:
            counter2 += 1
            assert memo1.entangled_memory["node_id"] == memo4.entangled_memory["node_id"] == None
            assert memo1.fidelity == memo4.fidelity == 0
            assert a1.resource_manager.log[-1] == (memo1, "RAW")
            assert a3.resource_manager.log[-1] == (memo4, "RAW")

    assert abs((counter1 / (counter1 + counter2)) - 0.2) < 0.1
