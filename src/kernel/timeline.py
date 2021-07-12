"""Definition of main Timeline class.

This module defines the Timeline class, which provides an interface for the simulation kernel and drives event execution.
All entities are required to have an attached timeline for simulation.
"""

from _thread import start_new_thread
from math import inf
from sys import stdout
from time import time_ns, sleep
from typing import TYPE_CHECKING
from tqdm import tqdm

if TYPE_CHECKING:
    from .event import Event
    from .entity import Entity

from .eventlist import EventList
from ..utils import log
from .quantum_manager import QuantumManagerKet, QuantumManagerDensity


class Timeline:
    """Class for a simulation timeline.

    Timeline holds entities, which are configured before the simulation.
    Before the start of simulation, the timeline must initialize all controlled entities.
    The initialization of entities may schedule events.
    The timeline pushes these events to its event list.
    The timeline starts simulation by popping the top event in the event list repeatedly.
    The time of popped event becomes current simulation time of the timeline.
    The process of popped event is executed.
    The simulation stops if the timestamp on popped event is equal or larger than the stop time, or if the eventlist is empty.

    To monitor the progress of simulation, the Timeline.show_progress attribute can be modified to show/hide a progress bar.

    Attributes:
        events (EventList): the event list of timeline.
        entities (Dict[str]:Entity): mapping of entity names to `Entity` class objects.
        time (int): current simulation time (picoseconds).
        stop_time (int): the stop (simulation) time of the simulation.
        schedule_counter (int): the counter of scheduled events.
        run_counter (int): the counter of executed events.
        show_progress (bool): indicates if timeline should show progress bar.
        quantum_manager (QuantumManager): quantum state manager.
    """

    def __init__(self, stop_time=inf, formalism='KET'):
        """Constructor for the Timeline class.

        Args:
            stop_time (int): stop time (in ps) of simulation (default inf).
            formalism (str): formalism to use for the quantum manager (default `'KET'` for ket vector).
        """

        self.events = EventList()
        self.entities = {}
        self.time = 0
        self.stop_time = stop_time
        self.schedule_counter = 0
        self.run_counter = 0
        self.show_progress = True

        if formalism == 'KET':
            self.quantum_manager = QuantumManagerKet()
        elif formalism == 'DENSITY':
            self.quantum_manager = QuantumManagerDensity()
        else:
            raise ValueError("Invalid formalism {}".format(formalism))

    def now(self) -> int:
        """Returns current simulation time."""

        return self.time

    def schedule(self, event: "Event") -> None:
        """Method to schedule an event."""

        if type(event.process.owner) is str:
            event.process.owner = self.get_entity_by_name(event.process.owner)
        self.schedule_counter += 1
        return self.events.push(event)

    def init(self) -> None:
        """Method to initialize all simulated entities."""

        log.logger.info("Timeline initial network")

        for entity in self.entities.values():
            entity.init()

    def run(self) -> None:
        """Main simulation method.

        The `run` method begins simulation of events.
        Events are continuously popped and executed, until the simulation time limit is reached or events are exhausted.
        A progress bar may also be displayed, if the `show_progress` flag is set.
        """
        
        log.logger.info("Timeline start simulation")
        tick = time_ns()

        if self.show_progress:
            pbar = tqdm(total=self.stop_time / 1e12, bar_format='{l_bar}{bar:50}{r_bar}{bar:-50b}')

        while len(self.events) > 0:
            event = self.events.pop()
            if event.time >= self.stop_time:
                self.schedule(event)
                break
            assert self.time <= event.time, "invalid event time for process scheduled on " + str(
                event.process.owner)
            if event.is_invalid():
                continue
            if self.show_progress:
                pbar.update((event.time - self.time) / 1e12)
            self.time = event.time
            event.process.run()
            self.run_counter += 1

        elapse = time_ns() - tick
        log.logger.info(
            "Timeline end simulation. Execution Time: %d ns; Scheduled Event: %d; Executed Event: %d" %
            (elapse, self.schedule_counter, self.run_counter))

    def stop(self) -> None:
        """Method to stop simulation."""

        log.logger.info("Timeline is stopped")
        self.stop_time = self.now()

    def remove_event(self, event: "Event") -> None:
        self.events.remove(event)

    def update_event_time(self, event: "Event", time: int) -> None:
        """Method to change execution time of an event.

        Args:
            event (Event): event to reschedule.
            time (int): new simulation time (should be >= current time).
        """

        self.events.update_event_time(event, time)

    def remove_entity_by_name(self, name: str):
        self.entities.pop(name)

    def get_entity_by_name(self, name: str) -> "Entity":
        if name in self.entities:
            return self.entities[name]
        else:
            return None

