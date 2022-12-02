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

from sequence.topology.router_net_topo import RouterNetTopo
from sequence.topology.qkd_topo import QKDTopo


parser = argparse.ArgumentParser()
parser.add_argument('config_file', help="path to json file defining network")
# TODO: add support for middle node not viewing
# parser.add_argument('-m', dest='draw_middle', action='store_true')

args = parser.parse_args()

# determine type of network
with open(args.config_file, 'r') as fh:
    config = load(fh)
nodes = config["nodes"]
node_type = nodes[0]["type"]

if node_type == RouterNetTopo.BSM_NODE or node_type == RouterNetTopo.QUANTUM_ROUTER:
    topo = RouterNetTopo(args.config_file)

elif node_type == QKDTopo.QKD_NODE:
    topo = QKDTopo(args.config_file)

else:
    raise Exception("Unknown node type '{}' in config file {}".format(node_type, args.config_file))

# make graph
g = Graph(format='png')
g.attr(layout='neato', overlap='false')

# add nodes and translate qchannels from graph
node_types = list(topo.nodes.keys())

for node_type in node_types:
    if node_type == RouterNetTopo.BSM_NODE:
        for node in topo.get_nodes_by_type(node_type):
            g.node(node.name, label='BSM', shape='rectangle')
    else:
        for node in topo.get_nodes_by_type(node_type):
            g.node(node.name)

for qchannel in topo.get_qchannels():
    g.edge(qchannel.sender.name, qchannel.receiver, color='blue', dir='forward')

g.view()
