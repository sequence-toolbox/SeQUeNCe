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
    -d --directory (str): name of the output directory (default tmp)
    -o --output (str): name of the output file (default out.json).
    -s --stop (float): simulation stop time (in s) (default infinity).
"""

import argparse
import json
import os

from sequence.utils.config_generator import add_default_args, generate_nodes, generate_classical, final_config, router_name_func
from sequence.topology.topology import Topology
from sequence.topology.router_net_topo import RouterNetTopo
from sequence.constants import MILLISECOND


# parse args
parser = argparse.ArgumentParser()
parser.add_argument('star_size', type=int, help='number of non-center network nodes')
parser.add_argument('memo_size_center', type=int, help='number of memories on center node')
parser = add_default_args(parser)
args = parser.parse_args()

output_dict = {}


# generate nodes, with middle having different num
center_name = "router_center"
router_names = [router_name_func(i) for i in range(args.star_size + 1)]
router_names[-1] = center_name

nodes = generate_nodes(router_names, args.memo_size)
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
                      Topology.DELAY: int(args.cc_delay * MILLISECOND)})
    cchannels.append({Topology.SRC: center_name,
                      Topology.DST: bsm_name,
                      Topology.DELAY: int(args.cc_delay * MILLISECOND)})
    cchannels.append({Topology.SRC: bsm_name,
                      Topology.DST: node_name,
                      Topology.DELAY: int(args.cc_delay * MILLISECOND)})
    cchannels.append({Topology.SRC: bsm_name,
                      Topology.DST: center_name,
                      Topology.DELAY: int(args.cc_delay * MILLISECOND)})

output_dict[Topology.ALL_NODE] = nodes + bsm_nodes
output_dict[Topology.ALL_Q_CHANNEL] = qchannels

# generate classical links
router_cchannels = generate_classical(router_names, args.cc_delay)
cchannels += router_cchannels
output_dict[Topology.ALL_C_CHANNEL] = cchannels

# write other config options to output dictionary
final_config(output_dict, args)

# write final json
path = os.path.join(args.directory, args.output)
output_file = open(path, 'w')
json.dump(output_dict, output_file, indent=4)

