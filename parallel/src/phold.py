from numpy.random import choice, exponential
from typing import List, TYPE_CHECKING

from sequence.kernel.process import Process
from sequence.kernel.event import Event

if TYPE_CHECKING:
    from .p_timeline import ParallelTimeline


class PholdNode:
    def __init__(self, name: 'str', timeline: 'ParallelTimeline',
                 init_work: int, lookahead: int, neighbors: List[str]):
        self.name = name
        self.timeline = timeline
        timeline.entities[name] = self
        self.init_work = init_work
        self.lookahead = lookahead
        self.neightbors = neighbors

    def generate_event(self) -> Event:
        next_str = str(choice(self.neightbors))
        entity = self.timeline.get_entity_by_name(next_str)
        if entity is None:
            process = Process(next_str, 'get', [])
        else:
            process = Process(entity, 'get', [])
        event = Event(self.timeline.now() + self.lookahead + int(
            exponential(self.lookahead)), process)
        return event

    def init(self):
        for _ in range(self.init_work):
            event = self.generate_event()
            self.timeline.schedule(event)

    def get(self):
        event = self.generate_event()
        self.timeline.schedule(event)
