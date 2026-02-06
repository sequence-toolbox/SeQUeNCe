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
from sequence.constants import *


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
        bsm_node = {NAME: bsm_name,
                    TYPE: BSM_NODE,
                    SEED: seed}
        bsm_nodes.append(bsm_node)
        # qchannels
        qchannels.append({SRC: node1,
                          DST: bsm_name,
                          DISTANCE: args.qc_length * 500,
                          ATTENUATION: args.qc_atten})
        qchannels.append({SRC: node2,
                          DST: bsm_name,
                          DISTANCE: args.qc_length * 500,
                          ATTENUATION: args.qc_atten})
        # cchannels
        cchannels.append({SRC: node1,
                          DST: bsm_name,
                          DELAY: int(args.cc_delay * MILLISECOND)})
        cchannels.append({SRC: node2,
                          DST: bsm_name,
                          DELAY: int(args.cc_delay * MILLISECOND)})
        cchannels.append({SRC: bsm_name,
                          DST: node1,
                          DELAY: int(args.cc_delay * MILLISECOND)})
        cchannels.append({SRC: bsm_name,
                          DST: node2,
                          DELAY: int(args.cc_delay * MILLISECOND)})
        cchannels.append({SRC: node1,
                          DST: node2,
                          DELAY: int(args.cc_delay * MILLISECOND)})
        cchannels.append({SRC: node2,
                          DST: node1,
                          DELAY: int(args.cc_delay * MILLISECOND)})
        seed += 1

nodes += bsm_nodes
output_dict[ALL_NODE] = nodes
output_dict[ALL_Q_CHANNEL] = qchannels
output_dict[ALL_C_CHANNEL] = cchannels

# write other config options to output dictionary
final_config(output_dict, args)

# write final json
path = os.path.join(args.directory, args.output)
output_file = open(path, 'w')
json.dump(output_dict, output_file, indent=4)

