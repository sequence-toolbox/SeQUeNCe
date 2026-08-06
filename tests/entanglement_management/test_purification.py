import numpy as np
import pytest

from sequence.components.memory import Memory
from sequence.components.optical_channel import ClassicalChannel
from sequence.constants import (
    BELL_DIAGONAL_STATE_FORMALISM,
    DENSITY_MATRIX_FORMALISM,
    KET_VECTOR_FORMALISM,
    SQRT_HALF,
    PHI_PLUS,
    PHI_MINUS,
    PSI_PLUS,
    PSI_MINUS,
)
from sequence.entanglement_management.purification import (
    BBPSSW_BDS,
    DEJMPS_BDS,
    BBPSSWCircuit,
    BBPSSWMessage,
    BBPSSWMsgType,
    BBPSSWProtocol,
    DEJMPS_BDS_PROTOCOL,
)
from sequence.kernel.quantum_manager import QuantumManager
from sequence.kernel.timeline import Timeline
from sequence.topology.node import Node
from sequence.message import Message

np.random.seed(0)

PURIFIED = 'PURIFIED'
ENTANGLED = 'ENTANGLED'
RAW = 'RAW'

HALF_MICRON = 500
ONE_MILLISECOND = 1e9
# SQRT_HALF = 0.5 ** 0.5

# phi_plus = [SQRT_HALF, 0, 0, SQRT_HALF]
# phi_minus = [SQRT_HALF, 0, 0, -SQRT_HALF]
# psi_plus = [0, SQRT_HALF, SQRT_HALF, 0]
# psi_minus = [0, SQRT_HALF, -SQRT_HALF, 0]
BELL_STATES = [PHI_PLUS, PHI_MINUS, PSI_PLUS, PSI_MINUS]


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

    def receive_message(self, src: str, msg: Message):
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


def test_BBPSSW_registered_formalisms_and_factory_selection():
    old_protocol_formalism = BBPSSWProtocol.get_formalism()
    old_manager_formalism = QuantumManager.get_active_formalism()

    try:
        registered_formalisms = set(BBPSSWProtocol.list_protocols())

        assert {
            KET_VECTOR_FORMALISM,
            DENSITY_MATRIX_FORMALISM,
            BELL_DIAGONAL_STATE_FORMALISM,
        }.issubset(registered_formalisms)

        for formalism in [KET_VECTOR_FORMALISM, DENSITY_MATRIX_FORMALISM]:
            QuantumManager.set_global_manager_formalism(formalism)
            BBPSSWProtocol.set_formalism(formalism)
            tl = Timeline()
            node = FakeNode("a1", tl)
            kept = Memory("kept", tl, fidelity=1, frequency=0, efficiency=1, coherence_time=1, wavelength=HALF_MICRON)
            measured = Memory("measured", tl, fidelity=1, frequency=0, efficiency=1, coherence_time=1, wavelength=HALF_MICRON)

            protocol = BBPSSWProtocol.create(node, "a1.ep1", kept, measured)

            assert isinstance(protocol, BBPSSWCircuit)

        QuantumManager.set_global_manager_formalism(BELL_DIAGONAL_STATE_FORMALISM)
        BBPSSWProtocol.set_formalism(BELL_DIAGONAL_STATE_FORMALISM)
        tl = Timeline()
        node = FakeNode("a1", tl)
        kept = Memory("kept", tl, fidelity=1, frequency=0, efficiency=1, coherence_time=1, wavelength=HALF_MICRON)
        measured = Memory("measured", tl, fidelity=1, frequency=0, efficiency=1, coherence_time=1, wavelength=HALF_MICRON)

        protocol = BBPSSWProtocol.create(node, "a1.ep1", kept, measured)

        assert isinstance(protocol, BBPSSW_BDS)
    finally:
        BBPSSWProtocol.set_formalism(old_protocol_formalism)
        QuantumManager.set_global_manager_formalism(old_manager_formalism)


def test_DEJMPS_BDS_registered_as_explicit_protocol_selector():
    old_protocol_formalism = BBPSSWProtocol.get_formalism()
    old_manager_formalism = QuantumManager.get_active_formalism()

    try:
        assert DEJMPS_BDS_PROTOCOL in set(BBPSSWProtocol.list_protocols())

        QuantumManager.set_global_manager_formalism(BELL_DIAGONAL_STATE_FORMALISM)
        BBPSSWProtocol.set_formalism(DEJMPS_BDS_PROTOCOL)

        tl = Timeline()
        node = FakeNode("a1", tl)
        kept = Memory("kept", tl, fidelity=1, frequency=0, efficiency=1,
                      coherence_time=1, wavelength=HALF_MICRON)
        measured = Memory("measured", tl, fidelity=1, frequency=0, efficiency=1,
                          coherence_time=1, wavelength=HALF_MICRON)

        protocol = BBPSSWProtocol.create(node, "a1.ep1", kept, measured)

        assert isinstance(protocol, DEJMPS_BDS)
        assert protocol.is_twirled is False
        assert protocol.protocol_type == DEJMPS_BDS_PROTOCOL
    finally:
        BBPSSWProtocol.set_formalism(old_protocol_formalism)
        QuantumManager.set_global_manager_formalism(old_manager_formalism)


