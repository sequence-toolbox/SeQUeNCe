from numpy import random

from sequence.kernel.timeline import Timeline
from sequence.kernel.process import Process
from sequence.kernel.event import Event
from sequence.topology.topology import Topology

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
        nm.request(node2, start_time=(now + 1e12), end_time=(now + 2e12),
                   memory_size=self.memory_size, target_fidelity=self.target_fidelity)
        
        # schedule future start
        process = Process(self, "start", [])
        event = Event(now + 2e12, process)
        self.node.timeline.schedule(event)

    def get_reserve_res(self, reservation: "Reservation", result: bool):
        if result:
            print("reservation approved at time", self.node.timeline.now() * 1e-12)
        else:
            print("reservation failed at time", self.node.timeline.now() * 1e-12)

    def get_memory(self, info: "MemoryInfo"):
        if info.state == "ENTANGLED" and info.remote_node == self.other:
            print("\treceived memory {} at time {}".format(info.index, self.node.timeline.now() * 1e-12))
            self.node.resource_manager.update(None, info.memory, "RAW")


if __name__ == "__main__":
    random.seed(0)
    network_config = "star_network.json"

    num_periods = 5
    tl = Timeline(2e12 * num_periods)
    network_topo = Topology("network_topo", tl)
    network_topo.load_config(network_config)

    node1 = "end1"
    node2 = "end2"
    app = PeriodicApp(network_topo.nodes[node1], node2)
    
    tl.init()
    app.start()
    tl.run()
