import numpy as np
import pytest

from sequence.kernel.timeline import Timeline
from sequence.components.photon import Photon

rng = np.random.default_rng()


def test_init():
    tl = Timeline()
    photon = Photon("", tl)
    
    assert photon.quantum_state.state == (complex(1), complex(0))


def test_combine_state():
    tl = Timeline()
    photon1 = Photon("p1", tl)
    photon2 = Photon("p2", tl)
    photon1.combine_state(photon2)

    state1 = photon1.quantum_state
    state2 = photon2.quantum_state

    test_state = (complex(1), complex(0), complex(0), complex(0))
    for i, coeff in enumerate(state1.state):
        assert coeff == state2.state[i]
        assert coeff == test_state[i]
    assert state1.entangled_states == state2.entangled_states
    assert state1.entangled_states == [state1, state2]


def test_set_state():
    tl = Timeline()
    photon = Photon("", tl)

    test_state = (complex(0), complex(1))
    photon.set_state(test_state)
    for i, coeff in enumerate(photon.quantum_state.state):
        assert coeff == test_state[i]

    # non-unit amplitudes
    test_state = (complex(2), complex(0))
    with pytest.raises(AssertionError, match="Illegal value with abs > 1 in quantum state"):
        photon.set_state(test_state)

    test_state = (complex(0), complex(0))
    with pytest.raises(AssertionError, match="Squared amplitudes do not sum to 1"):
        photon.set_state(test_state)

    # incorrect size
    test_state = (complex(1), complex(0), complex(0), complex(0))
    with pytest.raises(AssertionError):
        photon.set_state(test_state)


def test_measure():
    tl = Timeline()
    photon1 = Photon("p1", tl, quantum_state=(complex(1), complex(0)))
    photon2 = Photon("p2", tl, quantum_state=(complex(0), complex(1)))
    basis = ((complex(1), complex(0)), (complex(0), complex(1)))

    assert Photon.measure(basis, photon1, rng) == 0
    assert Photon.measure(basis, photon2, rng) == 1


def test_measure_multiple():
    tl = Timeline()
    photon1 = Photon("p1", tl)
    photon2 = Photon("p2", tl)
    photon1.combine_state(photon2)

    basis = ((complex(1), complex(0), complex(0), complex(0)),
             (complex(0), complex(1), complex(0), complex(0)),
             (complex(0), complex(0), complex(1), complex(0)),
             (complex(0), complex(0), complex(0), complex(1)))

    assert Photon.measure_multiple(basis, [photon1, photon2], rng) == 0


def test_add_loss():
    tl = Timeline()
    photon = Photon("", tl, encoding_type={"name": "single_atom"})
    assert photon.loss == 0

    photon.add_loss(0.5)
    assert photon.loss == 0.5

    photon.add_loss(0.5)
    assert photon.loss == 0.75
