"""Some useful utility functions for the quantum network simulation.
"""
import math
import random
from ..constants import EPSILON


class QuantumUtility:
    """Some useful utility functions for the quantum network simulation.
    """

    @classmethod
    def random_state(cls) -> list:
        """Generate a random pure state vector for a single qubit.
        
        The function returns a list of two elements representing the amplitudes of the quantum state
        in the computational basis [|0>, |1>]. The first element is a real number (float) corresponding
        to the amplitude of |0>, and the second element is a complex number corresponding to the amplitude of |1>.

        Returns:
            list: [float, complex] -- A list containing the amplitudes of the random qubit state.
        """
        u = random.random()
        θ = 2 * math.acos(math.sqrt(u))
        φ = 2 * math.pi * random.random()
        return [math.cos(θ / 2), complex(math.sin(θ / 2) * math.cos(φ), math.sin(θ / 2) * math.sin(φ))]


    @classmethod
    def verify_same_state_vector(cls, state1: list, state2: list) -> bool:
        """Verify if two quantum state vectors are the same.

           Note that two state vectors are the same regardless of the global phase

        Args:
            state1 (list): The first quantum state vector.
            state2 (list): The second quantum state vector.

        Returns:
            bool: True if the state vectors are the same, False otherwise.
        """
        if len(state1) != len(state2):    # Length check
            return False

        global_phase = None               # Find the first non-zero element in state1/state2 to estimate the global phase
        for a, b in zip(state1, state2):
            if abs(a) > 1e-12 and abs(b) > 1e-12:
                global_phase = b / a
                break

        if global_phase is None:
            return False

        global_phase /= abs(global_phase) # Normalize phase to have unit magnitude (global phase must be on the unit circle)

        for a, b in zip(state1, state2):  # Check if all elements match up to this global phase
            if abs(b - global_phase * a) > EPSILON:
                return False

        return True
