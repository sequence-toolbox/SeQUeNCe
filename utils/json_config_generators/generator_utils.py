"""This module defines common functions for the config generation files."""

import pandas as pd

from sequence.topology.topology import Topology
from sequence.topology.router_net_topo import RouterNetTopo


def add_default_args(parser):
    parser.add_argument('memo_size', type=int, help='number of memories per node')
    parser.add_argument('qc_length', type=float, help='distance between ring nodes (in km)')
    parser.add_argument('qc_atten', type=float, help='quantum channel attenuation (in dB/m)')
    parser.add_argument('cc_delay', type=float, help='classical channel delay (in ms)')
    parser.add_argument('-o', '--output', type=str, default='out.json', help='name of output config file')
    parser.add_argument('-s', '--stop', type=float, default=float('inf'), help='stop time (in s)')
    parser.add_argument('-p', '--parallel', nargs=4,
                        help='optional parallel arguments: server ip, server port, num. processes, lookahead')
    parser.add_argument('-n', '--nodes', type=str, help='path to csv file to provide process for each node')
    return parser


# get csv file
def get_node_csv(node_file):
    node_procs = {}

    # TODO: add length/proc assertions
    df = pd.read_csv(node_file)
    for name, group in zip(df['name'], df['group']):
        node_procs[name] = group

    return node_procs


def generate_node_procs(parallel, net_size, naming_func):
    if parallel:
        num_procs = int(parallel[2])
    else:
        num_procs = 1
    group_size = net_size / num_procs

    node_procs = {}
    for i in range(net_size):
        node_procs[naming_func(i)] = int(i // group_size)

    return node_procs


def generate_nodes(node_procs, router_names, memo_size):
    nodes = [{Topology.NAME: name,
              Topology.TYPE: RouterNetTopo.QUANTUM_ROUTER,
              Topology.SEED: i,
              RouterNetTopo.MEMO_ARRAY_SIZE: memo_size,
              RouterNetTopo.GROUP: node_procs[name]}
             for i, name in enumerate(router_names)]
    return nodes


def generate_bsm_links(graph, node_procs, parsed_args, bsm_naming_func):
    cchannels = []
    qchannels = []
    bsm_nodes = []

    for i, node_pair in enumerate(graph.edges):
        node1, node2 = node_pair
        bsm_name = bsm_naming_func(node1, node2)
        bsm_node = {Topology.NAME: bsm_name,
                    Topology.TYPE: RouterNetTopo.BSM_NODE,
                    Topology.SEED: i,
                    RouterNetTopo.GROUP: node_procs[node1]}
        bsm_nodes.append(bsm_node)

        for node in node_pair:
            qchannels.append({Topology.SRC: node,
                              Topology.DST: bsm_name,
                              Topology.DISTANCE: parsed_args.qc_length * 500,
                              Topology.ATTENUATION: parsed_args.qc_atten})

        for node in node_pair:
            cchannels.append({Topology.SRC: bsm_name,
                              Topology.DST: node,
                              Topology.DELAY: parsed_args.cc_delay * 1e9})

            cchannels.append({Topology.SRC: node,
                              Topology.DST: bsm_name,
                              Topology.DELAY: parsed_args.cc_delay * 1e9})

    return cchannels, qchannels, bsm_nodes


# generate classical network connections
def generate_classical(router_names, cc_delay):
    cchannels = []
    for node1 in router_names:
        for node2 in router_names:
            if node1 == node2:
                continue
            cchannels.append({Topology.SRC: node1,
                              Topology.DST: node2,
                              Topology.DELAY: cc_delay * 1e9})
    return cchannels


# add final touches to config dict
def final_config(output_dict, parsed_args):
    output_dict[Topology.STOP_TIME] = parsed_args.stop * 1e12
    if parsed_args.parallel:
        output_dict[RouterNetTopo.IS_PARALLEL] = True
        output_dict[RouterNetTopo.PROC_NUM] = int(parsed_args.parallel[2])
        output_dict[RouterNetTopo.IP] = parsed_args.parallel[0]
        output_dict[RouterNetTopo.PORT] = int(parsed_args.parallel[1])
        output_dict[RouterNetTopo.LOOKAHEAD] = int(parsed_args.parallel[4])
        if parsed_args.parallel[3] == "true":
            # set all to synchronous
            output_dict[RouterNetTopo.ALL_GROUP] = \
                    [{RouterNetTopo.TYPE: RouterNetTopo.SYNC} for _ in range(int(parsed_args.parallel[2]))] 
        else:
            output_dict[RouterNetTopo.ALL_GROUP] = \
                    [{RouterNetTopo.TYPE: RouterNetTopo.ASYNC}] * int(parsed_args.parallel[2])
    else:
        output_dict[RouterNetTopo.IS_PARALLEL] = False

