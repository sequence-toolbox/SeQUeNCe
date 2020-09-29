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
    assert (qm.get(key[0]).state == np.array(test_state)).all

    test_state_2 = [complex(1), complex(0), complex(0), complex(0)]
    keys = qm.new(test_state_2)
    assert len(keys) == 2
    assert qm.get(keys[0]) is qm.get(keys[1])
    assert (qm.get(keys[0]).state == np.array(test_state_2)).all
    assert (qm.get(keys[1]).state == np.array(test_state_2)).all


def test_qmanager_set():
    qm = QuantumManager()
    key = qm.new()
    new_state = [complex(0), complex(1)]
    qm.set(key[0], new_state)
    assert (qm.get(key[0]) == np.array(new_state)).all


def test_qmanager_remove():
    qm = QuantumManager()
    qm.states[0] = "test_string"
    qm.remove(0)
    assert len(qm.states.keys()) == 0

