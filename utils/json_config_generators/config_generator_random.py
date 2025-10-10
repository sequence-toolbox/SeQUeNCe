"""This module generates JSON config files for a random network (Waxman).

Help information may also be obtained using the `-h` flag.

Args:
    net_size (int): number of nodes in the random network.
    memo_size (int): number of memories per node.
    qc_length (float): distance between nodes (in km).
    qc_atten (float): quantum channel attenuation (in dB/m).
    cc_delay (float): classical channel delay (in ms).

Optional Args:
    -d --directory (str): name of the output directory (default tmp)
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
import json
import os
import numpy as np
import random
from networkx.generators.geometric import waxman_graph

from sequence.utils.config_generator import add_default_args, get_node_csv, generate_node_procs, generate_nodes, final_config, router_name_func
from sequence.topology.topology import Topology
from sequence.topology.router_net_topo import RouterNetTopo


def create_random_waxman(area_length: int, number_nodes: int, edge_density: float) -> tuple[list, list]:
    """create a random network using waxman.

    Return:
        a list of vertex in (x, y), where x, y are real number geographic coordinates
        a list of edges in (u, v), where u, v are integer vertex index
    """
    max_number_edges = (number_nodes - 1) * number_nodes // 2
    alpa_min, alpha_max = 0, 100
    while alpha_max - alpa_min > 0.001:
        alpha = (alpa_min + alpha_max) / 2
        graphx_list = []
        for _ in range(10):  # do average of 10
            graphx_list.append(waxman_graph(number_nodes, domain=(0, 0, area_length, area_length), beta=1, alpha=alpha)) # cannot understand the L parameter
        avg_length = np.average([len(graphx.edges()) for graphx in graphx_list])
        
        if (edge_density - 0.002) * max_number_edges <= avg_length <= (edge_density + 0.002) * max_number_edges:
            break
        elif avg_length > (edge_density + 0.002) * max_number_edges:
            alpha_max = alpha
        else:
            alpa_min = alpha
    # pick the best one of the 10
    target = edge_density * max_number_edges
    graphx = None
    difference = float('inf')
    for tmp_graphx in graphx_list:
        diff = abs(len(tmp_graphx.edges()) - target)
        if diff < difference:
            graphx = tmp_graphx
            difference = diff

    V = [(int(graphx.nodes[i]["pos"][0]), int(graphx.nodes[i]["pos"][1])) for i in range(number_nodes)]

    E = list(graphx.edges())

    # lengths = []
    print(f'number of nodes = {len(V)}')
    # print(f'average link length = {int(np.average(lengths)):,}')
    print(f'# of edge = {len(graphx.edges())}, edge density = {len(graphx.edges())/max_number_edges:.4f}')
    return V, E


def main():
    # parse args
    parser = argparse.ArgumentParser()
    parser.add_argument('net_size', type=int, help='number of network nodes')
    parser = add_default_args(parser)
    args = parser.parse_args()

    net_size = args.net_size
    area_length = 1000
    edge_density = 0.5

    random.seed(0)
    np.random.seed(0)
    V, E = create_random_waxman(area_length, net_size, edge_density)

    output_dict = {}

    # get node names, processes
    if args.nodes:
        node_procs = get_node_csv(args.nodes)
    else:
        node_procs = generate_node_procs(args.parallel, args.net_size, router_name_func)
    router_names = list(node_procs.keys())
    nodes = generate_nodes(node_procs, router_names, args.memo_size)

    # 1. generate quantum links and bsm nodes
    qchannels = []
    cchannels = []
    bsm_nodes = []
    seed = 0
    for node1, node2 in E:
        node1_name = router_name_func(node1)
        node2_name = router_name_func(node2)
        node1_loc = V[node1]
        node2_loc = V[node2]
        distance = np.sqrt((node1_loc[0] - node2_loc[0]) ** 2 + (node1_loc[1] - node2_loc[1]) ** 2)

        # bsm node
        bsm_name = "BSM_{}_{}".format(node1_name, node2_name)
        bsm_node = {Topology.NAME: bsm_name,
                    Topology.TYPE: RouterNetTopo.BSM_NODE,
                    Topology.SEED: seed,
                    RouterNetTopo.GROUP: node_procs[node1_name]}
        bsm_nodes.append(bsm_node)

        # qchannels
        qchannels.append({Topology.SRC: node1_name,
                          Topology.DST: bsm_name,
                          Topology.DISTANCE: distance / 2,
                          Topology.ATTENUATION: args.qc_atten})
        qchannels.append({Topology.SRC: node2_name,
                          Topology.DST: bsm_name,
                          Topology.DISTANCE: distance / 2,
                          Topology.ATTENUATION: args.qc_atten})
        # cchannels
        cchannels.append({Topology.SRC: node1_name,
                          Topology.DST: bsm_name,
                          Topology.DELAY: args.cc_delay * 1e9})
        cchannels.append({Topology.SRC: node2_name,
                          Topology.DST: bsm_name,
                          Topology.DELAY: args.cc_delay * 1e9})
        cchannels.append({Topology.SRC: bsm_name,
                          Topology.DST: node1_name,
                          Topology.DELAY: args.cc_delay * 1e9})
        cchannels.append({Topology.SRC: bsm_name,
                          Topology.DST: node2_name,
                          Topology.DELAY: args.cc_delay * 1e9})
        seed += 1

    # 2. generate classical links between all node pairs
    for i, node1_name in enumerate(router_names):
        for node2_name in router_names[i+1:]:
            cchannels.append({Topology.SRC: node1_name,
                              Topology.DST: node2_name,
                              Topology.DELAY: args.cc_delay * 1e9})
            cchannels.append({Topology.SRC: node2_name,
                              Topology.DST: node1_name,
                              Topology.DELAY: args.cc_delay * 1e9})

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


if __name__ == '__main__':
    main()
