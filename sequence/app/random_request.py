"""Code for a randomized application

This module defines the RandomRequestApp, which will create random entanglement requests repeatedly.
Useful for testing network properties and throughputs.
"""
from __future__ import annotations
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..network_management.reservation import Reservation

from numpy import random

from .request_app import RequestApp
from ..kernel.event import Event
from ..kernel.process import Process
from ..topology.node import QuantumRouter


class RandomRequestApp(RequestApp):
    """Code for the random request application.

    This application will create a request for entanglement with a random node (and with other random parameters).
    If the request is accepted, a new request will be made once it has expired.
    Otherwise, a new request will be made immediately.
    The responder and fidelity of failed request will be kept in the new request.

    The RandomRequestApp class inherits three functions from the RequsetApp class:
    get_memory(memory_info), get_throughput(), get_other_reservation(reservation).
    The "get_memory" function consumes the memory when the qualified entanglement is generated.
    The "get_throughput" function provides the throughput of the serving reservation.
    The "get_other_reservation" function accepts reservation when node is the responder node.

    Attributes:
        node (QuantumRouter): Node that code is attached to.
        others (List[str]): list of names for available other nodes.
        rg (numpy.random.default_rng): random number generator for application.
        request_time (int): simulation time at which current reservation requested.
        memory_counter (int): number of successfully received memories.
        wait_time (List[int]): aggregates times between request and accepted reservation.
        all_throughput (List[float]): aggregates average rate of memory entanglement per reservation.
        reserves (List[List[any]]): aggregates previous reservations.
        memo_to_reserve (Dict[int, Reservation]): mapping of memory index to corresponding reservation.
        min_dur (int): the minimum duration of request (ps).
        max_dur (int): the maximum duration of request (ps).
        min_size (int): the minimum required memory of request.
        max_size (int): the maximum required memory of request.
        min_fidelity (float): the minimum required fidelity of entanglement.
        max_fidelity (float): the maximum required fidelity of entanglement.
    """

    def __init__(self, node: QuantumRouter, others: List[str], seed: int,
                 min_dur: int, max_dur: int, min_size: int, max_size: int,
                 min_fidelity: float, max_fidelity: float):
        """Constructor for the random application class.

        Args:
            node (QuantumRouter): node that application is attached to.
            others (List[str]): list of names for other available routers.
            seed (int): seed for internal random number generator.
            min_dur (int): the minimum duration of request (ps).
            max_dur (int): the maximum duration of request (ps).
            min_size (int): the minimum required memory of request.
            max_size (int): the maximum required memory of request.
            min_fidelity (float): the minimum required fidelity of entanglement.
            max_fidelity (float): the maximum required fidelity of entanglement.
        """
        super().__init__(node)
        assert 0 < min_dur <= max_dur
        assert 0 < min_size <= max_size
        assert 0 < min_fidelity <= max_fidelity <= 1

        self.others: List[str] = others
        self.rg: random.Generator = random.default_rng(seed)

        self.request_time: int = 0

        self.wait_time: List[int] = []
        self.all_throughput: List[float] = []
        self.reserves = []
        self.paths: List[List[str]] = []

        self.min_dur: int = min_dur
        self.max_dur: int = max_dur
        self.min_size: int = int(min_size)
        self.max_size: int = int(max_size)
        self.min_fidelity: float = min_fidelity
        self.max_fidelity: float = max_fidelity

    def start(self):
        """Method to start the application.

        This method will:
        
        1. Choose a random destination node from the `others` list.
        2. Choose a start time between 1-2 seconds in the future.
        3. Choose a random duration between min_dur and max_dur to set end_time
        4. Pick a number of memories to request between min_size and max_size
        5. Pick a random fidelity between min_fidelity and max_fidelity.
        6. Use its parent class start function to create request

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
        super().start(responder, start_time, end_time, memory_size, fidelity)

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
        super().start(responder, start_time, end_time, memory_size, fidelity)

    def _update_last_rsvp_metrics(self):
        if self.responder and len(self.all_throughput) < len(self.reserves):
            throughput = self.get_throughput()
            self.all_throughput.append(throughput)

        self.request_time = self.node.timeline.now()
        self.memory_counter = 0
        self.path = []

    def get_reserve_res(self, reservation: Reservation, result: bool) -> None:
        """Method to receive reservation result from network manager.

        Args:
            reservation (Reservation): reservation that has been completed.
            result (bool): result of the request (approved/rejected).

        Side Effects:
            May schedule a start/retry event based on reservation result.
        """

        super().get_reserve_res(reservation, result)
        if result:
            process = Process(self, "start", [])
            self.reserves.append([self.responder, self.start_t, self.end_t,
                                  self.memo_size, self.fidelity])
            self.paths.append(self.path)
            event = Event(self.end_t + 1, process)
            self.node.timeline.schedule(event)
            self.wait_time.append(self.start_t - self.request_time)
        else:
            process = Process(self, "retry", [self.responder, self.fidelity])
            event = Event(self.node.timeline.now() + 1e12, process)
            self.node.timeline.schedule(event)

    def get_wait_time(self) -> List[int]:
        return self.wait_time

    def get_all_throughput(self) -> List[float]:
        return self.all_throughput
