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

    EG_FAILURE = auto()
    EG_SUCCESS = auto()
    THROUGHPUT = auto()


EG_FAILURE = EventType.EG_FAILURE
EG_SUCCESS = EventType.EG_SUCCESS
THROUGHPUT = EventType.THROUGHPUT


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
        return [
            record for record in self._records if record["event_type"] is event_type
        ]

    def get_by_owner(self, owner_name: str) -> list[dict[str, Any]]:
        return [
            record for record in self._records if record["owner_name"] == owner_name
        ]

    def clear(self) -> None:
        self._records.clear()


_enabled = False
_enabled_events: set[EventType] = set()
storage = InMemoryStorage()
_system_time_provider = SystemTimeProvider()
time_provider: TimeProvider = _system_time_provider

# Counter dicts that contain the failure and success counters for each node
_failures: dict[str, int] = {}
_successes: dict[str, int] = {}


def register_time_provider(provider: TimeProvider) -> None:
    """Register the active time source for recorded events."""
    global time_provider
    time_provider = provider


def reset_counters() -> None:
    """Reset per-node attempt and success counters."""
    _failures.clear()
    _successes.clear()


def get_failures(owner_name: str) -> int:
    return _failures.get(owner_name, 0)


def get_successes(owner_name: str) -> int:
    return _successes.get(owner_name, 0)


def get_success_rate(owner_name: str) -> float:
    failures = get_failures(owner_name)
    successes = get_successes(owner_name)
    attempts = failures + successes
    if attempts == 0:
        return 0.0
    return successes / attempts


def enable(event_types: list[EventType]) -> None:
    """Enable metrics recording for the given event types.

    Available metrics types are in the metrics.EventType enum.
    """
    global _enabled, _enabled_events
    _enabled = True
    _enabled_events = set(event_types)


def configure(storage_type: str = "in_memory") -> None:
    """Configure metrics storage

    Available storage options:
        - "in_memory": The default, uses `InMemoryStorage`. Keeps all records
          available stored as a dictionary object in memory.
    """
    global storage
    if storage_type == "in_memory":
        storage = InMemoryStorage()


def record(event_type: EventType, owner_name: str, **kwargs: Any) -> None:
    """Record a metrics event if metrics are enabled for this event type.

    Will increment counter if counter is available for metric.
    Metrics with counters:
        - EG_SUCCESS
        - EG_FAILURE

    Will automatically record success rate for:
        - EG_SUCCESS
        - EG_FAILURE
    """
    if not _enabled or event_type not in _enabled_events:
        return

    if event_type is EG_FAILURE:
        _failures[owner_name] = _failures.get(owner_name, 0) + 1
        kwargs["success_rate"] = get_success_rate(owner_name)
    elif event_type is EG_SUCCESS:
        _successes[owner_name] = _successes.get(owner_name, 0) + 1
        kwargs["success_rate"] = get_success_rate(owner_name)

    storage.append(
        {
            "event_type": event_type,
            "owner_name": owner_name,
            "sim_time": time_provider.now(),
            **kwargs,
        }
    )


def _get_throughput(owner_name: str) -> float:
    throughput_records = [
        record
        for record in storage.get_by_owner(owner_name)
        if record["event_type"] is THROUGHPUT
    ]
    if not throughput_records:
        return float("nan")
    return throughput_records[-1]["throughput"]


