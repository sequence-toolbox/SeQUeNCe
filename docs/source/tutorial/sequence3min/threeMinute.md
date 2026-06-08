# SeQUeNCe in 3 Minutes

In this introductory three minute tutorial, we will briefly cover the neccesary basics of SeQUeNCe. We will request a one entanglment pair between two quantum routers, Alice and Bob. The goal of this tutorial is to gain a general understanding of SeQUeNCe's topology generator to create a two-node network, attach a single application to the routers, and submit an entangment request through the network manager. 

### Step 1: Generate the Two-Node Topology

Before building the simulation, we first need a network configuration file that defines the two nodes and the channels between them. For this tutorial, we will use SeQUeNCe's built-in topology generator, which is implemented in [config_generator_cli.py](../../../../sequence/utils/config_generator_cli.py).

The following command generates a simple two-node linear topology and saves it as a JSON file:

```bash
generate-topology linear 2 --memory-size 1 --output two_node_topology.json --directory docs/source/tutorial/threeMinTutorial
```

This command creates a topology with two quantum routers connected through a Bell-state measurement node. The generated file, `two_node_topology.json`, can then be loaded directly by SeQUeNCe when running the tutorial simulation.

If you are working in a different directory, change the value passed to `--directory` so that the JSON file is saved in the same location as your tutorial files. Alternatively, if you downloaded SeQUeNCe with the tutorial files included, you may use the provided `two_node_topology.json` file directly instead of regenerating it.

### Step 2: Import the Required Modules

We begin by importing the request application, the router-network topology class, and the entanglement-generation protocol controls. The `RequestApp` class provides a simple application interface for making an entanglement request between two routers.

```python
from sequence.app.request_app import RequestApp
from sequence.topology.router_net_topo import RouterNetTopo
from sequence.constants import SINGLE_HERALDED
from sequence.entanglement_management.generation import EntanglementGenerationA, EntanglementGenerationB
```

This tutorial uses the single-heralded entanglement-generation protocol. Because the generated topology uses a `SingleHeraldedBSM`, we set both the router-side and BSM-side generation protocols to `SINGLE_HERALDED` before loading the network.

```python
EntanglementGenerationA.set_global_type(SINGLE_HERALDED)
EntanglementGenerationB.set_global_type(SINGLE_HERALDED)
```
### Step 3: Load the Network

Next, we load the generated JSON file into a `RouterNetTopo`. This constructs the timeline, quantum routers, BSM node, and communication channels defined in the topology file.

```python
network_config = "docs/source/tutorial/threeMinTutorial/two_node_topology.json"

network_topo = RouterNetTopo(network_config)
tl = network_topo.get_timeline()
tl.stop_time = 3e12
tl.show_progress = False
```

The stop time is given in picoseconds. In this example, `3e12` runs the simulation for 3 seconds of simulated time.

### Step 4: Select Alice and Bob

The topology generator names the two routers `router_0` and `router_1`. In this tutorial, we will refer to these nodes as Alice and Bob.

```python
alice_node_name = "router_0"
bob_node_name = "router_1"
alice = bob = None

for router in network_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
    if router.name == alice_node_name:
        alice = router
    elif router.name == bob_node_name:
        bob = router
```

This loop searches the topology for the two quantum routers and stores references to them. These node objects are then used to attach applications and make the entanglement request.

### Step 5: Attach the Applications

Each quantum router needs an application object. The application on Alice will make the request, while the application on Bob allows Bob's node to receive the corresponding reservation and memory updates.

```python
memory_size = 1
target_fidelity = 0.6

alice_app = RequestApp(alice)
bob_app = RequestApp(bob)

print("Alice is using node:", alice.name)
print("Bob is using node:", bob.name)
```

The `memory_size` value specifies the number of memory pairs requested. The `target_fidelity` value specifies the minimum desired fidelity for the generated entanglement.

### Step 6: Run the Simulation

Finally, we initialize the timeline, start Alice's request, and run the simulation.

```python
tl.init()
alice_app.start(bob_node_name, int(1e12), int(2e12), memory_size, target_fidelity)
tl.run()
```

The request asks Alice to establish entanglement with Bob between 1 second and 2 seconds of simulated time. After the timeline finishes running, we can check whether Alice received any entangled memories.

```python
if alice_app.memory_counter > 0:
    print("Entanglement established between Alice and Bob")
    print("Alice received", alice_app.memory_counter, "entangled memory pair(s)")
else:
    print("No entanglement was established between Alice and Bob")
```

If the simulation succeeds, the output should show that Alice and Bob were found, followed by a message confirming that entanglement was established. The exact number of entangled memory pairs may vary between runs.

```text
Alice is using node: router_0
Bob is using node: router_1
Entanglement established between Alice and Bob
Alice received 66 entangled memory pair(s)
```