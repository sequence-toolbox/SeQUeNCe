"""Definition of Reservation protocol and related tools.

This module provides a definition for the reservation protocol used by the network manager.
This includes the Reservation, MemoryTimeCard, and QCap classes, which are used by the network manager to track reservations.
Also included is the definition of the message type used by the reservation protocol.
"""

class Reservation:
    """Tracking of reservation parameters for the network manager.
       Each request will generate a reservation

    Attributes:
        initiator (str): name of the node that created the reservation request.
        responder (str): name of distant node with witch entanglement is requested.
        start_time (int): simulation time at which entanglement should be attempted.
        end_time (int): simulation time at which resources may be released.
        memory_size (int): number of entangled memory pairs requested.
        path (list): a list of router names from the source to destination
        entanglement_number (int): the number of entanglement pair that the request ask for.
        identity (int): the ID of a request.
    """

    def __init__(self, initiator: str, responder: str, start_time: int,
                 end_time: int, memory_size: int, fidelity: float, entanglement_number: int = 1, identity: int = 0):
        """Constructor for the reservation class.

        Args:
            initiator (str): node initiating the request.
            responder (str): node with which entanglement is requested.
            start_time (int): simulation start time of entanglement.
            end_time (int): simulation end time of entanglement.
            memory_size (int): number of entangled memories requested.
            fidelity (float): desired fidelity of entanglement.
            entanglement_number (int): the number of entanglement the request ask for.
            identity (int): the ID of a request
            path
            purification_mode
        """

        self.initiator = initiator
        self.responder = responder
        self.start_time = start_time
        self.end_time = end_time
        self.memory_size = memory_size
        self.fidelity = fidelity
        self.entanglement_number = entanglement_number
        self.identity = identity
        self.path = []
        self.purification_mode: str = 'until_target'
        assert self.start_time < self.end_time
        assert self.memory_size > 0

    def __str__(self) -> str:
        return f'|initiator={self.initiator}; responder={self.responder}; start_time={self.start_time:,}; end_time={self.end_time:,}; memory_size={self.memory_size}; target_fidelity={self.fidelity}; entanglement_number={self.entanglement_number}; identity={self.identity}|'

    def __repr__(self) -> str:
        return self.__str__()

    def set_path(self, path: list[str]):
        self.path = path

    def __eq__(self, other: "Reservation"):
        return other.initiator == self.initiator and \
            other.responder == self.responder and \
            other.start_time == self.start_time and \
            other.end_time == self.end_time and \
            other.memory_size == self.memory_size and \
            other.fidelity == self.fidelity

    def __lt__(self, other: "Reservation") -> bool:
        return self.identity < other.identity

    def __hash__(self):
        return hash((self.initiator, self.responder, self.start_time, self.end_time, self.memory_size, self.fidelity))


