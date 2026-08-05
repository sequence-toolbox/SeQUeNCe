"""Built-in metrics for the metrics module."""

from __future__ import annotations

from .event_types import EventTypes
from .metric_types import (
    BellPairUtilizationMetric,
    CounterMetric,
    EventAttributeMetric,
    Metric,
    ThroughputMetric,
    TimeToServeMetric,
)
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
ADMISSION_RATE_METRIC = CounterMetric(
    prefix="admission",
    failure_event=EventTypes.RESERVATION_REJECTED,
    success_event=EventTypes.RESERVATION_APPROVED,
    rate_field="admission_rate",
)
ADMISSION_RATE_METRIC.__doc__ = """Admission rate = n_approved / (n_approved + n_rejected).

In SeQUeNCe, n_approved is ``RESERVATION_APPROVED`` and n_rejected is
``RESERVATION_REJECTED``. The collected ``admission_success_rate`` is the
admission rate (fraction of reservation requests that are approved).

Defined in C. Cicconetti, M. Conti and A. Passarella, "Quality of Service
in Quantum Networks," in IEEE Network, vol. 36, no. 5, pp. 24-31,
September/October 2022, doi: 10.1109/MNET.001.2200163.
"""

# Resource Management Metrics

# Application Metrics
THROUGHPUT_METRIC = ThroughputMetric(
    key="app_throughput",
    delivery_event=EventTypes.DELIVERY,
)
TIME_TO_SERVE_METRIC = TimeToServeMetric(
    key="time_to_serve",
    delivery_event=EventTypes.DELIVERY,
)
BELL_PAIR_UTILIZATION_METRIC = BellPairUtilizationMetric(
    key="bell_pair_utilization",
    pair_event=EventTypes.EG_SUCCESS,
    delivery_event=EventTypes.DELIVERY,
)


def register_builtin_metrics() -> None:
    """Register all built-in metrics with the global registry."""

    BUILTIN_METRICS: list[Metric] = [
        EG_METRIC,
        EP_METRIC,
        ES_METRIC,
        PURIFIED_FIDELITIES_METRIC,
        SWAPPED_FIDELITIES_METRIC,
        ADMISSION_RATE_METRIC,
        THROUGHPUT_METRIC,
        TIME_TO_SERVE_METRIC,
        BELL_PAIR_UTILIZATION_METRIC,
    ]

    for metric in BUILTIN_METRICS:
        register_metric(metric)
