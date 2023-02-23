from sequence.topology.router_net_topo import RouterNetTopo
from sequence.app.random_request import RandomRequestApp
import time


topo_full = RouterNetTopo("two_node.json")
topo_prob = RouterNetTopo("two_node_prob.json")

# do simulation of two node
tl = topo_full.get_timeline()
routers = topo_full.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER)
router_names = [node.name for node in routers]
others = router_names[1:]
app = RandomRequestApp(routers[0], others, 0,
                       min_dur=int(1e13), max_dur=int(2e13), min_size=10,
                       max_size=25, min_fidelity=0.8, max_fidelity=1.0)
app.start()

tl.init()
tick = time.time()
tl.run()
total_time = time.time() - tick
print("TIME (original):", total_time)
print("\tmemories: {}".format(app.memory_counter))

# do simulation of two node with prob
tl = topo_prob.get_timeline()
routers = topo_prob.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER)
router_names = [node.name for node in routers]
others = router_names[1:]
app = RandomRequestApp(routers[0], others, 0,
                       min_dur=int(1e13), max_dur=int(2e13), min_size=10,
                       max_size=25, min_fidelity=0.8, max_fidelity=1.0)
app.start()

tl.init()
tick = time.time()
tl.run()
total_time = time.time() - tick
print("TIME (probablistic):", total_time)
print("\tmemories: {}".format(app.memory_counter))
