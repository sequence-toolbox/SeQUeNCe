"""Registrable event types for the metrics module."""

from __future__ import annotations

from dataclasses import dataclass

_registry: dict[str, EventType] = {}


@dataclass(frozen=True, slots=True)
class EventType:
    """Identifies a type of recordable simulation event."""

    name: str


def register_event_type(name: str) -> EventType:
    """Register an event type. Returns the existing instance if already registered."""
    if name in _registry:
        return _registry[name]
    type = EventType(name)
    _registry[name] = type
    return type


def get_event_type(name: str) -> EventType:
    """Return a registered event type by name."""
    try:
        return _registry[name]
    except KeyError as exc:
        raise KeyError(f"Event type '{name}' is not registered.") from exc


def list_event_types() -> list[EventType]:
    """Return all registered event types."""
    return list(_registry.values())
