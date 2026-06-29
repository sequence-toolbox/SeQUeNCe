"""Built-in event types and metrics."""

from __future__ import annotations

from .event_types import EventTypes
from .metric_types import CounterMetric, DeliveryTimeMetric, FidelityMetric, RateMetric
from .registry import register_metric

EG_METRIC = CounterMetric(
EG_FAILURE = register_event_type("EG_FAILURE")
EG_SUCCESS = register_event_type("EG_SUCCESS")
THROUGHPUT = register_event_type("THROUGHPUT")
EP_FAILURE = register_event_type("EP_FAILURE")
EP_SUCCESS = register_event_type("EP_SUCCESS")
PURIFIED_DELIVERY = register_event_type("PURIFIED_DELIVERY")
ES_FAILURE = register_event_type("ES_FAILURE")
ES_SUCCESS = register_event_type("ES_SUCCESS")

    prefix="eg",
    failure_event=EG_FAILURE,
    success_event=EG_SUCCESS,
    rate_field="success_rate",
)
EP_METRIC = CounterMetric(
    prefix="ep",
    failure_event=EP_FAILURE,
    success_event=EP_SUCCESS,
    rate_field="ep_success_rate",
)
THROUGHPUT_METRIC = RateMetric(key="app_throughput")
PURIFIED_FIDELITIES_METRIC = FidelityMetric(
    key="purified_fidelities",
    event=EP_SUCCESS,
    field="fidelity",
)
DELIVERY_TIME_METRIC = DeliveryTimeMetric(
    key="delivery_time",
    delivery_event=PURIFIED_DELIVERY,
)
ES_METRIC = CounterMetric(
    prefix="es",
    failure_event=ES_FAILURE,
    success_event=ES_SUCCESS,
    rate_field="es_success_rate",
)
SWAPPED_FIDELITIES_METRIC = FidelityMetric(
    key="swapped_fidelities",
    event=ES_SUCCESS,
    field="fidelity",
)

_BUILTIN_METRICS = (
    EG_METRIC,
    EP_METRIC,
    THROUGHPUT_METRIC,
    PURIFIED_FIDELITIES_METRIC,
    DELIVERY_TIME_METRIC,
    ES_METRIC,
    SWAPPED_FIDELITIES_METRIC,
)


def register_builtin_metrics() -> None:
    """Register all built-in metrics."""
    for metric in _BUILTIN_METRICS:
        register_metric(metric)
