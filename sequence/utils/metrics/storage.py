"""Storage and time providers for metrics."""

from __future__ import annotations

from time import monotonic_ns
from typing import Any, Protocol

from .event_types import EventType


class TimeProvider(Protocol):
    """Protocol for objects that supply a timestamp for recorded events."""

    def now(self) -> int:
        """Return the current timestamp in picoseconds."""
        ...


class SystemTimeProvider:
    """Fallback time source using the current system clock."""

    def now(self) -> int:
        """Return the current system time in picoseconds.

        Returns:
            Current wall-clock time from ``time_ns()``.
        """
        return monotonic_ns() * 1000


class InMemoryStorage:
    """Store metric records in memory for the lifetime of the simulation."""

    def __init__(self) -> None:
        """Initialize an empty in-memory record store."""
        self._records: list[dict[str, Any]] = []

    def append(self, record: dict[str, Any]) -> None:
        """Append a metric record to storage.

        Args:
            record: Event record with event type, owner, simulation time, and fields.
        """
        self._records.append(record)

    def get_all(self) -> list[dict[str, Any]]:
        """Return all stored metric records.

        Returns:
            Copy of every record appended since construction or last ``clear()``.
        """
        return list(self._records)

    def get_by_event(self, event_type: EventType) -> list[dict[str, Any]]:
        """Return records matching an event type.

        Args:
            event_type: Event type to filter on.

        Returns:
            Records whose ``event_type`` matches the given value.
        """
        return [record for record in self._records if record["event_type"] is event_type]

    def get_by_owner(self, owner_name: str) -> list[dict[str, Any]]:
        """Return records for a given owner.

        Args:
            owner_name: Owner name to filter on.

        Returns:
            Records whose ``owner_name`` matches the given value.
        """
        return [record for record in self._records if record["owner_name"] == owner_name]

    def clear(self) -> None:
        """Remove all stored records."""
        self._records.clear()
