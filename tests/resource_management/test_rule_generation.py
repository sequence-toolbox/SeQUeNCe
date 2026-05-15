from sequence.kernel.timeline import Timeline
from sequence.network_management.reservation import Reservation
from sequence.resource_management.rule_generation import DefaultReservationRuleGenerator
from sequence.resource_management.action_condition_set import (
    eg_rule_action_request,
    eg_rule_action_await,
    ep_rule_action_request,
    ep_rule_action_await,
    es_rule_action_B,
)
from sequence.topology.node import Node
from sequence.components.memory import MemoryArray
from sequence.resource_management.resource_manager import ResourceManager


class FakeOwner(Node):
    def __init__(self, name, tl):
        super().__init__(name, tl)
        self.map_to_middle_node = {
            "node2": "mid_node1",
            "node1": "mid_node1",
        }
        self.memory_array_name = name + ".MemoryArray"
        memory_array = MemoryArray(self.memory_array_name, tl)
        self.add_component(memory_array)
        self.resource_manager = ResourceManager(self, self.memory_array_name)

    def get_idle_memory(self, info):
        pass


def test_default_reservation_rule_generator_creates_direct_path_rules():
    tl = Timeline()
    owner = FakeOwner("node1", tl)
    generator = DefaultReservationRuleGenerator()

    reservation = Reservation(
        "node1",
        "node2",
        start_time=0,
        end_time=1e12,
        memory_size=1,
        fidelity=0.9,
        entanglement_number=1,
        identity=0,
    )

    rules = generator.create_rules(
        owner=owner,
        path=["node1", "node2"],
        reservation=reservation,
        memory_indices=[0],
        index=0,
    )

    actions = [rule.action for rule in rules]

    assert eg_rule_action_request in actions
    assert eg_rule_action_await not in actions
    assert ep_rule_action_await in actions
    assert ep_rule_action_request not in actions
    assert es_rule_action_B in actions


class TrackingRuleGenerator(DefaultReservationRuleGenerator):
    def __init__(self):
        self.called = False
        self.call_args = None

    def create_rules(self, owner, path, reservation, memory_indices, index):
        self.called = True
        self.call_args = {
            "owner": owner,
            "path": path,
            "reservation": reservation,
            "memory_indices": memory_indices,
            "index": index,
        }
        return []


class FakeTimeCard:
    def __init__(self, memory_index, reservations):
        self.memory_index = memory_index
        self.reservations = reservations


def test_resource_manager_uses_custom_rule_generator():
    tl = Timeline()
    owner = FakeOwner("node1", tl)
    generator = TrackingRuleGenerator()

    reservation = Reservation(
        "node1",
        "node2",
        start_time=0,
        end_time=1e12,
        memory_size=1,
        fidelity=0.9,
        entanglement_number=1,
        identity=0,
    )

    timecards = [
        FakeTimeCard(0, [reservation]),
        FakeTimeCard(1, []),
    ]

    owner.resource_manager.set_rule_generator(generator)
    owner.resource_manager.generate_load_rules(
        path=["node1", "node2"],
        reservation=reservation,
        timecards=timecards,
        memory_array_name=owner.memory_array_name,
    )

    assert generator.called
    assert generator.call_args["owner"] is owner
    assert generator.call_args["path"] == ["node1", "node2"]
    assert generator.call_args["reservation"] is reservation
    assert generator.call_args["memory_indices"] == [0]
    assert generator.call_args["index"] == 0


class NoPurificationRuleGenerator(DefaultReservationRuleGenerator):
    def create_purification_rules(
        self,
        _owner,
        _path,
        _reservation,
        _memory_indices,
        _index,
    ):
        return []


def test_rule_generator_can_override_only_purification_rules():
    tl = Timeline()
    owner = FakeOwner("node1", tl)
    generator = NoPurificationRuleGenerator()

    reservation = Reservation(
        "node1",
        "node2",
        start_time=0,
        end_time=1e12,
        memory_size=1,
        fidelity=0.9,
        entanglement_number=1,
        identity=0,
    )

    rules = generator.create_rules(
        owner=owner,
        path=["node1", "node2"],
        reservation=reservation,
        memory_indices=[0],
        index=0,
    )

    actions = [rule.action for rule in rules]

    assert eg_rule_action_request in actions
    assert ep_rule_action_await not in actions
    assert ep_rule_action_request not in actions
    assert es_rule_action_B in actions
