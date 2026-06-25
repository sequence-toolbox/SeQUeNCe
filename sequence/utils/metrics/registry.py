"""Metric registry and lookup helpers."""

from __future__ import annotations

from .metric_types import CounterPairMetric, Metric, ReservationDeliveryMetric

_metrics: list[Metric] = []
_counter_pairs: dict[str, CounterPairMetric] = {}
_reservation_delivery_metric: ReservationDeliveryMetric | None = None


def register_metric(metric: Metric) -> None:
    """Register a metric. Raises if output keys collide with existing metrics."""
    new_keys = metric.output_keys
    for existing in _metrics:
        overlap = existing.output_keys & new_keys
        if overlap:
            raise ValueError(
                f"Metric output keys {sorted(overlap)} already registered."
            )
    _metrics.append(metric)
    if isinstance(metric, CounterPairMetric):
        _counter_pairs[metric.prefix] = metric
    if isinstance(metric, ReservationDeliveryMetric):
        global _reservation_delivery_metric
        _reservation_delivery_metric = metric


def unregister_metric(metric: Metric) -> None:
    """Remove a metric from the registry."""
    if metric in _metrics:
        _metrics.remove(metric)
    if isinstance(metric, CounterPairMetric):
        _counter_pairs.pop(metric.prefix, None)
    if isinstance(metric, ReservationDeliveryMetric):
        global _reservation_delivery_metric
        if _reservation_delivery_metric is metric:
            _reservation_delivery_metric = None


def list_metrics() -> list[Metric]:
    """Return registered metrics in registration order."""
    return list(_metrics)


def get_counter_pair(prefix: str) -> CounterPairMetric:
    """Return a registered counter-pair metric by prefix."""
    try:
        return _counter_pairs[prefix]
    except KeyError as exc:
        raise KeyError(f"No CounterPairMetric registered with prefix '{prefix}'.") from exc


def get_reservation_delivery_metric() -> ReservationDeliveryMetric:
    """Return the registered reservation delivery metric."""
    if _reservation_delivery_metric is None:
        raise KeyError("No ReservationDeliveryMetric registered.")
    return _reservation_delivery_metric


def reset_metrics() -> None:
    """Reset per-trial state for all registered metrics."""
    for metric in _metrics:
        metric.reset()


def clear_registry() -> None:
    """Remove all metrics from the registry (for tests)."""
    global _reservation_delivery_metric
    _metrics.clear()
    _counter_pairs.clear()
    _reservation_delivery_metric = None
