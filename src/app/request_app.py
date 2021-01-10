from ..kernel.event import Event
from ..kernel.process import Process

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..topology.node import QuantumRouter
    from ..network_management.reservation import Reservation


class RequestApp():
    def __init__(self, node: "QuantumRouter"):
        self.node = node
        self.node.set_app(self)
        self.responder = ""
        self.start_t = -1
        self.end_t = -1
        self.memo_size = 0
        self.fidelity = 0
        self.reserve_res = None
        self.memory_counter = 0
        self.path = []
        self.reserve_as_responder = []
        self.memo_to_reserve = {}

    def start(self, responder: str, start_t: int, end_t: int, memo_size: int,
              fidelity: float):
        assert 0 < fidelity <= 1
        assert 0 <= start_t <= end_t
        assert 0 < memo_size
        self.responder = responder
        self.start_t = start_t
        self.end_t = end_t
        self.memo_size = memo_size
        self.fidelity = fidelity

        self.node.reserve_net_resource(responder, start_t, end_t,
                                       memo_size, fidelity)

    def get_reserve_res(self, reservation: "Reservation",
                        result: bool) -> None:
        """Method to receive reservation result from network manager.

        Args:
            reservation (Reservation): reservation that has been completed.
            result (bool): result of the request (approved/rejected).

        Side Effects:
            May schedule a start/retry event based on reservation result.
        """
        self.reserve_res = result
        if result:
            self.schedule_reservation(reservation)

    def add_memo_reserve_map(self, index: int,
                             reservation: "Reservation") -> None:
        self.memo_to_reserve[index] = reservation

    def remove_memo_reserve_map(self, index: int) -> None:
        self.memo_to_reserve.pop(index)

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

        if info.index in self.memo_to_reserve:
            reservation = self.memo_to_reserve[info.index]
            if info.remote_node == reservation.initiator \
                    and info.fidelity >= reservation.fidelity:
                self.node.resource_manager.update(None, info.memory, "RAW")
            elif info.remote_node == reservation.responder \
                    and info.fidelity >= reservation.fidelity:
                self.memory_counter += 1
                self.node.resource_manager.update(None, info.memory, "RAW")

    def get_throughput(self) -> float:
        return self.memory_counter / (self.end_t - self.start_t) * 1e12

    def get_other_reservation(self, reservation: "Reservation") -> None:
        """Method to add the approved reservation that is requested by other nodes

        Args:
            reservation (Reservation): reservation that uses the node of application as the responder

        Side Effects:
            Will add calls to `add_memo_reserve_map` and `remove_memo_reserve_map` methods.
        """
        self.schedule_reservation(reservation)

    def schedule_reservation(self, reservation: "Reservation") -> None:
        self.path = reservation.path
        for card in self.node.network_manager.protocol_stack[1].timecards:
            if reservation in card.reservations:
                process = Process(self, "add_memo_reserve_map",
                                  [card.memory_index, reservation])
                event = Event(reservation.start_time, process)
                self.node.timeline.schedule(event)
                process = Process(self, "remove_memo_reserve_map",
                                  [card.memory_index])
                event = Event(reservation.end_time, process)
                self.node.timeline.schedule(event)
