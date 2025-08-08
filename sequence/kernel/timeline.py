"""Definition of main Timeline class.

This module defines the Timeline class, which provides an interface for the simulation kernel and drives event execution.
All entities are required to have an attached timeline for simulation.
"""

from _thread import start_new_thread
from datetime import timedelta
from math import inf
from sys import stdout
from time import sleep, time_ns
from typing import TYPE_CHECKING, cast

from numpy import random

if TYPE_CHECKING:
    from .event import Event
    from .entity import Entity
    from .quantum_manager import QuantumManager

from ..constants import *
from ..utils import log
from .eventlist import EventList
from .quantum_manager import (BELL_DIAGONAL_STATE_FORMALISM,
                              DENSITY_MATRIX_FORMALISM,
                              FOCK_DENSITY_MATRIX_FORMALISM,
                              KET_STATE_FORMALISM, QuantumManagerBellDiagonal,
                              QuantumManagerDensity, QuantumManagerDensityFock,
                              QuantumManagerKet)


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
        entities (list[Entity]): the entity list of timeline used for initialization.
        time (int): current simulation time (picoseconds). The smallest amount of time in the simulation timeline is 1 picosecond
        stop_time (int): the stop (simulation) time of the simulation.
        schedule_counter (int): the counter of scheduled events
        run_counter (int): the counter of executed events
        is_running (bool): records if the simulation has stopped executing events.
        show_progress (bool): show/hide the progress bar of simulation.
        quantum_manager (QuantumManager): quantum state manager.
    """

    STOP_TIME_INFINITE = cast(int, inf)

    def __init__(self, stop_time: int = STOP_TIME_INFINITE, formalism=KET_STATE_FORMALISM, truncation=1):
        """Constructor for timeline.

        Args:
            stop_time (int): stop time (in ps) of simulation (default inf).
            formalism (str): formalism of quantum state representation.
            truncation (int): truncation of Hilbert space (currently only for Fock representation).
        """
        self.events: EventList = EventList()
        self.entities: dict[str, "Entity"] = {}
        self.time: int = 0
        self.stop_time: int = stop_time
        self.schedule_counter: int = 0
        self.run_counter: int = 0
        self.is_running: bool = False
        self.show_progress: bool = False
        self.quantum_manager: "QuantumManager"
        self.set_quantum_manager(formalism, truncation)

    def set_quantum_manager(self, formalism: str, truncation: int = 1) -> None:
        """Update the formalism

        Args:
            formalism (str): the formalism.
            truncation (int): truncation of Hilbert space (currently only for Fock representation).
        """
        if formalism == KET_STATE_FORMALISM:
            self.quantum_manager = QuantumManagerKet()
        elif formalism == DENSITY_MATRIX_FORMALISM:
            self.quantum_manager = QuantumManagerDensity()
        elif formalism == FOCK_DENSITY_MATRIX_FORMALISM:
            self.quantum_manager = QuantumManagerDensityFock(
                truncation=truncation)
        elif formalism == BELL_DIAGONAL_STATE_FORMALISM:
            self.quantum_manager = QuantumManagerBellDiagonal()
        else:
            raise ValueError(f"Invalid formalism {formalism}")

    def now(self) -> int:
        """Returns current simulation time."""
        return self.time

    def schedule(self, event: "Event") -> None:
        """Method to schedule an event."""
        if type(event.process.owner) is str:
            event.process.owner = self.get_entity_by_name(event.process.owner)
        self.schedule_counter += 1
        self.events.push(event)

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
        self.is_running = True

        if self.show_progress:
            self.progress_bar()

        while len(self.events) > 0:
            event = self.events.pop()

            if event.time >= self.stop_time:
                self.schedule(event)  # return to event list
                break
            assert self.time <= event.time, f"invalid event time for process scheduled on {event.process.owner}"
            if event.is_invalid():
                continue

            self.time = event.time

            log.logger.debug("Event #{}: process owner={}, activation={}".format(
                self.run_counter, event.process.owner, event.process.activation))
            event.process.run()
            self.run_counter += 1

        self.is_running = False
        time_elapsed = time_ns() - tick
        log.logger.info("Timeline end simulation. Execution Time: {}; Scheduled Event: {}; Executed Event: {}".format(
            self.ns_to_human_time(time_elapsed), self.schedule_counter, self.run_counter))

    def stop(self) -> None:
        """Method to stop simulation."""
        log.logger.info("Timeline is stopped")
        self.stop_time = self.now()

    def remove_event(self, event: "Event") -> None:
        """Remove an event from the event list"""
        self.events.remove(event)

    def update_event_time(self, event: "Event", time: int) -> None:
        """Method to change execution time of an event.

        Args:
            event (Event): event to reschedule.
            time (int): new simulation time (should be >= current time).
        """
        self.events.update_event_time(event, time)

    def add_entity(self, entity: "Entity") -> None:
        assert entity.name not in self.entities, f'{entity.name} already exists!'
        entity.timeline = self
        self.entities[entity.name] = entity

    def remove_entity_by_name(self, name: str) -> None:
        entity = self.entities.pop(name)
        entity.timeline = None  # type: ignore

    def get_entity_by_name(self, name: str) -> "Entity|None":
        return self.entities.get(name, None)

    @staticmethod
    def seed(seed: int) -> None:
        """Sets random seed for simulation."""
        random.seed(seed)

    def progress_bar(self):
        """Method to draw progress bar.

        Progress bar will display the execution time of simulation, as well as the current simulation time.
        """
        start_new_thread(self.print_time, ())

    def print_time(self):
        start_time = time_ns()

        while self.is_running:
            execution_time = self.ns_to_human_time(time_ns() - start_time)
            simulation_time = self.ns_to_human_time(
                self.convert_to_nanoseconds(self.time))
            stop_time = 'NaN' if self.stop_time == float('inf') else self.ns_to_human_time(
                self.convert_to_nanoseconds(self.stop_time))
            process_bar = f'{CARRIAGE_RETURN}execution time: {execution_time};     simulation time: {simulation_time} / {stop_time}'

            print(f'{process_bar}', end=CARRIAGE_RETURN)
            stdout.flush()
            sleep(SLEEP_SECONDS)

    @staticmethod
    def ns_to_human_time(nanoseconds: float) -> str:
        """Returns a string in the form [D day[s], ][H]H:MM:SS[.UUUUUU]
        """
        milliseconds = nanoseconds / NANOSECONDS_PER_MILLISECOND
        return str(timedelta(milliseconds=milliseconds))

    @staticmethod
    def convert_to_nanoseconds(picoseconds: int) -> float:
        return picoseconds / PICOSECONDS_PER_NANOSECOND
