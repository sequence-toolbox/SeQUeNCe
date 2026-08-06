"""Metric type hierarchy for the metrics module."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, override

from .event_types import EventType
from .storage import InMemoryStorage, Record


@dataclass
class CollectContext:
    """Context passed to metrics when collecting trial results.

    Attributes:
        delivery_owner: Node name for time-to-serve and throughput delivery lookup.
        target_pairs: Number of delivered pairs required to compute time to serve.
    """

    delivery_owner: str | None = None
    target_pairs: int | None = None


class Metric(ABC):
    """Base class for metrics that aggregate recorded events."""

    @property
    @abstractmethod
    def event_types(self) -> frozenset[EventType]:
        """Event types this metric reacts to during recording.

        Returns:
            Frozen set of event types handled by `on_record`.
        """

    @property
    @abstractmethod
    def output_keys(self) -> frozenset[str]:
        """Keys produced by `collect()`.

        Returns:
            Frozen set of keys written into per-trial result dictionaries.
        """

    def on_record(self, event_type: EventType, owner_name: str, record: Record) -> None:
        """Update metric state when a matching event is recorded.

        This method is called for every metric when it is recorded.
        Default implementation is a no-op.
        This method is completely optional for any metric subclasses.
        Should only be implemented if you need a hook when a metric is recorded.

        Args:
            event_type: Type of the recorded event.
            owner_name: Name of the node or component that owns the event.
            record: The stored record being written.
        """
        pass

    @abstractmethod
    def collect(self, owner_name: str, storage: InMemoryStorage, ctx: CollectContext) -> dict[str, Any]:
        """Return trial result keys and values for this metric.

        Args:
            owner_name: Node name for metrics to be collected.
            storage: In-memory store of recorded events for the trial.
            ctx: Empty

        Returns:
            Mapping of output keys to per-trial values.
        """

    def reset(self) -> None:
        """Clear per-trial metric state.

        This method is called for every metric by default when all metrics are reset.
        Default implementation is a no-op.
        This method is completely optional for any metric subclasses.
        Should only be implemented if you need a hook when the metric is reset.
        """
        pass


@dataclass
class CounterMetric(Metric):
    """Tracks failure/success counts and a running success rate."""

    prefix: str
    failure_event: EventType
    success_event: EventType
    rate_field: str
    _failures: dict[str, int] = field(default_factory=dict, init=False, repr=False)
    _successes: dict[str, int] = field(default_factory=dict, init=False, repr=False)
    __hash__ = object.__hash__

    @property
    def event_types(self) -> frozenset[EventType]:
        return frozenset({self.failure_event, self.success_event})

    @property
    def output_keys(self) -> frozenset[str]:
        return frozenset(
            {
                f"{self.prefix}_failures",
                f"{self.prefix}_success",
                f"{self.prefix}_success_rate",
            }
        )

    def failures(self, owner_name: str) -> int:
        """Return the failure count for an owner.

        Args:
            owner_name: Name of the node or component to query.

        Returns:
            Number of recorded failure events for the owner.
        """
        return self._failures.get(owner_name, 0)

    def successes(self, owner_name: str) -> int:
        """Return the success count for an owner.

        Args:
            owner_name: Name of the node or component to query.

        Returns:
            Number of recorded success events for the owner.
        """
        return self._successes.get(owner_name, 0)

    def success_rate(self, owner_name: str) -> float:
        """Return the success rate for an owner.

        Args:
            owner_name: Name of the node or component to query.

        Returns:
            Ratio of successes to total attempts, or 0.0 if there are no attempts.
        """
        failures = self.failures(owner_name)
        successes = self.successes(owner_name)
        attempts = failures + successes
        if attempts == 0:
            return 0.0
        return successes / attempts

    def on_record(self, event_type: EventType, owner_name: str, record: Record) -> None:
        """Increment failure or success counts.

        Args:
            event_type: Recorded event type; must match failure or success event.
            owner_name: Name of the node or component that owns the event.
            record: The stored record being written.
        """
        if event_type == self.failure_event:
            self._failures[owner_name] = self._failures.get(owner_name, 0) + 1
        elif event_type == self.success_event:
            self._successes[owner_name] = self._successes.get(owner_name, 0) + 1

    def collect(self, owner_name: str, storage: InMemoryStorage, ctx: CollectContext) -> dict[str, Any]:
        """Return failure, success, and success-rate counts for the trial owner.

        Args:
            owner_name: Node name for metrics to be collected.
            storage: In-memory store of recorded events for the trial.
            ctx: Empty

        Returns:
            Mapping of prefixed failure, success, and success-rate keys.
        """
        return {
            f"{self.prefix}_failures": self.failures(owner_name),
            f"{self.prefix}_success": self.successes(owner_name),
            f"{self.prefix}_success_rate": self.success_rate(owner_name),
        }

    def reset(self) -> None:
        """Clear per-owner failure and success counts."""
        self._failures.clear()
        self._successes.clear()


@dataclass
class ThroughputMetric(Metric):
    """Computes application throughput from recorded deliveries at collection time."""

    key: str
    delivery_event: EventType
    __hash__ = object.__hash__

    @property
    def event_types(self) -> frozenset[EventType]:
        return frozenset()

    @property
    def output_keys(self) -> frozenset[str]:
        return frozenset({self.key})

    def collect(self, owner_name: str, storage: InMemoryStorage, ctx: CollectContext) -> dict[str, Any]:
        """Compute throughput as delivered pairs per second over the reservation window.

        Args:
            owner_name: Node name for metrics to be collected.
            storage: In-memory store of recorded events for the trial.
            ctx: Empty

        Returns:
            Mapping with the configured rate key in pairs per second, or NaN if data is insufficient.
        """
        delivery_owner = ctx.delivery_owner or owner_name
        delivery_records = [
            record for record in storage.get_by_owner(delivery_owner) if record.event_type == self.delivery_event
        ]
        if not delivery_records:
            return {self.key: float("nan")}

        delivery_records.sort(key=lambda record: record.sim_time)
        start_time = delivery_records[0].data.start_time
        elapsed_ps = delivery_records[-1].sim_time - start_time
        if elapsed_ps <= 0:
            return {self.key: float("nan")}

        return {self.key: len(delivery_records) / elapsed_ps * 1e12}


@dataclass
class EventAttributeMetric(Metric):
    """Collects a specific attribute from matching events."""

    key: str
    event: EventType
    extractor: Callable[[Any], Any]
    __hash__ = object.__hash__

    @property
    def event_types(self) -> frozenset[EventType]:
        return frozenset({self.event})

    @property
    def output_keys(self) -> frozenset[str]:
        return frozenset({self.key})

    def collect(self, owner_name: str, storage: InMemoryStorage, ctx: CollectContext) -> dict[str, Any]:
        """Collect specific attribute values from matching events for the owner.

        Args:
            owner_name: Node name for metrics to be collected.
            storage: In-memory store of recorded events for the trial.
            ctx: Empty

        Returns:
            Mapping of the configured key to a list of attribute values.
        """
        values = [
            self.extractor(record)
            for record in storage.get_by_owner(owner_name)
            if record.event_type == self.event
        ]
        return {self.key: values}


@dataclass
class TimeToServeMetric(Metric):
    """On-demand end-to-end latency (time to serve) for delivered entangled pairs.

    In SeQUeNCe, time to serve is ``(sim_time of N-th DELIVERY − reservation.start_time)``
    in seconds, with ``N = target_pairs``. For ``target_pairs=1``, this is the
    on-demand latency from request/service start until one EPR pair is distributed.

    Defined in A. Zang, J. Chung, R. Kettimuthu, M. Suchara and T. Zhong,
    "Analytical Performance Estimations for Quantum Repeater Network Scenarios,"
    2024 IEEE International Conference on Quantum Computing and Engineering (QCE),
    Montreal, QC, Canada, 2024, pp. 1960-1966, doi: 10.1109/QCE60285.2024.00226.
    """

    key: str
    delivery_event: EventType
    __hash__ = object.__hash__

    @property
    def event_types(self) -> frozenset[EventType]:
        return frozenset({self.delivery_event})

    @property
    def output_keys(self) -> frozenset[str]:
        return frozenset({self.key})

    @override
    def collect(self, owner_name: str, storage: InMemoryStorage, ctx: CollectContext) -> dict[str, Any]:
        """Compute time to serve from reservation start to the N-th delivery.

        Returns ``(sim_time of N-th delivery − reservation.start_time)`` in
        seconds, where ``N = ctx.target_pairs``. Returns NaN if there are no
        deliveries, ``target_pairs`` is unset, or fewer than ``N`` deliveries
        were recorded.

        Args:
            owner_name: Node name for metrics to be collected.
            storage: In-memory store of recorded events for the trial.
            ctx: Collection context with delivery owner and target pair count.

        Returns:
            Mapping with time to serve in seconds, or NaN if data is insufficient.
        """
        delivery_owner = ctx.delivery_owner or owner_name
        delivery_records = [
            record for record in storage.get_by_owner(delivery_owner) if record.event_type == self.delivery_event
        ]
        if not delivery_records:
            return {self.key: float("nan")}

        delivery_records.sort(key=lambda record: record.sim_time)
        start_time = delivery_records[0].data.start_time

        if ctx.target_pairs is None or len(delivery_records) < ctx.target_pairs:
            return {self.key: float("nan")}
        target_time = delivery_records[ctx.target_pairs - 1].sim_time

        return {self.key: (target_time - start_time) * 1e-12}


@dataclass
class BellPairUtilizationMetric(Metric):
    """Bell pair utilization rate U = n_b / n_s.

    In SeQUeNCe, n_b is the number of recorded pair-generation successes
    (``pair_event``, typically ``EG_SUCCESS``) across storage, and n_s is
    the number of recorded deliveries (``delivery_event``) for the delivery
    owner.

    Defined in G. Ni, H. Claussen and L. Ho, "Joint Optimization of Routing
    and Purification to Meet Fidelity Targets in Quantum Networks," 2026
    International Conference on Quantum Communications, Networking, and
    Computing (QCNC), Kobe, Japan, 2026, pp. 259-263,
    doi: 10.1109/QCNC69040.2026.00044.
    """

    key: str
    pair_event: EventType
    delivery_event: EventType
    __hash__ = object.__hash__

    @property
    def event_types(self) -> frozenset[EventType]:
        return frozenset({self.pair_event, self.delivery_event})

    @property
    def output_keys(self) -> frozenset[str]:
        return frozenset({self.key})

    @override
    def collect(self, owner_name: str, storage: InMemoryStorage, ctx: CollectContext) -> dict[str, Any]:
        """Compute bell pair utilization U = n_b / n_s.

        Here n_b is the number of ``pair_event`` records across all owners in
        storage (generated low-fidelity Bell pairs), and n_s is the number of
        ``delivery_event`` records for the delivery owner (successfully
        established entanglement deliveries). Returns NaN when n_s is 0.

        Args:
            owner_name: Node name for metrics to be collected.
            storage: In-memory store of recorded events for the trial.
            ctx: Collection context; ``delivery_owner`` selects which node's
                deliveries count toward n_s (defaults to ``owner_name``).

        Returns:
            Mapping with the configured key to U, or NaN if there are no deliveries.
        """
        delivery_owner = ctx.delivery_owner or owner_name
        n_b = len(storage.get_by_event(self.pair_event))
        n_s = len([
            record for record in storage.get_by_owner(delivery_owner)
            if record.event_type == self.delivery_event
        ])
        if n_s == 0:
            return {self.key: float("nan")}
        return {self.key: n_b / n_s}


@dataclass
class MemoryUtilizationRatioMetric(Metric):
    """Time-averaged fraction of busy quantum memories at a node.

    Busy memories are those in ``OCCUPIED``, ``ENTANGLED``, or ``PURIFIED``
    state. The utilization ratio is computed from piecewise-constant
    ``MEMORY_UPDATE`` snapshots as the time-weighted average of
    ``(occupied + entangled + purified) / total_memories``.

    Defined in C. Tian et al., "RADAR-Q: Resource-Aware Distributed
    Asynchronous Routing for Entanglement Distribution in Multi-Tenant
    Quantum Networks," arXiv:2603.27570, 2026.
    """

    key: str
    update_event: EventType
    __hash__ = object.__hash__

    @property
    def event_types(self) -> frozenset[EventType]:
        return frozenset({self.update_event})

    @property
    def output_keys(self) -> frozenset[str]:
        return frozenset({self.key})

    @staticmethod
    def _busy_fraction(data: Any) -> float:
        total = data.total_memories
        if total <= 0:
            return float("nan")
        busy = data.occupied_count + data.entangled_count + data.purified_count
        return busy / total

    @override
    def collect(self, owner_name: str, storage: InMemoryStorage, ctx: CollectContext) -> dict[str, Any]:
        """Compute time-averaged memory utilization ratio for the owner.

        Sorts the owner's ``update_event`` records by ``sim_time`` and
        integrates the busy fraction
        ``(occupied_count + entangled_count + purified_count) / total_memories``
        as a piecewise-constant function between updates. The final interval
        extends from the last update to the registered metrics time provider's
        ``now()`` when available. Returns NaN if there are no updates or if
        ``total_memories`` is 0. If the total duration is 0, returns the
        instantaneous fraction at the last (or only) sample.

        Args:
            owner_name: Node name for metrics to be collected.
            storage: In-memory store of recorded events for the trial.
            ctx: Collection context (unused for this metric).

        Returns:
            Mapping with the configured key to utilization ratio in ``[0, 1]``,
            or NaN.
        """
        records = [
            record for record in storage.get_by_owner(owner_name)
            if record.event_type == self.update_event
        ]
        if not records:
            return {self.key: float("nan")}

        records.sort(key=lambda record: record.sim_time)
        if records[0].data.total_memories <= 0:
            return {self.key: float("nan")}

        from sequence.utils import metrics as metrics_mod

        end_time = records[-1].sim_time
        time_provider = getattr(metrics_mod, "time_provider", None)
        if time_provider is not None and hasattr(time_provider, "now"):
            end_time = max(end_time, time_provider.now())

        weighted_sum = 0.0
        for i, record in enumerate(records):
            frac = self._busy_fraction(record.data)
            if math.isnan(frac):
                return {self.key: float("nan")}
            next_time = records[i + 1].sim_time if i + 1 < len(records) else end_time
            duration = next_time - record.sim_time
            if duration > 0:
                weighted_sum += frac * duration

        total_duration = end_time - records[0].sim_time
        if total_duration <= 0:
            return {self.key: self._busy_fraction(records[-1].data)}
        return {self.key: weighted_sum / total_duration}
