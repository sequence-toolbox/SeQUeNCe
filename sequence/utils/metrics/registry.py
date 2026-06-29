"""Metric registry and lookup helpers."""

from __future__ import annotations

from .metric_types import CounterPairMetric, Metric

_metrics: list[Metric] = []
_counter_pairs: dict[str, CounterPairMetric] = {}


def register_metric(metric: Metric) -> None:
    """Register a metric. Raises if output keys collide with existing metrics."""
    new_keys = metric.output_keys
    for existing in _metrics:
        overlap = existing.output_keys & new_keys
        if overlap:
            raise ValueError(f"Metric output keys {sorted(overlap)} already registered.")
    _metrics.append(metric)
    if isinstance(metric, CounterPairMetric):
        _counter_pairs[metric.prefix] = metric


def unregister_metric(metric: Metric) -> None:
    """Remove a metric from the registry."""
    if metric in _metrics:
        _metrics.remove(metric)
    if isinstance(metric, CounterPairMetric):
        _counter_pairs.pop(metric.prefix, None)


def list_metrics() -> list[Metric]:
    """Return registered metrics in registration order."""
    return list(_metrics)


def get_counter_pair(prefix: str) -> CounterPairMetric:
    """Return a registered counter-pair metric by prefix."""
    try:
        return _counter_pairs[prefix]
    except KeyError as exc:
        raise KeyError(f"No CounterPairMetric registered with prefix '{prefix}'.") from exc


def reset_metrics() -> None:
    """Reset per-trial state for all registered metrics."""
    for metric in _metrics:
        metric.reset()


def clear_registry() -> None:
    """Remove all metrics from the registry (for tests)."""
    _metrics.clear()
    _counter_pairs.clear()
