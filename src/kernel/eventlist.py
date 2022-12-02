"""Definition of EventList class.

This module defines the EventList class, used by the timeline to order and execute events.
EventList is implemented as a min heap ordered by simulation time.
"""

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .event import Event

from heapq import heappush, heappop


class EventList:
    """Class of event list.

    This class is implemented as a min-heap. The event with the lowest time and priority is placed at the top of heap.

    Attributes:
        data (List[Event]): heap storing events.
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

    def top(self) -> "Event":
        return self.data[0]

    def isempty(self) -> bool:
        return len(self.data) == 0

    def remove(self, event: "Event") -> None:
        """Method to remove events from heap.

        The event is set as the invalid state to save the time of removing event from heap.
        """

        event.set_invalid()

    def update_event_time(self, event: "Event", time: int):
        """Method to update the timestamp of event and maintain the min-heap structure.
        """
        if time == event.time:
            return

        def _pop_updated_event(heap: "List", index: int):
            parent_i = (index - 1) // 2
            while index > 0 and event < self.data[parent_i]:
                heap[index], heap[parent_i] = heap[parent_i], heap[index]
                index = parent_i
                parent_i = (parent_i - 1) // 2

        for i, e in enumerate(self.data):
            if id(e) == id(event):
                if event.time > time:
                    event.time = time
                    _pop_updated_event(self.data, i)

                elif event.time < time:
                    event.time = -1
                    _pop_updated_event(self.data, i)
                    self.pop()
                    event.time = time
                    self.push(event)

                break
