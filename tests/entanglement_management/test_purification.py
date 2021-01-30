from typing import Dict, List
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

BELL_STATES = {
    'phi_plus': [SQRT_HALF, 0, 0, SQRT_HALF],
    'phi_minus': [SQRT_HALF, 0, 0, -SQRT_HALF],
    'psi_plus': [0, SQRT_HALF, SQRT_HALF, 0],
    'psi_minus': [0, SQRT_HALF, -SQRT_HALF, 0]
}

phi_plus = BELL_STATES['phi_plus']
phi_minus = BELL_STATES['phi_minus']
psi_plus = BELL_STATES['psi_plus']
psi_minus = BELL_STATES['psi_minus']


class FakeResourceManager():
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


def create_memories_by_type(tl: Timeline, states, fidelity: float = 1.0) -> Dict[str, List[Memory]]:
    memory_types = ['kept', 'meas']
    memories_by_type = {
        memory_type: [
            Memory(f'{memory_type}{i}', tl, fidelity=1, frequency=0, efficiency=1, coherence_time=1, wavelength=HALF_MICRON)
            for i in range(2)
        ]
        for memory_type in memory_types
    }

    for memory_type, memories in memories_by_type.items():
        for i in range(2):
            other_index = (i + 1) % 2
            memories[i].entangled_memory = {'node_id': f'a{other_index}', 'memo_id': f'{memory_type}{other_index}'}
            memories[i].fidelity = fidelity

    for i, memories in enumerate(memories_by_type.values()):
        qstate_keys = [memory.qstate_key for memory in memories]
        tl.quantum_manager.set(qstate_keys, states[i])

    return memories_by_type


def create_nodes(tl: Timeline) -> List[FakeNode]:
    a = [FakeNode(f'a{i}', tl) for i in range(2)]
    cc = [ClassicalChannel(f'cc{i}', tl, 0, 1e5) for i in range(2)]

    for i, channel in enumerate(cc):
        channel.delay = ONE_MILLISECOND
        channel.set_ends(a[i], a[not i])

    return a


def create_protocols(a: FakeNode, memories_by_type: Dict[str, List[Memory]]) -> List[EntanglementProtocol]:
    ep = [BBPSSW(a[i], f'a{i}.ep{i}', memories_by_type['kept'][i], memories_by_type['meas'][i]) for i in range(2)]

    for node, protocol in zip(a, ep):
        node.protocols.append(protocol)

    for i, protocol in enumerate(ep):
        protocol.set_others(ep[not i])

    for protocol in ep:
        protocol.start()

    return ep


def create_scenario(state0, state1, seed):
    tl = Timeline()
    tl.seed(seed)
    a = create_nodes(tl)

    tl.init()

    states = [state0, state1]
    memories_by_type = create_memories_by_type(tl, states)
    ep = create_protocols(a, memories_by_type)

    tl.run()

    assert all(memory.entangled_memory == {'node_id': None, 'memo_id': None} for memory in memories_by_type['meas'])

    return tl, memories_by_type['kept'], memories_by_type['meas'], ep


def complex_array_equal(arr1, arr2, precision=5):
    return all(abs(c1 - c2) < 2 ** -precision for c1, c2 in zip(arr1, arr2))


def correct_order(state, keys):
    if keys[0] > keys[1]:
        return np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]]) @ state


