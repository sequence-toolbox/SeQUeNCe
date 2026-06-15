from math import sqrt
from numpy.random import default_rng
import pytest
from stim import Tableau, PauliString

from sequence.kernel.quantum_state import KetState, FreeQuantumState, StabilizerState
from sequence.utils.encoding import polarization


rng = default_rng()


def test_build_ket():
    keys = [0]

    amps = [complex(1), complex(0)]
    _ = KetState(amps, keys)

    amps = [complex(sqrt(1/2)), complex(sqrt(1/2))]
    _ = KetState(amps, keys)

    amps = [complex(0), complex(1.j)]
    _ = KetState(amps, keys)

    # test with different size
    amps = [complex(1), complex(0), complex(0), complex(0)]
    _ = KetState(amps, [0, 1])

    # test non-unit amplitudes
    amps = [complex(3/2), complex(0)]
    with pytest.raises(AssertionError, match="Illegal value with abs > 1 in ket vector"):
        _ = KetState(amps, keys)

    amps = [complex(0), complex(0)]
    with pytest.raises(AssertionError, match="Squared amplitudes do not sum to 1"):
        _ = KetState(amps, keys)

    # test with invalid no. of amplitudes
    amps = [complex(1), complex(0), complex(0)]
    with pytest.raises(AssertionError):
        _ = KetState(amps, keys)

    amps = [complex(1), complex(0), complex(0), complex(0)]
    with pytest.raises(AssertionError):
        _ = KetState(amps, keys)


def test_build_stabilizer_zero_state():
    key = 3
    seed = 0
    qs = StabilizerState.zero_state(key=key, seed=seed)

    assert qs.keys == [key]
    assert qs.get_seed() == seed
    assert qs.state.num_qubits == 1
    assert qs.state.peek_z(0) == 1
    assert isinstance(qs.current_forward_tableau(), Tableau)
    assert isinstance(qs.current_inverse_tableau(), Tableau)
    zero_state_stabilizer = PauliString("+Z")
    assert qs.canonical_stabilizers()[0] == zero_state_stabilizer


def test_stabilizer_copy():
    key = 2
    seed = 1
    qs = StabilizerState.zero_state(key=key, seed=seed)
    copied = qs.copy()
    copied.keys.append(1)
    copied.state.x(0)

    assert qs.keys == [key]
    assert copied.keys == [key, 1]
    assert qs.state.peek_z(0) == 1
    assert copied.state.peek_z(0) == -1


def test_measure():
    qs = FreeQuantumState()
    states = [(complex(1), complex(0)),
              (complex(0), complex(1)),
              (complex(sqrt(1 / 2)), complex(sqrt(1 / 2))),
              (complex(-sqrt(1 / 2)), complex(sqrt(1 / 2)))]
    basis1, basis2 = polarization['bases'][0], polarization['bases'][1]
    basis = [basis1,
             basis1,
             basis2,
             basis2]
    expect = [0, 100, 0, 100]

    for s, b, e in zip(states, basis, expect):
        counter = 0
        for _ in range(100):
            qs.set_state_single(s)
            res = qs.measure(b, rng)
            if res:
                counter += 1
        assert counter == e

    basis = [basis2,
             basis2,
             basis1,
             basis1]
    expect = [500, 500, 500, 500]

    for s, b, e in zip(states, basis, expect):
        counter = 0
        for _ in range(1000):
            qs.set_state_single(s)
            res = qs.measure(b, rng)
            if res:
                counter += 1
        assert abs(0.5 - counter / 1000) < 0.1


def test_measure_entangled():
    qs1 = FreeQuantumState()
    states = [(complex(1), complex(0)),
              (complex(0), complex(1)),
              (complex(sqrt(1 / 2)), complex(sqrt(1 / 2))),
              (complex(-sqrt(1 / 2)), complex(sqrt(1 / 2)))]
    basis1, basis2 = polarization['bases'][0], polarization['bases'][1]
    basis = [basis1,
             basis1,
             basis2,
             basis2]
    expect = [0, 100, 0, 100]

    for s, b, e in zip(states, basis, expect):
        counter = 0
        for _ in range(100):
            qs1.set_state_single(s)
            qs2 = FreeQuantumState()
            qs1.combine_state(qs2)
            res = qs1.measure(b, rng)
            if res:
                counter += 1
        assert counter == e

    basis = [basis2,
             basis2,
             basis1,
             basis1]
    expect = [500, 500, 500, 500]

    for s, b, e in zip(states, basis, expect):
        counter = 0
        for _ in range(1000):
            qs1.set_state_single(s)
            qs2 = FreeQuantumState()
            qs1.combine_state(qs2)
            res = qs1.measure(b, rng)
            if res:
                counter += 1
        assert abs(0.5 - counter / 1000) < 0.1
