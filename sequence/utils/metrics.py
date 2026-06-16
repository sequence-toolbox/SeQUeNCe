"""Centralized metrics tracking for SeQUeNCe simulations.

This module provides a global registry for recording simulation events.
Metrics are disabled by default; call ``enable()`` to opt in to recording.
"""

from __future__ import annotations

from enum import Enum, auto
from time import time_ns
from typing import Any, Protocol


class EventType(Enum):
    """Event types that can be recorded by the metrics module."""

    EG_ATTEMPT = auto()
    EG_SUCCESS = auto()

EG_ATTEMPT = EventType.EG_ATTEMPT
EG_SUCCESS = EventType.EG_SUCCESS

class TimeProvider(Protocol):
    """Protocol for objects that supply a timestamp for recorded events."""

    def now(self) -> int:
        ...


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


_enabled = False
_enabled_events: set[EventType] = set()
storage = InMemoryStorage()
_system_time_provider = SystemTimeProvider()
time_provider: TimeProvider = _system_time_provider


def register_time_provider(provider: TimeProvider) -> None:
    """Register the active time source for recorded events."""
    global time_provider
    time_provider = provider


def enable(event_types: list[EventType]) -> None:
    """Enable metrics recording for the given event types."""
    global _enabled, _enabled_events
    _enabled = True
    _enabled_events = set(event_types)


def configure(storage_type: str = "in_memory", time_provider: TimeProvider | None = None) -> None:
    """Configure metrics storage and optional time source."""
    global storage
    if storage_type != "in_memory":
        raise ValueError("Only in_memory storage is supported")

    storage = InMemoryStorage()
    if time_provider is not None:
        register_time_provider(time_provider)


def record(event_type: EventType, owner_name: str, **kwargs: Any) -> None:
    """Record a metrics event if metrics are enabled for this event type."""
    if not _enabled or event_type not in _enabled_events:
        return

    storage.append({
        "event_type": event_type,
        "owner_name": owner_name,
        "sim_time": time_provider.now(),
        **kwargs,
    })
