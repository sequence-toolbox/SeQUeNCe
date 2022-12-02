"""This module generates JSON config files for a fully-connected mesh network.

Help information may also be obtained using the `-h` flag.

Args:
    net_size (int): number of nodes in the mesh.
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

import argparse
import json

from generator_utils import add_default_args, get_node_csv, generate_node_procs, generate_nodes, final_config

from sequence.topology.topology import Topology
from sequence.topology.router_net_topo import RouterNetTopo


def router_name_func(i):
    return f"router_{i}"


# parse args
parser = argparse.ArgumentParser()
parser.add_argument('net_size', type=int, help='number of network nodes')
parser = add_default_args(parser)
args = parser.parse_args()

output_dict = {}

# get node names, processes
if args.nodes:
    node_procs = get_node_csv(args.nodes)
else:
    node_procs = generate_node_procs(args.parallel, args.net_size, router_name_func)
router_names = list(node_procs.keys())
nodes = generate_nodes(node_procs, router_names, args.memo_size)

# generate quantum links, classical links, and bsm nodes
qchannels = []
cchannels = []
bsm_nodes = []
seed = 0
for i, node1 in enumerate(router_names):
    for node2 in router_names[i+1:]:
        bsm_name = "BSM_{}_{}".format(node1, node2)
        bsm_node = {Topology.NAME: bsm_name,
                    Topology.TYPE: RouterNetTopo.BSM_NODE,
                    Topology.SEED: seed,
                    RouterNetTopo.GROUP: node_procs[node1]}
        bsm_nodes.append(bsm_node)
        # qchannels
        qchannels.append({Topology.SRC: node1,
                          Topology.DST: bsm_name,
                          Topology.DISTANCE: args.qc_length * 500,
                          Topology.ATTENUATION: args.qc_atten})
        qchannels.append({Topology.SRC: node2,
                          Topology.DST: bsm_name,
                          Topology.DISTANCE: args.qc_length * 500,
                          Topology.ATTENUATION: args.qc_atten})
        # cchannels
        cchannels.append({Topology.SRC: node1,
                          Topology.DST: bsm_name,
                          Topology.DELAY: args.cc_delay * 1e9})
        cchannels.append({Topology.SRC: node2,
                          Topology.DST: bsm_name,
                          Topology.DELAY: args.cc_delay * 1e9})
        cchannels.append({Topology.SRC: bsm_name,
                          Topology.DST: node1,
                          Topology.DELAY: args.cc_delay * 1e9})
        cchannels.append({Topology.SRC: bsm_name,
                          Topology.DST: node2,
                          Topology.DELAY: args.cc_delay * 1e9})
        cchannels.append({Topology.SRC: node1,
                          Topology.DST: node2,
                          Topology.DELAY: args.cc_delay * 1e9})
        cchannels.append({Topology.SRC: node2,
                          Topology.DST: node1,
                          Topology.DELAY: args.cc_delay * 1e9})
        seed += 1

nodes += bsm_nodes
output_dict[Topology.ALL_NODE] = nodes
output_dict[Topology.ALL_Q_CHANNEL] = qchannels
output_dict[Topology.ALL_C_CHANNEL] = cchannels

# write other config options to output dictionary
final_config(output_dict, args)

# write final json
output_file = open(args.output, 'w')
json.dump(output_dict, output_file, indent=4)

