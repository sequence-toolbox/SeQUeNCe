"""Definition of the Event class.

This module defines the Event class, which is executed by the timeline.
Events should be scheduled through the timeline to take effect.
"""

from math import inf
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .process import Process


class Event:
    """Class of events for simulation.

    Events are sorted by their time and priority. Events with lower times come before events with higher times.
    Events with the same time are sorted by their priority from low to high.

    Attributes:
        time (int): the execution time of the event.
        process (Process): the process encapsulated in the event.
        priority (int): the priority of the event, lower value denotes a higher priority.
        _is_removed (bool): the flag to denotes if it's a valid event
    """

    def __init__(self, time: int, process: "Process", priority=inf):
        """Constructor for event class.
        
        Args:
            time (int): the execution time of the event.
            process (Process): the process encapsulated in the event.
            priority (int): the priority of the event, lower value denotes a higher priority (default inf).
        """

        self.time = time
        self.priority = priority
        self.process = process
        self._is_removed = False

    def __eq__(self, another):
        return (self.time == another.time) and (self.priority == another.priority)

    def __ne__(self, another):
        return (self.time != another.time) or (self.priority != another.priority)

    def __gt__(self, another):
        return (self.time > another.time) or (self.time == another.time and self.priority > another.priority)

    def __lt__(self, another):
        return (self.time < another.time) or (self.time == another.time and self.priority < another.priority)

    def set_invalid(self):
        self._is_removed = True

    def is_invalid(self):
        return self._is_removed
