"""Models for simulation of quantum memories.

This module defines the Memory class to simulate single atom memories as well as the MemoryArray class to aggregate memories.
Memories will attempt to send photons through the `send_qubit` interface of nodes.
Photons should be routed to a BSM device for entanglement generation, or through optical hardware for purification and swapping.
"""

from .memory import Memory
from .memory_array import MemoryArray
from .absorptive_memory import AbsorptiveMemory
from .random_coherence_memory import MemoryWithRandomCoherenceTime
