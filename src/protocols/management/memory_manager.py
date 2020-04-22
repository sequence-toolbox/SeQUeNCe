from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...components.memory import *
    from .manager import ResourceManager


class MemoryManager():
    def __init__(self, memory_array: "MemoryArray"):
        self.memory_array = memory_array
        self.memory_map = [MemoryInfo(memory) for memory in self.memory_array]
        self.resource_manager = None

    def set_resource_manager(self, resource_manager: "ResourceManager") -> None:
        self.resource_manager = resource_manager

    def update(self, memory: "AtomMemory", state: str) -> None:
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

    def get_info_by_memory(self, memory: "AtomMemory") -> "MemoryInfo":
        index = self.memory_array.memories.index(memory)
        return self.memory_map[index]


class MemoryInfo():
    """
    Allowed states:
    RAW       : Memory is unprocessed
    OCCUPIED  : Memory is occupied by some protocol
    ENTANGLED : Memory has been successfully entangled
    """

    def __init__(self, memory: "AtomMemory", state="RAW"):
        self.memory = memory
        self.state = state
        self.remote_node = None
        self.remote_memo = None
        self.fidelity = 0
        self.expire_event = None

    def to_raw(self) -> None:
        self.state = "RAW"
        self.memory.reset()
        self.remote_node = None
        self.remote_memo = None
        self.fidelity = 0

    def to_occupied(self) -> None:
        assert self.state != "OCCUPIED"
        self.state = "OCCUPIED"

    def to_entangled(self) -> None:
        self.state = "ENTANGLED"
        self.remote_node = self.memory.entangled_memory["node_id"]
        self.remote_memo = self.memory.entangled_memory["memo_id"]
        self.fidelity = self.memory.fidelity
