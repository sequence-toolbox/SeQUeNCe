"""Storage and time providers for metrics."""

from __future__ import annotations

from time import time_ns
from typing import Any, Protocol

from .event_types import EventType


class TimeProvider(Protocol):
    """Protocol for objects that supply a timestamp for recorded events."""

    def now(self) -> int: ...


class SystemTimeProvider:
    """Fallback time source using the current system clock."""

    def now(self) -> int:
        return time_ns()


class InMemoryStorage:
    """Store metric records in memory for the lifetime of the simulation."""

    def __init__(self) -> None:
        self._records: list[dict[str, Any]] = []

    def append(self, record: dict[str, Any]) -> None:
        self._records.append(record)

    def get_all(self) -> list[dict[str, Any]]:
        return list(self._records)

    def get_by_event(self, event_type: EventType) -> list[dict[str, Any]]:
        return [record for record in self._records if record["event_type"] is event_type]

    def get_by_owner(self, owner_name: str) -> list[dict[str, Any]]:
        return [record for record in self._records if record["owner_name"] == owner_name]

    def clear(self) -> None:
        self._records.clear()
