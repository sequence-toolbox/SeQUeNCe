from sequence.kernel.process import Process
from sequence.kernel.event import Event
from sequence.topology.router_net_topo import RouterNetTopo

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sequence.topology.node import QuantumRouter


class PeriodicApp:
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


class ResetApp:
    def __init__(self, node, other_node_name, target_fidelity=0.9):
        self.node = node
        self.node.set_app(self)
        self.other_node_name = other_node_name
        self.target_fidelity = target_fidelity

    def get_other_reservation(self, reservation):
        """called when receiving the request from the initiating node.

        For this application, we do not need to do anything.
        """

        pass

    def get_memory(self, info):
        """Similar to the get_memory method of the main application.

        We check if the memory info meets the request first,
        by noting the remote entangled memory and entanglement fidelity.
        We then free the memory for future use.
        """

        if (info.state == "ENTANGLED" and info.remote_node == self.other_node_name
                and info.fidelity > self.target_fidelity):
            self.node.resource_manager.update(None, info.memory, "RAW")


if __name__ == "__main__":
    network_config = "star_network.json"
    num_periods = 5

    network_topo = RouterNetTopo(network_config)
    tl = network_topo.get_timeline()
    tl.stop_time = 2e12 * num_periods
    tl.show_progress = False

    start_node_name = "end1"
    end_node_name = "end2"
    node1 = node2 = None

    for router in network_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
        if router.name == start_node_name:
            node1 = router
        elif router.name == end_node_name:
            node2 = router

    app = PeriodicApp(node1, end_node_name)
    reset_app = ResetApp(node2, start_node_name)
    
    tl.init()

    for name, component in tl.entities.items():
        print("{}: {}".format(name, component.get_generator()))

    app.start()
    tl.run()
