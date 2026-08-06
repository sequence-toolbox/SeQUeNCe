"""Built-in metrics for the metrics module."""

from __future__ import annotations

from .event_types import EventTypes
from .metric_types import (
    BellPairUtilizationMetric,
    CounterMetric,
    EventAttributeMetric,
    JainFairnessIndexMetric,
    MemoryUtilizationRatioMetric,
    Metric,
    ReservationSuccessRateMetric,
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
RESERVATION_SUCCESS_RATE_METRIC = ReservationSuccessRateMetric(
    key="reservation_success_rate",
    approved_event=EventTypes.RESERVATION_APPROVED,
    delivery_event=EventTypes.DELIVERY,
)
JAINS_FAIRNESS_INDEX_METRIC = JainFairnessIndexMetric(
    key="jains_fairness_index",
    approved_event=EventTypes.RESERVATION_APPROVED,
    delivery_event=EventTypes.DELIVERY,
)

# Resource Management Metrics
MEMORY_UTILIZATION_RATIO_METRIC = MemoryUtilizationRatioMetric(
    key="memory_utilization_ratio",
    update_event=EventTypes.MEMORY_UPDATE,
)
MEMORY_DECOHERENCE_RATE_METRIC = CounterMetric(
    prefix="memory_decoherence",
    failure_event=EventTypes.EG_SUCCESS,
    success_event=EventTypes.MEMORY_EXPIRED,
    rate_field="memory_decoherence_rate",
)
MEMORY_DECOHERENCE_RATE_METRIC.__doc__ = """Memory decoherence rate = n_expired / (n_expired + n_eg_success).

In SeQUeNCe, n_expired is ``MEMORY_EXPIRED`` and n_eg_success is
``EG_SUCCESS``. Expiry is the counted ``success_event`` so the collected
``memory_decoherence_rate`` is the decoherence loss fraction.

C. Tian et al., "RADAR-Q: Resource-Aware Distributed Asynchronous Routing
for Entanglement Distribution in Multi-Tenant Quantum Networks,"
arXiv:2603.27570, 2026.
"""

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
DELIVERY_FIDELITY_VIOLATION_RATE_METRIC = CounterMetric(
    prefix="delivery_fidelity_violation",
    failure_event=EventTypes.DELIVERY,
    success_event=EventTypes.DELIVERY_FIDELITY_VIOLATION,
    rate_field="delivery_fidelity_violation_success_rate",
)
DELIVERY_FIDELITY_VIOLATION_RATE_METRIC.__doc__ = """Delivery fidelity violation rate = n_violation / (n_violation + n_delivery).

In SeQUeNCe, n_violation is ``DELIVERY_FIDELITY_VIOLATION`` and n_delivery is
``DELIVERY``. Violation is the counted ``success_event`` so the collected
``delivery_fidelity_violation_success_rate`` is the fraction of delivery
attempts with fidelity below the reservation target.

D. Pérez-Castro, J. Fernández-Herrerín, A. Fernández-Vilas, M. Fernández-Veiga,
and R. P. Díaz-Redondo, "Simulation of entanglement based quantum networks
for performance characterization," Computer Networks, vol. 282, p. 112249,
Jun. 2026, doi: 10.1016/j.comnet.2026.112249.

C. Cicconetti, M. Conti, and A. Passarella, "Quality of Service in Quantum
Networks," IEEE Network, vol. 36, no. 5, pp. 24-31, Sep. 2022,
doi: 10.1109/MNET.001.2200163.
"""


def register_builtin_metrics() -> None:
    """Register all built-in metrics with the global registry."""

    BUILTIN_METRICS: list[Metric] = [
        EG_METRIC,
        EP_METRIC,
        ES_METRIC,
        PURIFIED_FIDELITIES_METRIC,
        SWAPPED_FIDELITIES_METRIC,
        ADMISSION_RATE_METRIC,
        RESERVATION_SUCCESS_RATE_METRIC,
        JAINS_FAIRNESS_INDEX_METRIC,
        MEMORY_UTILIZATION_RATIO_METRIC,
        MEMORY_DECOHERENCE_RATE_METRIC,
        THROUGHPUT_METRIC,
        TIME_TO_SERVE_METRIC,
        BELL_PAIR_UTILIZATION_METRIC,
        DELIVERY_FIDELITY_VIOLATION_RATE_METRIC,
    ]

    for metric in BUILTIN_METRICS:
        register_metric(metric)
