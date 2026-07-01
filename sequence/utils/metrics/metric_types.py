"""Metric type hierarchy for the metrics module."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, override

from .event_types import EventType
from .storage import InMemoryStorage


@dataclass
class CollectContext:
    """Context passed to metrics when collecting trial results.

    Attributes:
        owner_name: Node name for counter and fidelity metrics.
        storage: In-memory store of recorded events for the trial.
        delivery_owner: Node name for delivery-time metrics; defaults to ``owner_name``.
        target_pairs: Number of delivered pairs required to compute delivery time.
        reservation_start_time: Simulation time when the reservation started (ps).
        throughput: Application throughput supplied at collection time.
    """

    owner_name: str
    storage: InMemoryStorage
    delivery_owner: str | None = None
    target_pairs: int | None = None
    reservation_start_time: int | None = None
    throughput: float | None = None


class Metric(ABC):
    """Base class for metrics that aggregate recorded events."""

    @property
    @abstractmethod
    def event_types(self) -> frozenset[EventType]:
        """Event types this metric reacts to during recording.

        Returns:
            Frozen set of event types handled by ``on_record``.
        """

    @property
    @abstractmethod
    def output_keys(self) -> frozenset[str]:
        """Keys produced by ``collect()``.

        Returns:
            Frozen set of keys written into per-trial result dictionaries.
        """

    def on_record(self, event_type: EventType, owner_name: str, kwargs: dict[str, Any]) -> None:
        """Update metric state when a matching event is recorded.

        This method is called for every metric when it is recorded.
        Default implementation is a no-op. 
        This method is completely optional for any metric subclasses.
        Should only be implemented if you need a hook when a metric is recorded.

        Args:
            event_type: Type of the recorded event.
            owner_name: Name of the node or component that owns the event.
            kwargs: Mutable event payload; metrics may add derived fields.
        """
        pass

    @abstractmethod
    def collect(self, ctx: CollectContext) -> dict[str, Any]:
        """Return trial result keys and values for this metric.

        Args:
            ctx: Collection context with owner, storage, and trial parameters.

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

    def on_record(self, event_type: EventType, owner_name: str, kwargs: dict[str, Any]) -> None:
        """Increment failure or success counts and update the rate field in kwargs.

        Args:
            event_type: Recorded event type; must match failure or success event.
            owner_name: Name of the node or component that owns the event.
            kwargs: Event payload; updated with the current success rate.
        """
        if event_type is self.failure_event:
            self._failures[owner_name] = self._failures.get(owner_name, 0) + 1
            kwargs[self.rate_field] = self.success_rate(owner_name)
        elif event_type is self.success_event:
            self._successes[owner_name] = self._successes.get(owner_name, 0) + 1
            kwargs[self.rate_field] = self.success_rate(owner_name)

    def collect(self, ctx: CollectContext) -> dict[str, Any]:
        """Return failure, success, and success-rate counts for the trial owner.

        Args:
            ctx: Collection context with the owner name to report.

        Returns:
            Mapping of prefixed failure, success, and success-rate keys.
        """
        return {
            f"{self.prefix}_failures": self.failures(ctx.owner_name),
            f"{self.prefix}_success": self.successes(ctx.owner_name),
            f"{self.prefix}_success_rate": self.success_rate(ctx.owner_name),
        }

    def reset(self) -> None:
        """Clear per-owner failure and success counts."""
        self._failures.clear()
        self._successes.clear()


@dataclass
class RateMetric(Metric):
    """Collects a rate value supplied at trial collection time (e.g. throughput)."""

    key: str = "app_throughput"

    @property
    def event_types(self) -> frozenset[EventType]:
        return frozenset()

    @property
    def output_keys(self) -> frozenset[str]:
        return frozenset({self.key})

    def collect(self, ctx: CollectContext) -> dict[str, Any]:
        """Return the throughput value supplied at collection time.

        Args:
            ctx: Collection context; uses ``throughput`` when set.

        Returns:
            Mapping with the configured rate key and throughput or NaN.
        """
        if ctx.throughput is None:
            return {self.key: float("nan")}
        return {self.key: ctx.throughput}


@dataclass
class FidelityMetric(Metric):
    """Collects fidelity values from matching success events."""

    key: str
    event: EventType
    field: str

    @property
    def event_types(self) -> frozenset[EventType]:
        return frozenset({self.event})

    @property
    def output_keys(self) -> frozenset[str]:
        return frozenset({self.key})

    def collect(self, ctx: CollectContext) -> dict[str, Any]:
        """Collect fidelity values from matching success events for the owner.

        Args:
            ctx: Collection context with owner name and event storage.

        Returns:
            Mapping of the configured key to a list of fidelity values.
        """
        values = [
            record[self.field]
            for record in ctx.storage.get_by_owner(ctx.owner_name)
            if record["event_type"] is self.event and self.field in record
        ]
        return {self.key: values}


@dataclass
class DeliveryTimeMetric(Metric):
    """Time to deliver N pairs relative to reservation start."""

    key: str = "delivery_time"
    delivery_event: EventType | None = None

    @property
    def event_types(self) -> frozenset[EventType]:
        if self.delivery_event is None:
            return frozenset()
        return frozenset({self.delivery_event})

    @property
    def output_keys(self) -> frozenset[str]:
        return frozenset({self.key})

    @override
    def collect(self, ctx: CollectContext) -> dict[str, Any]:
        """Compute elapsed time to deliver the target number of pairs.

        Args:
            ctx: Collection context with delivery owner, target pair count,
                reservation start time, and stored delivery events.

        Returns:
            Mapping with delivery time in seconds, or NaN if data is insufficient.
        """
        delivery_owner = ctx.delivery_owner or ctx.owner_name
        delivery_records = [
            record
            for record in ctx.storage.get_by_owner(delivery_owner)
            if self.delivery_event is not None and record["event_type"] is self.delivery_event
        ]
        delivery_records.sort(key=lambda record: record["sim_time"])
        if ctx.target_pairs is None or len(delivery_records) < ctx.target_pairs:
            return {self.key: float("nan")}
        if ctx.reservation_start_time is None:
            return {self.key: float("nan")}
        target_time = delivery_records[ctx.target_pairs - 1]["sim_time"]
        return {
            self.key: (target_time - ctx.reservation_start_time) * 1e-12,
        }
