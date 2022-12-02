import numpy as np
import pytest

from sequence.components.memory import Memory
from sequence.components.optical_channel import ClassicalChannel
from sequence.kernel.timeline import Timeline
from sequence.entanglement_management.purification import *
from sequence.topology.node import Node

np.random.seed(0)

ENTANGLED = 'ENTANGLED'
RAW = 'RAW'

HALF_MICRON = 500
ONE_MILLISECOND = 1e9
SQRT_HALF = 0.5 ** 0.5

phi_plus = [SQRT_HALF, 0, 0, SQRT_HALF]
phi_minus = [SQRT_HALF, 0, 0, -SQRT_HALF]
psi_plus = [0, SQRT_HALF, SQRT_HALF, 0]
psi_minus = [0, SQRT_HALF, -SQRT_HALF, 0]
BELL_STATES = [phi_plus, phi_minus, psi_plus, psi_minus]


def success_probability(F: float) -> float:
    return F ** 2 + 2 * F * (1 - F) / 3 + 5 * ((1 - F) / 3) ** 2


class FakeResourceManager:
    def __init__(self, owner):
        self.log = []

    def update(self, protocol, memory, state):
        self.log.append((memory, state))
        if state == RAW:
            memory.reset()


class FakeNode(Node):
    def __init__(self, name, tl, **kwargs):
        Node.__init__(self, name, tl)
        self.msg_log = []
        self.resource_manager = FakeResourceManager(self)

    def receive_message(self, src: str, msg: "Message"):
        self.msg_log.append((self.timeline.now(), src, msg))
        for protocol in self.protocols:
            if protocol.name == msg.receiver:
                protocol.received_message(src, msg)


def test_BBPSSWMessage():
    msg = BBPSSWMessage(BBPSSWMsgType.PURIFICATION_RES, "another", meas_res=0)
    assert msg.msg_type == BBPSSWMsgType.PURIFICATION_RES
    assert msg.receiver == "another"
    assert msg.meas_res == 0
    with pytest.raises(Exception):
        BBPSSWMessage("unknown type")


def create_scenario(state1, state2, seed_index, fidelity=1.0):
    tl = Timeline()
    tl.show_progress = False
    a1 = FakeNode("a1", tl)
    a2 = FakeNode("a2", tl)
    a1.set_seed(2 * seed_index)
    a2.set_seed(2 * seed_index + 1)
    cc0 = ClassicalChannel("cc0", tl, 0, 1e5)
    cc1 = ClassicalChannel("cc1", tl, 0, 1e5)
    cc0.delay = ONE_MILLISECOND
    cc1.delay = ONE_MILLISECOND
    cc0.set_ends(a1, a2.name)
    cc1.set_ends(a2, a1.name)

    kept1 = Memory('kept1', tl, fidelity=fidelity, frequency=0, efficiency=1,
                   coherence_time=1, wavelength=HALF_MICRON)
    kept2 = Memory('kept2', tl, fidelity=fidelity, frequency=0, efficiency=1,
                   coherence_time=1, wavelength=HALF_MICRON)
    meas1 = Memory('mea1', tl, fidelity=fidelity, frequency=0, efficiency=1,
                   coherence_time=1, wavelength=HALF_MICRON)
    meas2 = Memory('mea2', tl, fidelity=fidelity, frequency=0, efficiency=1,
                   coherence_time=1, wavelength=HALF_MICRON)

    tl.init()

    tl.quantum_manager.set([kept1.qstate_key, kept2.qstate_key], state1)
    tl.quantum_manager.set([meas1.qstate_key, meas2.qstate_key], state2)

    kept1.entangled_memory = {'node_id': 'a2', 'memo_id': 'kept2'}
    kept2.entangled_memory = {'node_id': 'a1', 'memo_id': 'kept1'}
    meas1.entangled_memory = {'node_id': 'a2', 'memo_id': 'meas2'}
    meas2.entangled_memory = {'node_id': 'a1', 'memo_id': 'meas1'}
    kept1.fidelity = kept2.fidelity = meas1.fidelity = meas2.fidelity = fidelity

    ep1 = BBPSSW(a1, "a1.ep1", kept1, meas1)
    ep2 = BBPSSW(a2, "a2.ep2", kept2, meas2)
    a1.protocols.append(ep1)
    a2.protocols.append(ep2)
    ep1.set_others(ep2.name, a2.name, [kept2.name, meas2.name])
    ep2.set_others(ep1.name, a1.name, [kept1.name, meas1.name])

    ep1.start()
    ep2.start()

    tl.run()

    assert meas1.entangled_memory == meas2.entangled_memory == {'node_id': None, 'memo_id': None}

    return tl, kept1, kept2, meas1, meas2, ep1, ep2


