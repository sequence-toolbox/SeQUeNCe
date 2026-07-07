"""Metric registry and lookup helpers."""

from __future__ import annotations

from .metric_types import CounterMetric, Metric, ReservationDeliveryMetric

_metrics: list[Metric] = []
_reservation_delivery_metric: ReservationDeliveryMetric | None = None
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
    if isinstance(metric, ReservationDeliveryMetric):
        global _reservation_delivery_metric
        _reservation_delivery_metric = metric


def unregister_metric(metric: Metric) -> None:
    """Remove a metric from the registry.

    Args:
        metric: Metric instance to remove.
    """
    if metric in _metrics:
        _metrics.remove(metric)
    if isinstance(metric, CounterMetric):
        _counters.pop(metric.prefix, None)
    if isinstance(metric, ReservationDeliveryMetric):
        global _reservation_delivery_metric
        if _reservation_delivery_metric is metric:
            _reservation_delivery_metric = None


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


def get_reservation_delivery_metric() -> ReservationDeliveryMetric:
    """Return the registered reservation delivery metric."""
    if _reservation_delivery_metric is None:
        raise KeyError("No ReservationDeliveryMetric registered.")
    return _reservation_delivery_metric


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
