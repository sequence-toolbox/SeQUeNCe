"""
Program for drawing network from json file
input: relative path to json file
Graphviz library must be installed

NOTE: this file currently only works for sequential simulation files.
If your JSON file contains parallel simulation information, please remove before use.
"""

import argparse
from graphviz import Graph
from json import load
from collections import defaultdict

from sequence.topology.router_net_topo import RouterNetTopo
from sequence.topology.qkd_topo import QKDTopo
from sequence.topology.dqc_net_topo import DQCNetTopo


parser = argparse.ArgumentParser()
parser.add_argument('config_file', help="path to json file defining network")
parser.add_argument('-d', '--directory', type=str, default='tmp', help='directory to save the figure')
parser.add_argument('-f', '--filename', type=str, default='topology', help='filename of the figure')
parser.add_argument('-m', '--draw_middle', action='store_true')

args = parser.parse_args()
directory = args.directory
filename = args.filename
draw_middle = args.draw_middle

# determine type of network
with open(args.config_file, 'r') as fh:
    config = load(fh)
nodes = config["nodes"]
node_type = nodes[0]["type"]

if node_type == RouterNetTopo.BSM_NODE or node_type == RouterNetTopo.QUANTUM_ROUTER:
    topo = RouterNetTopo(args.config_file)

elif node_type == QKDTopo.QKD_NODE:
    topo = QKDTopo(args.config_file)

elif node_type == DQCNetTopo.DQC_NODE:
    topo = DQCNetTopo(args.config_file)

else:
    raise Exception("Unknown node type '{}' in config file {}".format(node_type, args.config_file))

# make graph
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
    qconnections = set()
    for bsm, nodes in bsm_to_node.items():
        assert len(nodes) == 2, f'{bsm} connects to {len(nodes)} number of nodes (should be 2)'
        g.edge(nodes[0], nodes[1], color='blue')


g.view(directory=directory, filename=filename)
