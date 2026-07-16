"""Abstract base class for SeQUeNCe applications.

This module defines the `App` interface that all node-attached applications
must implement.  The three abstract callback methods, `get_memory`, `get_reservation_result`,
and `get_other_reservation` are correspond to the calls that `QuantumRouter` already
makes on whatever application is attached via `set_app`.

Subclasses that track throughput (e.g. `RequestApp`) should override it with a
meaningful implementation.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..network_management.reservation import Reservation
    from ..resource_management.memory_manager import MemoryInfo
    from ..topology.node import QuantumRouter


class App(ABC):
    """Abstract base application attached to a quantum network node.

    Every concrete application must subclass `App` and implement the three
    abstract callback methods that `QuantumRouter` relies on.

    The constructor automatically registers the application on the node via
    `node.set_app(self)`, so subclasses should always call
    `super().__init__(node)`!

    Attributes:
        node (QuantumRouter): The node this application is attached to.
        name (str): Human-readable name for the application instance.
    """

    def __init__(self, node: "QuantumRouter"):
        self.node: "QuantumRouter" = node
        self.node.set_app(self)
        self.name: str = f"{self.node.name}.{self.__class__.__name__}"

    @abstractmethod
    def get_memory(self, info: "MemoryInfo") -> None:
        """Called when an entangled memory becomes available.

        Args:
            info (MemoryInfo): Information about the available memory.
        """

    @abstractmethod
    def get_reservation_result(self, reservation: "Reservation", result: bool) -> None:
        """Called when a reservation result is received from the network manager.

        Args:
            reservation (Reservation): The reservation that completed.
            result (bool): Whether the reservation was approved.
        """

    @abstractmethod
    def get_other_reservation(self, reservation: "Reservation") -> None:
        """Called when a reservation initiated by another node is approved and
        uses this node as the responder.

        Args:
            reservation (Reservation): The approved reservation.
        """

    def set_name(self, name: str) -> None:
        """Override the default application name.

        Args:
            name (str): New name for the application.
        """
        self.name = name

    def __str__(self) -> str:
        return self.name
