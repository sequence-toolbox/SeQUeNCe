"""This module generates JSON config files for networks in a star configuration.

Help information may also be obtained using the `-h` flag.

Args:
    star_size (int): number of non-center network nodes (network size is star_size+1).
    memo_size (int): number of memories per end node.
    memo_size_center (int): number of memories on the center node.
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

import argparse
import json

from generator_utils import add_default_args, get_node_csv, generate_node_procs, generate_nodes, \
    generate_classical, final_config

from sequence.topology.topology import Topology
from sequence.topology.router_net_topo import RouterNetTopo


def router_name_func(i):
    return f"router_{i}"


# parse args
parser = argparse.ArgumentParser()
parser.add_argument('star_size', type=int, help='number of non-center network nodes')
parser.add_argument('memo_size_center', type=int, help='number of memories on center node')
parser = add_default_args(parser)
args = parser.parse_args()

output_dict = {}

# get csv file (if present) and node names
if args.nodes:
    node_procs = get_node_csv(args.nodes)
    # assume center node is last listed
    center_name = list(node_procs.keys())[-1]
else:
    node_procs = generate_node_procs(args.parallel, args.star_size+1, router_name_func)
    # rename center router
    center_name = "router_center"
    proc = node_procs[router_name_func(args.star_size)]
    del node_procs[router_name_func(args.star_size)]
    node_procs[center_name] = proc
router_names = list(node_procs.keys())

# generate nodes, with middle having different num
nodes = generate_nodes(node_procs, router_names, args.memo_size)
for node in nodes:
    if node[Topology.NAME] == center_name:
        node[RouterNetTopo.MEMO_ARRAY_SIZE] = args.memo_size_center
        break

# generate quantum links
qchannels = []
cchannels = []
bsm_names = ["BSM_" + str(i) for i in range(args.star_size)]
bsm_nodes = [{Topology.NAME: bsm_name,
              Topology.TYPE: RouterNetTopo.BSM_NODE,
              Topology.SEED: i}
              for i, bsm_name in enumerate(bsm_names)]
if args.parallel:
    for i in range(args.star_size):
        bsm_nodes[i][RouterNetTopo.GROUP] = nodes[i][RouterNetTopo.GROUP]

for node_name, bsm_name in zip(router_names, bsm_names):
    # qchannels
    qchannels.append({Topology.SRC: node_name,
                      Topology.DST: bsm_name,
                      Topology.DISTANCE: args.qc_length * 500,
                      Topology.ATTENUATION: args.qc_atten})
    qchannels.append({Topology.SRC: center_name,
                      Topology.DST: bsm_name,
                      Topology.DISTANCE: args.qc_length * 500,
                      Topology.ATTENUATION: args.qc_atten})
    # cchannels
    cchannels.append({Topology.SRC: node_name,
                      Topology.DST: bsm_name,
                      Topology.DELAY: args.cc_delay * 1e9})
    cchannels.append({Topology.SRC: center_name,
                      Topology.DST: bsm_name,
                      Topology.DELAY: args.cc_delay * 1e9})
    cchannels.append({Topology.SRC: bsm_name,
                      Topology.DST: node_name,
                      Topology.DELAY: args.cc_delay * 1e9})
    cchannels.append({Topology.SRC: bsm_name,
                      Topology.DST: center_name,
                      Topology.DELAY: args.cc_delay * 1e9})

output_dict[Topology.ALL_NODE] = nodes + bsm_nodes
output_dict[Topology.ALL_Q_CHANNEL] = qchannels

# generate classical links
router_cchannels = generate_classical(router_names, args.cc_delay)
cchannels += router_cchannels
output_dict[Topology.ALL_C_CHANNEL] = cchannels

# write other config options to output dictionary
final_config(output_dict, args)

# write final json
output_file = open(args.output, 'w')
json.dump(output_dict, output_file, indent=4)

