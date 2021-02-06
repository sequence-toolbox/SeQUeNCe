from typing import Dict, List, Tuple
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

MEMORY_TYPES = ['kept', 'meas']

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
    def __init__(self, name, timeline, **kwargs):
        Node.__init__(self, name, timeline)
        self.message_log = []
        self.resource_manager = FakeResourceManager(self)

    def receive_message(self, src: str, message: "Message"):
        self.message_log.append((self.timeline.now(), src, message))
        for protocol in self.protocols:
            if protocol.name == message.receiver:
                protocol.received_message(src, message)


def test_BBPSSWMessage():
    message = BBPSSWMessage(BBPSSWMsgType.PURIFICATION_RES, "another", meas_res=0)
    assert message.msg_type == BBPSSWMsgType.PURIFICATION_RES
    assert message.receiver == "another"
    assert message.meas_res == 0
    with pytest.raises(Exception):
        BBPSSWMessage("unknown type")


def assert_error_detected(kets: list, kept_memories: List[Memory], ep: List[EntanglementProtocol]) -> None:
    assert all(memory.entangled_memory == {'node_id': None, 'memo_id': None} for memory in kept_memories)
    assert ep[0].meas_res != ep[1].meas_res

    assert id(kets[0]) != id(kets[1])
    assert all(len(ket.keys) == 1 for ket in kets)


def get_kets_from(timeline: Timeline, kept_memories: List[Memory]) -> list:
    return [timeline.quantum_manager.get(memory.qstate_key) for memory in kept_memories]


def get_correct_order_state_from(kets: list, kept_memories: List[Memory]) -> np.array:
    assert id(kets[0]) == id(kets[1])
    assert all(memory.qstate_key in kets[0].keys for memory in kept_memories)

    return correct_order(kets[0].state, kets[0].keys)


def complex_array_equal(arr1, arr2, precision: int = 5) -> bool:
    return all(abs(c1 - c2) < 2 ** -precision for c1, c2 in zip(arr1, arr2))


def correct_order(state: List[float], keys) -> np.array:
    if keys[0] > keys[1]:
        return np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]]) @ state


def create_memories_by_type(timeline: Timeline, states, fidelity: float = 1.0) -> Dict[str, List[Memory]]:
    memories_by_type = {
        memory_type: [
            Memory(f'{memory_type}{i}', timeline, fidelity, frequency=0, efficiency=1, coherence_time=1, wavelength=HALF_MICRON)
            for i in range(2)
        ]
        for memory_type in MEMORY_TYPES
    }

    for memory_type, memories in memories_by_type.items():
        for i, memory in enumerate(memories):
            other_index = (i + 1) % 2
            memory.entangled_memory = {'node_id': f'a{other_index}', 'memo_id': f'{memory_type}{other_index}'}
            memory.fidelity = fidelity

    for i, memories in enumerate(memories_by_type.values()):
        qstate_keys = [memory.qstate_key for memory in memories]
        timeline.quantum_manager.set(qstate_keys, states[i])

    return memories_by_type


def create_nodes(timeline: Timeline) -> List[FakeNode]:
    nodes = [FakeNode(f'a{i}', timeline) for i in range(2)]
    classical_channels = [ClassicalChannel(f'cc{i}', timeline, 0, 1e5) for i in range(2)]

    for i, classical_channel in enumerate(classical_channels):
        classical_channel.delay = ONE_MILLISECOND
        classical_channel.set_ends(nodes[i], nodes[not i])

    return nodes


def create_protocols(nodes: List[FakeNode], memories_by_type: Dict[str, List[Memory]]) -> List[EntanglementProtocol]:
    ep = [BBPSSW(nodes[i], f'a{i}.ep{i}', memories_by_type['kept'][i], memories_by_type['meas'][i]) for i in range(2)]

    for node, protocol in zip(nodes, ep):
        node.protocols.append(protocol)

    for i, protocol in enumerate(ep):
        protocol.set_others(ep[not i])

    for protocol in ep:
        protocol.start()

    return ep


def prepare_timeline_with_nodes(seed = None) -> Tuple[Timeline, List[FakeNode]]:
    timeline = Timeline()

    if seed is not None:
        timeline.seed(seed)

    nodes = create_nodes(timeline)

    timeline.init()

    return timeline, nodes


