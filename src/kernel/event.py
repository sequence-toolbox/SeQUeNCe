"""Definition of the Event class.

This module defines the Event class, which is executed by the timeline.
Events should be scheduled through the timeline to take effect.
"""

from math import inf
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .process import Process


class Event:
    """Class of event for simulation

    The event is sorted by its time and priority. The event with lower time is less than the event with higher time.
    Events with the same time is sorted by their priority from low to high.

    Args:
        time (int): the execution time of event
        process (Process): the process encapsulated in the event
        priority (int): the priority of event, lower value denotes the higher priority

    Attributes:
        time (int): the execution time of event
        process (Process): the process encapsulated in the event
        priority (int): the priority of event, lower value denotes the higher priority
    """

    def __init__(self, time: int, process: "Process", priority=inf):
        self.time = time
        self.priority = priority
        self.process = process

    def __eq__(self, another):
        return (self.time == another.time) and (self.priority == another.priority)

    def __ne__(self, another):
        return (self.time != another.time) or (self.priority != another.priority)

    def __gt__(self, another):
        return (self.time > another.time) or (self.time == another.time and self.priority > another.priority)

    def __lt__(self, another):
        return (self.time < another.time)  or (self.time == another.time and self.priority < another.priority)
