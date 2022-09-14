from typing import List

from mpi4py import MPI
from time import time
from sequence.kernel.timeline import Timeline
from sequence.kernel.event import Event
from sequence.kernel.quantum_manager import KET_STATE_FORMALISM

from .quantum_manager_client import QuantumManagerClient


class ParallelTimeline(Timeline):
    """Class for a simulation timeline with parallel computation.

    The Parallel Timeline acts behaves similarly to the Timeline class, maintaining and executing a queue of events.
    There is one Parallel Timeline per simulation process.
    Each timeline controls a subset of the simulated network nodes.
    For events executed on nodes belonging to other timelines, an event buffer is maintained.
    These buffers are exchanged between timelines at regular synchronization intervals.
    All Parallel Timelines in a simulation communicate with a Quantum Manager Server for shared quantum states.

    Attributes:
        id (int): rank of MPI process running the Parallel Timeline instance.
        foreign_entities (Dict[str, int]): mapping of object names on other processes to process id.
        event_buffer(List[List[Event]]): stores events for execution on foreign entities;
            swapped during synchronization.
        lookahead (int): defines width of time window for execution (simulation time between synchronization).
        quantum_manager (QuantumManagerClient): local quantum manager client to communicate with server.
    """

    def __init__(self, lookahead: int, stop_time=float('inf'), formalism=KET_STATE_FORMALISM,
                 qm_ip=None, qm_port=None):
        """Constructor for the ParallelTimeline class.

        Also creates a quantum manager client, unless `qm_ip` and `qm_port` are both set to None.

        Args:
            lookahead (int): sets the timeline lookahead time.
            stop_time (int): stop (simulation) time of simulation (default inf).
            formalism (str): formalism to use for storing quantum states (default 'KET').
            qm_ip (str): IP address for the quantum manager server (default None).
            qm_port (int): port to connect to for quantum manager server (default None).
        """

        super(ParallelTimeline, self).__init__(stop_time, formalism)

        self.id = MPI.COMM_WORLD.Get_rank()
        self.foreign_entities = {}
        self.event_buffer = [[] for _ in range(MPI.COMM_WORLD.Get_size())]
        self.lookahead = lookahead
        if qm_ip is not None and qm_port is not None:
            self.quantum_manager = QuantumManagerClient(formalism, qm_ip, qm_port)

        self.show_progress = False

        self.buffer_min_ts = float('inf')

        self.sync_counter = 0
        self.exchange_counter = 0
        self.computing_time = 0
        self.communication_time = 0

    def schedule(self, event: 'Event'):
        """Method to schedule an event."""

        if type(event.process.owner) is str \
                and event.process.owner in self.foreign_entities:
            self.buffer_min_ts = min(self.buffer_min_ts, event.time)
            tl_id = self.foreign_entities[event.process.owner]
            self.event_buffer[tl_id].append(event)
            self.schedule_counter += 1
        else:
            super(ParallelTimeline, self).schedule(event)

    def top_time(self) -> float:
        """Method to get the timestamp of the soonest event in the local queue.

        Used for the conservative synchronization algorithm.
        If the event queue is empty, returns infinity.
        """

        if len(self.events) > 0:
            return self.events.top().time
        else:
            return float('inf')

    def run(self):
        while self.time < self.stop_time:
            tick = time()
            min_time = min(self.buffer_min_ts, self.top_time())
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
            while len(self.events) > 0 and self.events.top().time < sync_time:
                event = self.events.pop()
                if event.is_invalid():
                    continue
                assert self.time <= event.time, "invalid event time for process scheduled on " + str(
                    event.process.owner)
                self.time = event.time
                event.process.run()
                self.run_counter += 1
            if isinstance(self.quantum_manager, QuantumManagerClient):
                self.quantum_manager.flush_before_sync()
            self.computing_time += time() - tick

    def add_foreign_entity(self, entity_name: str, foreign_id: int):
        """Adds the name of an entity on another parallel timeline.

        Args:
            entity_name (str): name of the entity on another parallel timeline.
            foreign_id (int): id of the process containing the entity.
        """

        self.foreign_entities[entity_name] = foreign_id
