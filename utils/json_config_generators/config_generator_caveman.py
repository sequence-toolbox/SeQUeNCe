"""This module generates JSON config files for networks in a caveman graph configuration.

More information may be found here: https://mathworld.wolfram.com/CavemanGraph.html
Help information may also be obtained using the `-h` flag.

Args:
    l (int): number of cliques (clusters) in the graph.
    k (int): number of nodes per clique.
    memo_size (int): number of memories per node.
    qc_length (float): distance between nodes (in km).
    qc_atten (float): quantum channel attenuation (in dB/m).
    cc_delay (float): classical channel delay (in ms).

Optional Args:
    -o --output (str): name of the output file (default out.json).
    -s --stop (float): simulation stop time (in s) (default infinity).
    -p --parallel: sets simulation as parallel and requires addition args:
        server ip (str): IP address of quantum manager server.
        server port (int): port quantum manager server is attached to.
        num. processes (int): number of processes to use for simulation.
        sync/async (bool): denotes if timelines should be synchronous (true) or not (false).
        lookahead (int): simulation lookahead time for timelines (in ps).
    -n --nodes (str): path to csv file providing process information for nodes.
"""

import networkx as nx
import argparse
import json

from generator_utils import *

from sequence.topology.topology import Topology


def router_name_func(i):
    return f"router_{i}"


def bsm_name_func(i, j):
    return f"BSM_{i}_{j}"


parser = argparse.ArgumentParser()
parser.add_argument('l', type=int, help="l (int) – Number of cliques")
parser.add_argument('k', type=int, help="k (int) – Size of cliques")
add_default_args(parser)
args = parser.parse_args()

graph = nx.connected_caveman_graph(args.l, args.k)
mapping = {}
NODE_NUM = args.l * args.k
for i in range(NODE_NUM):
    mapping[i] = router_name_func(i)
nx.relabel_nodes(graph, mapping, copy=False)

output_dict = {}

# get node names, processes
if args.nodes:
    node_procs = get_node_csv(args.nodes)
else:
    node_procs = generate_node_procs(args.parallel, NODE_NUM, router_name_func)
router_names = list(node_procs.keys())
nodes = generate_nodes(node_procs, router_names, args.memo_size)

cchannels, qchannels, bsm_nodes = generate_bsm_links(graph, node_procs, args, bsm_name_func)
nodes += bsm_nodes
output_dict[Topology.ALL_NODE] = nodes
output_dict[Topology.ALL_Q_CHANNEL] = qchannels

router_cchannels = generate_classical(router_names, args.cc_delay)
cchannels += router_cchannels
output_dict[Topology.ALL_C_CHANNEL] = cchannels

final_config(output_dict, args)

# write final json
output_file = open(args.output, 'w')
json.dump(output_dict, output_file, indent=4)
