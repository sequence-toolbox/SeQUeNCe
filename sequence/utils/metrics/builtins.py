"""Built-in metrics for the metrics module."""

from __future__ import annotations

from .event_types import EventTypes
from .metric_types import (
    CounterMetric,
    DeliveryTimeMetric,
    FidelityMetric,
    Metric,
    RateMetric,
    ReservationDeliveryMetric,
)
from .registry import register_metric


EG_METRIC = CounterMetric(
    prefix="eg",
    failure_event=EventTypes.EG_FAILURE,
    success_event=EventTypes.EG_SUCCESS,
    rate_field="success_rate",
)
EP_METRIC = CounterMetric(
    prefix="ep",
    failure_event=EventTypes.EP_FAILURE,
    success_event=EventTypes.EP_SUCCESS,
    rate_field="ep_success_rate",
)
THROUGHPUT_METRIC = RateMetric(
    key="app_throughput",
    delivery_event=EventTypes.DELIVERY,
)
PURIFIED_FIDELITIES_METRIC = FidelityMetric(
    key="purified_fidelities",
    event=EventTypes.EP_SUCCESS,
    field="fidelity",
)
DELIVERY_TIME_METRIC = DeliveryTimeMetric(
    key="delivery_time",
    delivery_event=EventTypes.DELIVERY,
)
ES_METRIC = CounterMetric(
    prefix="es",
    failure_event=EventTypes.ES_FAILURE,
    success_event=EventTypes.ES_SUCCESS,
    rate_field="es_success_rate",
)
SWAPPED_FIDELITIES_METRIC = FidelityMetric(
    key="swapped_fidelities",
    event=EventTypes.ES_SUCCESS,
    field="fidelity",
)
RESERVATION_DELIVERY_METRIC = ReservationDeliveryMetric(
    delivery_event=EventTypes.DELIVERY,
)


def register_builtin_metrics() -> None:
    """Register all built-in metrics with the global registry.

    Registers entanglement generation, purification, swapping, throughput,
    fidelity, and delivery-time metrics defined in this module.
    """

    BUILTIN_METRICS: list[Metric] = [
        EG_METRIC,
        EP_METRIC,
        THROUGHPUT_METRIC,
        PURIFIED_FIDELITIES_METRIC,
        DELIVERY_TIME_METRIC,
        ES_METRIC,
        SWAPPED_FIDELITIES_METRIC,
        RESERVATION_DELIVERY_METRIC,
    ]

    for metric in BUILTIN_METRICS:
        register_metric(metric)
