from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..protocols.management.memory_manager import MemoryInfo

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

    def start(self):
        self._update_last_rsvp_metrics()

        responder = self.rg.choice(self.others)
        start_time = self.node.timeline.now() + self.rg.integers(10, 20) * 1e11
        end_time = start_time + self.rg.integers(10, 20) * 1e12
        memory_size = self.rg.integers(10, len(self.node.memory_array) // 2)
        fidelity = self.rg.uniform(0.7, 0.9)
        self.node.reserve_net_resource(responder, start_time, end_time, memory_size, fidelity)
        self.cur_reserve = [responder, start_time, end_time, memory_size, fidelity]
        # print(self.node.timeline.now(), self.node.name, "request", self.cur_reserve)

    def _update_last_rsvp_metrics(self):
        if self.cur_reserve and len(self.throughput) < len(self.reserves):
            throughput = self.memory_counter / (self.cur_reserve[2] - self.cur_reserve[1]) * 1e12
            self.throughput.append(throughput)

        self.cur_reserve = []
        self.request_time = self.node.timeline.now()
        self.memory_counter = 0

    def get_reserve_res(self, result: bool) -> None:
        process = Process(self, "start", [])
        if result:
            self.reserves.append(self.cur_reserve)
            # print(self.node.timeline.now(), self.node.name, "request", self.cur_reserve, result)
            event = Event(self.cur_reserve[2] + 1, process)
            self.node.timeline.schedule(event)
            self.wait_time.append(self.cur_reserve[1] - self.request_time)
        else:
            event = Event(self.node.timeline.now() + 5e12, process)
            self.node.timeline.schedule(event)

    def get_memory(self, info: "MemoryInfo") -> None:
        if info.remote_node == self.cur_reserve[0] and info.fidelity >= self.cur_reserve[-1]:
            self.memory_counter += 1
            self.node.resource_manager.update(None, info.memory, "RAW")

    def get_wait_time(self) -> List[int]:
        return self.wait_time

    def get_throughput(self) -> List[float]:
        return self.throughput
