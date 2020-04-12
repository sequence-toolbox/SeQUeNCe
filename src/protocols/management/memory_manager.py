from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...components.memory import *


class MemoryManager():
    def __init__(self, memory_array: "MemoryArray"):
        self.memory_array = memory_array
        self.memory_map = [MemoryInfo() for _ in self.memory_array]

    def update(self, memory: "AtomMemory", state: str):
        index = self.memory_array.memories.index(memory)
        info = self.memory_map[index]
        info.state = state
        info.remote_node = memory.entangled_memory["node_id"]
        info.remote_memo = memory.entangled_memory["memo_id"]
        info.fidelity = memory.fidelity

    def __len__(self):
        return len(self.memory_map)

    def __getitem__(self, item):
        return self.memory_map[item]


class MemoryInfo():
    def __init__(self):
        self.state = "RAW"
        self.remote_node = None
        self.remote_memo = None
        self.fidelity = None
        self.expire = None


