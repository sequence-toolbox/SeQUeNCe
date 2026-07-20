"""Storage and record types for the metrics module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .event_types import EventType


@dataclass(slots=True)
class Record:
    """A single stored metrics event.

    Attributes:
        event_type: The type of event that was recorded.
        owner_name: Name of the node or component that owns the event.
        sim_time: Simulation timestamp when the event was recorded.
        data: Typed payload dataclass instance, or ``None`` if the event
            type carries no additional data.
    """

    event_type: EventType
    owner_name: str
    sim_time: int
    data: Any


class InMemoryStorage:
    """Store metric records in memory for the lifetime of the simulation."""

    def __init__(self) -> None:
        """Initialize an empty in-memory record store."""
        self._records: list[Record] = []

    def append(self, record: Record) -> None:
        """Append a metric record to storage.

        Args:
            record: Event record with event type, owner, simulation time, and payload.
        """
        self._records.append(record)

    def get_all(self) -> list[Record]:
        """Return all stored metric records.

        Returns:
            Copy of every record appended since construction or last `clear()`.
        """
        return list(self._records)

    def get_by_event(self, event_type: EventType) -> list[Record]:
        """Return records matching an event type.

        Args:
            event_type: Event type to filter on.

        Returns:
            Records whose `event_type` matches the given value.
        """
        return [record for record in self._records if record.event_type == event_type]

    def get_by_owner(self, owner_name: str) -> list[Record]:
        """Return records for a given owner.

        Args:
            owner_name: Owner name to filter on.

        Returns:
            Records whose `owner_name` matches the given value.
        """
        return [record for record in self._records if record.owner_name == owner_name]

    def clear(self) -> None:
        """Remove all stored records."""
        self._records.clear()
