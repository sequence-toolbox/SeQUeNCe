import argparse

from graphviz import Graph
from sequence.kernel.timeline import Timeline
from sequence.topology.node import BSMNode
from sequence.topology.topology import Topology

if __name__ == "__main__":
    '''
    Program for drawing network from json file
    input: relative path to json file
    Graphviz library must be installed
    '''
    
    parser = argparse.ArgumentParser()
    parser.add_argument('config_file')
    parser.add_argument('-m', dest='draw_middle', action='store_true')

    args = parser.parse_args()

    tl = Timeline()
    topo = Topology("", tl)
    topo.load_config(args.config_file)
    g = Graph(format='png')
    g.attr(layout='neato', overlap='false')

    nodes = list(topo.nodes.keys())
    qc_ends = [(qc.ends[0].name, qc.ends[1].name) for qc in topo.qchannels]

    # add nodes and update qchannels if necessary
    for node in nodes:
        if type(topo.nodes[node]) == BSMNode:
            if args.draw_middle:
                g.node(node, label='BSM', shape='rectangle')
            else:
                connected_channels = [qc for qc in qc_ends if node in qc]
                qc_ends = [qc for qc in qc_ends if qc not in connected_channels]
                node1 = [end for end in connected_channels[0] if end not in connected_channels[1]][0]
                node2 = [end for end in connected_channels[1] if end not in connected_channels[0]][0]
                qc_ends.append((node1, node2))
        else:
            g.node(node)

    # add qconnections
    for qc in qc_ends:
        g.edge(qc[0], qc[1], color='blue')

    g.view()


