"""Built-in metrics for the metrics module."""

from __future__ import annotations

from .event_types import EventTypes
from .metric_types import CounterMetric, DeliveryTimeMetric, EventAttributeMetric, Metric, ThroughputMetric
from .registry import register_metric

# Entanglement Management Metrics
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
ES_METRIC = CounterMetric(
    prefix="es",
    failure_event=EventTypes.ES_FAILURE,
    success_event=EventTypes.ES_SUCCESS,
    rate_field="es_success_rate",
)
PURIFIED_FIDELITIES_METRIC = EventAttributeMetric(
    key="purified_fidelities",
    event=EventTypes.EP_SUCCESS,
    extractor=lambda record: record.data.fidelity,
)
SWAPPED_FIDELITIES_METRIC = EventAttributeMetric(
    key="swapped_fidelities",
    event=EventTypes.ES_SUCCESS,
    extractor=lambda record: record.data.fidelity,
)

# Network Management Metrics
RESERVATION_APPROVAL_RATE = CounterMetric(
    prefix="reservation_approval",
    failure_event=EventTypes.RESERVATION_REJECTED,
    success_event=EventTypes.RESERVATION_APPROVED,
    rate_field="reservation_approval_rate",
)

# Resource Management Metrics

# Application Metrics
THROUGHPUT_METRIC = ThroughputMetric(
    key="app_throughput",
    delivery_event=EventTypes.DELIVERY,
)
DELIVERY_TIME_METRIC = DeliveryTimeMetric(
    key="delivery_time",
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
        ES_METRIC,
        PURIFIED_FIDELITIES_METRIC,
        SWAPPED_FIDELITIES_METRIC,
        THROUGHPUT_METRIC,
        DELIVERY_TIME_METRIC,
    ]

    for metric in BUILTIN_METRICS:
        register_metric(metric)
