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

    # Entanglement Management Events
    EG_FAILURE = register_event_type("EG_FAILURE")
    EG_SUCCESS = register_event_type("EG_SUCCESS")
    EP_FAILURE = register_event_type("EP_FAILURE")
    EP_SUCCESS = register_event_type("EP_SUCCESS")
    ES_FAILURE = register_event_type("ES_FAILURE")
    ES_SUCCESS = register_event_type("ES_SUCCESS")

    # Network Management Events
    RESERVATION_APPROVED = register_event_type("RESERVATION_APPROVED")
    RESERVATION_REJECTED = register_event_type("RESERVATION_REJECTED")
    RESERVATION_REQUESTED = register_event_type("RESERVATION_REQUESTED")
    RESERVATION_HOP_REJECT = register_event_type("RESERVATION_HOP_REJECT")
    RESERVATION_REACHED_RESPONDER = register_event_type("RESERVATION_REACHED_RESPONDER")

    # Forwarding
    FORWARDING_TABLE_MISS = register_event_type("FORWARDING_TABLE_MISS")

    # Routing
    NEIGHBOR_DOWN = register_event_type("NEIGHBOR_DOWN")
    NEIGHBOR_FULL = register_event_type("NEIGHBOR_FULL")
    ROUTE_RECOMPUTED = register_event_type("ROUTE_RECOMPUTED")
    LSA_ORIGINATED = register_event_type("LSA_ORIGINATED")
    LSDB_UPDATED = register_event_type("LSDB_UPDATED")

    # Application Events
    DELIVERY = register_event_type("DELIVERY")
