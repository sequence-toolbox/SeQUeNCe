"""Centralized metrics tracking for SeQUeNCe simulations.

This module provides a global registry for recording simulation events.
Metrics are disabled by default; call ``enable()`` to opt in to recording.
"""

from __future__ import annotations

import math
from statistics import mean, stdev
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...kernel.timeline import Timeline

from . import builtins
from .builtins import (
    DELIVERY_TIME_METRIC,
    EG_METRIC,
    EP_METRIC,
    ES_METRIC,
    PURIFIED_FIDELITIES_METRIC,
    SWAPPED_FIDELITIES_METRIC,
    THROUGHPUT_METRIC,
)
from .event_types import (
    EventType,
    EventTypes,
    list_event_types,
    register_event_type,
)
from .metric_types import CollectContext, CounterMetric, DeliveryTimeMetric, FidelityMetric, Metric, ThroughputMetric
from .registry import (
    clear_registry,
    get_counter,
    list_metrics,
    register_metric,
    reset_metrics,
    unregister_metric,
)
from .storage import InMemoryStorage


_enabled = False
_enabled_events: set[EventType] = set()
storage: InMemoryStorage = InMemoryStorage()
time_provider: Timeline | None = None


def register_time_provider(provider: Timeline) -> None:
    """Register the active time source for recorded events.

    Args:
        provider: Object supplying timestamps via ``now()``.
    """
    global time_provider
    time_provider = provider


def enable(metrics_to_enable: list[Metric]) -> None:
    """Enable metrics recording for the given metrics.

    The event types required by each metric are automatically derived from
    each metric's `event_types` property and added to the recording filter.
    Metrics with empty `event_types` (e.g. `RateMetric`) contribute no
    events to the filter; enabling them alone will not cause any events to
    be recorded. That will only affect what is collected in
    `collect_trial_metrics`.

    Args:
        metrics_to_enable: Metrics whose event types should be recorded.
    """
    global _enabled, _enabled_events
    _enabled = True
    _enabled_events = set().union(*(m.event_types for m in metrics_to_enable))


def configure(storage_type: str = "in_memory") -> None:
    """Configure metrics storage.

    Available storage options:
        - "in_memory": The default, uses `InMemoryStorage`.

    Args:
        storage_type: Storage backend identifier.
    """
    global storage
    if storage_type == "in_memory":
        storage = InMemoryStorage()
        reset_metrics()
        return
    raise ValueError(f"Unknown storage_type '{storage_type}'. Supported: 'in_memory'.")


def record(event_type: EventType, owner_name: str, **kwargs: Any) -> None:
    """Record a metrics event if metrics are enabled for this event type.

    Args:
        event_type: Type of simulation event to record.
        owner_name: Name of the node or component that owns the event.
        **kwargs: Additional event-specific fields stored with the record.
    """
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
    target_pairs: int | None = None,
) -> dict[str, Any]:
    """Collect per-trial metrics for a node from the metrics module.

    Args:
        owner_name: Node name to collect counter and fidelity metrics for.
        delivery_owner: Node name used for delivery-time metrics; defaults to `owner_name`.
        target_pairs: Number of delivered pairs required to compute delivery time.

    Returns:
        Mapping of metric output keys to per-trial values.
    """
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


