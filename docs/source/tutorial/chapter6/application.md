# Chapter 6: Application

In this sixth and final tutorial chapter, we will create a custom application to interact with the modules we have already seen. The goal of this tutorial is thus to see how applications are constructed in SeQUeNCe and how they interface with the network.

### Step 1: Building our Custom Application

We'll jump right in and build our custom application class `PeriodicApp`, which will periodically make a request for entanglement with a distant node. Each period, our application will make a request to entangle some variable number of nodes for 1 second.

To start, we will create a constructor for the application that requires
- `node`, the node to which the application is attached,
- `other`, the string name of the other node with which to attempt communications,
- `memory_size`, the number of memories that are requested for entanglement, and
- `target_fidelity`, the desired fidelity of the entangled pairs.

We will also need a function that starts the application's behavior (a method named `start`). In this case, we will make a request to the network manager (using properties specified in the constructor) and schedule another `start` event in the future. The request uses the same interface described in tutorial 5.

```python
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
```

We will also need two more methods for our application to run properly: `get_reserve_res` and `get_memory`. The first method `get_reserve_res` is called by the network manager when the reservation request has returned (as described in tutorial 5). As such, it will take two arguments:
- `reservation`, the reservation object created by and returned to the network manager, and
- `result`, a boolean indicating the success or failure of the reservation request.

For our application, we will only document this success/failure. We have no need to reattempt a request on failure, as we have another attempt already scheduled (via the `start` method).

The other method we require, `get_memory`, is called by the resource manager when memory states are updated. We will check if the memory is properly entangled, print out information on the memory, and then return it to the resource manager as a `RAW` (unentangled) memory.

```python
...

    def get_reserve_res(self, reservation: "Reservation", result: bool):
        if result:
            print("Reservation approved at time", self.node.timeline.now() * 1e-12)
        else:
            print("Reservation failed at time", self.node.timeline.now() * 1e-12)

    def get_memory(self, info: "MemoryInfo"):
        if info.state == "ENTANGLED" and info.remote_node == self.other:
            print("\t{} app received memory {} ENTANGLED at time {}".format(self.node.name, info.index, self.node.timeline.now() * 1e-12))
            self.node.resource_manager.update(None, info.memory, "RAW")
```

### Step 2: Reset Application

To ensure the memories are utilized properly and returned to the memory manager, we will need a second application on the receiving node.
This application will also take in memories and reset them to `"RAW"` if they are properly entangled.
The `get_reserve_res` method will do nothing.

```python
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
```

### Step 3: Building and Running the Simulation

With all of the tools we have seen through the tutorials, creating our network and running the simulation are now a very simple process. We will use the same json file as the last tutorial (`star_network.json`) to automatically build the network, and will add our custom application to one node. Finally, we will begin the application processes with the `start` method.

```python
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

tl.init()
app.start()
tl.run()
```

We should see a completed reservation request approximately every 2 seconds, with entangled memories appearing about 1
second after the request. For example:

```
Reservation approved at time 0.002
	end1 app received memory 13 ENTANGLED at time 1.05277778751
	end1 app received memory 17 ENTANGLED at time 1.08430426251
	end1 app received memory 21 ENTANGLED at time 1.11859467501
	end1 app received memory 0 ENTANGLED at time 1.15936738751
	end1 app received memory 1 ENTANGLED at time 1.19964515001
	end1 app received memory 10 ENTANGLED at time 1.23068431251
	end1 app received memory 1 ENTANGLED at time 1.26570691251
	end1 app received memory 10 ENTANGLED at time 1.29771452501
...
```

