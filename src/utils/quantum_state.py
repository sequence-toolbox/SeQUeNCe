from math import sqrt
from numpy import pi, cos, sin, array, outer, kron, identity, arange
from numpy.random import random, random_sample, choice


# used for photon.measure_multiple
def swap_bits(num, pos1, pos2):
    bit1 = (num >> pos1) & 1
    bit2 = (num >> pos2) & 1
    x = bit1 ^ bit2
    x = (x << pos1) | (x << pos2)
    return num ^ x


class QuantumState():
    def __init__(self):
        self.state = [complex(1), complex(0)]
        self.entangled_states = [self]

    def entangle(self, another_state):
        entangled_states = self.entangled_states + another_state.entangled_states
        new_state = kron(self.state, another_state.state)

        for quantum_state in entangled_states:
            quantum_state.entangled_states = entangled_states
            quantum_state.state = new_state

    def random_noise(self):
        # TODO: rewrite for entangled states
        angle = random() * 2 * pi
        self.state = [complex(cos(angle)), complex(sin(angle))]

    # only for use with entangled state
    def set_state(self, state):
        for qs in self.entangled_states:
            qs.state = state

    # for use with single, unentangled state
    def set_state_single(self, state):
        for qs in self.entangled_states:
            if qs is not None and qs != self:
                index = qs.entangled_states.index(self)
                qs.entangled_states[index] = None
        self.entangled_states = [self]
        self.state = state

    def measure(self, basis):
        state = array(self.state)
        u = array(basis[0], dtype=complex)
        v = array(basis[1], dtype=complex)
        # measurement operator
        M0 = outer(u.conj(), u)
        M1 = outer(v.conj(), v)

        # generate projectors
        if len(self.entangled_states) > 1:
            projector0 = [1]
            projector1 = [1]
            for s in self.entangled_states:
                if s == self:
                    projector0 = kron(projector0, M0)
                    projector1 = kron(projector1, M1)
                else:
                    projector0 = kron(projector0, identity(2))
                    projector1 = kron(projector1, identity(2))
        else:
            projector0 = M0
            projector1 = M1

        # probability of measuring basis[0]
        prob_0 = (state.conj().transpose() @ projector0.conj().transpose() @ projector0 @ state).real

        result = 0
        if random_sample() > prob_0:
            result = 1

        if result:
            new_state = (projector1 @ state) / sqrt(1 - prob_0)
        else:
            new_state = (projector0 @ state) / sqrt(prob_0)

        for s in self.entangled_states:
            if s is not None:
                s.state = new_state

        return result

    @staticmethod
    def measure_multiple(basis, states):
        # ensure states are entangled
        # (must be entangled prior to calling measure_multiple)
        entangled_list = states[0].entangled_states
        for state in states[1:]:
            assert state in states[0].entangled_states
        # ensure basis and vectors in basis are the right size
        basis_dimension = 2 ** len(states)
        assert len(basis) == basis_dimension
        for vector in basis:
            assert len(vector) == len(basis)

        state = states[0].state

        # move states to beginning of entangled list and quantum state
        pos_state_0 = entangled_list.index(states[0])
        pos_state_1 = entangled_list.index(states[1])
        entangled_list[0], entangled_list[pos_state_0] = entangled_list[pos_state_0], entangled_list[0]
        entangled_list[1], entangled_list[pos_state_1] = entangled_list[pos_state_1], entangled_list[1]
        switched_state = array([complex(0)] * len(state))
        for i, coefficient in enumerate(state):
            switched_i = swap_bits(i, pos_state_0, pos_state_1)
            switched_state[switched_i] = coefficient

        state = switched_state

        # math for probability calculations
        length_diff = len(entangled_list) - len(states)

        # construct measurement operators, projectors, and probabilities of measurement
        projectors = [None] * basis_dimension
        probabilities = [0] * basis_dimension
        for i, vector in enumerate(basis):
            vector = array(vector, dtype=complex)
            M = outer(vector.conj(), vector)  # measurement operator
            projectors[i] = kron(M, identity(2 ** length_diff))  # projector
            probabilities[i] = (state.conj().transpose() @ projectors[i].conj().transpose() @ projectors[i] @ state).real
            if probabilities[i] < 0:
                probabilities[i] = 0

        possible_results = arange(0, basis_dimension, 1)
        # result gives index of the basis vector that will be projected to
        res = choice(possible_results, p=probabilities)
        # project to new state, then reassign quantum state and entangled photons
        new_state = (projectors[res] @ state) / sqrt(probabilities[res])
        for state in entangled_list:
            state.quantum_state = new_state
            state.entangled_photons = entangled_list

        return res