def get_probabilities_from(fidelity):
    return [fidelity] + 3 * [(1 - fidelity) / 3]


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
        tl, kept, meas, ep = create_scenario(phi_plus, phi_plus, i)
        assert kept[0].entangled_memory == {'node_id': 'a1', 'memo_id': 'kept1'}
        assert kept[1].entangled_memory == {'node_id': 'a0', 'memo_id': 'kept0'}
        assert ep[0].meas_res == ep[1].meas_res
        if ep[0].meas_res == 0:
            counter += 1
        ket0 = tl.quantum_manager.get(kept[0].qstate_key)
        ket1 = tl.quantum_manager.get(kept[1].qstate_key)
        assert id(ket0) == id(ket1)
        assert kept[0].qstate_key in ket0.keys and kept[1].qstate_key in ket0.keys
        state = correct_order(ket0.state, ket0.keys)
        assert complex_array_equal(phi_plus, state)
        # assert kept[0] and kept[1] point to the same Ketstate
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
        tl, kept, meas, ep = create_scenario(phi_plus, phi_minus, i)
        assert kept[0].entangled_memory == {'node_id': 'a1', 'memo_id': 'kept1'}
        assert kept[1].entangled_memory == {'node_id': 'a0', 'memo_id': 'kept0'}
        assert ep[0].meas_res == ep[1].meas_res
        ket0 = tl.quantum_manager.get(kept[0].qstate_key)
        ket1 = tl.quantum_manager.get(kept[1].qstate_key)
        assert id(ket0) == id(ket1)
        assert kept[0].qstate_key in ket0.keys and kept[1].qstate_key in ket0.keys
        state = correct_order(ket0.state, ket0.keys)
        if ep[0].meas_res == 0:
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
        tl, kept, meas, ep = create_scenario(phi_minus, phi_plus, i)
        assert kept[0].entangled_memory == {'node_id': 'a1', 'memo_id': 'kept1'}
        assert kept[1].entangled_memory == {'node_id': 'a0', 'memo_id': 'kept0'}
        assert ep[0].meas_res == ep[1].meas_res

        ket0 = tl.quantum_manager.get(kept[0].qstate_key)
        ket1 = tl.quantum_manager.get(kept[1].qstate_key)
        assert id(ket0) == id(ket1)
        assert kept[0].qstate_key in ket0.keys and kept[1].qstate_key in ket0.keys
        state = correct_order(ket0.state, ket0.keys)

        assert complex_array_equal(phi_minus, state)
        if ep[0].meas_res == 0:
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
        tl, kept, meas, ep = create_scenario(phi_minus, phi_minus, i)
        assert kept[0].entangled_memory == {'node_id': 'a1', 'memo_id': 'kept1'}
        assert kept[1].entangled_memory == {'node_id': 'a0', 'memo_id': 'kept0'}
        assert ep[0].meas_res == ep[1].meas_res

        ket0 = tl.quantum_manager.get(kept[0].qstate_key)
        ket1 = tl.quantum_manager.get(kept[1].qstate_key)
        assert id(ket0) == id(ket1)
        assert kept[0].qstate_key in ket0.keys and kept[1].qstate_key in ket0.keys
        state = correct_order(ket0.state, ket0.keys)

        if ep[0].meas_res == 0:
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
        tl, kept, meas, ep = create_scenario(phi_plus, psi_plus, i)
        assert kept[0].entangled_memory == kept[1].entangled_memory == {'node_id': None, 'memo_id': None}
        assert ep[0].meas_res != ep[1].meas_res

        ket0 = tl.quantum_manager.get(kept[0].qstate_key)
        ket1 = tl.quantum_manager.get(kept[1].qstate_key)
        assert id(ket0) != id(ket1)
        assert len(ket0.keys) == len(ket1.keys) == 1

        if ep[0].meas_res == 0:
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
        tl, kept, meas, ep = create_scenario(phi_plus, psi_minus, i)
        assert kept[0].entangled_memory == kept[1].entangled_memory == {'node_id': None, 'memo_id': None}
        assert ep[0].meas_res != ep[1].meas_res

        ket0 = tl.quantum_manager.get(kept[0].qstate_key)
        ket1 = tl.quantum_manager.get(kept[1].qstate_key)
        assert id(ket0) != id(ket1)
        assert len(ket0.keys) == len(ket1.keys) == 1

        if ep[0].meas_res == 0:
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
        tl, kept, meas, ep = create_scenario(phi_minus, psi_plus, i)
        assert kept[0].entangled_memory == kept[1].entangled_memory == {'node_id': None, 'memo_id': None}
        assert ep[0].meas_res != ep[1].meas_res

        ket0 = tl.quantum_manager.get(kept[0].qstate_key)
        ket1 = tl.quantum_manager.get(kept[1].qstate_key)
        assert id(ket0) != id(ket1)
        assert len(ket0.keys) == len(ket1.keys) == 1

        if ep[0].meas_res == 0:
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
        tl, kept, meas, ep = create_scenario(phi_minus, psi_minus, i)
        assert kept[0].entangled_memory == kept[1].entangled_memory == {'node_id': None, 'memo_id': None}
        assert ep[0].meas_res != ep[1].meas_res

        ket0 = tl.quantum_manager.get(kept[0].qstate_key)
        ket1 = tl.quantum_manager.get(kept[1].qstate_key)
        assert id(ket0) != id(ket1)
        assert len(ket0.keys) == len(ket1.keys) == 1

        if ep[0].meas_res == 0:
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
        tl, kept, meas, ep = create_scenario(psi_plus, phi_plus, i)
        assert kept[0].entangled_memory == kept[1].entangled_memory == {'node_id': None, 'memo_id': None}
        assert ep[0].meas_res != ep[1].meas_res

        ket0 = tl.quantum_manager.get(kept[0].qstate_key)
        ket1 = tl.quantum_manager.get(kept[1].qstate_key)
        assert id(ket0) != id(ket1)
        assert len(ket0.keys) == len(ket1.keys) == 1

        if ep[0].meas_res == 0:
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
        tl, kept, meas, ep = create_scenario(psi_plus, phi_minus, i)
        assert kept[0].entangled_memory == kept[1].entangled_memory == {'node_id': None, 'memo_id': None}
        assert ep[0].meas_res != ep[1].meas_res

        ket0 = tl.quantum_manager.get(kept[0].qstate_key)
        ket1 = tl.quantum_manager.get(kept[1].qstate_key)
        assert id(ket0) != id(ket1)
        assert len(ket0.keys) == len(ket1.keys) == 1

        if ep[0].meas_res == 0:
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
        tl, kept, meas, ep = create_scenario(psi_minus, phi_plus, i)
        assert kept[0].entangled_memory == kept[1].entangled_memory == {'node_id': None, 'memo_id': None}
        assert ep[0].meas_res != ep[1].meas_res

        ket0 = tl.quantum_manager.get(kept[0].qstate_key)
        ket1 = tl.quantum_manager.get(kept[1].qstate_key)
        assert id(ket0) != id(ket1)
        assert len(ket0.keys) == len(ket1.keys) == 1

        if ep[0].meas_res == 0:
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
        tl, kept, meas, ep = create_scenario(psi_minus, phi_minus, i)
        assert kept[0].entangled_memory == kept[1].entangled_memory == {'node_id': None, 'memo_id': None}
        assert ep[0].meas_res != ep[1].meas_res

        ket0 = tl.quantum_manager.get(kept[0].qstate_key)
        ket1 = tl.quantum_manager.get(kept[1].qstate_key)
        assert id(ket0) != id(ket1)
        assert len(ket0.keys) == len(ket1.keys) == 1

        if ep[0].meas_res == 0:
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
        tl, kept, meas, ep = create_scenario(psi_plus, psi_plus, i)
        assert kept[0].entangled_memory == {'node_id': 'a1', 'memo_id': 'kept1'}
        assert kept[1].entangled_memory == {'node_id': 'a0', 'memo_id': 'kept0'}
        assert ep[0].meas_res == ep[1].meas_res

        ket0 = tl.quantum_manager.get(kept[0].qstate_key)
        ket1 = tl.quantum_manager.get(kept[1].qstate_key)
        assert id(ket0) == id(ket1)
        assert kept[0].qstate_key in ket0.keys and kept[1].qstate_key in ket0.keys

        state = correct_order(ket0.state, ket0.keys)
        assert complex_array_equal(psi_plus, state)
        if ep[0].meas_res == 0:
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
        tl, kept, meas, ep = create_scenario(psi_plus, psi_minus, i)
        assert kept[0].entangled_memory == {'node_id': 'a1', 'memo_id': 'kept1'}
        assert kept[1].entangled_memory == {'node_id': 'a0', 'memo_id': 'kept0'}
        assert ep[0].meas_res == ep[1].meas_res

        ket0 = tl.quantum_manager.get(kept[0].qstate_key)
        ket1 = tl.quantum_manager.get(kept[1].qstate_key)
        assert id(ket0) == id(ket1)
        assert kept[0].qstate_key in ket0.keys and kept[1].qstate_key in ket0.keys

        state = correct_order(ket0.state, ket0.keys)

        if ep[0].meas_res == 0:
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
        tl, kept, meas, ep = create_scenario(psi_minus, psi_plus, i)
        assert kept[0].entangled_memory == {'node_id': 'a1', 'memo_id': 'kept1'}
        assert kept[1].entangled_memory == {'node_id': 'a0', 'memo_id': 'kept0'}
        assert ep[0].meas_res == ep[1].meas_res

        ket0 = tl.quantum_manager.get(kept[0].qstate_key)
        ket1 = tl.quantum_manager.get(kept[1].qstate_key)
        assert id(ket0) == id(ket1)
        assert kept[0].qstate_key in ket0.keys and kept[1].qstate_key in ket0.keys

        state = correct_order(ket0.state, ket0.keys)
        assert complex_array_equal(psi_minus, state)
        if ep[0].meas_res == 0:
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
        tl, kept, meas, ep = create_scenario(psi_minus, psi_minus, i)
        assert kept[0].entangled_memory == {'node_id': 'a1', 'memo_id': 'kept1'}
        assert kept[1].entangled_memory == {'node_id': 'a0', 'memo_id': 'kept0'}
        assert ep[0].meas_res == ep[1].meas_res

        ket0 = tl.quantum_manager.get(kept[0].qstate_key)
        ket1 = tl.quantum_manager.get(kept[1].qstate_key)
        assert id(ket0) == id(ket1)
        assert kept[0].qstate_key in ket0.keys and kept[1].qstate_key in ket0.keys
        state = correct_order(ket0.state, ket0.keys)

        if ep[0].meas_res == 0:
            counter += 1
            assert complex_array_equal(psi_plus, state)
        else:
            assert complex_array_equal([0, -SQRT_HALF, -SQRT_HALF, 0], state)
    assert abs(counter - 50) < 10


