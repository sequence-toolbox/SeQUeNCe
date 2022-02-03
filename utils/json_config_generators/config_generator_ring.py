"""This module generates JSON config files for networks in a ring configuration.

Help information may also be obtained using the `-h` flag.

Args:
    ring_size (int): number of nodes in the network ring.
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

from generator_utils import add_default_args, get_node_csv, generate_node_procs, generate_nodes, \
    generate_classical, final_config

from sequence.topology.topology import Topology
from sequence.topology.router_net_topo import RouterNetTopo


def router_name_func(i):
    return f"router_{i}"


# parse args
parser = argparse.ArgumentParser()
parser.add_argument('ring_size', type=int, help='number of network nodes')
parser = add_default_args(parser)
args = parser.parse_args()

output_dict = {}

# get node names, processes
if args.nodes:
    node_procs = get_node_csv(args.nodes)
else:
    node_procs = generate_node_procs(args.parallel, args.ring_size, router_name_func)
router_names = list(node_procs.keys())
nodes = generate_nodes(node_procs, router_names, args.memo_size)

# generate quantum links and bsm connections
qchannels = []
cchannels = []
bsm_names = ["BSM_{}_{}".format(i % args.ring_size, (i+1) % args.ring_size)
             for i in range(args.ring_size)]
bsm_nodes = [{Topology.NAME: bsm_name,
              Topology.TYPE: RouterNetTopo.BSM_NODE,
              Topology.SEED: i}
             for i, bsm_name in enumerate(bsm_names)]
if args.parallel:
    for i in range(args.ring_size):
        bsm_nodes[i][RouterNetTopo.GROUP] = int(i // (args.ring_size / int(args.parallel[2])))

for i, bsm_name in enumerate(bsm_names):
    # qchannels
    qchannels.append({Topology.SRC: router_names[i % args.ring_size],
                      Topology.DST: bsm_name,
                      Topology.DISTANCE: args.qc_length * 500,
                      Topology.ATTENUATION: args.qc_atten})
    qchannels.append({Topology.SRC: router_names[(i + 1) % args.ring_size],
                      Topology.DST: bsm_name,
                      Topology.DISTANCE: args.qc_length * 500,
                      Topology.ATTENUATION: args.qc_atten})
    # cchannels
    cchannels.append({Topology.SRC: router_names[i % args.ring_size],
                      Topology.DST: bsm_name,
                      Topology.DELAY: args.cc_delay * 1e9})
    cchannels.append({Topology.SRC: router_names[(i + 1) % args.ring_size],
                      Topology.DST: bsm_name,
                      Topology.DELAY: args.cc_delay * 1e9})
    cchannels.append({Topology.SRC: bsm_name,
                      Topology.DST: router_names[i % args.ring_size],
                      Topology.DELAY: args.cc_delay * 1e9})
    cchannels.append({Topology.SRC: bsm_name,
                      Topology.DST: router_names[(i + 1) % args.ring_size],
                      Topology.DELAY: args.cc_delay * 1e9})

nodes += bsm_nodes
output_dict[Topology.ALL_NODE] = nodes
output_dict[Topology.ALL_Q_CHANNEL] = qchannels

# generate classical links
# generate classical links
router_cchannels = generate_classical(router_names, args.cc_delay)
cchannels += router_cchannels
output_dict[Topology.ALL_C_CHANNEL] = cchannels

# write other config options to output dictionary
final_config(output_dict, args)

# write final json
output_file = open(args.output, 'w')
json.dump(output_dict, output_file, indent=4)

