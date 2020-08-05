"""Definition of Memory Manager.

This module provides a definition for the memory manager, which tracks the state of memories on a node.
There are three states of quantum memory represented by the string: "RAW", "OCCUPIED", "ENTANGLED". 
    "RAW" denotes a free memory that is not entangling with other memories.
    "OCCUPIED" denotes a memory that is allocated to protocols or applications.
    "ENTANGLED" denotes a free memory that is entangling with other memories. 
This is done through instances of the MemoryInfo class, which track a single memory.
"""

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .resource_manager import ResourceManager
    from ..components.memory import Memory, MemoryArray


class MemoryManager():
    def __init__(self, memory_array: "MemoryArray"):
        self.memory_array = memory_array
        self.memory_array.upper_protocols.append(self)
        self.memory_map = [MemoryInfo(memory, index) for index, memory in enumerate(self.memory_array)]
        self.resource_manager = None

    def set_resource_manager(self, resource_manager: "ResourceManager") -> None:
        self.resource_manager = resource_manager

    def update(self, memory: "Memory", state: str) -> None:
        info = self.get_info_by_memory(memory)
        if state == "RAW":
            info.to_raw()
        elif state == "OCCUPIED":
            info.to_occupied()
        elif state == "ENTANGLED":
            info.to_entangled()
        else:
            raise Exception("Unknown state '%s'" % state)

    def __len__(self):
        return len(self.memory_map)

    def __getitem__(self, item: int) -> "MemoryInfo":
        return self.memory_map[item]

    def get_info_by_memory(self, memory: "Memory") -> "MemoryInfo":
        index = self.memory_array.memories.index(memory)
        return self.memory_map[index]

    def pop(self, **kwargs):
        if kwargs["info_type"] != "expired_memory":
            return

        index = kwargs["index"]


class MemoryInfo():
    """
    Allowed states:
    RAW       : Memory is unprocessed
    OCCUPIED  : Memory is occupied by some protocol
    ENTANGLED : Memory has been successfully entangled
    """

    def __init__(self, memory: "Memory", index: int, state="RAW"):
        self.memory = memory
        self.index = index
        self.state = state
        self.remote_node = None
        self.remote_memo = None
        self.fidelity = 0
        self.expire_event = None
        self.entangle_time = -1

    def to_raw(self) -> None:
        self.state = "RAW"
        self.memory.reset()
        self.remote_node = None
        self.remote_memo = None
        self.fidelity = 0
        self.entangle_time = -1

    def to_occupied(self) -> None:
        assert self.state != "OCCUPIED"
        self.state = "OCCUPIED"

    def to_entangled(self) -> None:
        self.state = "ENTANGLED"
        self.remote_node = self.memory.entangled_memory["node_id"]
        self.remote_memo = self.memory.entangled_memory["memo_id"]
        self.fidelity = self.memory.fidelity
        self.entangle_time = self.memory.timeline.now()
