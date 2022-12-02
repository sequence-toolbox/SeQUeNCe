import pytest
from mpi4py import MPI
from sequence.kernel.entity import Entity
from sequence.kernel.process import Process
from sequence.kernel.event import Event

from psequence.p_timeline import ParallelTimeline

rank = MPI.COMM_WORLD.Get_rank()
size = MPI.COMM_WORLD.Get_size()


class FakeEntity(Entity):
    def __init__(self, name, tl):
        super().__init__(name, tl)
        self.counter = 0

    def init(self) -> None:
        pass

    def add(self):
        self.counter += 1


def build_env(lookahead):
    tl = ParallelTimeline(lookahead)

    entity = FakeEntity(str(rank), tl)
    for i in range(size):
        if i == rank: continue
        tl.add_foreign_entity(str(i), i)
    return tl, entity


@pytest.mark.mpi
def test_p_timeline_schedule_local_events():
    tl, entity = build_env(10)
    assert len(tl.events) == 0
    event = Event(20, Process(entity, "add", []))
    tl.schedule(event)
    assert len(tl.events) == 1


def test_p_timeline_schedule_remote_events():
    tl, entity = build_env(10)
    assert len(tl.events) == 0
    foreign_rank = (int(entity.name) + 1) % size
    foreign_entity_name = str(foreign_rank)
    event = Event(20, Process(foreign_entity_name, "add", []))
    tl.schedule(event)
    assert len(tl.events) == 0
    assert len(tl.event_buffer[foreign_rank]) == 1


def test_p_timeline_run():
    tl, entity = build_env(10)
    assert len(tl.events) == 0
    foreign_rank = (int(entity.name) + 1) % size
    foreign_entity_name = str(foreign_rank)
    event = Event(20, Process(foreign_entity_name, "add", []))
    tl.schedule(event)
    tl.run()
    assert entity.counter == 1
