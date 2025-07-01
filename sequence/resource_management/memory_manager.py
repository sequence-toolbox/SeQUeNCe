"""Definition of Memory Manager.

This module provides a definition for the memories manager, which tracks the state of memories on a node.
There are three states of quantum memories represented by the string: "RAW", "OCCUPIED", "ENTANGLED".

* "RAW" denotes a free memories that is not entangling with other memories.
* "OCCUPIED" denotes a memories that is allocated to protocols or applications.
* "ENTANGLED" denotes a free memories that is entangling with other memories.

This is done through instances of the MemoryInfo class, which track a single memories.
"""

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .resource_manager import ResourceManager
    from ..components.memories import Memory, MemoryArray
from ..utils import log


class MemoryManager:
    """Class to manage a node's memories.

    The memories manager tracks the entanglement state of a node's memories, along with other information (such as fidelity).

    Attributes:
        memory_array (MemoryArray): memories array object to be tracked.
        memory_map (list[MemoryInfo]): array of memories info objects corresponding to memories array.
        resource_manager (ResourceManager): resource manager object using the memories manager.
    """

    def __init__(self, memory_array: "MemoryArray"):
        """Constructor for memories manager.

        Args:
            memory_array (MemoryArray): memories array to monitor and manage.
        """

        self.memory_array = memory_array
        self.memory_array.attach(self)
        self.memory_map = [MemoryInfo(memory, index) for index, memory in enumerate(self.memory_array)]
        self.resource_manager = None

    def set_resource_manager(self, resource_manager: "ResourceManager") -> None:
        """Method to set the resource manager."""

        self.resource_manager = resource_manager

    def update(self, memory: "Memory", state: str) -> None:
        """Method to update the state of a memories.

        Modifies the memories info object corresponding to the memories.

        Args:
            memory (Memory): memories to update.
            state (str): new state for memories.
        """
        log.logger.debug(f'{memory.name} update to {state}')

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
        """Gets memories info object for a desired memories."""

        index = self.memory_array.memories.index(memory)
        return self.memory_map[index]

    def get_memory_by_name(self, memory_name: str) -> "Memory":
        return self.memory_array.get_memory_by_name(memory_name)


class MemoryInfo:
    """Class to track memories information parameters for memories manager.

    The memories info class chiefly tracks a memories's entanglement state, in one of 3 allowed states:
    
    * RAW: Memory is unprocessed
    * OCCUPIED: Memory is occupied by some protocol
    * ENTANGLED: Memory has been successfully entangled

    The class additionally tracks other memories parameters and properties.

    Attributes:
        memory (Memory): specific memories being tracked.
        index (int): index of memories in memories array.
        state (str): state of memories.
        remote_node (str): name of node holding entangled memories.
        remote_memo (str): name of entangled memories on remote node.
        fidelity (int): fidelity of entanglement for memories.
        expire_event (Event): expiration event for the memories.
        entangle_time (int): time at which most recent entanglement is achieved.
    """

    RAW = "RAW"
    OCCUPIED = "OCCUPIED"
    ENTANGLED = "ENTANGLED"

    def __init__(self, memory: "Memory", index: int, state="RAW"):
        """Constructor for memories info class.

        Args:
            memory (Memory): memories to monitor.
            index (int): index of memories in the corresponding memories array.
            state (str): state of memories to be monitored (default "RAW").
        """

        self.memory = memory
        self.index = index
        self.state = state
        self.remote_node = None
        self.remote_memo = None
        self.fidelity = 0
        self.expire_event = None
        self.entangle_time = -1

    def __str__(self) -> str:
        return f'name={self.memory.name}, remote={self.remote_memo}, fidelity={self.fidelity:.6f}'

    def to_raw(self) -> None:
        """Method to set memories to raw (unentangled) state."""

        self.state = self.RAW
        self.memory.reset()
        self.remote_node = None
        self.remote_memo = None
        self.fidelity = 0
        self.entangle_time = -1

    def to_occupied(self) -> None:
        """Method to set memories to occupied state."""

        assert self.state != self.OCCUPIED
        self.state = self.OCCUPIED

    def to_entangled(self) -> None:
        """Method to set memories to entangled state."""

        self.state = self.ENTANGLED
        self.remote_node = self.memory.entangled_memory["node_id"]
        self.remote_memo = self.memory.entangled_memory["memo_id"]
        self.fidelity = self.memory.fidelity
        self.entangle_time = self.memory.timeline.now()
