"""This module defines common functions for the config generation files."""

import pandas as pd

from sequence.topology.topology import Topology
from sequence.topology.router_net_topo import RouterNetTopo


# get csv file
def get_node_csv(node_file):
    # TODO: add length/proc assertions
    df = pd.read_csv(node_file)
    node_procs = {}
    for name, group in zip(df['name'], df['group']):
        node_procs[name] = group
    return node_procs


# generate list of nodes
def generate_nodes(parallel, node_procs, net_size, memo_size, ):
    if parallel and node_procs:
        node_names = list(node_procs.keys())
    else:
        node_names = ["router_" + str(i) for i in range(net_size)]
    nodes = [{Topology.NAME: name,
              Topology.TYPE: RouterNetTopo.QUANTUM_ROUTER,
              Topology.SEED: i,
              RouterNetTopo.MEMO_ARRAY_SIZE: memo_size}
              for i, name in enumerate(node_names)]
    # TODO: memory fidelity?
    if parallel:
        if node_procs:
            for i in range(net_size):
                name = nodes[i][Topology.NAME]
                nodes[i][RouterNetTopo.GROUP] = node_procs[name]
        else:
            for i in range(net_size):
                nodes[i][RouterNetTopo.GROUP] = int(i // (net_size / int(parallel[2])))

    return nodes, node_names


# generate classical network connections
def generate_classical(node_names):
    cchannels = []
    for node2 in node_names:
        if node1 == node2:
            continue
        cchannels.append({Topology.SRC: node1,
                          Topology.DST: node2,
                          Topology.DELAY: args.cc_delay * 1e9})
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