def test_BBPSSW_BDS_improves_fidelity_for_equal_noisy_pairs():
    old_protocol_formalism = BBPSSWProtocol.get_formalism()
    old_manager_formalism = QuantumManager.get_active_formalism()
    input_fidelity = 0.7
    expected_success_probability = success_probability(input_fidelity)
    expected_fidelity = (
        input_fidelity ** 2 + ((1 - input_fidelity) / 3) ** 2
    ) / expected_success_probability

    try:
        QuantumManager.set_global_manager_formalism(BELL_DIAGONAL_STATE_FORMALISM)
        BBPSSWProtocol.set_formalism(BELL_DIAGONAL_STATE_FORMALISM)

        tl = Timeline()
        a1 = FakeNode("a1", tl)
        FakeNode("a2", tl)
        kept1 = Memory("kept1", tl, fidelity=input_fidelity, frequency=0, efficiency=1,
                       coherence_time=1, wavelength=HALF_MICRON)
        kept2 = Memory("kept2", tl, fidelity=input_fidelity, frequency=0, efficiency=1,
                       coherence_time=1, wavelength=HALF_MICRON)
        meas1 = Memory("meas1", tl, fidelity=input_fidelity, frequency=0, efficiency=1,
                       coherence_time=1, wavelength=HALF_MICRON)
        meas2 = Memory("meas2", tl, fidelity=input_fidelity, frequency=0, efficiency=1,
                       coherence_time=1, wavelength=HALF_MICRON)

        tl.init()
        noisy_bds = np.array([
            input_fidelity,
            (1 - input_fidelity) / 3,
            (1 - input_fidelity) / 3,
            (1 - input_fidelity) / 3,
        ])
        tl.quantum_manager.set([kept1.qstate_key, kept2.qstate_key], noisy_bds)
        tl.quantum_manager.set([meas1.qstate_key, meas2.qstate_key], noisy_bds)
        kept1.fidelity = kept2.fidelity = meas1.fidelity = meas2.fidelity = input_fidelity
        kept1.entangled_memory = {"node_id": "a2", "memo_id": "kept2"}
        kept2.entangled_memory = {"node_id": "a1", "memo_id": "kept1"}
        meas1.entangled_memory = {"node_id": "a2", "memo_id": "meas2"}
        meas2.entangled_memory = {"node_id": "a1", "memo_id": "meas1"}

        protocol = BBPSSWProtocol.create(a1, "a1.ep1", kept1, meas1)
        protocol.set_others("a2.ep2", "a2", [kept2.name, meas2.name])

        p_success, purified_bds = protocol.purification_res()

        assert isinstance(protocol, BBPSSW_BDS)
        assert p_success == pytest.approx(expected_success_probability)
        assert purified_bds[0] == pytest.approx(expected_fidelity)
        assert purified_bds[0] > input_fidelity
        assert sum(purified_bds) == pytest.approx(1)
    finally:
        BBPSSWProtocol.set_formalism(old_protocol_formalism)
        QuantumManager.set_global_manager_formalism(old_manager_formalism)



def dejmps_bds_expected(kept_state, meas_state):
    """Return ideal DEJMPS success probability and output in SeQUeNCe BDS order.

    SeQUeNCe uses [Phi+, Phi-, Psi+, Psi-].
    DEJMPS uses paper order [Phi+, Psi-, Psi+, Phi-].
    """
    k_phi_plus, k_phi_minus, k_psi_plus, k_psi_minus = kept_state
    m_phi_plus, m_phi_minus, m_psi_plus, m_psi_minus = meas_state

    p_success = (
        (k_phi_plus + k_psi_minus) * (m_phi_plus + m_psi_minus)
        + (k_psi_plus + k_phi_minus) * (m_psi_plus + m_phi_minus)
    )
    output = np.array([
        k_phi_plus * m_phi_plus + k_psi_minus * m_psi_minus,
        k_phi_plus * m_psi_minus + m_phi_plus * k_psi_minus,
        k_psi_plus * m_psi_plus + k_phi_minus * m_phi_minus,
        m_psi_plus * k_phi_minus + k_psi_plus * m_phi_minus,
    ]) / p_success

    return p_success, output