def test_BBPSSW_fidelity():
    tl = Timeline()
    a = create_nodes(tl)

    tl.init()

    for i in range(1000):
        fidelity = np.random.uniform(0.5, 1)
        probabilities = get_probabilities_from(fidelity)
        states = [BELL_STATES[np.random.choice(list(BELL_STATES.keys()), 1, p=probabilities)[0]] for _ in range(2)]
        memories_by_type = create_memories_by_type(tl, states, fidelity)
        ep = create_protocols(a, memories_by_type)

        tl.run()

        assert all(a[i].resource_manager.log[-2] == (memories_by_type['meas'][i], RAW) for i in range(2))
        assert all(memory.fidelity == 0 for memory in memories_by_type['meas'])

        if ep[0].meas_res == ep[1].meas_res:
            assert all(memory.fidelity == BBPSSW.improved_fidelity(fidelity) for memory in memories_by_type['kept'])
            assert all(memory.entangled_memory["node_id"] == f'a{(i + 1) % 2}' for i, memory in enumerate(memories_by_type['kept']))
            assert all(a[i].resource_manager.log[-1] == (memories_by_type['kept'][i], ENTANGLED) for i in range(2))
        else:
            assert all(memory.fidelity == 0 for memory in memories_by_type['kept'])
            assert all(memory.entangled_memory["node_id"] is None for memory in memories_by_type['kept'])
            assert all(a[i].resource_manager.log[-1] == (memories_by_type['kept'][i], RAW) for i in range(2))


def test_BBPSSW_success_rate():
    tl = Timeline()
    a = create_nodes(tl)

    tl.init()
    counters = [0, 0]
    fidelity = 0.8

    for i in range(1000):
        probabilities = get_probabilities_from(fidelity)
        states = [BELL_STATES[np.random.choice(list(BELL_STATES.keys()), 1, p=probabilities)[0]] for _ in range(2)]
        memories_by_type = create_memories_by_type(tl, states, fidelity)
        ep = create_protocols(a, memories_by_type)

        counters[ep[0].meas_res != ep[1].meas_res] += 1

        tl.run()

    assert abs(counters[0] / sum(counters) - BBPSSW.success_probability(fidelity)) < 0.1
