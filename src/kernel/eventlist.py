"""Definition of EventList class.

This module defines the EventList class, used by the timeline to order and execute events.
EventList is implemented as a min heap ordered by simulation time.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .event import Event

from heapq import heappush, heappop, heapify


class EventList:
    """Class of event list.

    This class is implemented as a min-heap. The event with the lowest time and priority is placed at the top of heap.
    """

    def __init__(self):
        self.data = []

    def __len__(self):
        return len(self.data)

    def __iter__(self):
        for data in self.data:
            yield data

    def push(self, event: "Event") -> "None":
        heappush(self.data, event)

    def pop(self) -> "Event":
        return heappop(self.data)

    def isempty(self) -> bool:
        return len(self.data) == 0

    def remove(self, event: "Event") -> None:
        for i, e in enumerate(self.data):
            if id(e) == id(event):
                self.data.pop(i)
                heapify(self.data)
                break