def complex_array_equal(arr1, arr2, precision=5):
    for c1, c2 in zip(arr1, arr2):
        if abs(c1 - c2) >= 2 ** -precision:
            return False
    return True


def correct_order(state, keys):
    if keys[0] > keys[1]:
        return np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]]) @ state


def test_BBPSSW_phi_plus_phi_plus():
    """
    phi+ phi+
     0b0
         [0.5+0.j 0. +0.j 0. +0.j 0.5+0.j]
     0b1
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
     0b10
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
     0b11
         [0.5+0.j 0. +0.j 0. +0.j 0.5+0.j]
    """
    counter = 0
    for i in range(100):
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(phi_plus, phi_plus, i)
        assert kept1.entangled_memory == {'node_id': 'a2', 'memo_id': 'kept2'}
        assert kept2.entangled_memory == {'node_id': 'a1', 'memo_id': 'kept1'}
        assert ep1.meas_res == ep2.meas_res
        if ep1.meas_res == 0:
            counter += 1
        ket1 = tl.quantum_manager.get(kept1.qstate_key)
        ket2 = tl.quantum_manager.get(kept2.qstate_key)
        assert id(ket1) == id(ket2)
        assert kept1.qstate_key in ket1.keys and kept2.qstate_key in ket1.keys
        state = correct_order(ket1.state, ket1.keys)
        assert complex_array_equal(phi_plus, state)
        # assert kept1 and kept2 point to the same Ketstate
        # assert the state is phi+
    assert abs(counter - 50) < 10


def test_BBPSSW_phi_plus_phi_minus():
    """
    phi+ phi-
     0b0
         [ 0.5+0.j  0. +0.j  0. +0.j -0.5+0.j]
     0b1
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
     0b10
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
     0b11
         [-0.5+0.j  0. +0.j  0. +0.j  0.5+0.j]

    """
    counter = 0
    for i in range(100):
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(phi_plus, phi_minus, i)
        assert kept1.entangled_memory == {'node_id': 'a2', 'memo_id': 'kept2'}
        assert kept2.entangled_memory == {'node_id': 'a1', 'memo_id': 'kept1'}
        assert ep1.meas_res == ep2.meas_res
        ket1 = tl.quantum_manager.get(kept1.qstate_key)
        ket2 = tl.quantum_manager.get(kept2.qstate_key)
        assert id(ket1) == id(ket2)
        assert kept1.qstate_key in ket1.keys and kept2.qstate_key in ket1.keys
        state = correct_order(ket1.state, ket1.keys)
        if ep1.meas_res == 0:
            counter += 1
            assert complex_array_equal(phi_minus, state)
        else:
            assert complex_array_equal([-SQRT_HALF, 0, 0, SQRT_HALF], state)

    assert abs(counter - 50) < 10


def test_BBPSSW_phi_minus_phi_plus():
    """
    phi- phi+
     0b0
         [ 0.5+0.j  0. +0.j  0. +0.j -0.5+0.j]
     0b1
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
     0b10
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
     0b11
         [ 0.5+0.j  0. +0.j  0. +0.j -0.5+0.j]
    """
    counter = 0
    for i in range(100):
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(phi_minus, phi_plus, i)
        assert kept1.entangled_memory == {'node_id': 'a2', 'memo_id': 'kept2'}
        assert kept2.entangled_memory == {'node_id': 'a1', 'memo_id': 'kept1'}
        assert ep1.meas_res == ep2.meas_res

        ket1 = tl.quantum_manager.get(kept1.qstate_key)
        ket2 = tl.quantum_manager.get(kept2.qstate_key)
        assert id(ket1) == id(ket2)
        assert kept1.qstate_key in ket1.keys and kept2.qstate_key in ket1.keys
        state = correct_order(ket1.state, ket1.keys)

        assert complex_array_equal(phi_minus, state)
        if ep1.meas_res == 0:
            counter += 1
        else:
            pass

    assert abs(counter - 50) < 10


