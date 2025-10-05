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
"""

import networkx as nx
import argparse
import json
import os

from sequence.utils.config_generator import *
from sequence.topology.topology import Topology



parser = argparse.ArgumentParser()
parser.add_argument('l', type=int, help="l (int) - Number of cliques")
parser.add_argument('k', type=int, help="k (int) - Size of cliques")
add_default_args(parser)
args = parser.parse_args()

graph = nx.connected_caveman_graph(args.l, args.k)
mapping = {}
NODE_NUM = args.l * args.k
for i in range(NODE_NUM):
    mapping[i] = router_name_func(i)
nx.relabel_nodes(graph, mapping, copy=False)

output_dict = {}

router_names = [router_name_func(i) for i in range(NODE_NUM)]
nodes = generate_nodes(router_names, args.memo_size)

cchannels, qchannels, bsm_nodes = generate_bsm_links(graph, args, bsm_name_func)
nodes += bsm_nodes
output_dict[Topology.ALL_NODE] = nodes
output_dict[Topology.ALL_Q_CHANNEL] = qchannels

router_cchannels = generate_classical(router_names, args.cc_delay)
cchannels += router_cchannels
output_dict[Topology.ALL_C_CHANNEL] = cchannels

final_config(output_dict, args)

# write final json
path = os.path.join(args.directory, args.output)
output_file = open(path, 'w')
json.dump(output_dict, output_file, indent=4)
