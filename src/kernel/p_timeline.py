from typing import List

from mpi4py import MPI
from time import time

from .timeline import Timeline
from .event import Event
from .quantum_manager_client import QuantumManagerClient


class ParallelTimeline(Timeline):

    def __init__(self, lookahead: int, stop_time=float('inf'), formalism='KET',
                 qm_ip=None, qm_port=None):
        super(ParallelTimeline, self).__init__(stop_time, formalism)

        self.id = MPI.COMM_WORLD.Get_rank()
        self.foreign_entities = {}
        self.event_buffer = [[] for _ in range(MPI.COMM_WORLD.Get_size())]
        self.lookahead = lookahead
        if qm_ip is not None and qm_port is not None:
            self.quantum_manager = QuantumManagerClient(formalism, qm_ip,
                                                        qm_port)

        self.async_tl = AsyncParallelTimeline(lookahead, self.quantum_manager,
                                              stop_time, formalism)
        self.async_entities = set()

        self.show_progress = False

        self.buffer_min_ts = float('inf')

        self.sync_counter = 0
        self.exchange_counter = 0
        self.computing_time = 0
        self.communication_time = 0

    def schedule(self, event: 'Event'):
        if type(event.process.owner) is str:
            if event.process.owner in self.foreign_entities:
                if event.process.owner not in self.async_entities:
                    self.buffer_min_ts = min(self.buffer_min_ts, event.time)
                tl_id = self.foreign_entities[event.process.owner]
                self.event_buffer[tl_id].append(event)
                self.schedule_counter += 1
            elif event.process.owner in self.async_tl.entities:
                self.async_tl.import_event(event)
            else:
                super(ParallelTimeline, self).schedule(event)
        else:
            super(ParallelTimeline, self).schedule(event)

    def top_time(self) -> float:
        if len(self.events) > 0:
            return self.events.top().time
        else:
            return float('inf')

    def run(self):
        while self.time < self.stop_time:
            tick = time()
            min_time = min(self.buffer_min_ts, self.top_time(),
                           self.async_tl.top_time())
            for buf in self.event_buffer:
                buf.append(min_time)
            inbox = MPI.COMM_WORLD.alltoall(self.event_buffer)
            self.communication_time += time() - tick

            for buff in self.event_buffer:
                buff.clear()
            self.buffer_min_ts = float('inf')

            for events in inbox:
                min_time = min(min_time, events.pop())
                for event in events:
                    self.exchange_counter += 1
                    self.schedule(event)

            assert min_time >= self.time

            if min_time >= self.stop_time:
                break

            self.sync_counter += 1

            sync_time = min(min_time + self.lookahead, self.stop_time)
            self.time = min_time

            tick = time()
            events = self.async_tl.run(sync_time)
            for event in events:
                self.schedule(event)
            while len(self.events) > 0 and self.events.top().time < sync_time:
                event = self.events.pop()
                if event.is_invalid():
                    continue
                assert self.time <= event.time, "invalid event time for process scheduled on " + str(
                    event.process.owner)
                self.time = event.time
                event.process.run()
                self.run_counter += 1
            self.quantum_manager.flush_before_sync()
            self.computing_time += time() - tick

    def add_foreign_entity(self, entity_name: str, foreign_id: int):
        self.foreign_entities[entity_name] = foreign_id

    def move_entity_to_async_tl(self, entity_name: str):
        self.async_tl.entities[entity_name] = self.entities[entity_name]
        self.entities[entity_name].change_timeline(self.async_tl)
        del self.entities[entity_name]


class AsyncParallelTimeline(Timeline):
    def __init__(self, lookahead, quantum_manager, stop_time=float('inf'),
                 formalism='KET'):
        super().__init__(stop_time, formalism)
        self.quantum_manager = quantum_manager
        self.lookahead = lookahead
        self.exchange_counter = 0
        self.computing_time = 0
        self.new_events = []

    def top_time(self):
        if len(self.events) > 0:
            return self.events.top().time + self.lookahead
        else:
            return float('inf')

    def run(self, stop_time: int) -> List["Event"]:
        self.new_events = []
        tick = time()
        while len(self.events) > 0 and self.events.top().time < stop_time:
            event = self.events.pop()
            if event.is_invalid():
                continue
            assert self.time <= event.time, "invalid event time for process scheduled on " + str(
                event.process.owner)
            self.time = event.time
            event.process.run()
            self.run_counter += 1
        self.computing_time += time() - tick
        return self.new_events

    def schedule(self, event: "Event") -> None:
        self.new_events.append(event)

    def import_event(self, event: "Event"):
        if type(event.process.owner) == str:
            event.process.owner = self.get_entity_by_name(event.process.owner)
        self.events.push(event)