def run(timeline: Timeline, nodes: List[FakeNode], states: List[List[float]]) \
        -> Tuple[list, List[Memory], List[EntanglementProtocol]]:
    memories_by_type = create_memories_by_type(timeline, states)
    ep = create_protocols(nodes, memories_by_type)

    timeline.run()

    assert all(memory.entangled_memory == {'node_id': None, 'memo_id': None} for memory in memories_by_type['meas'])

    kets = get_kets_from(timeline, memories_by_type['kept'])

    return kets, memories_by_type['kept'], ep


def create_scenario(state0: List[float], state1: List[float], seed) \
        -> Tuple[Timeline, List[Memory], List[EntanglementProtocol]]:
    timeline, nodes = prepare_timeline_with_nodes(seed)
    states = [state0, state1]

    return run(timeline, nodes, states)


def get_probabilities_from(fidelity: float) -> List[float]:
    return [fidelity] + 3 * [(1 - fidelity) / 3]


def get_random_bell_states_from_phi_plus(fidelity: float) -> List[List[float]]:
    probabilities = get_probabilities_from(fidelity)
    return [BELL_STATES[np.random.choice(list(BELL_STATES.keys()), 1, p=probabilities)[0]] for _ in range(2)]


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
        kets, kept_memories, ep = create_scenario(phi_plus, phi_plus, i)
        assert all(memory.entangled_memory == {'node_id': f'a{(i + 1) % 2}', 'memo_id': f'kept{(i + 1) % 2}'} for i, memory in enumerate(kept_memories))
        assert ep[0].meas_res == ep[1].meas_res
        if ep[0].meas_res == 0:
            counter += 1
        state = get_correct_order_state_from(kets, kept_memories)
        assert complex_array_equal(phi_plus, state)
        # assert kept_memories[0] and kept_memories[1] point to the same ketsstate
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
        kets, kept_memories, ep = create_scenario(phi_plus, phi_minus, i)
        assert all(memory.entangled_memory == {'node_id': f'a{(i + 1) % 2}', 'memo_id': f'kept{(i + 1) % 2}'} for i, memory in enumerate(kept_memories))
        assert ep[0].meas_res == ep[1].meas_res
        state = get_correct_order_state_from(kets, kept_memories)
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
        kets, kept_memories, ep = create_scenario(phi_minus, phi_plus, i)
        assert all(memory.entangled_memory == {'node_id': f'a{(i + 1) % 2}', 'memo_id': f'kept{(i + 1) % 2}'} for i, memory in enumerate(kept_memories))
        assert ep[0].meas_res == ep[1].meas_res

        state = get_correct_order_state_from(kets, kept_memories)

        assert complex_array_equal(phi_minus, state)
        if ep[0].meas_res == 0:
            counter += 1

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
        kets, kept_memories, ep = create_scenario(phi_minus, phi_minus, i)
        assert all(memory.entangled_memory == {'node_id': f'a{(i + 1) % 2}', 'memo_id': f'kept{(i + 1) % 2}'} for i, memory in enumerate(kept_memories))
        assert ep[0].meas_res == ep[1].meas_res

        state = get_correct_order_state_from(kets, kept_memories)

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
        kets, kept_memories, ep = create_scenario(phi_plus, psi_plus, i)
        assert_error_detected(kets, kept_memories, ep)

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
        kets, kept_memories, ep = create_scenario(phi_plus, psi_minus, i)
        assert_error_detected(kets, kept_memories, ep)

        if ep[0].meas_res == 0:
            counter += 1

    assert abs(counter - 50) < 10


