from mpi4py import MPI
from typing import TYPE_CHECKING

from .eventlist import EventList
from .quantum_manager_client import QuantumManagerClient
from ..utils.phold import PholdNode
from numpy.random import seed

if TYPE_CHECKING:
    from .event import Event


class ParallelTimeline():

    def __init__(self, lookahead: int, stop_time=float('inf'),
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
        self.sync_counter = 0
        self.event_counter = 0
        self.schedule_counter = 0
        self.quantum_manager = QuantumManagerClient(qm_ip, qm_port)
        self.quantum_manager.init()

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
        if type(event.process.owner) == type(''):
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
            keep_run = MPI.COMM_WORLD.allreduce(self.execute_flag, op=MPI.BOR)
            if not keep_run:
                break
            inbox = MPI.COMM_WORLD.alltoall(self.event_buffer)
            for buff in self.event_buffer:
                buff.clear()

            for events in inbox:
                for event in events:
                    event.process.owner = self.get_entity_by_name(event.process.owner)
                    self.schedule(event)

            min_time = MPI.COMM_WORLD.allreduce(self.events.top().time, op=MPI.MIN)
            self.execute_flag = False
            self.sync_counter += 1
            print("sync counter=", self.sync_counter)

            sync_time = min(min_time + self.lookahead, self.stop_time)
            while len(self.events) > 0 and self.events.top().time < sync_time:
                event = self.events.pop()
                if event.is_invalid():
                    continue
                assert self.time <= event.time, "invalid event time for process scheduled on " + str(event.process.owner)
                if type(event.process.owner) == type(''):
                    fh = open('log', 'a')
                    fh.write("%d %.2f %s" % (self.id, self.time, event.process.owner))
                    fh.close()
                self.time = event.time
                event.process.run()
                self.execute_flag = True
                self.event_counter += 1