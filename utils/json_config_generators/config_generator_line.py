"""This module generates JSON config files for networks in a linear configuration.

Help information may also be obtained using the `-h` flag.

Args:
    linear_size (int): number of nodes in the graph.
    memo_size (int): number of memories per node.
    qc_length (float): distance between nodes (in km).
    qc_atten (float): quantum channel attenuation (in dB/m).
    cc_delay (float): classical channel delay (in ms).

Optional Args:
    -d --directory (str): name of the output directory (default tmp)
    -o --output (str): name of the output file (default out.json).
    -s --stop (float): simulation stop time (in s) (default infinity).
"""

import argparse
import json
import os

from sequence.utils.config_generator import add_default_args, generate_nodes, generate_classical, final_config, router_name_func
from sequence.constants import *

# example: python config_generator_line.py 2 10 10 0.0002 1 -d config -o line_2.json -s 10 -gf 0.99 -mf 0.99

parser = argparse.ArgumentParser()
parser.add_argument('linear_size', type=int, help='number of network nodes')
parser = add_default_args(parser)
args = parser.parse_args()

output_dict = {}


router_names = [router_name_func(i) for i in range(args.linear_size)]
nodes = generate_nodes(router_names, args.memo_size)

# generate bsm nodes
bsm_names = ["BSM_{}_{}".format(i, i + 1)
             for i in range(args.linear_size - 1)]
bsm_nodes = [{NAME: bsm_name,
              TYPE: BSM_NODE,
              SEED: i}
             for i, bsm_name in enumerate(bsm_names)]

nodes += bsm_nodes
output_dict[ALL_NODE] = nodes

# generate quantum links, classical with bsm nodes
qchannels = []
cchannels = []
for i, bsm_name in enumerate(bsm_names):
    # qchannels
    qchannels.append({SRC: router_names[i],
                      DST: bsm_name,
                      DISTANCE: args.qc_length * 500,
                      ATTENUATION: args.qc_atten})
    qchannels.append({SRC: router_names[i + 1],
                      DST: bsm_name,
                      DISTANCE: args.qc_length * 500,
                      ATTENUATION: args.qc_atten})
    # cchannels
    for node in [router_names[i], router_names[i + 1]]:
        cchannels.append({SRC: bsm_name,
                          DST: node,
                          DELAY: int(args.cc_delay * MILLISECOND)})

        cchannels.append({SRC: node,
                          DST: bsm_name,
                          DELAY: int(args.cc_delay * MILLISECOND)})
output_dict[ALL_Q_CHANNEL] = qchannels

# generate classical links
router_cchannels = generate_classical(router_names, args.cc_delay)
cchannels += router_cchannels
output_dict[ALL_C_CHANNEL] = cchannels

# write other config options to output dictionary
final_config(output_dict, args)

# write final json
path = os.path.join(args.directory, args.output)
output_file = open(path, 'w')
json.dump(output_dict, output_file, indent=4)