def test_BBPSSW_phi_minus_phi_minus():
    """
    phi- phi-
     0b0
         [0.5+0.j 0. +0.j 0. +0.j 0.5+0.j]
     0b1
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
     0b10
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
     0b11
         [-0.5+0.j  0. +0.j  0. +0.j -0.5+0.j]
    """
    counter = 0
    for i in range(100):
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(phi_minus, phi_minus, i)
        assert kept1.entangled_memory == {'node_id': 'a2', 'memo_id': 'kept2'}
        assert kept2.entangled_memory == {'node_id': 'a1', 'memo_id': 'kept1'}
        assert ep1.meas_res == ep2.meas_res

        ket1 = tl.quantum_manager.get(kept1.qstate_key)
        ket2 = tl.quantum_manager.get(kept2.qstate_key)
        assert id(ket1) == id(ket2)
        assert kept1.qstate_key in ket1.keys and kept2.qstate_key in ket1.keys
        state = correct_order(ket1.state, ket1.keys)

        if ep1.meas_res == 0:
            counter += 1
            assert complex_array_equal(phi_plus, state)
        else:
            assert complex_array_equal([-SQRT_HALF, 0, 0, -SQRT_HALF], state)

    assert abs(counter - 50) < 10


def test_BBPSSW_phi_plus_psi_plus():
    """
    phi+ psi+
     0b0
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
     0b1
         [0.5+0.j 0. +0.j 0. +0.j 0.5+0.j]
     0b10
         [0.5+0.j 0. +0.j 0. +0.j 0.5+0.j]
     0b11
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
    """
    counter = 0
    for i in range(100):
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(phi_plus, psi_plus, i)
        assert kept1.entangled_memory == kept2.entangled_memory == {'node_id': None, 'memo_id': None}
        assert ep1.meas_res != ep2.meas_res

        ket1 = tl.quantum_manager.get(kept1.qstate_key)
        ket2 = tl.quantum_manager.get(kept2.qstate_key)
        assert id(ket1) != id(ket2)
        assert len(ket1.keys) == len(ket2.keys) == 1

        if ep1.meas_res == 0:
            counter += 1

    assert abs(counter - 50) < 10


def test_BBPSSW_phi_plus_psi_minus():
    """
    phi+ psi-
     0b0
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
     0b1
         [ 0.5+0.j  0. +0.j  0. +0.j -0.5+0.j]
     0b10
         [-0.5+0.j  0. +0.j  0. +0.j  0.5+0.j]
     0b11
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
    """
    counter = 0
    for i in range(100):
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(phi_plus, psi_minus, i)
        assert kept1.entangled_memory == kept2.entangled_memory == {'node_id': None, 'memo_id': None}
        assert ep1.meas_res != ep2.meas_res

        ket1 = tl.quantum_manager.get(kept1.qstate_key)
        ket2 = tl.quantum_manager.get(kept2.qstate_key)
        assert id(ket1) != id(ket2)
        assert len(ket1.keys) == len(ket2.keys) == 1

        if ep1.meas_res == 0:
            counter += 1
    assert abs(counter - 50) < 10


