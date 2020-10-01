import numpy as np
import math

from sequence.kernel.quantum_manager import *


class DumbCircuit():
    def __init__(self, size, matrix):
        self.size = size
        self.matrix = matrix
        self.measured_qubits = []

    def get_unitary_matrix(self):
        return self.matrix


def test_qmanager_get():
    qm = QuantumManager()
    qm.states[49] = "test_string"
    assert qm.get(49) == "test_string"


def test_qmanager_new():
    NUM_TESTS = 1000

    qm = QuantumManager()
    
    keys = []
    for _ in range(NUM_TESTS):
        keys.append(qm.new())
    assert len(set(keys)) == NUM_TESTS

    test_state = [complex(0), complex(1)]
    key = qm.new(test_state)
    assert (qm.get(key).state == np.array(test_state)).all


def test_qmanager_set():
    qm = QuantumManager()
    key = qm.new()
    new_state = [complex(0), complex(1)]
    qm.set([key], new_state)
    assert (qm.get(key) == np.array(new_state)).all

    key2 = qm.new()
    keys = [key, key2]
    new_state = [complex(1), complex(0), complex(0), complex(0)]
    qm.set(keys, new_state)
    assert (qm.get(key).state == qm.get(key2).state).all
    assert (qm.get(key).state == np.array(new_state)).all


def test_qmanager_remove():
    qm = QuantumManager()
    qm.states[0] = "test_string"
    qm.remove(0)
    assert len(qm.states.keys()) == 0


def test_qmanager_circuit():
    qm = QuantumManager()

    # single state
    key = qm.new()
    circuit = DumbCircuit(1, np.array([[0, 1], [1, 0]]))
    qm.run_circuit(circuit, [key])
    assert (qm.get(key).state == np.array([0, 1])).all

    # two states
    key1 = qm.new()
    key2 = qm.new()
    circuit = DumbCircuit(2, np.identity(4))
    qm.run_circuit(circuit, [key1, key2])
    assert (qm.get(key1).state == qm.get(key2).state).all
    assert (qm.get(key1).state == np.array([1, 0, 0, 0])).all

    # two states, wrong order
    qm.run_circuit(circuit, [key2, key1])
    assert (qm.get(key1).state == qm.get(key2).state).all
    assert (qm.get(key1).state == np.array([1, 0, 0, 0])).all
    assert qm.get(key1).keys == [key2, key1]


def test_qmanager__measure():
    NUM_TESTS = 1000
    
    qm = QuantumManager()

    # single state
    meas_0 = []
    meas_1 = []
    for _ in range(NUM_TESTS):
        key = qm.new([math.sqrt(1/2), math.sqrt(1/2)])
        res = qm._measure(key)
        if res:
            meas_1.append(key)
        else:
            meas_0.append(key)
    
    assert abs((len(meas_0) / NUM_TESTS) - 0.5) < 0.1
    for key in meas_0:
        assert (qm.get(key).state == np.array([1, 0])).all
    for key in meas_1:
        assert (qm.get(key).state == np.array([0, 1])).all

