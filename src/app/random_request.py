"""Code for a randomozed application

This module defines the RandomRequestApp, which will create random entanglement requests repeatedly.
Useful for testing network properties and throughputs.
"""

from typing import List, TYPE_CHECKING
if TYPE_CHECKING:
    from ..resource_management.memory_manager import MemoryInfo
    from ..network_management.reservation import Reservation

from numpy import random

from ..kernel.event import Event
from ..kernel.process import Process
from ..topology.node import QuantumRouter


class RandomRequestApp():
    """Code for the random request application.

    This application will create a request for entanglement with a random node (and with other random parameters).
    If the request is accepted, a new request will be made once it has expired.
    Otherwise, a new request will be made immediately.
    The responder and fidelity of failed request will be kept in the new request.

    Attributes:
        node (QuantumRouter): Node that code is attached to.
        others (List[str]): list of names for available other nodes.
        rg (numpy.random.default_rng): random number generator for application.
        cur_reserve (List[any]): list describing current reservation.
        request_time (int): simulation time at which current reservation requested.
        memory_counter (int): number of successfully received memories.
        wait_time (List[int]): aggregates times between request and accepted reservation.
        throughput (List[float]): aggregates average rate of memory entanglement per reservation
        reserves (List[List[any]]): aggregates previous reservations 
        memo_to_reserve (Dict[int, Reservation]): mapping of memory index to corresponding reservation.
        min_dur (int): the minimum duration of request (ps)
        max_dur (int): the maximum duration of request (ps)
        min_size (int): the minimum required memory of request
        max_size (int): the maximum required memory of request
        min_fidelity (float): the minimum required fidelity of entanglement
        max_fidelity (float): the maximum required fidelity of entanglement
    """

    def __init__(self, node: "QuantumRouter", others: List[str], seed: int,
                 min_dur: int, max_dur: int, min_size: int, max_size: int,
                 min_fidelity: float, max_fidelity: float):
        """Constructor for the random application class.

        Args:
            node (QuantumRouter): node that application is attached to.
            others (List[str]): list of names for other available routers.
            seed (int): seed for internal random number generator.
            min_dur (int): the minimum duration of request (ps)
            max_dur (int): the maximum duration of request (ps)
            min_size (int): the minimum required memory of request
            max_size (int): the maximum required memory of request
            min_fidelity (float): the minimum required fidelity of entanglement
            max_fidelity (float): the maximum required fidelity of entanglement
        """
        assert 0 < min_dur <= max_dur
        assert 0 < min_size <= max_size
        assert 0 < min_fidelity <= max_fidelity <= 1

        self.node = node
        self.node.set_app(self)
        self.others = others
        self.rg = random.default_rng(seed)

        self.cur_reserve = []
        self.request_time = 0
        self.memory_counter = 0

        self.wait_time = []
        self.throughput = []
        self.reserves = []
        self.paths = []
        self.memo_to_reserve = {}

        self.min_dur = min_dur
        self.max_dur = max_dur
        self.min_size = int(min_size)
        self.max_size = int(max_size)
        self.min_fidelity = min_fidelity
        self.max_fidelity = max_fidelity

    def start(self):
        """Method to start the application.

        This method will:
        
        1. Choose a random destination node from the `others` list.
        2. Choose a start time between 1-2 seconds in the future.
        3. Choose a random duration between min_dur and max_dur to set end_time
        4. Pick a number of memories to request between min_size and max_size
        5. Pick a random fidelity between min_fidelity and max_fidelity.
        6. Create a request and start recording metrics.

        Side Effects:
            Will create request for network manager on node.
        """

        self._update_last_rsvp_metrics()

        responder = self.rg.choice(self.others)
        start_time = self.node.timeline.now() + \
                     self.rg.integers(10, 20) * 1e11  # now + 1 sec - 2 sec
        end_time = start_time + self.rg.integers(self.min_dur, self.max_dur)
        memory_size = self.rg.integers(self.min_size, self.max_size)
        fidelity = self.rg.uniform(self.min_fidelity, self.max_fidelity)
        self.cur_reserve = [responder, start_time, end_time, memory_size,
                            fidelity]
        self.node.reserve_net_resource(responder, start_time, end_time,
                                       memory_size, fidelity)
        # print(self.node.timeline.now(), self.node.name, "request", self.cur_reserve)

    def retry(self, responder: str, fidelity: float) -> None:
        """Method to retry a failed request.

        Args:
            responder (str): responder node of failed request.
            fidelity (float): fidelity of failed request.

        Side Effects:
            Will create request for network manager on node.
        """

        start_time = self.node.timeline.now() + \
                     self.rg.integers(10, 20) * 1e11  # now + 1 sec - 2 sec
        end_time = start_time + self.rg.integers(self.min_dur, self.max_dur)
        memory_size = self.rg.integers(self.min_size, self.max_size)
        self.node.reserve_net_resource(responder, start_time, end_time,
                                       memory_size, fidelity)
        self.cur_reserve = [responder, start_time, end_time, memory_size,
                            fidelity]

    def _update_last_rsvp_metrics(self):
        if self.cur_reserve and len(self.throughput) < len(self.reserves):
            throughput = self.memory_counter / \
                         (self.cur_reserve[2] - self.cur_reserve[1]) * 1e12
            self.throughput.append(throughput)

        self.cur_reserve = []
        self.request_time = self.node.timeline.now()
        self.memory_counter = 0

    def get_reserve_res(self, reservation: "Reservation", result: bool) -> None:
        """Method to receive reservation result from network manager.

        Args:
            reservation (Reservation): reservation that has been completed.
            result (bool): result of the request (approved/rejected).

        Side Effects:
            May schedule a start/retry event based on reservation result.
        """

        if result:
            # todo: temp
            self.get_other_reservation(reservation)
            process = Process(self, "start", [])
            self.reserves.append(self.cur_reserve)
            self.paths.append(reservation.path)
            # print(self.node.timeline.now(), self.node.name, "request", self.cur_reserve, result)
            event = Event(self.cur_reserve[2] + 1, process)
            self.node.timeline.schedule(event)
            self.wait_time.append(self.cur_reserve[1] - self.request_time)
        else:
            process = Process(self, "retry", [self.cur_reserve[0], self.cur_reserve[4]])
            event = Event(self.node.timeline.now() + 1e12, process)
            self.node.timeline.schedule(event)

    def get_other_reservation(self, reservation: "Reservation") -> None:
        """Method to add the approved reservation that is requested by other nodes

        Args:
            reservation (Reservation): reservation that uses the node of application as the responder

        Side Effects:
            Will add calls to `add_memo_reserve_map` and `remove_memo_reserve_map` methods.
        """

        for card in self.node.network_manager.protocol_stack[1].timecards:
            if reservation in card.reservations:
                process = Process(self, "add_memo_reserve_map", [card.memory_index, reservation])
                event = Event(reservation.start_time, process)
                self.node.timeline.schedule(event)
                process = Process(self, "remove_memo_reserve_map", [card.memory_index])
                event = Event(reservation.end_time, process)
                self.node.timeline.schedule(event)

    def add_memo_reserve_map(self, index: int, reservation: "Reservation") -> None:
        self.memo_to_reserve[index] = reservation

    def remove_memo_reserve_map(self, index: int) -> None:
        self.memo_to_reserve.pop(index)

    def get_memory(self, info: "MemoryInfo") -> None:
        """Method to receive entangled memories.

        Will check if the received memory is qualified.
        If it's a qualified memory, the application sets memory to RAW state and release back to resource manager.
        The counter of entanglement memories, 'memory_counter', is added.
        Otherwise, the application does not modify the state of memory and release back to the resource manager.

        Args:
            info (MemoryInfo): info on the qualified entangled memory.
        """

        if info.state != "ENTANGLED":
            return

        if info.index in self.memo_to_reserve:
            reservation = self.memo_to_reserve[info.index]
            if info.remote_node == reservation.initiator and info.fidelity >= reservation.fidelity:
                self.node.resource_manager.update(None, info.memory, "RAW")
            elif self.cur_reserve and info.remote_node == reservation.responder and info.fidelity >= reservation.fidelity:
                self.memory_counter += 1
                self.node.resource_manager.update(None, info.memory, "RAW")

    def get_wait_time(self) -> List[int]:
        return self.wait_time

    def get_throughput(self) -> List[float]:
        return self.throughput