def bds_protocol_result(protocol_class, kept_state, meas_state, input_fidelity):
    old_protocol_formalism = BBPSSWProtocol.get_formalism()
    old_manager_formalism = QuantumManager.get_active_formalism()

    try:
        QuantumManager.set_global_manager_formalism(BELL_DIAGONAL_STATE_FORMALISM)
        BBPSSWProtocol.set_formalism(BELL_DIAGONAL_STATE_FORMALISM)

        tl = Timeline()
        a1 = FakeNode("a1", tl)
        a2 = FakeNode("a2", tl)
        a1.gate_fid = a2.gate_fid = 1
        a1.meas_fid = a2.meas_fid = 1

        kept1 = Memory("kept1", tl, fidelity=input_fidelity, frequency=0, efficiency=1,
                       coherence_time=1, wavelength=HALF_MICRON)
        kept2 = Memory("kept2", tl, fidelity=input_fidelity, frequency=0, efficiency=1,
                       coherence_time=1, wavelength=HALF_MICRON)
        meas1 = Memory("meas1", tl, fidelity=input_fidelity, frequency=0, efficiency=1,
                       coherence_time=1, wavelength=HALF_MICRON)
        meas2 = Memory("meas2", tl, fidelity=input_fidelity, frequency=0, efficiency=1,
                       coherence_time=1, wavelength=HALF_MICRON)

        tl.init()
        tl.quantum_manager.set([kept1.qstate_key, kept2.qstate_key], kept_state)
        tl.quantum_manager.set([meas1.qstate_key, meas2.qstate_key], meas_state)
        kept1.entangled_memory = {"node_id": "a2", "memo_id": "kept2"}
        kept2.entangled_memory = {"node_id": "a1", "memo_id": "kept1"}
        meas1.entangled_memory = {"node_id": "a2", "memo_id": "meas2"}
        meas2.entangled_memory = {"node_id": "a1", "memo_id": "meas1"}

        protocol = protocol_class(a1, "a1.ep1", kept1, meas1)
        protocol.set_others("a2.ep2", "a2", [kept2.name, meas2.name])

        return protocol, protocol.purification_res()
    finally:
        BBPSSWProtocol.set_formalism(old_protocol_formalism)
        QuantumManager.set_global_manager_formalism(old_manager_formalism)


def test_BBPSSW_BDS_twirls_non_werner_bds_input():
    input_fidelity = 0.7
    kept_state = np.array([0.7, 0.2, 0.05, 0.05])
    meas_state = np.array([0.7, 0.04, 0.20, 0.06])

    expected_success_probability = success_probability(input_fidelity)
    expected_fidelity = (
        input_fidelity ** 2 + ((1 - input_fidelity) / 3) ** 2
    ) / expected_success_probability
    expected_bds = np.array([
        expected_fidelity,
        (1 - expected_fidelity) / 3,
        (1 - expected_fidelity) / 3,
        (1 - expected_fidelity) / 3,
    ])

    protocol, (p_success, purified_bds) = bds_protocol_result(
        BBPSSW_BDS, kept_state, meas_state, input_fidelity
    )

    assert protocol.is_twirled is True
    assert p_success == pytest.approx(expected_success_probability)
    assert purified_bds == pytest.approx(expected_bds)


def test_DEJMPS_BDS_matches_dejmps_recurrence_for_bell_diagonal_states():
    kept_state = np.array([0.72, 0.08, 0.11, 0.09])
    meas_state = np.array([0.68, 0.06, 0.18, 0.08])
    expected_success_probability, expected_bds = dejmps_bds_expected(kept_state, meas_state)

    protocol, (p_success, purified_bds) = bds_protocol_result(
        DEJMPS_BDS, kept_state, meas_state, input_fidelity=kept_state[0]
    )

    assert isinstance(protocol, BBPSSW_BDS)
    assert protocol.is_twirled is False
    assert protocol.protocol_type == 'dejmps_bds'
    assert p_success == pytest.approx(expected_success_probability)
    assert purified_bds == pytest.approx(expected_bds)
    assert np.sum(purified_bds) == pytest.approx(1)


# Pure Bell states in SeQUeNCe BDS order:
# 0 = Phi+, 1 = Phi-, 2 = Psi+, 3 = Psi-.
PURE_BDS_STATES = np.eye(4)

