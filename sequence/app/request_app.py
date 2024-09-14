from __future__ import annotations
from typing import TYPE_CHECKING, List, Dict

if TYPE_CHECKING:
    from ..topology.node import QuantumRouter
    from ..network_management.reservation import Reservation
    from ..resource_management.memory_manager import MemoryInfo

from ..kernel.event import Event
from ..kernel.process import Process
from ..utils import log


class RequestApp:
    """Code for the request application.

        This application will create a request for entanglement.
        If the request is accepted, the network will start to serve the request
        at the start time of the request and end at the end time of the request.
        Otherwise, the app do nothing.
        The information about the request is defined in the arguments of the start function.

        Attributes:
            node (QuantumRouter): Node that code is attached to.
            responder (str): name of the responder node
            start_t (int): the start time of request (ps)
            end_t (int): the end time of request (ps)
            memo_size (int): the size of memory used for the request
            fidelity (float): the target fidelity of the entanglement
            reservation_result (bool): if network approves the request
            memory_counter (int): number of successfully received memories
            path (List[str]): the path of flow denoted by a list of node names
            memo_to_reserve (Dict[int, Reservation]): mapping of memory index to corresponding reservation.
            name (str): the name of the app
    """

    def __init__(self, node: QuantumRouter):
        self.node: QuantumRouter = node
        self.node.set_app(self)
        self.responder: str = ""
        self.start_t: int = -1
        self.end_t: int = -1
        self.memo_size: int = 0
        self.fidelity: float = 0
        self.reservation_result: bool = False
        self.memory_counter: int = 0
        self.path: List[str] = []
        self.memo_to_reservation: Dict[int, Reservation] = {}
        self.name: str = f"{self.node.name}.RequestApp"

    def start(self, responder: str, start_t: int, end_t: int, memo_size: int, fidelity: float):
        """Method to start the application.

            This method will use arguments to create a request and send to the network.

        Side Effects:
            Will create request for network manager on node.
        """
        assert 0 < fidelity <= 1
        assert 0 <= start_t <= end_t
        assert 0 < memo_size
        self.responder = responder
        self.start_t = start_t
        self.end_t = end_t
        self.memo_size = memo_size
        self.fidelity = fidelity

        self.node.reserve_net_resource(responder, start_t, end_t, memo_size, fidelity)

    def get_reservation_result(self, reservation: "Reservation", result: bool) -> None:
        """Method to receive reservation result from network manager. 

        The initiator will call this method once received a response from the responder.

        Args:
            reservation (Reservation): reservation that has been completed.
            result (bool): result of the request (approved/rejected).

        Side Effects:
            May schedule a start/retry event based on reservation result.
        """
        self.reservation_result = result
        if result:
            self.schedule_reservation(reservation)
            log.logger.info("Successful reservation of resources for request app on node {}".format(self.node.name))

    def add_memo_reservation_map(self, index: int, reservation: "Reservation") -> None:
        """Maps memory index to the corresponding reservation.

        Args:
            index (int): Memory index
            reservation (Reservation): Reservation that index should map to.
        """
        self.memo_to_reservation[index] = reservation

    def remove_memo_reservation_map(self, index: int) -> None:
        """Function to remove mapping from self.memo_to_reservation.

        When a reservation ends, it should be removed from mapping by this method.

        Args:
            index (int): The memory index to remove.
        """
        self.memo_to_reservation.pop(index)

    def get_memory(self, info: "MemoryInfo") -> None:
        """Method to receive entangled memories.

        Will check if the received memory is qualified.
        If it's a qualified memory, the application sets memory to RAW state
        and release back to resource manager.
        The counter of entanglement memories, 'memory_counter', is added.
        Otherwise, the application does not modify the state of memory and
        release back to the resource manager.

        Args:
            info (MemoryInfo): info on the qualified entangled memory.
        """

        if info.state != "ENTANGLED":
            return

        if info.index in self.memo_to_reservation:
            reservation = self.memo_to_reservation[info.index]
            if info.remote_node == reservation.initiator and info.fidelity >= reservation.fidelity:
                self.node.resource_manager.update(None, info.memory, "RAW")
            elif info.remote_node == reservation.responder and info.fidelity >= reservation.fidelity:
                self.memory_counter += 1
                log.logger.info("Successfully generated entanglement. Counter is at {}.".format(self.memory_counter))
                self.node.resource_manager.update(None, info.memory, "RAW")

    def get_throughput(self) -> float:
        return self.memory_counter / (self.end_t - self.start_t) * 1e12

    def get_other_reservation(self, reservation: "Reservation") -> None:
        """Method to add the approved reservation that is requested by other nodes. The responder will call this method

        Args:
            reservation (Reservation): reservation that uses the node of application as the responder

        Side Effects:
            Will add calls to `add_memo_reservation_map` and `remove_memo_reservation_map` methods.
        """
        self.schedule_reservation(reservation)

    def schedule_reservation(self, reservation: "Reservation") -> None:
        if reservation.initiator == self.node.name:
            self.path = reservation.path

        reservation_protocol = self.node.network_manager.protocol_stack[1]
        for card in reservation_protocol.timecards:
            if reservation in card.reservations:
                process = Process(self, "add_memo_reservation_map", [card.memory_index, reservation])
                event = Event(reservation.start_time, process)
                self.node.timeline.schedule(event)
                process = Process(self, "remove_memo_reservation_map", [card.memory_index])
                event = Event(reservation.end_time, process)
                self.node.timeline.schedule(event)

    def set_name(self, name: str):
        self.name = name

    def __str__(self) -> str:
        return self.name