def collect_reservation_data(owner_name: str | None = None) -> list[list]:
    """Collect per-reservation tabular metrics from recorded delivery events."""
    from collections import defaultdict

    records = storage.get_by_event(EventTypes.DELIVERY)
    if owner_name is not None:
        records = [record for record in records if record["owner_name"] == owner_name]

    groups: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        groups[(record["owner_name"], record["identity"])].append(record)

    data: list[list] = []
    for (node, _), deliveries in groups.items():
        if not deliveries:
            continue
        deliveries.sort(key=lambda record: record["sim_time"])
        timestamps = [record["sim_time"] for record in deliveries]
        fidelities = [record["fidelity"] for record in deliveries]

        first = deliveries[0]
        start_time = first["start_time"]
        end_time = first["end_time"]
        reserved_time = end_time - start_time
        served_pairs = len(deliveries)
        throughput = served_pairs / reserved_time * 1e12 if reserved_time > 0 else 0.0
        completion_time = timestamps[-1]
        entanglement_number = first["entanglement_number"]
        fulfilled = served_pairs == entanglement_number
        path = first.get("path", [])
        path_length = len(path)
        first_pair = timestamps[0]
        avg_fidelity = mean(fidelities) if fidelities else 0.0
        std_fidelity = stdev(fidelities) if len(fidelities) > 1 else 0.0
        durations = [n - c for c, n in zip(timestamps, timestamps[1:])]
        avg_duration = mean(durations) if durations else 0.0
        std_duration = stdev(durations) if len(durations) > 1 else 0.0

        data.append(
            [
                node,
                first["identity"],
                first["initiator"],
                first["responder"],
                start_time,
                end_time,
                reserved_time,
                entanglement_number,
                served_pairs,
                throughput,
                completion_time,
                fulfilled,
                path_length,
                first_pair,
                avg_fidelity,
                std_fidelity,
                avg_duration,
                std_duration,
            ]
        )
    return data


def _mean_and_std(values: list[float]) -> tuple[float, float]:
    finite_values = [value for value in values if math.isfinite(value)]
    if not finite_values:
        return float("nan"), float("nan")
    return mean(finite_values), stdev(finite_values) if len(finite_values) > 1 else 0.0


def aggregate_trial_metrics(
    trials: list[dict[str, Any]],
    *,
    list_metric_cap: int | None = 500,
) -> dict[str, float]:
    """Aggregate trial metrics across multiple trials.

    Args:
        trials: Per-trial metric dictionaries from `collect_trial_metrics`.
        list_metric_cap: Maximum list elements per trial to include when aggregating list metrics.

    Returns:
        Mapping of ``avg_*`` and ``std_*`` keys to aggregated statistics.
    """
    if not trials:
        raise ValueError("Cannot aggregate an empty list of trials")

    aggregated: dict[str, float] = {}
    scalar_metrics = [key for key, value in trials[0].items() if not isinstance(value, (list, dict))]
    list_metrics_keys = [key for key, value in trials[0].items() if isinstance(value, list)]

    for metric in scalar_metrics:
        values = [float(trial[metric]) for trial in trials if isinstance(trial[metric], (int, float))]
        avg, std = _mean_and_std(values)
        aggregated[f"avg_{metric}"] = avg
        aggregated[f"std_{metric}"] = std

    for metric in list_metrics_keys:
        all_values: list[float] = []
        for trial in trials:
            trial_values = trial[metric]
            if list_metric_cap is not None:
                trial_values = trial_values[:list_metric_cap]
            all_values.extend(trial_values)
        avg, std = _mean_and_std(all_values)
        aggregated[f"avg_{metric}"] = avg
        aggregated[f"std_{metric}"] = std

    return aggregated


builtins.register_builtin_metrics()

# Exported symbols
__all__ = [
    # From builtins
    "DELIVERY_TIME_METRIC",
    "EG_METRIC",
    "EP_METRIC",
    "ES_METRIC",
    "PURIFIED_FIDELITIES_METRIC",
    "SWAPPED_FIDELITIES_METRIC",
    "THROUGHPUT_METRIC",
    # From event_types
    "EventType",
    "EventTypes",
    "list_event_types",
    "register_event_type",
    # From metric_types
    "CollectContext",
    "CounterMetric",
    "DeliveryTimeMetric",
    "FidelityMetric",
    "Metric",
    "ThroughputMetric",
    # From registry
    "clear_registry",
    "get_counter",
    "list_metrics",
    "register_metric",
    "reset_metrics",
    "unregister_metric",
    # From storage
    "InMemoryStorage",
    # Top-level symbols in this module
    "register_time_provider",
    "enable",
    "configure",
    "record",
    "collect_trial_metrics",
    "aggregate_trial_metrics",
]
