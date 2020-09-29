import numpy as np

from sequence.kernel.quantum_state import *


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

