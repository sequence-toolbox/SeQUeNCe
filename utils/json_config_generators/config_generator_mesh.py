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
import sys
import json
import pandas as pd

from sequence.kernel.quantum_manager_server import valid_ip, valid_port
from sequence.topology.topology import Topology
from sequence.topology.router_net_topo import RouterNetTopo


# parse args
parser = argparse.ArgumentParser()
parser.add_argument('net_size', type=int, help='number of network nodes')
parser.add_argument('memo_size', type=int, help='number of memories per node')
parser.add_argument('qc_length', type=float, help='distance between ring nodes (in km)')
parser.add_argument('qc_atten', type=float, help='quantum channel attenuation (in dB/m)')
parser.add_argument('cc_delay', type=float, help='classical channel delay (in ms)')
parser.add_argument('-o', '--output', type=str, default='out.json', help='name of output config file')
parser.add_argument('-s', '--stop', type=float, default=float('inf'), help='stop time (in s)')
parser.add_argument('-p', '--parallel', nargs=5,
    help='optional parallel arguments: server ip, server port, num. processes, sync/async, lookahead')
parser.add_argument('-n', '--nodes', type=str, help='path to csv file to provide process for each node') 

args = parser.parse_args()
output_dict = {}

# get csv file (if present)
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
else:
    node_names = ["router_" + str(i) for i in range(args.net_size)]
nodes = [{Topology.NAME: name,
          Topology.TYPE: RouterNetTopo.QUANTUM_ROUTER,
          Topology.SEED: i,
          RouterNetTopo.MEMO_ARRAY_SIZE: args.memo_size}
          for i, name in enumerate(node_names)]
# TODO: memory fidelity?
if args.parallel:
    if node_procs:
        for i in range(args.net_size):
            name = nodes[i][Topology.NAME]
            nodes[i][RouterNetTopo.GROUP] = node_procs[name]
    else:
        for i in range(args.net_size):
            nodes[i][RouterNetTopo.GROUP] = int(i // (args.net_size / int(args.parallel[2])))

# generate quantum links, classical links, and bsm nodes
qchannels = []
cchannels = []
bsm_nodes = []
seed = 0
for i, node1 in enumerate(node_names):
    for node2 in node_names[i+1:]:
        bsm_name = "BSM_{}_{}".format(node1, node2)
        bsm_node = {Topology.NAME: bsm_name,
                    Topology.TYPE: RouterNetTopo.BSM_NODE,
                    Topology.SEED: seed}
        if args.parallel:
            # TODO: rewrite to move outside loop
            bsm_node[RouterNetTopo.GROUP] = nodes[i][RouterNetTopo.GROUP]
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