def test_BBPSSW_phi_minus_psi_plus():
    """
    phi- psi+
     0b0
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
     0b1
         [ 0.5+0.j  0. +0.j  0. +0.j -0.5+0.j]
     0b10
         [ 0.5+0.j  0. +0.j  0. +0.j -0.5+0.j]
     0b11
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
    """
    counter = 0
    for i in range(100):
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(phi_minus, psi_plus, i)
        assert kept1.entangled_memory == kept2.entangled_memory == {'node_id': None, 'memo_id': None}
        assert ep1.meas_res != ep2.meas_res

        ket1 = tl.quantum_manager.get(kept1.qstate_key)
        ket2 = tl.quantum_manager.get(kept2.qstate_key)
        assert id(ket1) != id(ket2)
        assert len(ket1.keys) == len(ket2.keys) == 1

        if ep1.meas_res == 0:
            counter += 1
    assert abs(counter - 50) < 10


def test_BBPSSW_phi_minus_psi_minus():
    """
    phi- psi-
     0b0
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
     0b1
         [0.5+0.j 0. +0.j 0. +0.j 0.5+0.j]
     0b10
         [-0.5+0.j  0. +0.j  0. +0.j -0.5+0.j]
     0b11
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
    """
    counter = 0
    for i in range(100):
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(phi_minus, psi_minus, i)
        assert kept1.entangled_memory == kept2.entangled_memory == {'node_id': None, 'memo_id': None}
        assert ep1.meas_res != ep2.meas_res

        ket1 = tl.quantum_manager.get(kept1.qstate_key)
        ket2 = tl.quantum_manager.get(kept2.qstate_key)
        assert id(ket1) != id(ket2)
        assert len(ket1.keys) == len(ket2.keys) == 1

        if ep1.meas_res == 0:
            counter += 1

    assert abs(counter - 50) < 10


def test_BBPSSW_psi_plus_phi_plus():
    """
    psi+ phi+
     0b0
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
     0b1
         [0. +0.j 0.5+0.j 0.5+0.j 0. +0.j]
     0b10
         [0. +0.j 0.5+0.j 0.5+0.j 0. +0.j]
     0b11
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
    """
    counter = 0
    for i in range(100):
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(psi_plus, phi_plus, i)
        assert kept1.entangled_memory == kept2.entangled_memory == {'node_id': None, 'memo_id': None}
        assert ep1.meas_res != ep2.meas_res

        ket1 = tl.quantum_manager.get(kept1.qstate_key)
        ket2 = tl.quantum_manager.get(kept2.qstate_key)
        assert id(ket1) != id(ket2)
        assert len(ket1.keys) == len(ket2.keys) == 1

        if ep1.meas_res == 0:
            counter += 1

    assert abs(counter - 50) < 10


def test_BBPSSW_psi_plus_phi_minus():
    """
    psi+ phi-
     0b0
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
     0b1
         [ 0. +0.j -0.5+0.j  0.5+0.j  0. +0.j]
     0b10
         [ 0. +0.j  0.5+0.j -0.5+0.j  0. +0.j]
     0b11
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
    """
    counter = 0
    for i in range(100):
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(psi_plus, phi_minus, i)
        assert kept1.entangled_memory == kept2.entangled_memory == {'node_id': None, 'memo_id': None}
        assert ep1.meas_res != ep2.meas_res

        ket1 = tl.quantum_manager.get(kept1.qstate_key)
        ket2 = tl.quantum_manager.get(kept2.qstate_key)
        assert id(ket1) != id(ket2)
        assert len(ket1.keys) == len(ket2.keys) == 1

        if ep1.meas_res == 0:
            counter += 1
    assert abs(counter - 50) < 10


def test_BBPSSW_psi_minus_phi_plus():
    """
    psi- phi+
     0b0
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
     0b1
         [ 0. +0.j  0.5+0.j -0.5+0.j  0. +0.j]
     0b10
         [ 0. +0.j  0.5+0.j -0.5+0.j  0. +0.j]
     0b11
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
    """
    counter = 0
    for i in range(100):
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(psi_minus, phi_plus, i)
        assert kept1.entangled_memory == kept2.entangled_memory == {'node_id': None, 'memo_id': None}
        assert ep1.meas_res != ep2.meas_res

        ket1 = tl.quantum_manager.get(kept1.qstate_key)
        ket2 = tl.quantum_manager.get(kept2.qstate_key)
        assert id(ket1) != id(ket2)
        assert len(ket1.keys) == len(ket2.keys) == 1

        if ep1.meas_res == 0:
            counter += 1

    assert abs(counter - 50) < 10


