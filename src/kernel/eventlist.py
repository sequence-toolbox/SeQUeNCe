from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .event import Event

from heapq import heappush, heappop, heapify


class EventList:
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
