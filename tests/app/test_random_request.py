from sequence.app.random_request import RandomRequestApp
from sequence.kernel.timeline import Timeline
from sequence.topology.node import QuantumRouter


class FakeNode(QuantumRouter):
    def __init__(self, name, tl):
        super().__init__(name, tl)
        self.reserve_log = []

    def reserve_net_resource(self, responder: str, start_time: int, end_time: int, memory_size: int,
                             target_fidelity: float) -> None:
        self.reserve_log.append(responder)


def test_RandomRequestApp_update_last_rsvp_metrics():
    tl = Timeline()
    node = QuantumRouter("n1", tl)
    app = RandomRequestApp(node, [])
    app._update_last_rsvp_metrics()
    assert len(app.get_throughput()) == 0
    app.cur_reserve = ["n2", 10, 20, 5, 0.9]
    app.memory_counter = 10
    tl.time = 20
    assert app.request_time == 0
    app._update_last_rsvp_metrics()
    assert len(app.get_throughput()) == 1 and app.get_throughput()[0] == 1
    assert app.cur_reserve == []
    assert app.request_time == 20
    assert app.memory_counter == 0


def test_RandomRequestApp_start():
    tl = Timeline()
    node = FakeNode("n1", tl)
    app = RandomRequestApp(node, ["n2", "n3"])
    for _ in range(1000):
        app.start()
        assert app.cur_reserve[0] == node.reserve_log[-1]

    counter = 0
    for responder in node.reserve_log:
        if responder == "n2":
            counter += 1
    assert abs(counter / (1000 - counter) - 1) < 0.1


def test_RandomRequestApp_get_reserve_res():
    tl = Timeline()
    tl.time = 6
    node = FakeNode("n1", tl)
    app = RandomRequestApp(node, ["n2", "n3"])
    app.cur_reserve = ["n3", 10, 20, 5, 0.9]
    app.request_time = 5
    app.get_reserve_res(True)
    assert app.get_wait_time()[0] == 5
    assert len(tl.events) == 1 and tl.events.data[0].time == 21

    tl = Timeline()
    tl.time = 6
    node = FakeNode("n1", tl)
    app = RandomRequestApp(node, ["n2", "n3"])
    app.cur_reserve = ["n3", 10, 20, 5, 0.9]
    app.request_time = 5
    app.get_reserve_res(False)
    assert len(app.get_wait_time()) == 0
    assert app.cur_reserve[-1] != 0.9
    assert len(node.reserve_log) == 1


def test_RandomRequestApp_get_memory():
    tl = Timeline()
    node = FakeNode("n1", tl)
    app = RandomRequestApp(node, ["n2", "n3"])
    app.cur_reserve = ["n2", 0, 100, 0.85]

    node.memory_array[0].entangled_memory["node_id"] = "n2"
    node.memory_array[0].entangled_memory["memo_id"] = "1"
    node.memory_array[0].fidelity = 0.9
    node.resource_manager.update(None, node.memory_array[0], "ENTANGLED")
    app.get_memory(node.resource_manager.memory_manager[0])
    assert node.resource_manager.memory_manager[0].state == "RAW"
    assert node.memory_array[0].entangled_memory["node_id"] == None
    assert node.memory_array[0].fidelity == node.memory_array[0].raw_fidelity

    node.memory_array[1].entangled_memory["node_id"] = "n3"
    node.memory_array[1].entangled_memory["memo_id"] = "1"
    node.memory_array[1].fidelity = 0.9
    node.resource_manager.update(None, node.memory_array[1], "ENTANGLED")
    app.get_memory(node.resource_manager.memory_manager[1])
    assert node.resource_manager.memory_manager[1].state == "ENTANGLED"

    node.memory_array[2].entangled_memory["node_id"] = "n2"
    node.memory_array[2].entangled_memory["memo_id"] = "1"
    node.memory_array[2].fidelity = 0.84
    node.resource_manager.update(None, node.memory_array[2], "ENTANGLED")
    app.get_memory(node.resource_manager.memory_manager[2])
    assert node.resource_manager.memory_manager[2].state == "ENTANGLED"
