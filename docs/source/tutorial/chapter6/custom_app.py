from sequence.kernel.process import Process
from sequence.kernel.event import Event
from sequence.topology.router_net_topo import RouterNetTopo

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sequence.topology.node import QuantumRouter


class PeriodicApp():
    def __init__(self, node: "QuantumRouter", other: str, memory_size=25, target_fidelity=0.9):
        self.node = node
        self.node.set_app(self)
        self.other = other
        self.memory_size = memory_size
        self.target_fidelity = target_fidelity

    def start(self):
        now = self.node.timeline.now()
        nm = self.node.network_manager
        nm.request(self.other, start_time=(now + 1e12), end_time=(now + 2e12),
                   memory_size=self.memory_size,
                   target_fidelity=self.target_fidelity)

        # schedule future start
        process = Process(self, "start", [])
        event = Event(now + 2e12, process)
        self.node.timeline.schedule(event)

    def get_reserve_res(self, reservation: "Reservation", result: bool):
        if result:
            print("Reservation approved at time", self.node.timeline.now() * 1e-12)
        else:
            print("Reservation failed at time", self.node.timeline.now() * 1e-12)

    def get_memory(self, info: "MemoryInfo"):
        if info.state == "ENTANGLED" and info.remote_node == self.other:
            print("\t{} app received memory {} ENTANGLED at time {}".format(
                self.node.name, info.index, self.node.timeline.now() * 1e-12))
            self.node.resource_manager.update(None, info.memory, "RAW")


if __name__ == "__main__":
    network_config = "star_network.json"
    num_periods = 5

    network_topo = RouterNetTopo(network_config)
    tl = network_topo.get_timeline()
    tl.stop_time = 2e12 * num_periods
    tl.show_progress = False

    node1 = "end1"
    node2 = "end2"
    for node in network_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
        if node.name == node1:
            node1 = node
        elif node.name == node2:
            node2 = node

    app = PeriodicApp(node1, node2.name)
    
    tl.init()
    app.start()
    tl.run()
