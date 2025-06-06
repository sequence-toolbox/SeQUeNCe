
import math
import random

def random_state():
    u = random.random()
    θ = 2 * math.acos(math.sqrt(u))
    φ = 2 * math.pi * random.random()
    return [
        math.cos(θ / 2),
        complex(math.sin(θ / 2) * math.cos(φ), math.sin(θ / 2) * math.sin(φ))
    ]