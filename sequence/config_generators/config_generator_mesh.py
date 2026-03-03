"""This module generates JSON config files for a fully-connected mesh network.

Help information may also be obtained using the `-h` flag.

Args:
    net_size (int): number of nodes in the mesh.
    memo_size (int): number of memories per node.
    qc_length (float): distance between nodes (in km).
    qc_atten (float): quantum channel attenuation (in dB/m).
    cc_delay (float): classical channel delay (in ms).

Optional Args:
    -d --directory (str): name of the output directory (default tmp)
    -o --output (str): name of the output file (default out.json).
    -s --stop (float): simulation stop time (in s) (default infinity).
"""

import os
import argparse
import json

from sequence.utils.config_generator import add_default_args, generate_nodes, final_config, router_name_func
from sequence.topology.topology import Topology
from sequence.topology.router_net_topo import RouterNetTopo
from sequence.constants import MILLISECOND


# parse args
parser = argparse.ArgumentParser()
parser.add_argument('net_size', type=int, help='number of network nodes')
parser = add_default_args(parser)
args = parser.parse_args()

output_dict = {}

router_names = [router_name_func(i) for i in range(args.net_size)]
nodes = generate_nodes(router_names, args.memo_size)

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
                    Topology.SEED: seed}
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
                          Topology.DELAY: int(args.cc_delay * MILLISECOND)})
        cchannels.append({Topology.SRC: node2,
                          Topology.DST: bsm_name,
                          Topology.DELAY: int(args.cc_delay * MILLISECOND)})
        cchannels.append({Topology.SRC: bsm_name,
                          Topology.DST: node1,
                          Topology.DELAY: int(args.cc_delay * MILLISECOND)})
        cchannels.append({Topology.SRC: bsm_name,
                          Topology.DST: node2,
                          Topology.DELAY: int(args.cc_delay * MILLISECOND)})
        cchannels.append({Topology.SRC: node1,
                          Topology.DST: node2,
                          Topology.DELAY: int(args.cc_delay * MILLISECOND)})
        cchannels.append({Topology.SRC: node2,
                          Topology.DST: node1,
                          Topology.DELAY: int(args.cc_delay * MILLISECOND)})
        seed += 1

nodes += bsm_nodes
output_dict[Topology.ALL_NODE] = nodes
output_dict[Topology.ALL_Q_CHANNEL] = qchannels
output_dict[Topology.ALL_C_CHANNEL] = cchannels

# write other config options to output dictionary
final_config(output_dict, args)

# write final json
path = os.path.join(args.directory, args.output)
output_file = open(path, 'w')
json.dump(output_dict, output_file, indent=4)

