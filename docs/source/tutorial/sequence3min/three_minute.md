# SeQUeNCe in 3 Minutes

In this introductory three-minute tutorial, we will briefly cover the necessary basics of SeQUeNCe. We will request entanglement pairs between two quantum routers, Alice and Bob. The goal of this tutorial is to gain a basic usage of SeQUeNCe.

The whole tutorial can be found at <a href="https://github.com/sequence-toolbox/SeQUeNCe/blob/master/docs/source/tutorial/sequence3min/three_minute.py" target="_blank" rel="noopener">three_minute.py</a>, and is broken down into 5 steps, discussed in detail in the following sections.


### Step 1: Generate the Two-Node Topology

Before building the simulation, we first need a network configuration file that defines the two nodes and the channels between them. For this tutorial, we will use SeQUeNCe's built-in topology generator, which is implemented in <a href="https://github.com/sequence-toolbox/SeQUeNCe/blob/master/sequence/utils/config_generator_cli.py" target="_blank" rel="noopener">config_generator_cli.py</a>. 
The `generate-topology` command-line executable is installed automatically when SeQUeNCe is installed, so it is available from the same Python environment without any additional setup. 

```bash
generate-topology linear 2 --memory-size 1 --output two_node.json --directory docs/source/tutorial/sequence3min
```

This command creates a topology with two quantum routers connected through a Bell-state measurement node. The generated file, `two_node.json` is under the directory `docs/source/tutorial/sequence3min`. 
If you want to change directory, simply change the value passed to `--directory`. 
Alternatively, if you downloaded SeQUeNCe with the tutorial files included, you may use the provided `two_node.json` file directly instead of regenerating it.

### Step 2: Import the Required Modules

We begin by importing the request application, the router-network topology class, and the entanglement-generation protocol controls. The `RequestApp` class provides a simple application interface for making an entanglement request between two routers.

```python
from sequence.app.request_app import RequestApp
from sequence.topology.router_net_topo import RouterNetTopo
from sequence.constants import SINGLE_HERALDED, SECOND
from sequence.entanglement_management.generation import EntanglementGenerationA, EntanglementGenerationB
```

This tutorial uses the single-heralded entanglement-generation protocol. We set both the router-side and BSM-side generation protocols to `SINGLE_HERALDED` before loading the network.

```python
EntanglementGenerationA.set_global_type(SINGLE_HERALDED)
EntanglementGenerationB.set_global_type(SINGLE_HERALDED)
```
### Step 3: Load the Network

Next, we load the generated JSON file into a `RouterNetTopo`. This constructs the timeline, quantum routers, BSM node, and communication channels defined in the topology file.

```python
network_topo = RouterNetTopo(config_source="docs/source/tutorial/sequence3min/two_node.json")
tl = network_topo.get_timeline()
```

### Step 4: Attach the Application Module to the Nodes

Loop over the node objects, and then attach the application to the nodes and make the entanglement request.

```python
name_to_app = {}
for router in network_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
    name_to_app[router.name] = RequestApp(router)
```

### Step 5: Run the Simulation

Finally, we initialize the timeline, start Alice's request to Bob, and run the simulation.

```python
tl.init()
alice = "router_0"
bob = "router_1"
name_to_app[alice].start(responder=bob, start_t=1 * SECOND, end_t=2.5 * SECOND, memo_size=1, fidelity=0.8)
tl.run()
```

The request asks Alice to establish entanglement with Bob between `1` second and `2.5` seconds of simulation time. It uses `1` quantum memory at Alice and Bob and requires the end-to-end fidelity to be above `0.8`.
After the timeline finishes running, we can check the number of entangled pairs between Alice and Bob and the throughput.

```python
print(f"Entangled pair count between Alice and Bob: {name_to_app[alice].memory_counter}")
print(f"The throughput is {name_to_app[alice].get_throughput()} pairs per second")
```

You will see the following:

```text
Entangled pair count between Alice and Bob: 105
The throughput is 70.0 pairs per second
```