def error_detected():
    counter = 0
    for i in range(100):
        kets, kept_memories, ep = create_scenario(phi_plus, psi_minus, i)
        assert_error_detected(kets, kept_memories, ep)

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
        kets, kept_memories, ep = create_scenario(phi_minus, psi_plus, i)
        assert_error_detected(kets, kept_memories, ep)

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
        kets, kept_memories, ep = create_scenario(phi_minus, psi_minus, i)
        assert_error_detected(kets, kept_memories, ep)

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
        kets, kept_memories, ep = create_scenario(psi_plus, phi_plus, i)
        assert_error_detected(kets, kept_memories, ep)

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
        kets, kept_memories, ep = create_scenario(psi_plus, phi_minus, i)
        assert_error_detected(kets, kept_memories, ep)

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
        kets, kept_memories, ep = create_scenario(psi_minus, phi_plus, i)
        assert_error_detected(kets, kept_memories, ep)

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
        kets, kept_memories, ep = create_scenario(psi_minus, phi_minus, i)
        assert_error_detected(kets, kept_memories, ep)

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
        kets, kept_memories, ep = create_scenario(psi_plus, psi_plus, i)
        assert all(memory.entangled_memory == {'node_id': f'a{(i + 1) % 2}', 'memo_id': f'kept{(i + 1) % 2}'} for i, memory in enumerate(kept_memories))
        assert ep[0].meas_res == ep[1].meas_res

        state = get_correct_order_state_from(kets, kept_memories)
        assert complex_array_equal(psi_plus, state)
        if ep[0].meas_res == 0:
            counter += 1


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
        kets, kept_memories, ep = create_scenario(psi_plus, psi_minus, i)
        assert all(memory.entangled_memory == {'node_id': f'a{(i + 1) % 2}', 'memo_id': f'kept{(i + 1) % 2}'} for i, memory in enumerate(kept_memories))
        assert ep[0].meas_res == ep[1].meas_res

        state = get_correct_order_state_from(kets, kept_memories)

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
        kets, kept_memories, ep = create_scenario(psi_minus, psi_plus, i)
        assert all(memory.entangled_memory == {'node_id': f'a{(i + 1) % 2}', 'memo_id': f'kept{(i + 1) % 2}'} for i, memory in enumerate(kept_memories))
        assert ep[0].meas_res == ep[1].meas_res

        state = get_correct_order_state_from(kets, kept_memories)
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
        kets, kept_memories, ep = create_scenario(psi_minus, psi_minus, i)
        assert all(memory.entangled_memory == {'node_id': f'a{(i + 1) % 2}', 'memo_id': f'kept{(i + 1) % 2}'} for i, memory in enumerate(kept_memories))
        assert ep[0].meas_res == ep[1].meas_res

        state = get_correct_order_state_from(kets, kept_memories)

        if ep[0].meas_res == 0:
            counter += 1
            assert complex_array_equal(psi_plus, state)
        else:
            assert complex_array_equal([0, -SQRT_HALF, -SQRT_HALF, 0], state)
    assert abs(counter - 50) < 10


def test_BBPSSW_fidelity():
    timeline, nodes = prepare_timeline_with_nodes()

    for i in range(1000):
        fidelity = np.random.uniform(0.5, 1)
        states = get_random_bell_states_from_phi_plus(fidelity)
        memories_by_type = create_memories_by_type(timeline, states, fidelity)
        ep = create_protocols(nodes, memories_by_type)

        timeline.run()

        assert all(node.resource_manager.log[-2] == (memory, RAW) for node, memory in zip(nodes, memories_by_type['meas']))
        assert all(memory.fidelity == 0 for memory in memories_by_type['meas'])

        pure = ep[0].meas_res == ep[1].meas_res
        kept_fidelity = BBPSSW.improved_fidelity(fidelity) if pure else 0

        assert all(memory.fidelity == kept_fidelity for memory in memories_by_type['kept'])
        assert all(node.resource_manager.log[-1] == (memory, ENTANGLED if pure else RAW)
                   for node, memory in zip(nodes, memories_by_type['kept']))
        assert all(memory.entangled_memory["node_id"] == (f'a{(i + 1) % 2}' if pure else None)
                   for i, memory in enumerate(memories_by_type['kept']))


def test_BBPSSW_success_rate():
    timeline, nodes = prepare_timeline_with_nodes()
    counters = [0, 0]
    fidelity = 0.8

    for i in range(1000):
        states = get_random_bell_states_from_phi_plus(fidelity)
        memories_by_type = create_memories_by_type(timeline, states, fidelity)
        ep = create_protocols(nodes, memories_by_type)

        timeline.run()

        counters[ep[0].meas_res != ep[1].meas_res] += 1

    assert abs(counters[0] / sum(counters) - BBPSSW.success_probability(fidelity)) < 0.1
