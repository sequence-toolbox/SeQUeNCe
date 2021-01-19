"""This module defines the quantum manager class, to track quantum states.

The states may currently be defined in two possible ways:
    - KetState (with the QuantumManagerKet class)
    - DensityMatrix (with the QuantumManagerDensity class)

The manager defines an API for interacting with quantum states.
"""
from typing import List, Dict

from .quantum_manager import QuantumManagerKet, QuantumManagerDensity, KetState, DensityState


def p_new_ket(states, least_available, locks, manager, amplitudes=[complex(1), complex(0)]) -> int:
    key = least_available.value

    with least_available.get_lock():
        least_available.value += 1

    states[key] = KetState(amplitudes, [key])
    locks[key] = manager.Lock()
    return key

def p_new_density(states, least_available, locks, manager,
                  state=[[complex(1), complex(0)], [complex(0), complex(0)]]) -> int:        
    key = least_available.value

    with least_available.get_lock():
        least_available.value += 1

    states[key] = DensityState(state, [key])
    locks[key] = manager.Lock()
    return key

def p_get(states, key: int):
    return states[key]

def p_run_circuit_ket(states, locks, circuit: "Circuit", keys: List[int]) -> Dict[int, int]:
    for key in keys:
        locks[key].acquire()
    try:
        ret_dict = QuantumManagerKet._run_circuit_static(states, circuit, keys)
    finally:
        for key in keys:
            locks[key].release()

    return ret_dict

def p_set_ket(states, keys: List[int], amplitudes: List[complex]) -> None:
    new_state = KetState(amplitudes, keys)
    for key in keys:
        states[key] = new_state

def p_set_density(states, keys: List[int], state: List[List[complex]]) -> None:
    new_state = DensityState(state, keys)
    for key in keys:
        states[key] = new_state

def p_remove(states, locks, key: int) -> None:
    del states[key]
    del locks[key]

