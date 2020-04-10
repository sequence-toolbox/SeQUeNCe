from ..protocol import Protocol
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...components.memory import AtomMemory


class MemoryManager(Protocol):
    def __init__(self, own, name, resource_manager: Protocol):
        super().__init__(own, name)
        self.memory_map = {"EMPTY": []
                           "OCCUPIED": []
                           "ENTANGLED": []}
        self.memory_array = self.own.memory_array
        self.resource_manager = resource_manager

    def init(self):
        memories = [m for m in self.memory_array]
        self.memory_map["EMPTY"] = memories

    def received_message(self):
        pass

    def update(self, memory: "AtomMemory", state: str, protocol=None):
        for key in self.memory_map:
            if memory in self.memory_map[key]:
                self.memory_map[key].remove(memory)
                break
        self.memory_map[state].append(memory)

        # remove old protocol
        if protocol:
            self.own.protocols.remove(protocol)

        self.resource_manager.update_rules()

    def num_empty(self):
        return len(self.memory_map["EMPTY"])

    def entangled_memories(self, node: str, remote_index: int):
        return [m for m in self.memory_map["ENTANGLED"] if
                m.entangled_memory["node_id"] == node and m.entangled_memory["memo_id"] == remote_index]


