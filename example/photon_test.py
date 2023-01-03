import time

from numpy import sin, cos
from numpy.random import random_sample, default_rng
from sequence.components.circuit import Circuit
from sequence.kernel.quantum_manager import QuantumManagerKet
from sequence.utils.quantum_state import QuantumState


SAMPLE_SIZE = 10000

basis = ((complex(1), complex(0)), (complex(0), complex(1)))
rng = default_rng()
qm = QuantumManagerKet()
meas_circ = Circuit(1)
meas_circ.measure(0)

runtimes = []


def timeit_wrapper(func):
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        return_val = func(*args, **kwargs)
        end = time.perf_counter()
        runtimes.append(end - start)
        return return_val
    return wrapper


class ParticleOld:
    def __init__(self, state):
        self.qs = QuantumState()
        self.qs.state = state

    def measure(self):
        return self.qs.measure(basis, rng)


class ParticleNew:
    def __init__(self, state):
        self.qs_key = qm.new(state)

    def measure(self):
        return qm.run_circuit(meas_circ, [self.qs_key], rng.random())


if __name__ == "__main__":
    random_angles = random_sample(SAMPLE_SIZE)
    states = []
    for theta in random_angles:
        states.append((cos(theta), sin(theta)))

    @timeit_wrapper
    def create_and_measure(states, particle_type):
        for s in states:
            p = particle_type(s)
            p.measure()

    create_and_measure(states, ParticleOld)
    create_and_measure(states, ParticleNew)
    print("Old Runtime: {}".format(runtimes[0]))
    print("New Runtime: {}".format(runtimes[1]))
    print("Old Per Photon: {}".format(runtimes[0]/SAMPLE_SIZE))
    print("New Per Photon: {}".format(runtimes[1]/SAMPLE_SIZE))
