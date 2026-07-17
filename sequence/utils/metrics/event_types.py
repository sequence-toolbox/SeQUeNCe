"""Event types for the metrics module."""

from __future__ import annotations

from dataclasses import dataclass

_registry: dict[str, EventType] = {}


@dataclass(frozen=True, slots=True)
class EventType:
    """Identifies a type of recordable simulation event.

    Attributes:
        name: Unique string identifier for the event type.
    """

    name: str


def register_event_type(name: str) -> EventType:
    """Register an event type.

    Args:
        name: Unique name for the event type.

    Returns:
        The registered event type, or the existing instance if already registered.
    """
    if name in _registry:
        return _registry[name]
    event_type = EventType(name)
    _registry[name] = event_type
    return event_type


def list_event_types() -> list[EventType]:
    """Return all registered event types.

    Returns:
        All event types registered so far.
    """
    return list(_registry.values())


class EventTypes:
    """Namespace for built-in simulation event types."""

    EG_FAILURE = register_event_type("EG_FAILURE")
    EG_SUCCESS = register_event_type("EG_SUCCESS")
    EP_FAILURE = register_event_type("EP_FAILURE")
    EP_SUCCESS = register_event_type("EP_SUCCESS")
    DELIVERY = register_event_type("DELIVERY")
    ES_FAILURE = register_event_type("ES_FAILURE")
    ES_SUCCESS = register_event_type("ES_SUCCESS")
    RESERVATION_APPROVED = register_event_type("RESERVATION_APPROVED")
    RESERVATION_REJECTED = register_event_type("RESERVATION_REJECTED")
    RESERVATION_COMPLETE = register_event_type("RESERVATION_COMPLETE")
