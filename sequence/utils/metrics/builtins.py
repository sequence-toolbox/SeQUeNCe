"""Built-in event types and metrics."""

from __future__ import annotations

from .event_types import register_event_type
from .metric_types import (
    AppEpTimeMetric,
    CounterPairMetric,
    EventFieldListMetric,
    EventRecordsMetric,
    LastValueMetric,
)
from .registry import register_metric

EG_FAILURE = register_event_type("EG_FAILURE")
EG_SUCCESS = register_event_type("EG_SUCCESS")
THROUGHPUT = register_event_type("THROUGHPUT")
EP_FAILURE = register_event_type("EP_FAILURE")
EP_SUCCESS = register_event_type("EP_SUCCESS")
PURIFIED_DELIVERY = register_event_type("PURIFIED_DELIVERY")

EG_METRIC = CounterPairMetric(
    prefix="eg",
    failure_event=EG_FAILURE,
    success_event=EG_SUCCESS,
    rate_field="success_rate",
)
EP_METRIC = CounterPairMetric(
    prefix="ep",
    failure_event=EP_FAILURE,
    success_event=EP_SUCCESS,
    rate_field="ep_success_rate",
)
THROUGHPUT_METRIC = LastValueMetric(
    key="app_throughput",
    event=THROUGHPUT,
    field="throughput",
)
PURIFIED_FIDELITIES_METRIC = EventFieldListMetric(
    key="purified_fidelities",
    event=EP_SUCCESS,
    field="fidelity",
)
APP_EP_TIME_METRIC = AppEpTimeMetric(
    key="app_ep_time",
    delivery_event=PURIFIED_DELIVERY,
)
EVENT_RECORDS_METRIC = EventRecordsMetric()

_BUILTIN_METRICS = (
    EG_METRIC,
    EP_METRIC,
    THROUGHPUT_METRIC,
    PURIFIED_FIDELITIES_METRIC,
    APP_EP_TIME_METRIC,
    EVENT_RECORDS_METRIC,
)


def register_builtin_metrics() -> None:
    """Register all built-in metrics."""
    for metric in _BUILTIN_METRICS:
        register_metric(metric)
