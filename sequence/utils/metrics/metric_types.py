"""Metric type hierarchy for the metrics module."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from .event_types import EventType
from .storage import InMemoryStorage


@dataclass
class CollectContext:
    """Context passed to metrics when collecting trial results."""

    owner_name: str
    storage: InMemoryStorage
    delivery_owner: str | None = None
    target_pairs: int = 500
    reservation_start_time: int | None = None


class Metric(ABC):
    """Base class for metrics that aggregate recorded events."""

    @property
    @abstractmethod
    def event_types(self) -> frozenset[EventType]:
        """Event types this metric reacts to during recording."""

    @property
    @abstractmethod
    def output_keys(self) -> frozenset[str]:
        """Keys produced by collect()."""

    def on_record(
        self,
        event_type: EventType,
        owner_name: str,
        kwargs: dict[str, Any],
    ) -> None:
        """Update metric state when a matching event is recorded."""

    @abstractmethod
    def collect(self, ctx: CollectContext) -> dict[str, Any]:
        """Return trial result keys and values for this metric."""

    def reset(self) -> None:
        """Clear per-trial metric state."""


@dataclass
class CounterPairMetric(Metric):
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
        return self._failures.get(owner_name, 0)

    def successes(self, owner_name: str) -> int:
        return self._successes.get(owner_name, 0)

    def success_rate(self, owner_name: str) -> float:
        failures = self.failures(owner_name)
        successes = self.successes(owner_name)
        attempts = failures + successes
        if attempts == 0:
            return 0.0
        return successes / attempts

    def on_record(
        self,
        event_type: EventType,
        owner_name: str,
        kwargs: dict[str, Any],
    ) -> None:
        if event_type is self.failure_event:
            self._failures[owner_name] = self._failures.get(owner_name, 0) + 1
            kwargs[self.rate_field] = self.success_rate(owner_name)
        elif event_type is self.success_event:
            self._successes[owner_name] = self._successes.get(owner_name, 0) + 1
            kwargs[self.rate_field] = self.success_rate(owner_name)

    def collect(self, ctx: CollectContext) -> dict[str, Any]:
        return {
            f"{self.prefix}_failures": self.failures(ctx.owner_name),
            f"{self.prefix}_success": self.successes(ctx.owner_name),
            f"{self.prefix}_success_rate": self.success_rate(ctx.owner_name),
        }

    def reset(self) -> None:
        self._failures.clear()
        self._successes.clear()


@dataclass
class LastValueMetric(Metric):
    """Collects the last scalar field value from matching events."""

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
        records = [
            record
            for record in ctx.storage.get_by_owner(ctx.owner_name)
            if record["event_type"] is self.event
        ]
        if not records:
            return {self.key: float("nan")}
        return {self.key: records[-1][self.field]}


@dataclass
class EventFieldListMetric(Metric):
    """Collects a list of field values from matching events."""

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
        values = [
            record[self.field]
            for record in ctx.storage.get_by_owner(ctx.owner_name)
            if record["event_type"] is self.event and self.field in record
        ]
        return {self.key: values}


@dataclass
class DeliveryTimeMetric(Metric):
    """Time to deliver N purified pairs relative to reservation start."""

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

    def collect(self, ctx: CollectContext) -> dict[str, Any]:
        delivery_owner = ctx.delivery_owner or ctx.owner_name
        delivery_records = [
            record
            for record in ctx.storage.get_by_owner(delivery_owner)
            if self.delivery_event is not None
            and record["event_type"] is self.delivery_event
        ]
        delivery_records.sort(key=lambda record: record["sim_time"])
        if len(delivery_records) < ctx.target_pairs:
            return {self.key: float("nan")}
        if ctx.reservation_start_time is None:
            return {self.key: float("nan")}
        target_time = delivery_records[ctx.target_pairs - 1]["sim_time"]
        return {
            self.key: (target_time - ctx.reservation_start_time) * 1e-12,
        }
