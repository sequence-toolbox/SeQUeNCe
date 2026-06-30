"""Metric registry and lookup helpers."""

from __future__ import annotations

from .metric_types import CounterMetric, Metric

_metrics: list[Metric] = []
_counters: dict[str, CounterMetric] = {}


def register_metric(metric: Metric) -> None:
    """Register a metric.

    Args:
        metric: Metric instance to add to the registry.

    Raises:
        ValueError: If output keys collide with an existing metric.
    """
    new_keys = metric.output_keys
    for existing in _metrics:
        overlap = existing.output_keys & new_keys
        if overlap:
            raise ValueError(f"Metric output keys {sorted(overlap)} already registered.")
    _metrics.append(metric)
    if isinstance(metric, CounterMetric):
        _counters[metric.prefix] = metric


def unregister_metric(metric: Metric) -> None:
    """Remove a metric from the registry.

    Args:
        metric: Metric instance to remove.
    """
    if metric in _metrics:
        _metrics.remove(metric)
    if isinstance(metric, CounterMetric):
        _counters.pop(metric.prefix, None)


def list_metrics() -> list[Metric]:
    """Return registered metrics in registration order.

    Returns:
        Registered metrics in the order they were added.
    """
    return list(_metrics)


def get_counter(prefix: str) -> CounterMetric:
    """Return a registered counter metric by prefix.

    Args:
        prefix: Counter metric prefix used at registration time.

    Returns:
        The matching counter metric.
    """
    try:
        return _counters[prefix]
    except KeyError as exc:
        raise KeyError(f"No CounterMetric registered with prefix '{prefix}'.") from exc


def reset_metrics() -> None:
    """Reset per-trial state for all registered metrics.

    Clears accumulated counts and other state held by each metric between trials.
    """
    for metric in _metrics:
        metric.reset()


def clear_registry() -> None:
    """Remove all metrics from the registry.

    Intended for test isolation; also clears the counter lookup table.
    """
    _metrics.clear()
    _counters.clear()
