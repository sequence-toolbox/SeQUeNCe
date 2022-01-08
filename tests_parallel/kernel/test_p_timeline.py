import pytest
from mpi4py import MPI
from sequence.kernel.p_timeline import ParallelTimeline
from sequence.kernel.entity import Entity


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
    rank = MPI.COMM_WORLD.Get_rank()
    size = MPI.COMM_WORLD.Get_size()
    entity = FakeEntity(rank, tl)
    for i in range(size):
        if i == rank: continue
        tl.add_foreign_entity(str(i), i)
    return tl


@pytest.mark.mpi
def test_p_timeline_schedule():
    tl = build_env(10)
