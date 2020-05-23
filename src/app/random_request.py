from typing import List, TYPE_CHECKING
if TYPE_CHECKING:
    from ..protocols.management.memory_manager import MemoryInfo
    from ..protocols.network.rsvp import Reservation

from numpy import random

from ..kernel.event import Event
from ..kernel.process import Process
from ..topology.node import QuantumRouter


class RandomRequestApp():
    def __init__(self, node: "QuantumRouter", others: List[str], seed: int):
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
        self.memo_to_reserve = {}

    def start(self):
        self._update_last_rsvp_metrics()

        responder = self.rg.choice(self.others)
        start_time = self.node.timeline.now() + self.rg.integers(10, 20) * 1e11  # now + 1 sec - 2 sec
        end_time = start_time + self.rg.integers(10, 20) * 1e12  # start time + (10 second - 20 second)
        memory_size = self.rg.integers(10, len(self.node.memory_array) // 2)  # 10 - max_memory_size / 2
        fidelity = self.rg.uniform(0.7, 0.9)
        self.cur_reserve = [responder, start_time, end_time, memory_size, fidelity]
        self.node.reserve_net_resource(responder, start_time, end_time, memory_size, fidelity)
        # print(self.node.timeline.now(), self.node.name, "request", self.cur_reserve)

    def retry(self, responder: str, fidelity: float) -> None:
        start_time = self.node.timeline.now() + self.rg.integers(10, 20) * 1e11  # now + 1 sec - 2 sec
        end_time = start_time + self.rg.integers(10, 20) * 1e12  # start time + (10 second - 20 second)
        memory_size = self.rg.integers(10, len(self.node.memory_array) // 2)  # 10 - max_memory_size / 2
        self.node.reserve_net_resource(responder, start_time, end_time, memory_size, fidelity)
        self.cur_reserve = [responder, start_time, end_time, memory_size, fidelity]

    def _update_last_rsvp_metrics(self):
        if self.cur_reserve and len(self.throughput) < len(self.reserves):
            throughput = self.memory_counter / (self.cur_reserve[2] - self.cur_reserve[1]) * 1e12
            self.throughput.append(throughput)

        self.cur_reserve = []
        self.request_time = self.node.timeline.now()
        self.memory_counter = 0

    def get_reserve_res(self, reservation: "Reservation", result: bool) -> None:
        if result:
            # todo: temp
            self.get_other_reservation(reservation)
            process = Process(self, "start", [])
            self.reserves.append(self.cur_reserve)
            # print(self.node.timeline.now(), self.node.name, "request", self.cur_reserve, result)
            event = Event(self.cur_reserve[2] + 1, process)
            self.node.timeline.schedule(event)
            self.wait_time.append(self.cur_reserve[1] - self.request_time)
        else:
            process = Process(self, "retry", [self.cur_reserve[0], self.cur_reserve[4]])
            event = Event(self.node.timeline.now() + 1e12, process)
            self.node.timeline.schedule(event)

    def get_other_reservation(self, reservation: "Reservation") -> None:
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
        if info.state != "ENTANGLED":
            return

        if info.index in self.memo_to_reserve:
            reservation = self.memo_to_reserve[info.index]
            if info.remote_node == reservation.initiator and info.fidelity >= reservation.fidelity:
                self.node.resource_manager.update(None, info.memory, "RAW")
        elif self.cur_reserve and info.remote_node == self.cur_reserve[0] and info.fidelity >= self.cur_reserve[-1]:
            self.memory_counter += 1
            self.node.resource_manager.update(None, info.memory, "RAW")

    def get_wait_time(self) -> List[int]:
        return self.wait_time

    def get_throughput(self) -> List[float]:
        return self.throughput
