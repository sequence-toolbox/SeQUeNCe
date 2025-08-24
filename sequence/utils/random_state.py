
import math
import random

def random_state() -> list:
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
