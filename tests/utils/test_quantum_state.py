from sequence.utils.quantum_state import QuantumState
from sequence.utils.encoding import polarization
from math import sqrt
from numpy.random import default_rng

rng = default_rng()


def test_measure():
    qs = QuantumState()
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
    qs1 = QuantumState()
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
            qs2 = QuantumState()
            qs1.entangle(qs2)
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
            qs2 = QuantumState()
            qs1.entangle(qs2)
            res = qs1.measure(b, rng)
            if res:
                counter += 1
        assert abs(0.5 - counter / 1000) < 0.1