# Independent ideal DEJMPS transition table obtained from the protocol's
# bilateral rotations, bilateral CNOTs, and equal-outcome postselection.
# Entries not listed here fail postselection with probability 1.
DEJMPS_PURE_STATE_TRANSITIONS = {
    (0, 0): 0,
    (0, 3): 1,
    (3, 0): 1,
    (3, 3): 0,
    (2, 2): 2,
    (2, 1): 3,
    (1, 2): 3,
    (1, 1): 2,
}


@pytest.mark.parametrize(
    ("kept_index", "meas_index"),
    [
        (kept_index, meas_index)
        for kept_index in range(4)
        for meas_index in range(4)
    ],
)
def test_DEJMPS_BDS_matches_pure_bell_state_transition_table(
    kept_index, meas_index
):
    """Check all 16 ideal pure-Bell input combinations independently."""
    kept_state = PURE_BDS_STATES[kept_index]
    meas_state = PURE_BDS_STATES[meas_index]

    expected_output_index = DEJMPS_PURE_STATE_TRANSITIONS.get(
        (kept_index, meas_index)
    )

    if expected_output_index is None:
        # No successful branch exists, so the conditional output state is
        # undefined and purification_res() normalizes a zero vector by zero.
        with np.errstate(divide="ignore", invalid="ignore"):
            protocol, (p_success, purified_bds) = bds_protocol_result(
                DEJMPS_BDS,
                kept_state,
                meas_state,
                input_fidelity=kept_state[0],
            )
    else:
        protocol, (p_success, purified_bds) = bds_protocol_result(
            DEJMPS_BDS,
            kept_state,
            meas_state,
            input_fidelity=kept_state[0],
        )

    assert protocol.is_twirled is False

    if expected_output_index is None:
        assert p_success == pytest.approx(0)
        return

    assert p_success == pytest.approx(1)
    assert purified_bds == pytest.approx(
        PURE_BDS_STATES[expected_output_index]
    )


def create_scenario(state1, state2, seed_index, fidelity=1.0) -> tuple[Timeline, Memory, Memory, Memory, Memory, BBPSSWProtocol, BBPSSWProtocol]:
    """create the whole quantum network (timeline, nodes, channels, memory, protocols)
    """
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

    kept1 = Memory('kept1', tl, fidelity=fidelity, frequency=0, efficiency=1, coherence_time=1, wavelength=HALF_MICRON)  # memory kept
    kept2 = Memory('kept2', tl, fidelity=fidelity, frequency=0, efficiency=1, coherence_time=1, wavelength=HALF_MICRON)
    meas1 = Memory('meas1', tl, fidelity=fidelity, frequency=0, efficiency=1, coherence_time=1, wavelength=HALF_MICRON)  # memory measured
    meas2 = Memory('meas2', tl, fidelity=fidelity, frequency=0, efficiency=1, coherence_time=1, wavelength=HALF_MICRON)

    tl.init()

    tl.quantum_manager.set([kept1.qstate_key, kept2.qstate_key], state1)
    tl.quantum_manager.set([meas1.qstate_key, meas2.qstate_key], state2)

    kept1.entangled_memory = {'node_id': 'a2', 'memo_id': 'kept2'}
    kept2.entangled_memory = {'node_id': 'a1', 'memo_id': 'kept1'}
    meas1.entangled_memory = {'node_id': 'a2', 'memo_id': 'meas2'}
    meas2.entangled_memory = {'node_id': 'a1', 'memo_id': 'meas1'}
    kept1.fidelity = kept2.fidelity = meas1.fidelity = meas2.fidelity = fidelity

    ep1 = BBPSSWProtocol.create(a1, "a1.ep1", kept1, meas1)
    ep2 = BBPSSWProtocol.create(a2, "a2.ep2", kept2, meas2)
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
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(PHI_PLUS, PHI_PLUS, i)
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
        assert complex_array_equal(PHI_PLUS, state)
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
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(PHI_PLUS, PHI_MINUS, i)
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
            assert complex_array_equal(PHI_MINUS, state)
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
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(PHI_MINUS, PHI_PLUS, i)
        assert kept1.entangled_memory == {'node_id': 'a2', 'memo_id': 'kept2'}
        assert kept2.entangled_memory == {'node_id': 'a1', 'memo_id': 'kept1'}
        assert ep1.meas_res == ep2.meas_res

        ket1 = tl.quantum_manager.get(kept1.qstate_key)
        ket2 = tl.quantum_manager.get(kept2.qstate_key)
        assert id(ket1) == id(ket2)
        assert kept1.qstate_key in ket1.keys and kept2.qstate_key in ket1.keys
        state = correct_order(ket1.state, ket1.keys)

        assert complex_array_equal(PHI_MINUS, state)
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
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(PHI_MINUS, PHI_MINUS, i)
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
            assert complex_array_equal(PHI_PLUS, state)
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
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(PHI_PLUS, PSI_PLUS, i)
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
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(PHI_PLUS, PSI_MINUS, i)
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
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(PHI_MINUS, PSI_PLUS, i)
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
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(PHI_MINUS, PSI_MINUS, i)
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
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(PSI_PLUS, PHI_PLUS, i)
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
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(PSI_PLUS, PHI_MINUS, i)
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
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(PSI_MINUS, PHI_PLUS, i)
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
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(PSI_MINUS, PHI_MINUS, i)
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
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(PSI_PLUS, PSI_PLUS, i)
        assert kept1.entangled_memory == {'node_id': 'a2', 'memo_id': 'kept2'}
        assert kept2.entangled_memory == {'node_id': 'a1', 'memo_id': 'kept1'}
        assert ep1.meas_res == ep2.meas_res

        ket1 = tl.quantum_manager.get(kept1.qstate_key)
        ket2 = tl.quantum_manager.get(kept2.qstate_key)
        assert id(ket1) == id(ket2)
        assert kept1.qstate_key in ket1.keys and kept2.qstate_key in ket1.keys

        state = correct_order(ket1.state, ket1.keys)
        assert complex_array_equal(PSI_PLUS, state)
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
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(PSI_PLUS, PSI_MINUS, i)
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
            assert complex_array_equal(PSI_MINUS, state)
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
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(PSI_MINUS, PSI_PLUS, i)
        assert kept1.entangled_memory == {'node_id': 'a2', 'memo_id': 'kept2'}
        assert kept2.entangled_memory == {'node_id': 'a1', 'memo_id': 'kept1'}
        assert ep1.meas_res == ep2.meas_res

        ket1 = tl.quantum_manager.get(kept1.qstate_key)
        ket2 = tl.quantum_manager.get(kept2.qstate_key)
        assert id(ket1) == id(ket2)
        assert kept1.qstate_key in ket1.keys and kept2.qstate_key in ket1.keys

        state = correct_order(ket1.state, ket1.keys)
        assert complex_array_equal(PSI_MINUS, state)
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
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(PSI_MINUS, PSI_MINUS, i)
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
            assert complex_array_equal(PSI_PLUS, state)
        else:
            assert complex_array_equal([0, -SQRT_HALF, -SQRT_HALF, 0], state)
    assert abs(counter - 50) < 10


