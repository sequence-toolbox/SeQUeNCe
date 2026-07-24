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


@dataclass(frozen=True, slots=True)
class ReservationRequestedData:
    """Payload for a reservation requested event."""

    responder: str
    start_time: int
    end_time: int
    memory_size: int
    target_fidelity: float
    identity: int


@dataclass(frozen=True, slots=True)
class ReservationHopRejectData:
    """Payload for a reservation hop rejection event."""

    initiator: str
    responder: str
    identity: int
    path_so_far: list[str]


@dataclass(frozen=True, slots=True)
class ReservationReachedResponderData:
    """Payload for a reservation reached responder event."""

    initiator: str
    identity: int
    path: list[str]


@dataclass(frozen=True, slots=True)
class ForwardingTableMissData:
    """Payload for a forwarding table miss event."""

    dst: str


@dataclass(frozen=True, slots=True)
class NeighborDownData:
    """Payload for a neighbor down event."""

    neighbor: str


@dataclass(frozen=True, slots=True)
class NeighborFullData:
    """Payload for a neighbor full adjacency event."""

    neighbor: str


@dataclass(frozen=True, slots=True)
class RouteRecomputedData:
    """Payload for a route recomputed event."""

    num_routes: int


@dataclass(frozen=True, slots=True)
class LSAOriginatedData:
    """Payload for an LSA originated event."""

    seq_number: int
    num_links: int


@dataclass(frozen=True, slots=True)
class LsdbUpdatedData:
    """Payload for an LSDB updated event."""

    src: str
    num_updated_lsas: int


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
    RESERVATION_REQUESTED = register_event_type("RESERVATION_REQUESTED", ReservationRequestedData)
    RESERVATION_HOP_REJECT = register_event_type("RESERVATION_HOP_REJECT", ReservationHopRejectData)
    RESERVATION_REACHED_RESPONDER = register_event_type("RESERVATION_REACHED_RESPONDER", ReservationReachedResponderData)

    # Forwarding
    FORWARDING_TABLE_MISS = register_event_type("FORWARDING_TABLE_MISS", ForwardingTableMissData)

    # Routing
    NEIGHBOR_DOWN = register_event_type("NEIGHBOR_DOWN", NeighborDownData)
    NEIGHBOR_FULL = register_event_type("NEIGHBOR_FULL", NeighborFullData)
    ROUTE_RECOMPUTED = register_event_type("ROUTE_RECOMPUTED", RouteRecomputedData)
    LSA_ORIGINATED = register_event_type("LSA_ORIGINATED", LSAOriginatedData)
    LSDB_UPDATED = register_event_type("LSDB_UPDATED", LsdbUpdatedData)

    # Application Events #
    DELIVERY = register_event_type("DELIVERY", DeliveryData)
