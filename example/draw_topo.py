import sys
from graphviz import Graph
from sequence.kernel.timeline import Timeline
from sequence.topology.topology import Topology
from sequence.topology.node import MiddleNode


if __name__ == "__main__":
    '''
    Program for drawing network from json file
    input: relative path to json file
    Graphviz library must be installed
    '''
    
    config_file = sys.argv[1]
    tl = Timeline()
    topo = Topology("", tl)
    topo.load_config(config_file)
    g = Graph(format='png')
    g.attr(layout='fdp', overlap='false')

    # add nodes
    for node in topo.graph:
        if type(topo.nodes[node]) == MiddleNode:
            g.node(node, label='middle', shape='rectangle')
        else:
            g.node(node)
    # add qconnections
    for qc in topo.qchannels:
        node1 = qc.ends[0].name
        node2 = qc.ends[1].name
        g.edge(node1, node2, color='red')
    # add cconnections
    for cc in topo.cchannels:
        node1 = cc.ends[0].name
        node2 = cc.ends[1].name
        g.edge(node1, node2, color='blue')

    g.view()