def get_random_state_by_fidelity(fidelity):
    def prob_distribution(f: float) -> list[float]:
        return [f, (1 - f) / 3, (1 - f) / 3, (1 - f) / 3]

    choice = np.random.choice
    index1, index2 = [choice(range(4), 1, p=prob_distribution(fidelity))[0] for _ in range(2)]
    return BELL_STATES[index1], BELL_STATES[index2]


def test_BBPSSW_fidelity():
    for i in range(1000):
        fidelity = np.random.uniform(0.5, 1)
        state1, state2 = get_random_state_by_fidelity(fidelity)
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(state1, state2, i, fidelity)
        a1, a2 = [tl.get_entity_by_name(name) for name in ["a1", "a2"]]
        assert (meas1, RAW) in a1.resource_manager.log
        assert (meas2, RAW) in a2.resource_manager.log
        assert kept1.fidelity == kept2.fidelity

        if ep1.meas_res == ep2.meas_res:
            assert kept1.fidelity == BBPSSWCircuit.improved_fidelity(fidelity)
            assert kept1.entangled_memory["node_id"] == "a2" and \
                   kept2.entangled_memory["node_id"] == "a1"
            assert a1.resource_manager.log[-1] == (kept1, PURIFIED)
            assert a2.resource_manager.log[-1] == (kept2, PURIFIED)
        else:
            assert kept1.fidelity == 0
            assert kept1.entangled_memory["node_id"] is None
            assert kept2.entangled_memory["node_id"] is None
            assert a1.resource_manager.log[-1] == (kept1, RAW)
            assert a2.resource_manager.log[-1] == (kept2, RAW)


def test_BBPSSW_success_rate():
    counter1 = counter2 = 0
    fidelity = 0.8

    for i in range(1000):
        state1, state2 = get_random_state_by_fidelity(fidelity)
        tl, kept1, kept2, meas1, meas2, ep1, ep2 = create_scenario(state1, state2, i, fidelity)
        if ep1.meas_res == ep2.meas_res:
            counter1 += 1
        else:
            counter2 += 1

        tl.run()

    assert abs(counter1 / (counter1 + counter2) - success_probability(fidelity)) < 0.1
