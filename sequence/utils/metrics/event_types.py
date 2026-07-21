"""Event types and payload dataclasses for the metrics module."""

from __future__ import annotations

from dataclasses import dataclass

_registry: dict[str, EventType] = {}


@dataclass(frozen=True, slots=True)
class EventType:
    """Identifies a type of recordable simulation event.

    Attributes:
        name: Unique string identifier for the event type.
        payload_type: Dataclass type for the event payload, or `None`
            if the event carries no additional data beyond event type
            and owner name.
    """

    name: str
    payload_type: type | None = None


def register_event_type(name: str, payload_type: type | None = None) -> EventType:
    """Register an event type.

    Args:
        name: Unique name for the event type.
        payload_type: Dataclass type for the event payload, or `None`
            if the event carries no additional data.

    Returns:
        The registered event type, or the existing instance if already registered.
    """
    if name in _registry:
        return _registry[name]
    event_type = EventType(name, payload_type)
    _registry[name] = event_type
    return event_type


def list_event_types() -> list[EventType]:
    """Return all registered event types.

    Returns:
        All event types registered so far.
    """
    return list(_registry.values())


@dataclass(frozen=True, slots=True)
class EGSuccessData:
    """Payload for a successful entanglement generation event."""

    remote_node: str
    fidelity: float


@dataclass(frozen=True, slots=True)
class EGFailureData:
    """Payload for a failed entanglement generation event."""

    remote_node: str
    fidelity: float


@dataclass(frozen=True, slots=True)
class EPSuccessData:
    """Payload for a successful entanglement purification event."""

    remote_node: str
    fidelity: float


@dataclass(frozen=True, slots=True)
class EPFailureData:
    """Payload for a failed entanglement purification event."""

    remote_node: str


@dataclass(frozen=True, slots=True)
class ESSuccessData:
    """Payload for a successful entanglement swapping event."""

    left_node: str
    right_node: str
    fidelity: float


@dataclass(frozen=True, slots=True)
class ESFailureData:
    """Payload for a failed entanglement swapping event."""

    left_node: str
    right_node: str


@dataclass(frozen=True, slots=True)
class ReservationApprovedData:
    """Payload for a reservation approval event."""

    identity: int
    initiator: str
    responder: str
    start_time: int
    end_time: int
    memory_size: int
    entanglement_number: int
    target_fidelity: float
    path: list[str]


@dataclass(frozen=True, slots=True)
class ReservationRejectedData:
    """Payload for a reservation rejection event."""

    identity: int
    initiator: str
    responder: str
    start_time: int
    end_time: int
    memory_size: int
    entanglement_number: int
    target_fidelity: float
    path: list[str]


@dataclass(frozen=True, slots=True)
class DeliveryData:
    """Payload for an entanglement delivery event."""

    fidelity: float
    identity: int
    initiator: str
    responder: str
    start_time: int
    end_time: int
    memory_size: int
    entanglement_number: int
    target_fidelity: float
    path: list[str]


class EventTypes:
    """Namespace for built-in simulation event types."""

    # Entanglement Management Events #
    EG_FAILURE = register_event_type("EG_FAILURE", EGFailureData)
    EG_SUCCESS = register_event_type("EG_SUCCESS", EGSuccessData)
    EP_FAILURE = register_event_type("EP_FAILURE", EPFailureData)
    EP_SUCCESS = register_event_type("EP_SUCCESS", EPSuccessData)
    ES_FAILURE = register_event_type("ES_FAILURE", ESFailureData)
    ES_SUCCESS = register_event_type("ES_SUCCESS", ESSuccessData)

    # Network Management Events #
    RESERVATION_APPROVED = register_event_type("RESERVATION_APPROVED", ReservationApprovedData)
    RESERVATION_REJECTED = register_event_type("RESERVATION_REJECTED", ReservationRejectedData)
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

    # Application Events #
    DELIVERY = register_event_type("DELIVERY", DeliveryData)
