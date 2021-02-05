import argparse
import sys
import json5

from sequence.kernel.quantum_manager_server import valid_ip, valid_port
from sequence.topology.topology import Topology
from sequence.topology.router_net_topo import RouterNetTopo


# parse args
parser = argparse.ArgumentParser()
parser.add_argument('ring_size', type=int, help='number of network nodes')
parser.add_argument('memo_size', type=int, help='number of memories per node')
parser.add_argument('qc_length', type=float, help='distance between ring nodes (in km)')
parser.add_argument('qc_atten', type=float, help='quantum channel attenuation (in dB/km)')
parser.add_argument('cc_delay', type=float, help='classical channel delay (in ms)')
parser.add_argument('-o', '--output', type=str, default='out.json', help='name of output config file')
parser.add_argument('-s', '--stop', type=float, default=float('inf'), help='stop time (in s)')
parser.add_argument('-p', '--parallel', nargs=5,
    help='optional parallel arguments: server ip, server port, num. processes, sync/async, lookahead')

args = parser.parse_args()
output_dict = {}

# generate router nodes
nodes = []
node_names = []
for i in range(args.ring_size):
    name = "router_" + str(i)
    node_names.append(name)
    nodes.append({Topology.NAME: name,
                  Topology.TYPE: RouterNetTopo.QUANTUM_ROUTER,
                  Topology.SEED: i,
                  RouterNetTopo.MEMO_ARRAY_SIZE: args.memo_size})
    # TODO: fidelity of memory?
output_dict[Topology.ALL_NODE] = nodes

# generate quantum links
qchannels = []
bsm_names = []
for i in range(args.ring_size):
    # BSM
    node_indices = (i % args.ring_size, (i+1) % args.ring_size)
    bsm_name = "BSM.{}.{}".format(node_indices[0], node_indices[1])
    bsm_names.append(bsm_name)
    nodes.append({Topology.NAME: bsm_name,
                  Topology.TYPE: RouterNetTopo.BSM_NODE,
                  Topology.SEED: i})
    # qchannels
    qchannels.append({Topology.SRC: node_names[node_indices[0]],
                      Topology.DST: bsm_name,
                      Topology.DISTANCE: args.qc_length * 500,
                      Topology.ATTENUATION: args.qc_atten})
    qchannels.append({Topology.SRC: node_names[node_indices[1]],
                      Topology.DST: bsm_name,
                      Topology.DISTANCE: args.qc_length * 500,
                      Topology.ATTENUATION: args.qc_atten})
output_dict[Topology.ALL_Q_CHANNEL] = qchannels

# generate classical links
cchannels = []
combined_nodes = node_names + bsm_names
for node1 in combined_nodes:
    for node2 in combined_nodes:
        if node1 == node2:
            continue
        cchannels.append({Topology.SRC: node1,
                          Topology.DST: node2,
                          Topology.DELAY: args.cc_delay * 1e9})
output_dict[Topology.ALL_C_CHANNEL] = cchannels

if args.parallel:
    raise NotImplementedError()
else:
    output_dict[RouterNetTopo.IS_PARALLEL] = False
    output_dict[Topology.STOP_TIME] = args.stop * 1e12

output_file = open(args.output, 'w')
json5.dump(output_dict, output_file)

