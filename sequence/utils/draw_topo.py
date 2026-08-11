"""
Program for drawing network from json file
input: relative path to json file
Graphviz library must be installed

NOTE: this file currently only works for sequential simulation files.
"""

import argparse
from graphviz import Graph
from json import load
from collections import defaultdict

from sequence.topology.topology import Topology
from sequence.topology.router_net_topo import RouterNetTopo
from sequence.topology.qkd_topo import QKDTopo
from sequence.topology.dqc_net_topo import DQCNetTopo


def get_topology(config_file: str) -> Topology:
    """
    Determine the type of network described by a config file and load it.
    Args:
        config_file: path to json file defining network

    Returns: The topology matching the type of the config file's first node
    """
    with open(config_file, 'r') as fh:
        config = load(fh)
    nodes = config["nodes"]
    node_type = nodes[0]["type"]

    if node_type == RouterNetTopo.BSM_NODE or node_type == RouterNetTopo.QUANTUM_ROUTER:
        return RouterNetTopo(config_file)

    elif node_type == QKDTopo.QKD_NODE:
        return QKDTopo(config_file)

    elif node_type == DQCNetTopo.DQC_NODE:
        return DQCNetTopo(config_file)

    else:
        raise Exception("Unknown node type '{}' in config file {}".format(node_type, config_file))


def draw_topology(topo: Topology, draw_middle: bool = False) -> Graph:
    """
    Build the graph of a topology's nodes and quantum channels.
    Args:
        topo: the topology to draw
        draw_middle: draw the middle BSM nodes, default is False

    Returns: The graph of the topology
    """
    g = Graph(format='png')
    g.attr(layout='neato', overlap='false')

    # add nodes and translate qchannels from graph
    node_types = list(topo.nodes.keys())

    for node_type in node_types:
        if node_type == RouterNetTopo.BSM_NODE:
            if draw_middle:
                for node in topo.get_nodes_by_type(node_type):
                    g.node(node.name, label='BSM', shape='rectangle')
        else:
            for node in topo.get_nodes_by_type(node_type):
                g.node(node.name)

    if draw_middle:
        # draw the middle BSM node
        for qchannel in topo.get_qchannels():
            g.edge(qchannel.sender.name, qchannel.receiver, color='blue', dir='forward')
    else:
        # do not draw the middle BSM node
        bsm_to_node = defaultdict(list)
        for qchannel in topo.get_qchannels():
            node = qchannel.sender.name
            bsm = qchannel.receiver
            bsm_to_node[bsm].append(node)
        for bsm, nodes in bsm_to_node.items():
            assert len(nodes) == 2, f'{bsm} connects to {len(nodes)} number of nodes (should be 2)'
            g.edge(nodes[0], nodes[1], color='blue')

    return g


def main() -> None:
    """Draw the network of a json config file and open the resulting figure."""
    parser = argparse.ArgumentParser()
    parser.add_argument('config_file', help="path to json file defining network")
    parser.add_argument('-d', '--directory', type=str, default='tmp', help='directory to save the figure')
    parser.add_argument('-f', '--filename', type=str, default='topology', help='filename of the figure')
    parser.add_argument('-m', '--draw_middle', action='store_true')

    args = parser.parse_args()

    topo = get_topology(args.config_file)
    g = draw_topology(topo, args.draw_middle)
    g.view(directory=args.directory, filename=args.filename)


if __name__ == "__main__":
    main()
