from sequence.kernel.entity import Entity
from sequence.kernel.timeline import Timeline
from numpy.random import default_rng
from numpy.random._generator import Generator


class FakeOwnerNoGen:
    def __init__(self):
        pass


class FakeOwner:
    def __init__(self):
        self.generator = None

    def get_generator(self):
        return self.generator


class Foo(Entity):
    def init(self):
        pass


def test_get_generator():
    tl = Timeline()

    # owner does not have generator
    owner = FakeOwnerNoGen()
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


def test_change_timeline():
    tl1 = Timeline()
    tl2 = Timeline()

    ENTITY_NAME = "foo"
    foo = Foo(ENTITY_NAME, tl1)
    assert foo.timeline == tl1
    assert tl1.get_entity_by_name(ENTITY_NAME) == foo
    assert tl2.get_entity_by_name(ENTITY_NAME) is None

    foo.change_timeline(tl2)
    assert foo.timeline == tl2
    assert tl1.get_entity_by_name(ENTITY_NAME) is None
    assert tl2.get_entity_by_name(ENTITY_NAME) == foo