def test_BBPSSW_psi_minus_phi_minus():
    """
    psi- phi-
     0b0
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
     0b1
         [ 0. +0.j -0.5+0.j -0.5+0.j  0. +0.j]
     0b10
         [0. +0.j 0.5+0.j 0.5+0.j 0. +0.j]
     0b11
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
    """
    counter = 0
    for i in range(100):
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(psi_minus, phi_minus, i)
        assert kept1.entangled_memory == kept2.entangled_memory == {'node_id': None, 'memo_id': None}
        assert ep1.meas_res != ep2.meas_res

        ket1 = tl.quantum_manager.get(kept1.qstate_key)
        ket2 = tl.quantum_manager.get(kept2.qstate_key)
        assert id(ket1) != id(ket2)
        assert len(ket1.keys) == len(ket2.keys) == 1

        if ep1.meas_res == 0:
            counter += 1

    assert abs(counter - 50) < 10


def test_BBPSSW_psi_plus_psi_plus():
    """
    psi+ psi+
     0b0
         [0. +0.j 0.5+0.j 0.5+0.j 0. +0.j]
     0b1
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
     0b10
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
     0b11
         [0. +0.j 0.5+0.j 0.5+0.j 0. +0.j]
    """
    counter = 0
    for i in range(100):
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(psi_plus, psi_plus, i)
        assert kept1.entangled_memory == {'node_id': 'a2', 'memo_id': 'kept2'}
        assert kept2.entangled_memory == {'node_id': 'a1', 'memo_id': 'kept1'}
        assert ep1.meas_res == ep2.meas_res

        ket1 = tl.quantum_manager.get(kept1.qstate_key)
        ket2 = tl.quantum_manager.get(kept2.qstate_key)
        assert id(ket1) == id(ket2)
        assert kept1.qstate_key in ket1.keys and kept2.qstate_key in ket1.keys

        state = correct_order(ket1.state, ket1.keys)
        assert complex_array_equal(psi_plus, state)
        if ep1.meas_res == 0:
            counter += 1
        else:
            pass

    assert abs(counter - 50) < 10


def test_BBPSSW_psi_plus_psi_minus():
    """
    psi+ psi-
     0b0
         [ 0. +0.j  0.5+0.j -0.5+0.j  0. +0.j]
     0b1
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
     0b10
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
     0b11
         [ 0. +0.j -0.5+0.j  0.5+0.j  0. +0.j]
    """
    counter = 0
    for i in range(100):
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(psi_plus, psi_minus, i)
        assert kept1.entangled_memory == {'node_id': 'a2', 'memo_id': 'kept2'}
        assert kept2.entangled_memory == {'node_id': 'a1', 'memo_id': 'kept1'}
        assert ep1.meas_res == ep2.meas_res

        ket1 = tl.quantum_manager.get(kept1.qstate_key)
        ket2 = tl.quantum_manager.get(kept2.qstate_key)
        assert id(ket1) == id(ket2)
        assert kept1.qstate_key in ket1.keys and kept2.qstate_key in ket1.keys

        state = correct_order(ket1.state, ket1.keys)

        if ep1.meas_res == 0:
            counter += 1
            assert complex_array_equal(psi_minus, state)
        else:
            assert complex_array_equal([0, -SQRT_HALF, SQRT_HALF, 0], state)

    assert abs(counter - 50) < 10


def test_BBPSSW_psi_minus_psi_plus():
    """
    psi- psi+
     0b0
         [ 0. +0.j  0.5+0.j -0.5+0.j  0. +0.j]
     0b1
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
     0b10
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
     0b11
         [ 0. +0.j  0.5+0.j -0.5+0.j  0. +0.j]
    """
    counter = 0
    for i in range(100):
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(psi_minus, psi_plus, i)
        assert kept1.entangled_memory == {'node_id': 'a2', 'memo_id': 'kept2'}
        assert kept2.entangled_memory == {'node_id': 'a1', 'memo_id': 'kept1'}
        assert ep1.meas_res == ep2.meas_res

        ket1 = tl.quantum_manager.get(kept1.qstate_key)
        ket2 = tl.quantum_manager.get(kept2.qstate_key)
        assert id(ket1) == id(ket2)
        assert kept1.qstate_key in ket1.keys and kept2.qstate_key in ket1.keys

        state = correct_order(ket1.state, ket1.keys)
        assert complex_array_equal(psi_minus, state)
        if ep1.meas_res == 0:
            counter += 1
        else:
            # assert quantum state
            pass

    assert abs(counter - 50) < 10


