"""This module generates JSON config files for networks in a ring configuration.

Help information may also be obtained using the `-h` flag.

Args:
    ring_size (int): number of nodes in the network ring.
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


# python config_generator_ring.py 4 10 1 0.0002 1 -o ring_topo.json -s 100

# parse args
parser = argparse.ArgumentParser()
parser.add_argument('ring_size', type=int, help='number of network nodes')
parser = add_default_args(parser)
args = parser.parse_args()

output_dict = {}

# get node names, processes
router_names = [router_name_func(i) for i in range(args.ring_size)]
nodes = generate_nodes(router_names, args.memo_size)

# generate bsm nodes, quantum links (quantum channels + classical channels)
qchannels = []
cchannels = []
bsm_names = ["BSM_{}_{}".format(i % args.ring_size, (i+1) % args.ring_size)
             for i in range(args.ring_size)]
bsm_nodes = [{NAME: bsm_name, TYPE: BSM_NODE, SEED: i}
             for i, bsm_name in enumerate(bsm_names)]


for i, bsm_name in enumerate(bsm_names):
    # qchannels
    qchannels.append({SRC: router_names[i % args.ring_size],
                      DST: bsm_name,
                      DISTANCE: args.qc_length * 500,
                      ATTENUATION: args.qc_atten})
    qchannels.append({SRC: router_names[(i + 1) % args.ring_size],
                      DST: bsm_name,
                      DISTANCE: args.qc_length * 500,
                      ATTENUATION: args.qc_atten})
    # cchannels
    cchannels.append({SRC: router_names[i % args.ring_size],
                      DST: bsm_name,
                      DELAY: int(args.cc_delay * MILLISECOND)})
    cchannels.append({SRC: router_names[(i + 1) % args.ring_size],
                      DST: bsm_name,
                      DELAY: int(args.cc_delay * MILLISECOND)})
    cchannels.append({SRC: bsm_name,
                      DST: router_names[i % args.ring_size],
                      DELAY: int(args.cc_delay * MILLISECOND)})
    cchannels.append({SRC: bsm_name,
                      DST: router_names[(i + 1) % args.ring_size],
                      DELAY: int(args.cc_delay * MILLISECOND)})

nodes += bsm_nodes
output_dict[ALL_NODE] = nodes
output_dict[ALL_Q_CHANNEL] = qchannels

# generate classical links (classical channels)
router_cchannels = generate_classical(router_names, args.cc_delay)
cchannels += router_cchannels
output_dict[ALL_C_CHANNEL] = cchannels

# write other config options to output dictionary
final_config(output_dict, args)

# write final json
path = os.path.join(args.directory, args.output)
output_file = open(path, 'w')
json.dump(output_dict, output_file, indent=4)

