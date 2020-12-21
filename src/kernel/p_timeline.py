from mpi4py import MPI
from typing import TYPE_CHECKING
from time import time

from .eventlist import EventList
from .quantum_manager_client import QuantumManagerClient
from ..utils.phold import PholdNode
from numpy.random import seed

if TYPE_CHECKING:
    from .event import Event


class ParallelTimeline():

    def __init__(self, lookahead: int, stop_time=float('inf'), formalism='KET',
                 qm_ip="127.0.0.1", qm_port="6789"):
        self.stop_time = stop_time
        self.id = MPI.COMM_WORLD.Get_rank()
        self.entities = {}
        self.time = 0
        self.foreign_entities = {}
        self.event_buffer = [[] for _ in range(MPI.COMM_WORLD.Get_size())]
        self.events = EventList()
        self.lookahead = lookahead
        self.execute_flag = False
        self.quantum_manager = QuantumManagerClient(formalism, qm_ip, qm_port)
        self.quantum_manager.init()

        self.sync_counter = 0
        self.event_counter = 0
        self.schedule_counter = 0
        self.exchange_counter = 0
        self.computing_time = 0
        self.communication_time = 0

    def seed(self, n):
        seed(n)

    def get_entity_by_name(self, name: str):
        if name in self.entities:
            return self.entities[name]
        else:
            return None

    def now(self):
        return self.time

    def schedule(self, event:'Event'):
        if type(event.process.owner) is str:
            if event.process.owner in self.foreign_entities:
                tl_id = self.foreign_entities[event.process.owner]
                self.event_buffer[tl_id].append(event)
            else:
                event.process.owner = self.entities[event.process.owner]
                self.events.push(event)
        else:
            self.events.push(event)
        self.schedule_counter += 1

    def init(self):
        for entity in self.entities.values():
            entity.init()

    def run(self):
        self.execute_flag = True
        while self.time < self.stop_time:
            tick = time()
            keep_run = MPI.COMM_WORLD.allreduce(self.execute_flag, op=MPI.BOR)
            self.communication_time += time() - tick

            if not keep_run:
                break

            tick = time()
            inbox = MPI.COMM_WORLD.alltoall(self.event_buffer)
            self.communication_time += time() - tick

            for buff in self.event_buffer:
                buff.clear()

            for events in inbox:
                for event in events:
                    self.exchange_counter += 1
                    self.schedule(event)

            tick = time()
            min_time = MPI.COMM_WORLD.allreduce(self.events.top().time,
                                                op=MPI.MIN)
            self.communication_time += time() - tick

            self.execute_flag = False
            self.sync_counter += 1

            sync_time = min(min_time + self.lookahead, self.stop_time)

            tick = time()
            while len(self.events) > 0 and self.events.top().time < sync_time:
                event = self.events.pop()
                if event.is_invalid():
                    continue
                assert self.time <= event.time, "invalid event time for process scheduled on " + str(
                    event.process.owner)
                self.time = event.time
                event.process.run()
                self.execute_flag = True
                self.event_counter += 1
            self.computing_time += time() - tick

    def remove_event(self, event: "Event") -> None:
        self.events.remove(event)
