from sequence.kernel.entity import Entity
from sequence.kernel.timeline import Timeline
from numpy.random import default_rng
from numpy.random._generator import Generator


class FakeOwner():
    def get_generator(self):
        return self.generator


class Foo(Entity):
    def init(self):
        pass


def test_get_generator():
    tl = Timeline()

    # owner does not have generator
    owner = FakeOwner()
    foo = Foo("foo", tl)
    foo.owner = owner
    assert isinstance(foo.get_generator(), Generator)

    # owner has generator
    rng = default_rng()
    owner = FakeOwner()
    owner.generator = rng
    foo = Foo("foo2", tl)
    foo.owner = owner
    assert foo.get_generator() == rng
