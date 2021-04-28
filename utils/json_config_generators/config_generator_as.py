import networkx as nx
import argparse
import json
import pandas as pd
import matplotlib.pyplot as plt
import random

from simanneal import Annealer

SEED = 1
random.seed(SEED)

from sequence.topology.topology import Topology
from sequence.topology.router_net_topo import RouterNetTopo


def router_name_func(i):
    return f"router_{i}"


def bsm_name_func(i, j):
    return f"BSM_{i}_{j}"


def get_partition(graph, GROUP_NUM):
    all_path = list(nx.all_pairs_shortest_path(graph))
    net_size = len(graph.nodes)

    class State():
        def __init__(self, group, alpha):
            assert 0 < alpha <= 1
            self.group = group
            self.alpha = alpha
            self.reverse_map_group = {}
            for i, g in enumerate(self.group):
                for n in g:
                    self.reverse_map_group[n] = i

            self.e = 0
            for src, paths in all_path:
                for dst in paths:
                    for node in paths[dst]:
                        if self.reverse_map_group[src] != \
                                self.reverse_map_group[node]:
                            self.e += (self.alpha ** len(paths[dst]))
                            break

        def get_energy(self):
            return self.e

        def move(self):
            group = self.group
            r_group = self.reverse_map_group

            g1, g2 = random.choices(list(range(len(group))), k=2)
            index1, index2 = random.choices(list(range(len(group[g1]))), k=2)
            n1, n2 = group[g1][index1], group[g2][index2]

            group[g1][index1], group[g2][index2] = n2, n1
            r_group[group[g1][index1]] = g1
            r_group[group[g2][index2]] = g2

            self.e = 0
            for src, paths in all_path:
                for dst in paths:
                    for node in paths[dst]:
                        if self.reverse_map_group[src] != \
                                self.reverse_map_group[node]:
                            self.e += (self.alpha ** len(paths[dst]))
                            break

    class Partition(Annealer):
        def move(self):
            self.state.move()

        def energy(self):
            return self.state.get_energy()

    group = [[] for _ in range(GROUP_NUM)]
    for i in range(net_size):
        index = i // (net_size // GROUP_NUM)
        group[index].append(router_name_func(i))

    ini_state = State(group, 0.5)
    partition = Partition(ini_state)
    auto_schedule = partition.auto(minutes=1)

    partition.set_schedule(auto_schedule)
    state, energy = partition.anneal()
    print(state.group)
    return state.group


parser = argparse.ArgumentParser()
parser.add_argument('net_size', type=int,
                    help="net_size (int) – Number of routers")
parser.add_argument('seed', type=int,
                    help="seed (int) – Indicator of random number generation state. ")
parser.add_argument('group_n', type=int, help="group_n (int) - Number of "
                                              "groups for parallel simulation")
parser.add_argument('memo_size', type=int, help='number of memories per node')
parser.add_argument('qc_length', type=float,
                    help='distance between nodes (in km)')
parser.add_argument('qc_atten', type=float,
                    help='quantum channel attenuation (in dB/m)')
parser.add_argument('cc_delay', type=float,
                    help='classical channel delay (in ms)')
parser.add_argument('-o', '--output', type=str, default='out.json',
                    help='name of output config file')
parser.add_argument('-s', '--stop', type=float, default=float('inf'),
                    help='stop time (in s)')
parser.add_argument('-p', '--parallel', nargs=5,
                    help='optional parallel arguments: server ip, server port,'
                         ' num. processes, sync/async, lookahead')
parser.add_argument('-n', '--nodes', type=str,
                    help='path to csv file to provide process for each node')
args = parser.parse_args()

graph = nx.random_internet_as_graph(args.net_size, args.seed)
mapping = {}
NODE_NUM = args.net_size
for i in range(NODE_NUM):
    mapping[i] = router_name_func(i)
nx.relabel_nodes(graph, mapping, copy=False)
# nx.draw(graph, with_labels=True)
# plt.show()

output_dict = {}

node_procs = {}
router_names = []

if args.nodes:
    # TODO: add length/proc assertions
    df = pd.read_csv(args.nodes)
    for name, group in zip(df['name'], df['group']):
        node_procs[name] = group
        router_names.append(name)
else:
    groups = get_partition(graph, int(args.parallel[2]))
    for i, g in enumerate(groups):
        for name in g:
            node_procs[name] = i
    print(node_procs)

router_names = list(node_procs.keys())
nodes = [{Topology.NAME: name,
          Topology.TYPE: RouterNetTopo.QUANTUM_ROUTER,
          Topology.SEED: i,
          RouterNetTopo.MEMO_ARRAY_SIZE: args.memo_size,
          RouterNetTopo.GROUP: node_procs[name]}
         for i, name in enumerate(router_names)]

cchannels = []
qchannels = []
bsm_nodes = []
for i, node_pair in enumerate(graph.edges):
    node1, node2 = node_pair
    bsm_name = bsm_name_func(node1, node2)
    bsm_node = {Topology.NAME: bsm_name,
                Topology.TYPE: RouterNetTopo.BSM_NODE,
                Topology.SEED: i,
                RouterNetTopo.GROUP: node_procs[node1]}
    bsm_nodes.append(bsm_node)

    for node in node_pair:
        qchannels.append({Topology.SRC: node,
                          Topology.DST: bsm_name,
                          Topology.DISTANCE: args.qc_length * 500,
                          Topology.ATTENUATION: args.qc_atten})

    for node in node_pair:
        cchannels.append({Topology.SRC: bsm_name,
                          Topology.DST: node,
                          Topology.DELAY: args.cc_delay * 1e9})

        cchannels.append({Topology.SRC: node,
                          Topology.DST: bsm_name,
                          Topology.DELAY: args.cc_delay * 1e9})

nodes += bsm_nodes
output_dict[Topology.ALL_NODE] = nodes
output_dict[Topology.ALL_Q_CHANNEL] = qchannels

for node1 in router_names:
    for node2 in router_names:
        if node1 == node2:
            continue
        cchannels.append({Topology.SRC: node1,
                          Topology.DST: node2,
                          Topology.DELAY: args.cc_delay * 1e9})

output_dict[Topology.ALL_C_CHANNEL] = cchannels
output_dict[Topology.STOP_TIME] = args.stop * 1e12
if args.parallel:
    output_dict[RouterNetTopo.IS_PARALLEL] = True
    output_dict[RouterNetTopo.PROC_NUM] = int(args.parallel[2])
    output_dict[RouterNetTopo.IP] = args.parallel[0]
    output_dict[RouterNetTopo.PORT] = int(args.parallel[1])
    output_dict[RouterNetTopo.LOOKAHEAD] = int(args.parallel[4])
    if args.parallel[3] == "true":
        # set all to synchronous
        output_dict[RouterNetTopo.ALL_GROUP] = \
            [{RouterNetTopo.TYPE: RouterNetTopo.SYNC} for _ in
             range(int(args.parallel[2]))]
    else:
        output_dict[RouterNetTopo.ALL_GROUP] = \
            [{RouterNetTopo.TYPE: RouterNetTopo.ASYNC}] * int(args.parallel[2])
else:
    output_dict[RouterNetTopo.IS_PARALLEL] = False

# write final json
output_file = open(args.output, 'w')
json.dump(output_dict, output_file, indent=4)