def test_BBPSSW_psi_minus_psi_minus():
    """
    psi- psi-
     0b0
         [0. +0.j 0.5+0.j 0.5+0.j 0. +0.j]
     0b1
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
     0b10
         [0.+0.j 0.+0.j 0.+0.j 0.+0.j]
     0b11
         [ 0. +0.j -0.5+0.j -0.5+0.j  0. +0.j]
    """
    counter = 0
    for i in range(100):
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(psi_minus, psi_minus, i)
        assert kept1.entangled_memory == {'node_id': 'a2', 'memo_id': 'kept2'}
        assert kept2.entangled_memory == {'node_id': 'a1', 'memo_id': 'kept1'}
        assert ep1.meas_res == ep2.meas_res

        ket1 = tl.quantum_manager.get(kept1.qstate_key)
        ket2 = tl.quantum_manager.get(kept2.qstate_key)
        assert id(ket1) == id(ket2)
        assert kept1.qstate_key in ket1.keys and kept2.qstate_key in ket1.keys
        state = correct_order(ket1.state, ket1.keys)

        if ep1.meas_res == 0:
            counter += 1
            assert complex_array_equal(psi_plus, state)
        else:
            assert complex_array_equal([0, -SQRT_HALF, -SQRT_HALF, 0], state)
    assert abs(counter - 50) < 10


def get_random_state_by_fidelity(fidelity):
    def prob_distribution(f: float) -> List[float]:
        return [f, (1 - f) / 3, (1 - f) / 3, (1 - f) / 3]

    choice = np.random.choice
    index1, index2 = [choice(range(4), 1, p=prob_distribution(fidelity))[0]
                      for _ in range(2)]
    return BELL_STATES[index1], BELL_STATES[index2]


def test_BBPSSW_fidelity():
    for i in range(1000):
        fidelity = np.random.uniform(0.5, 1)
        state1, state2 = get_random_state_by_fidelity(fidelity)
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(state1,
                                                                   state2,
                                                                   i,
                                                                   fidelity)
        a1, a2 = [tl.get_entity_by_name(name) for name in ["a1", "a2"]]
        assert (meas1, RAW) in a1.resource_manager.log
        assert (meas2, RAW) in a2.resource_manager.log
        assert kept1.fidelity == kept2.fidelity

        if ep1.meas_res == ep2.meas_res:
            assert kept1.fidelity == BBPSSW.improved_fidelity(fidelity)
            assert kept1.entangled_memory["node_id"] == "a2" and \
                   kept2.entangled_memory["node_id"] == "a1"
            assert a1.resource_manager.log[-1] == (kept1, ENTANGLED)
            assert a2.resource_manager.log[-1] == (kept2, ENTANGLED)
        else:
            assert kept1.fidelity == 0
            assert kept1.entangled_memory["node_id"] == kept2.entangled_memory["node_id"] == None
            assert a1.resource_manager.log[-1] == (kept1, RAW)
            assert a2.resource_manager.log[-1] == (kept2, RAW)


def test_BBPSSW_success_rate():
    counter1 = counter2 = 0
    fidelity = 0.8

    for i in range(1000):
        state1, state2 = get_random_state_by_fidelity(fidelity)
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(state1,
                                                                   state2,
                                                                   i,
                                                                   fidelity)
        if ep1.meas_res == ep2.meas_res:
            counter1 += 1
        else:
            counter2 += 1

        tl.run()

    assert abs(counter1 / (counter1 + counter2) - success_probability(fidelity)) < 0.1
