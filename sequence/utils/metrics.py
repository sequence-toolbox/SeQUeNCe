"""Centralized metrics tracking for SeQUeNCe simulations.

This module provides a global registry for recording simulation events.
Metrics are disabled by default; call ``enable()`` to opt in to recording.
"""

from __future__ import annotations

import json
import math
import time
from enum import Enum, auto
from statistics import mean, stdev
from time import time_ns
from typing import Any, Protocol


class EventType(Enum):
    """Event types that can be recorded by the metrics module."""

    EG_FAILURE = auto()
    EG_SUCCESS = auto()
    THROUGHPUT = auto()
    EP_FAILURE = auto()
    EP_SUCCESS = auto()
    PURIFIED_DELIVERY = auto()


EG_FAILURE = EventType.EG_FAILURE
EG_SUCCESS = EventType.EG_SUCCESS
THROUGHPUT = EventType.THROUGHPUT
EP_FAILURE = EventType.EP_FAILURE
EP_SUCCESS = EventType.EP_SUCCESS
PURIFIED_DELIVERY = EventType.PURIFIED_DELIVERY


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

_eg_failures: dict[str, int] = {}
_eg_successes: dict[str, int] = {}
_ep_failures: dict[str, int] = {}
_ep_successes: dict[str, int] = {}


def register_time_provider(provider: TimeProvider) -> None:
    """Register the active time source for recorded events."""
    global time_provider
    time_provider = provider


def reset_counters() -> None:
    """Reset per-node attempt and success counters."""
    _eg_failures.clear()
    _eg_successes.clear()
    _ep_failures.clear()
    _ep_successes.clear()


def get_eg_failures(owner_name: str) -> int:
    return _eg_failures.get(owner_name, 0)


def get_eg_successes(owner_name: str) -> int:
    return _eg_successes.get(owner_name, 0)


def get_eg_success_rate(owner_name: str) -> float:
    failures = get_eg_failures(owner_name)
    successes = get_eg_successes(owner_name)
    attempts = failures + successes
    if attempts == 0:
        return 0.0
    return successes / attempts


def get_ep_failures(owner_name: str) -> int:
    return _ep_failures.get(owner_name, 0)


def get_ep_successes(owner_name: str) -> int:
    return _ep_successes.get(owner_name, 0)


def get_ep_success_rate(owner_name: str) -> float:
    failures = get_ep_failures(owner_name)
    successes = get_ep_successes(owner_name)
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
        - EG_SUCCESS, EG_FAILURE
        - EP_SUCCESS, EP_FAILURE

    Will automatically record success rate for:
        - EG_SUCCESS, EG_FAILURE (as ``success_rate``)
        - EP_SUCCESS, EP_FAILURE (as ``ep_success_rate``)
    """
    if not _enabled or event_type not in _enabled_events:
        return

    if event_type is EG_FAILURE:
        _eg_failures[owner_name] = _eg_failures.get(owner_name, 0) + 1
        kwargs["success_rate"] = get_eg_success_rate(owner_name)
    elif event_type is EG_SUCCESS:
        _eg_successes[owner_name] = _eg_successes.get(owner_name, 0) + 1
        kwargs["success_rate"] = get_eg_success_rate(owner_name)
    elif event_type is EP_FAILURE:
        _ep_failures[owner_name] = _ep_failures.get(owner_name, 0) + 1
        kwargs["ep_success_rate"] = get_ep_success_rate(owner_name)
    elif event_type is EP_SUCCESS:
        _ep_successes[owner_name] = _ep_successes.get(owner_name, 0) + 1
        kwargs["ep_success_rate"] = get_ep_success_rate(owner_name)

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


def _get_purified_fidelities(owner_name: str) -> list[float]:
    return [
        record["fidelity"]
        for record in storage.get_by_owner(owner_name)
        if record["event_type"] is EP_SUCCESS and "fidelity" in record
    ]


def _get_app_ep_time(
    delivery_owner: str,
    target_pairs: int,
    reservation_start_time: int | None,
) -> float:
    delivery_records = [
        record
        for record in storage.get_by_owner(delivery_owner)
        if record["event_type"] is PURIFIED_DELIVERY
    ]
    delivery_records.sort(key=lambda record: record["sim_time"])
    if len(delivery_records) < target_pairs:
        return float("nan")
    if reservation_start_time is None:
        return float("nan")
    target_time = delivery_records[target_pairs - 1]["sim_time"]
    return (target_time - reservation_start_time) * 1e-12


def collect_trial_metrics(
    owner_name: str,
    *,
    delivery_owner: str | None = None,
    target_pairs: int = 500,
    reservation_start_time: int | None = None,
) -> dict[str, Any]:
    """Collect per-trial metrics for a node from the metrics module."""
    delivery_owner = delivery_owner or owner_name
    result = {
        "eg_failures": get_eg_failures(owner_name),
        "eg_success": get_eg_successes(owner_name),
        "eg_success_rate": get_eg_success_rate(owner_name),
        "ep_failures": get_ep_failures(owner_name),
        "ep_success": get_ep_successes(owner_name),
        "ep_success_rate": get_ep_success_rate(owner_name),
        "purified_fidelities": _get_purified_fidelities(owner_name),
        "app_throughput": _get_throughput(owner_name),
        "app_ep_time": _get_app_ep_time(
            delivery_owner, target_pairs, reservation_start_time
        ),
        "event_records": storage.get_by_owner(owner_name),
    }
    return result


def aggregate_trial_metrics(
    trials: list[dict[str, Any]],
    *,
    list_metric_cap: int | None = 500,
) -> dict[str, float]:
    """Aggregate trial metrics across multiple trials."""
    if not trials:
        raise ValueError("Cannot aggregate an empty list of trials")

    aggregated: dict[str, float] = {}
    scalar_metrics = [
        key for key, value in trials[0].items() if not isinstance(value, (list, dict))
    ]
    list_metrics = [key for key, value in trials[0].items() if isinstance(value, list)]

    for metric in scalar_metrics:
        values = [trial[metric] for trial in trials]
        finite_values = [
            value
            for value in values
            if isinstance(value, (int, float)) and math.isfinite(value)
        ]
        if finite_values:
            aggregated[f"avg_{metric}"] = mean(finite_values)
            aggregated[f"std_{metric}"] = (
                stdev(finite_values) if len(finite_values) > 1 else 0.0
            )
        else:
            aggregated[f"avg_{metric}"] = float("nan")
            aggregated[f"std_{metric}"] = float("nan")

    for metric in list_metrics:
        if metric == "event_records":
            continue
        all_values: list[float] = []
        for trial in trials:
            trial_values = trial[metric]
            if list_metric_cap is not None:
                trial_values = trial_values[:list_metric_cap]
            all_values.extend(trial_values)
        if all_values:
            aggregated[f"avg_{metric}"] = mean(all_values)
            aggregated[f"std_{metric}"] = (
                stdev(all_values) if len(all_values) > 1 else 0.0
            )
        else:
            aggregated[f"avg_{metric}"] = float("nan")
            aggregated[f"std_{metric}"] = float("nan")

    return aggregated
