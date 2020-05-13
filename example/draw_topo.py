import sys
from graphviz import Graph
from sequence.kernel.timeline import Timeline
from sequence.topology.topology import Topology


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
    g = Graph()

    # add nodes
    for node in topo.graph:
        g.node(node, str(type(topo.nodes[node])))
    # add qconnections
    for qc in topo.qchannels:
        node1 = qc.ends[0].name
        node2 = qc.edns[1].name
        g.edge(node1, node2, color='red')
    # add cconnections
    for cc in topo.cchannels:
        node1 = cc.ends[0].name
        node2 = cc.edns[1].name
        g.edge(node1, node2, color='blue')
