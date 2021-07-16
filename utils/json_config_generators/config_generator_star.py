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
import sys
import json
import pandas as pd

from sequence.kernel.quantum_manager_server import valid_ip, valid_port
from sequence.topology.topology import Topology
from sequence.topology.router_net_topo import RouterNetTopo


# parse args
parser = argparse.ArgumentParser()
parser.add_argument('star_size', type=int, help='number of non-center network nodes')
parser.add_argument('memo_size', type=int, help='number of memories per end node')
parser.add_argument('memo_size_center', type=int, help='number of memories on center node')
parser.add_argument('qc_length', type=float, help='distance between star nodes and center (in km)')
parser.add_argument('qc_atten', type=float, help='quantum channel attenuation (in dB/m)')
parser.add_argument('cc_delay', type=float, help='classical channel delay (in ms)')
parser.add_argument('-o', '--output', type=str, default='out.json', help='name of output config file')
parser.add_argument('-s', '--stop', type=float, default=float('inf'), help='stop time (in s)')
parser.add_argument('-p', '--parallel', nargs=5,
    help='optional parallel arguments: server ip, server port, num. processes, sync/async, lookahead')
parser.add_argument('-n', '--nodes', type=str,
    help='path to csv file to provide process for each node. First node is the center.')

args = parser.parse_args()
output_dict = {}

# get csv file
if args.nodes:
    # TODO: add length/proc assertions
    df = pd.read_csv(args.nodes)
    node_procs = {}
    for name, group in zip(df['name'], df['group']):
        node_procs[name] = group

else:
    node_procs = None

# generate router nodes
if args.parallel and node_procs:
    node_names = list(node_procs.keys())
    center_name = node_names.pop(0)
else:
    center_name = "router_center"
    node_names = ["router_" + str(i) for i in range(args.star_size)]
nodes = [{Topology.NAME: name,
          Topology.TYPE: RouterNetTopo.QUANTUM_ROUTER,
          Topology.SEED: i,
          RouterNetTopo.MEMO_ARRAY_SIZE: args.memo_size}
          for i, name in enumerate(node_names)]
nodes.append({Topology.NAME: center_name,
              Topology.TYPE: RouterNetTopo.QUANTUM_ROUTER,
              Topology.SEED: args.star_size,
              RouterNetTopo.MEMO_ARRAY_SIZE: args.memo_size_center})
if args.parallel:
    combined = node_names + [center_name]
    if node_procs:
        for i in range(args.star_size + 1):
            name = nodes[i][Topology.NAME]
            nodes[i][RouterNetTopo.GROUP] = node_procs[name]
    else:
        for i in range(args.star_size + 1):
            nodes[i][RouterNetTopo.GROUP] = int(i // ((args.star_size + 1) / int(args.parallel[2])))

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

for node_name, bsm_name in zip(node_names, bsm_names):
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
combined_nodes = node_names + [center_name]
for node1 in combined_nodes:
    for node2 in combined_nodes:
        if node1 == node2:
            continue
        cchannels.append({Topology.SRC: node1,
                          Topology.DST: node2,
                          Topology.DELAY: args.cc_delay * 1e9})
output_dict[Topology.ALL_C_CHANNEL] = cchannels

# write other config options to output dictionary
output_dict[Topology.STOP_TIME] = args.stop * 1e12
if args.parallel:
    output_dict[RouterNetTopo.IS_PARALLEL] = True
    output_dict[RouterNetTopo.PROC_NUM] = int(args.parallel[2])
    output_dict[RouterNetTopo.IP] = args.parallel[0]
    output_dict[RouterNetTopo.PORT] = int(args.parallel[1])
    output_dict[RouterNetTopo.LOOKAHEAD] = int(args.parallel[4])
    if args.parallel[3] == "true":
        # set all to synchronous
        output_dict[RouterNetTopo.ALL_GROUP] = \
                [{RouterNetTopo.TYPE: RouterNetTopo.SYNC} for _ in range(int(args.parallel[2]))] 
    else:
        output_dict[RouterNetTopo.ALL_GROUP] = \
                [{RouterNetTopo.TYPE: RouterNetTopo.ASYNC}] * int(args.parallel[2])
else:
    output_dict[RouterNetTopo.IS_PARALLEL] = False

# write final json
output_file = open(args.output, 'w')
json.dump(output_dict, output_file, indent=4)

