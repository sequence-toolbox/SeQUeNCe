import json
import yaml
import os
import networkx as nx
import pandas as pd
import numpy as np

from .app import QuantumGUI
from .graph_comp import GraphNode
from ..constants import *


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

    @staticmethod
    def _load_config(filename: str) -> dict:
        """Load configuration from JSON or YAML file."""
        with open(filename) as fh:
            if filename.endswith(('.yaml', '.yml')):
                return yaml.safe_load(fh)
            return json.load(fh)

    def load_graph(self, path_to_topology=None):
        if path_to_topology is None:
            directory, _ = os.path.split(__file__)
            network_in = self._load_config(directory + RunGui.DEFAULT_CONFIG)
        else:
            network_in = self._load_config(path_to_topology)

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
            new_node = GraphNode(node[NAME], node[TYPE], 'default_router')
            graph.add_node(
                node[NAME],
                label=node[NAME],
                node_type=node[TYPE],
                data=new_node.__dict__
            )

        for edge in network_in[ALL_Q_CONNECT]:
            graph.add_edge(
                edge[CONNECT_NODE_1],
                edge[CONNECT_NODE_2],
                data={
                    'source': edge[CONNECT_NODE_1],
                    'target': edge[CONNECT_NODE_2],
                    'distance': edge[DISTANCE],
                    'attenuation': edge[ATTENUATION],
                    'link_type': 'Quantum'
                }
            )

        # input = nx.readwrite.cytoscape_data(graph)['elements']

        self.gui = QuantumGUI(
            graph,
            delays=delay_table,
            tdm=tdm_table
        ).get_app(self.name)
