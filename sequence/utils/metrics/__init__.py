"""Centralized metrics tracking for SeQUeNCe simulations.

This module provides a global registry for recording simulation events.
Metrics are disabled by default; call ``enable()`` to opt in to recording.
"""

from __future__ import annotations

import math
from statistics import mean, stdev
from typing import Any

from . import builtins
from .event_types import (
    EventType,
    get_event_type,
    list_event_types,
    register_event_type,
)
from .metric_types import (
    DeliveryTimeMetric,
    CollectContext,
    CounterPairMetric,
    EventFieldListMetric,
    LastValueMetric,
    Metric,
)
from .registry import (
    clear_registry,
    get_counter_pair,
    list_metrics,
    register_metric,
    reset_metrics,
    unregister_metric,
)
from .storage import InMemoryStorage, SystemTimeProvider, TimeProvider

# Built-in event type aliases
EG_FAILURE = builtins.EG_FAILURE
EG_SUCCESS = builtins.EG_SUCCESS
THROUGHPUT = builtins.THROUGHPUT
EP_FAILURE = builtins.EP_FAILURE
EP_SUCCESS = builtins.EP_SUCCESS
PURIFIED_DELIVERY = builtins.PURIFIED_DELIVERY
ES_FAILURE = builtins.ES_FAILURE
ES_SUCCESS = builtins.ES_SUCCESS

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


def configure(storage_type: str = "in_memory") -> None:
    """Configure metrics storage.

    Available storage options:
        - "in_memory": The default, uses ``InMemoryStorage``.
    """
    global storage
    if storage_type == "in_memory":
        storage = InMemoryStorage()
        reset_metrics()


def record(event_type: EventType, owner_name: str, **kwargs: Any) -> None:
    """Record a metrics event if metrics are enabled for this event type."""
    if not _enabled or event_type not in _enabled_events:
        return

    record_kwargs = dict(kwargs)
    for metric in list_metrics():
        if event_type in metric.event_types:
            metric.on_record(event_type, owner_name, record_kwargs)

    storage.append(
        {
            "event_type": event_type,
            "owner_name": owner_name,
            "sim_time": time_provider.now(),
            **record_kwargs,
        }
    )


def collect_trial_metrics(
    owner_name: str,
    *,
    delivery_owner: str | None = None,
    target_pairs: int = 500,
) -> dict[str, Any]:
    """Collect per-trial metrics for a node from the metrics module."""
    ctx = CollectContext(
        owner_name=owner_name,
        storage=storage,
        delivery_owner=delivery_owner or owner_name,
        target_pairs=target_pairs,
    )
    result: dict[str, Any] = {}
    for metric in list_metrics():
        result.update(metric.collect(ctx))
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
    list_metrics_keys = [
        key for key, value in trials[0].items() if isinstance(value, list)
    ]

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

    for metric in list_metrics_keys:
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


builtins.register_builtin_metrics()
