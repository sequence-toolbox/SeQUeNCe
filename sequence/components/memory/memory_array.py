from typing import Any, TYPE_CHECKING

from ...kernel.entity import Entity

if TYPE_CHECKING:
    from ...kernel.timeline import Timeline

from .memory_base import Memory


class MemoryArray(Entity):
    """Aggregator for Memory objects.

    Equivalent to an array of single atom memories.
    The MemoryArray can be accessed as a list to get individual memories.

    Attributes:
        name (str): label for memory array instance.
        timeline (Timeline): timeline for simulation.
        memories (list[Memory]): list of all memories.
    """

    def __init__(self, name: str, timeline: "Timeline", num_memories=10,
                 fidelity=0.85, frequency=80e6, efficiency=1, coherence_time=-1, wavelength=500,
                 decoherence_errors: list[float] = None, cutoff_ratio=1):
        """Constructor for the Memory Array class.

        Args:
            name (str): name of the memory array instance.
            timeline (Timeline): simulation timeline.
            num_memories (int): number of memories in the array (default 10).
            fidelity (float): fidelity of memories (default 0.85).
            frequency (float): maximum frequency of excitation for memories (default 80e6).
            efficiency (float): efficiency of memories (default 1).
            coherence_time (float): average time (in s) that memory state is valid (default -1 -> inf).
            wavelength (int): wavelength (in nm) of photons emitted by memories (default 500).
            decoherence_errors (list[int]): pauli decoherence errors. Passed to memory object.
            cutoff_ratio (float): the ratio between cutoff time and memory coherence time (default 1, should be between 0 and 1).
        """

        Entity.__init__(self, name, timeline)
        self.memories = []
        self.memory_name_to_index = {}

        for i in range(num_memories):
            memory_name = self.name + f"[{i}]"
            self.memory_name_to_index[memory_name] = i
            memory = Memory(memory_name, timeline, fidelity, frequency, efficiency, coherence_time, wavelength,
                            decoherence_errors, cutoff_ratio)
            memory.attach(self)
            self.memories.append(memory)
            memory.set_memory_array(self)

    def __getitem__(self, key: int) -> "Memory":
        return self.memories[key]

    def __setitem__(self, key: int, value: "Memory"):
        self.memories[key] = value

    def __len__(self) -> int:
        return len(self.memories)

    def init(self):
        """Implementation of Entity interface (see base class).

        Set the owner of memory as the owner of memory array.
        """

        for memory in self.memories:
            memory.owner = self.owner

    def memory_expire(self, memory: "Memory"):
        """Method to receive expiration events from memories.

        Args:
            memory (Memory): expired memory.
        """

        self.owner.memory_expire(memory)

    def update_memory_params(self, arg_name: str, value: Any) -> None:
        for memory in self.memories:
            memory.__setattr__(arg_name, value)

    def add_receiver(self, receiver: "Entity") -> None:
        """Add receiver to each memory in the memory array to receive photons.

        Args:
            receiver (Entity): receiver of the memory
        """
        for memory in self.memories:
            memory.add_receiver(receiver)

    def get_memory_by_name(self, name: str) -> "Memory":
        """Given the memory's name, get the memory object.

        Args:
            name (str): name of memory
        Return:
            (Memory): the memory object
        """
        index = self.memory_name_to_index.get(name, -1)
        assert index >= 0, "Oops! name={} not exist!"
        return self.memories[index]
