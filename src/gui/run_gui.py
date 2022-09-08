import json
import os
import networkx as nx
import pandas as pd
import numpy as np

from .app import QuantumGUI
from .graph_comp import GraphNode
from ..topology.topology import Topology
from ..topology.router_net_topo import RouterNetTopo


class RunGui:
    DEFAULT_CONFIG = '/starlight.json'

    def __init__(self, name):
        graph = nx.DiGraph()
        tdm_table = pd.DataFrame()
        delay_table = pd.DataFrame()
        self.name = name
        self.gui = QuantumGUI(
            graph,
            delays=delay_table,
            tdm=tdm_table
        ).get_app(name)

    def load_graph(self, path_to_topology=None):
        # JSON
        if path_to_topology is None:
            directory, _ = os.path.split(__file__)
            with open(directory + RunGui.DEFAULT_CONFIG) as json_file:
                network_in = json.load(json_file)
        else:
            with open(path_to_topology) as json_file:
                network_in = json.load(json_file)

        # Delay table initialization
        # TODO: rewrite for non-table format
        pd.options.display.float_format = '{:.2e}'.format
        table = network_in['cchannels_table']
        delay_table = pd.DataFrame(table['table'])
        delay_table.columns = table['labels']

        # TDM table initialization
        tdm_default = np.empty(
            [len(table['labels']), len(table['labels'])],
            dtype=int
        )
        tdm_default.fill(20000)

        index = 0

        for x in range(tdm_default.shape[0]):
            tdm_default[x][index] = 0
            index += 1

        tdm_table = pd.DataFrame(tdm_default)
        tdm_table.columns = table['labels']

        # Network initialization
        graph = nx.DiGraph()

        for node in network_in['nodes']:
            if node['type'] == RouterNetTopo.QUANTUM_ROUTER:
                node['type'] = 'Quantum_Router'
            new_node = GraphNode(node[Topology.NAME], node[Topology.TYPE], 'default_router')
            graph.add_node(
                node[Topology.NAME],
                label=node[Topology.NAME],
                node_type=node[Topology.TYPE],
                data=new_node.__dict__
            )

        for edge in network_in[Topology.ALL_QC_CONNECT]:
            graph.add_edge(
                edge[Topology.CONNECT_NODE_1],
                edge[Topology.CONNECT_NODE_2],
                data={
                    'source': edge[Topology.CONNECT_NODE_1],
                    'target': edge[Topology.CONNECT_NODE_2],
                    'distance': edge[Topology.DISTANCE],
                    'attenuation': edge[Topology.ATTENUATION],
                    'link_type': 'Quantum'
                }
            )

        # input = nx.readwrite.cytoscape_data(graph)['elements']

        self.gui = QuantumGUI(
            graph,
            delays=delay_table,
            tdm=tdm_table
        ).get_app(self.name)
