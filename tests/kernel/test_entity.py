from typing import Any, cast

import pytest
from numpy.random import default_rng
from numpy.random._generator import Generator

from sequence.kernel.entity import ClassicalEntity, Entity
from sequence.kernel.timeline import Timeline


class FakeOwnerNoGen:
    def __init__(self):
        pass


class FakeOwner:
    def __init__(self):
        self.generator: Generator | None = None

    def get_generator(self):
        return self.generator


class FakeObserver:
    pass


class Foo(Entity):
    def init(self):
        pass


class Bar(ClassicalEntity):
    def init(self):
        pass


@pytest.mark.parametrize(["EntityType"], [(Foo, ), (Bar, )])
def test_get_generator(EntityType: type[Foo | Bar]):
    tl = Timeline()

    # no owner
    ent = EntityType("ent0", tl)
    assert isinstance(ent.get_generator(), Generator)

    # owner does not have generator
    owner1 = FakeOwnerNoGen()
    ent = EntityType("ent1", tl)
    ent.owner = cast(Any, owner1)
    assert isinstance(ent.get_generator(), Generator)

    # owner has generator
    rng = default_rng()
    owner2 = FakeOwner()
    owner2.generator = rng
    ent = EntityType("ent2", tl)
    ent.owner = cast(Any, owner2)
    assert ent.get_generator() == rng


@pytest.mark.parametrize(["EntityType"], [(Foo, ), (Bar, )])
def test_change_timeline(EntityType: type[Foo | Bar]):
    tl1 = Timeline()
    tl2 = Timeline()

    # Entitity

    ENTITY_NAME = "ent"
    ent = EntityType(ENTITY_NAME, tl1)
    assert ent.timeline == tl1
    assert tl1.get_entity_by_name(ENTITY_NAME) == ent
    assert tl2.get_entity_by_name(ENTITY_NAME) is None

    ent.change_timeline(tl2)
    assert ent.timeline == tl2
    assert tl1.get_entity_by_name(ENTITY_NAME) is None
    assert tl2.get_entity_by_name(ENTITY_NAME) == ent


def test_classical_entity_unsupported():
    tl = Timeline()
    bar = Bar("bar", tl)

    observer = FakeObserver()

    try:
        bar._observers
    except Exception as e:
        assert type(e) is AttributeError

    try:
        bar.attach(observer)
    except Exception as e:
        assert type(e) is NotImplementedError
