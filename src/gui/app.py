"""
A Class which contains all of the logic and data for the GUI
"""

import dash
import threading
import os
import json
import time
import datetime
import shutil
import pandas as pd
import numpy as np
from dash import dcc
from dash import html
import dash_bootstrap_components as dbc
import networkx as nx
from collections import OrderedDict
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
from .simulator_bindings import GUI_Sim
from .menus import *
from .graph_comp import GraphNode
from .layout import get_app_layout
from .layout import TYPE_COLORS, TYPES
from .css_styles import *


EDGE_DICT_ORDER = OrderedDict(
    {
        'source': '',
        'target': '',
        'distance': '',
        'attenuation': '',
        'link_type': ''
    }
)

NODE_TABLE_COLUMNS = [
    'name',
    'type',
    'template'
]

EDGE_TABLE_COLUMNS = [
    'source',
    'target',
    'distance',
    'attenuation',
    'link_type'
]

DIRECTORY, _ = os.path.split(__file__)
TEMPLATES = '/user_templates.json'


class QuantumGUI:
    """Class which holds the methods and properties of the SeQUeNCe GUI

        The Quantum_GUI can be instantiated without specifying any parameters.
        Using no parameters creates an instance of the GUI with only the
        default node templates and nothing else. The GUI can also be
        instantiated with a number of additional parameters, described
        within the attributes section. The Quantum_GUI manages graphical
        user elements. The structure of the data used can be divided into three
        categories, templates, topology, and simulations.
        The composition of each is in terms of Quantum_GUI elements is:

        templates
            - templates
        topology
            - data
            - cc_delays
            - qc_tdm
        simulation
            - sim_params

        To monitor the progress of simulation, the Timeline.show_progress
        attribute can be modified to show/hide a progress bar.

        Attributes:
            data (Graph or DiGraph):
                A NetworkX Graph of DiGraph object with attributes node, label,
                node_type, and data. The data attribute can be set to store any
                number of node attributes, though the gui uses the __dict__
                of GraphNode (defined in graph_comp.py) for consistency.
            cc_delays (DataFrame):
                Pandas DataFrame which represents an adjacency matrix of
                classical channel time delays.
            qc_tdm (DataFrame):
                Pandas DataFrame which represents an adjacency matrix of
                quantum channel tdm frames.
            defaults (Dict):
                Dictionary containing the default values of all node types.
            templates (Dict):
                Dictionary containing any user defined templates, loaded
                from file or given as parameter.
            edge_table (List[Dict]):
                A list of dictionaries which represents a table listing all
                edges in the current network. Should not be directly set
            node_table (List[Dict]):
                A list of dictionaries which represents a table listing all
                nodes in the current network. Should not be directly set
            edge_columns (List[String]):
                A list containing the column heading for the edge_table
            node_columns (List[String]):
                A list containing the column heading for the node_table
    """

    def __init__(self, graph_in, templates=None, delays=None, tdm=None):
        self.data = graph_in
        self.cc_delays = delays
        self.qc_tdm = tdm
        self.defaults = {}
        with open(DIRECTORY + '/default_params.json', 'r') as json_file:
            self.defaults = json.load(json_file)
        json_file.close()

        if templates is None:

            if os.path.exists(DIRECTORY + TEMPLATES):
                with open(DIRECTORY + TEMPLATES, 'r') as json_file:
                    self.templates = json.load(json_file)
                json_file.close()

            else:
                user_defaults = {}
                for x in TYPES:
                    user_defaults[x] = {}
                self.templates = user_defaults
                with open(DIRECTORY + '/user_templates.json', 'w') as outfile:
                    json.dump(
                        user_defaults,
                        outfile,
                        quote_keys=True,
                        sort_keys=True,
                        indent=4,
                        trailing_commas=False
                    )
                outfile.close()

        # TODO: re-add simulation
        # self.simulation = GUI_Sim(0, 0, 'NOTSET', 'init', self)
        self.sim_params = None

        # nodes = list(self.data.edges.data())

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, graph_in):
        self._data = self.color_image_graph(graph_in)
        edges = self.get_graph_table_edges(self._data)
        nodes = self.get_graph_table_nodes(self._data)
        self._edge_table = edges[0].to_dict('records')
        self._node_table = nodes[0].to_dict('records')
        self._edge_columns = edges[1]
        self._node_columns = nodes[1]

    @property
    def templates(self):
        return self._templates

    @templates.setter
    def templates(self, templates_in):
        self._templates = templates_in
        with open(DIRECTORY+'/'+'user_templates.json', 'w') as outfile:
            json.dump(
                templates_in,
                outfile,
                quote_keys=True,
                sort_keys=True,
                indent=4,
                trailing_commas=False
            )
        outfile.close()

    @property
    def edge_table(self):
        return self._edge_table

    @property
    def node_table(self):
        return self._node_table

    @property
    def edge_columns(self):
        return self._edge_columns

    @property
    def node_columns(self):
        return self._node_columns

    def convert_columns(self, columns, case_norm=True):
        """Function which takes a list of columns and coverts them into a
        dictionary format for their use in a Dash DataTable.

        Args:
            columns (List[str]):
                columns to convert to datatable column dictionary
            case_norm (Boolean):
                whether to capitalize the columns displayed
        """

        column_data = []
        for column in columns:
            to_add = {}
            to_add['id'] = column
            to_add['type'] = 'text'
            if case_norm:
                to_add['name'] = column.capitalize()
            else:
                to_add['name'] = column
            column_data.append(to_add)

        return column_data

    # returns the data and columns for the nodes table
    def get_graph_table_nodes(self, graph):
        """Function which returns the node and column data for use in a Dash DataTable.

        Args:
            graph (DiGraph): graph to construct data from
        """

        nodes = list(graph.nodes.data())
        columns = NODE_TABLE_COLUMNS
        table_data = pd.DataFrame(columns=columns)
        column_data = self.convert_columns(columns)
        # print(nodes)

        if len(nodes) != 0:
            values = []
            for node in nodes:
                values.append(list(node[1]['data'].values()))

            values = np.transpose(np.array(values)).tolist()
            to_build = []
            for x in range(len(columns)):
                to_build.append((columns[x], values[x]))

            table_data = pd.DataFrame(OrderedDict(to_build))

        return [table_data, column_data]

    def get_graph_table_edges(self, graph):
        """Function which returns the edge and column data for use in a Dash DataTable.

        Arguments:
            graph (DiGraph):
                graph to construct data from
        """

        edges = list(graph.edges.data())
        columns = EDGE_TABLE_COLUMNS
        table_data = pd.DataFrame(columns=columns)
        column_data = self.convert_columns(columns)

        if len(edges) != 0:
            values = []
            for edge in edges:
                values.append(list(edge[2]['data'].values()))

            values = np.transpose(np.array(values)).tolist()
            to_build = []
            for x in range(len(columns)):
                to_build.append((columns[x], values[x]))

            table_data = pd.DataFrame(OrderedDict(to_build))

        return [table_data, column_data]

    def color_image_graph(self, graph_in):
        """Function which takes any graph containing sequence components
        and returns a new colored graph based on predefined constants.

        Arguments:
            graph_in (DiGraph):
                graph to construct data from
        """

        colored_graph = graph_in.copy()
        nodes = list(colored_graph.nodes.data())
        edges = list(colored_graph.edges.data())
        node_colors = {}
        edge_colors = {}
        for node in nodes:
            node_colors[node[0]] = TYPE_COLORS[node[1]['node_type']]
            # node_images[node[0]] = getNodeImage(node[1]['node_type'])
        for edge in edges:
            color = TYPE_COLORS[edge[2]['data']['link_type']]
            edge_colors[(edge[0], edge[1])] = color

        nx.set_node_attributes(colored_graph, node_colors, 'color')
        nx.set_edge_attributes(colored_graph, edge_colors, 'color')
        # nx.set_node_attributes(colored_graph, node_images, 'image')
        return colored_graph

    def graph_to_topology(self):
        """Function which serializes the class's current data field to a dictionary for export or other use."""

        graph = self.data.copy()
        nodes = list(graph.nodes.data())
        edges = list(graph.edges.data())
        q_delay = self.qc_tdm.copy()
        c_delay = self.cc_delays.copy()

        nodes_top = []

        for node in nodes:
            nodes_top.append(
                {
                    'name': node[1]['label'],
                    'type': node[1]['node_type']
                }
            )

        qconnections = []

        for edge in edges:
            qconnections.append(
                {
                    'node1': edge[2]['data']['source'],
                    'node2': edge[2]['data']['target'],
                    'attenuation': edge[2]['data']['attenuation'],
                    'distance': edge[2]['data']['distance']
                }
            )

        output = {
            'nodes': nodes_top,
            'qconnections': qconnections,
            'cchannels_table': {
                'type': 'RT',
                'labels': list(c_delay.columns),
                'table': c_delay.to_numpy().tolist()
            },
            'qchannels_table': {
                'type': 'RT',
                'labels': list(q_delay.columns),
                'table': q_delay.to_numpy().tolist()
            }
        }

        return output

    def _callback_add_node(self, add_node_name, add_node_type):
        """Function which adds a node with the given name and type to the current graph.

        Args:
            add_node_name (str):
                a string identifier for the node (must be unique)
            add_node_type (str):
                the type of the node to be added (must be of recognized type)
        """

        if add_node_name is None:
            raise PreventUpdate

        new_graph = self.data.copy()
        nodes = new_graph.nodes

        # Check to see if node with that name already exists
        # If it does, error
        for data in nodes:
            if data == add_node_name:
                return [dash.no_update, 'Node already exists']

        new_node = GraphNode(add_node_name, add_node_type, 'test')
        new_graph.add_node(
            add_node_name,
            label=add_node_name,
            node_type=add_node_type,
            data=new_node.__dict__
        )
        self.data = new_graph
        return [nx.readwrite.cytoscape_data(self.data)['elements'], '']

    def _callback_add_edge(self, node_from, node_to, attributes):
        """Function which adds a new edge between two existing nodes with the given source, destination, and attributes.

        Arguments:
            node_from (str):
                a string identifier for the source of the edge (must exist)
            node_to (str):
                a string identifier for the destination of the edge (must exist)
            attributes (List):
                a list of attributes of the given edge
                (must be json serializable)
        """

        # Check if input was given, if not, silently do nothing
        if (node_from is None) or (node_to is None):
            raise PreventUpdate

        # Check if given edges are already in the network, if yes give error
        if self.data.has_edge(node_from, node_to):
            return [dash.no_update, 'Edge already exists']

        new_graph = self.data.copy()
        new_graph.add_edge(node_from, node_to, data=attributes)
        self.data = new_graph

        return [nx.readwrite.cytoscape_data(self.data)['elements'], '']

    def edit_node(self, data_in):
        new_graph = self.data.copy()
        nx.set_node_attributes(new_graph, )
        self.data = new_graph
        return [nx.readwrite.cytoscape_data(self.data)['elements'], '']

    # Takes the 'children' value from a callback and returns it as a
    # python dictionary that follows the format of a node in the graph
    def parse_edge(self, from_node, to_node, type_in, children):
        """Function which parses input for a new edge given by the user.
        Returns it as a python dictionary that follows the format of a Cytoscape edge.

        Args:
            from_node (str):
                a string identifier for the source of the edge (must exist)
            to_node (str):
                a string identifier for the destination of the edge (must exist)
            type_in (str):
                a string (Classical or Quantum) which identifies the type of edge
            children (Dict[any,any]):
                raw user input read from the edge_properties form in menu
        """

        if (from_node is None) or (to_node is None) or (children is None):
            raise PreventUpdate
        output = EDGE_DICT_ORDER.copy()

        for x in children:
            if x['type'] == 'Input':
                out = x['props']['value']
                output['_'.join(x['props']['id'].split('_')[:-1])] = out
        output['source'] = from_node[6:]
        output['target'] = to_node[4:]
        output['link_type'] = type_in
        return output

    def parse_node(self, children):
        """Function which parses input given by the user for a new node.
        Returns it as a python dictionary that follows the format of a Cytoscape node

        Args:
            children (Dict[any,any]):
                raw user input read from the edge_properties form in menu
        """

        values = {}

        if children is not None:
            for x in children:
                try:
                    if(x['props']['className'] == 'compound'):
                        parsed_val = 1
                        key = ''
                        child = ''
                        for y in x['props']['children']:
                            try:
                                child = y['props']['children']
                                key = child['props']['className']
                            except Exception:
                                continue
                            parsed_val *= float(child['props']['value'])
                        values[key] = parsed_val
                except Exception:
                    continue
                if(x['type'] == 'Input' or x['type'] == 'Dropdown'):
                    values[x['props']['className']] = x['props']['value']

            # print(values)
            output = values
            return output

        return 'No Input'

    def parse_edit(self, children):
        """Function which parses input from the edit menu.

        Args:
            children (Dict[any,any]):
                raw user input read from the edge_properties form in menu
        """

        output = {}
        data = children['props']['children']
        for x in data:
            values = x['props']['children'][1]['props']['children']['props']
            output[values['className']] = values['value']
        return output

    def clean_directory(self):
        """Function which clears the program root directory of temporary files."""

        if os.path.exists(DIRECTORY+'/sequence_data.zip'):
            os.remove(DIRECTORY+'/sequence_data.zip')
        if os.path.exists(DIRECTORY+'/templates.json'):
            os.remove(DIRECTORY+'/templates.json')
        if os.path.exists(DIRECTORY+'/simulation.json'):
            os.remove(DIRECTORY+'/simulation.json')
        if os.path.exists(DIRECTORY+'/topology.json'):
            os.remove(DIRECTORY+'/topology.json')
        return

    def save_all(self, path):
        """Function which saves all parts of the gui to a file (Topology, Templates, and Simulations).

        Args:
            path (str):
                file path to where output should be saved
        """

        new_path = path + '/data'
        if not os.path.exists(DIRECTORY+'/data'):
            os.mkdir(DIRECTORY+'/data')

        self.save_templates(new_path)
        self.save_simulation(new_path)
        self.save_topology(new_path)
        return new_path

    def save_topology(self, path):
        """Function which saves the topology of the GUI.

        Args:
            path (str):
                file path to where output should be saved
        """

        with open(path+'/topology.json', 'w') as outfile:
            json.dump(
                self.graph_to_topology(),
                outfile,
                quote_keys=True,
                sort_keys=True,
                indent=4,
                trailing_commas=False
            )
        outfile.close()
        return path + '/topology.json'

    def save_simulation(self, path):
        """Function which saves the simulation parameters of the GUI.

        Args:
            path (str):
                file path to where output should be saved
        """

        with open(path+'/simulation.json', 'w') as outfile:
            json.dump(
                self.sim_params,
                outfile,
                quote_keys=True,
                sort_keys=True,
                indent=4,
                trailing_commas=False
            )
        outfile.close()
        return path + '/simulation.json'

    def save_templates(self, path):
        """Function which saves the templates of the GUI.

        Args:
            path (str):
                file path to where output should be saved
        """

        with open(path+'/templates.json', 'w') as outfile:
            json.dump(
                self.templates,
                outfile,
                quote_keys=True,
                sort_keys=True,
                indent=4,
                trailing_commas=False
            )
        outfile.close()
        return path+'/templates.json'

    def get_app(self, name):
        """Function which builds an instance of the GUI as a Dash app.

        Note: All callback functions are defined within the the get_app function.

        Args:
            vis_opts (Dict[str,any]):
                optional visualization parameters for the network graph
        """

        # create the app
        CSS = [
            dbc.themes.BOOTSTRAP,
            'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.5.0/font/bootstrap-icons.css'  # nopep8
        ]
        external_scripts = [

        ]
        app = dash.Dash(
            __name__,
            external_stylesheets=CSS,
            external_scripts=external_scripts,
            title='SeQUeNCe',
            suppress_callback_exceptions=True
        )

        # define layout
        table_data, table_columns = self.get_graph_table_nodes(self.data)
        table_data = table_data.to_dict('records')
        table_graph = (table_data, table_columns)

        table_data = self.cc_delays.copy()
        table_columns = self.convert_columns(
            list(self.cc_delays.columns),
            case_norm=False
        )
        table_delays = (table_data, table_columns)

        table_data = self.qc_tdm.copy()
        table_columns = self.convert_columns(
            list(self.qc_tdm.columns),
            case_norm=False
        )
        table_tdm = (table_data, table_columns)

        app.layout = get_app_layout(
            self.data,
            table_graph,
            table_delays,
            table_tdm,
            name
        )

        @app.callback(
            
            Output('graph', 'elements'),
            Output('make_node_error', 'children'),
            Output('make_edge_error', 'children'),
            Output('all_nodes', 'data'),
            Output('legend', 'children'),

            Input('add_node', 'n_clicks'),
            Input('add_edge', 'n_clicks'),
            Input('new_network', 'n_clicks'),
            Input('refresh', 'n_clicks'),
            Input('submit_edit', 'n_clicks'),
            Input('delete_button', 'n_clicks'),

            State('node_to_add_name', 'value'),
            State('type_menu', 'value'),
            State('edge_properties', 'children'),
            State('from_node', 'value'),
            State('to_node', 'value'),
            State('edge_type_menu', 'value'),
            State('selected_element', 'children'),
            State('last_clicked', 'data')
        )
        def edit_graph(
            node_state,
            edge_state,
            new_net,
            refresh,
            submit_edit,
            delete_b,
            node_name,
            node_to_add_type,
            properties,
            from_node,
            to_node,
            edge_type,
            selected,
            last_clicked
        ):
            ctx = dash.callback_context
            if not ctx.triggered:
                # print("No trigger")
                data = nx.readwrite.cytoscape_data(self.data)['elements']
                nodes = list(self.data.nodes())
                legend_vals = list(self.data.nodes.data())
                legend_vals = [x[1]['node_type'] for x in legend_vals]
                legend = makeLegend(set(legend_vals))
                return [
                    data,
                    '',
                    '',
                    nodes,
                    legend
                ]
            else:
                input_id = ctx.triggered[0]['prop_id'].split('.')[0]
                # print(input_id)
                if input_id == 'add_node':
                    info = self._callback_add_node(node_name, node_to_add_type)
                    graph_data = info[0]
                    err_msg = info[1]
                    nodes = list(self.data.nodes())
                    legend_vals = list(self.data.nodes.data())
                    legend_vals = [x[1]['node_type'] for x in legend_vals]
                    legend = makeLegend(set(legend_vals))
                    return [
                        graph_data,
                        err_msg,
                        dash.no_update,
                        nodes,
                        legend
                    ]
                elif input_id == 'add_edge':
                    info = self._callback_add_edge(
                        from_node,
                        to_node,
                        self.parse_edge(
                            from_node,
                            to_node,
                            edge_type,
                            properties
                        )
                    )
                    graph_data = info[0]
                    err_msg = info[1]
                    nodes = list(self.data.nodes())
                    legend_vals = list(self.data.nodes.data())
                    legend_vals = [x[1]['node_type'] for x in legend_vals]
                    legend = makeLegend(set(legend_vals))
                    return [
                        graph_data,
                        dash.no_update,
                        err_msg,
                        nodes,
                        legend
                    ]
                elif input_id == 'new_network':
                    self.data = nx.empty_graph(create_using=nx.DiGraph())
                    nodes = list(self.data.nodes())
                    legend_vals = list(self.data.nodes.data())
                    legend_vals = [x[1]['node_type'] for x in legend_vals]
                    legend = makeLegend(set(legend_vals))
                    return [
                        nx.readwrite.cytoscape_data(self.data)['elements'],
                        '',
                        '',
                        nodes,
                        legend
                    ]
                elif input_id == 'refresh':
                    nodes = list(self.data.nodes())
                    legend_vals = list(self.data.nodes.data())
                    legend_vals = [x[1]['node_type'] for x in legend_vals]
                    legend = makeLegend(set(legend_vals))
                    return [
                        nx.readwrite.cytoscape_data(self.data)['elements'],
                        dash.no_update,
                        dash.no_update,
                        nodes,
                        legend
                    ]
                elif input_id == 'submit_edit':
                    # print(selected)
                    edited = self.parse_edit(selected)
                    if 'source' in edited:
                        src = last_clicked['source']
                        trgt = last_clicked['target']
                        new_data = {k: edited[k] for k in EDGE_DICT_ORDER}
                        self.data.edges[src][trgt]['data'] = new_data
                        gd = nx.readwrite.cytoscape_data(self.data)['elements']
                        err_msg = ''
                        nodes = list(self.data.nodes())
                        legend_vals = list(self.data.nodes.data())
                        legend_vals = [x[1]['node_type'] for x in legend_vals]
                        legend = makeLegend(set(legend_vals))
                        return [
                            gd,
                            dash.no_update,
                            err_msg,
                            nodes,
                            legend
                        ]
                    else:
                        old_name = last_clicked['name']
                        self.data.nodes[old_name]['data'] = edited
                        self.data.nodes[old_name]['node_type'] = edited['type']
                        self.data = nx.relabel_nodes(
                            self.data,
                            {old_name: edited['name']}
                        )
                        gd = nx.readwrite.cytoscape_data(self.data)['elements']
                        err_msg = ''
                        nodes = list(self.data.nodes())
                        legend_vals = list(self.data.nodes.data())
                        legend_vals = [x[1]['node_type'] for x in legend_vals]
                        legend = makeLegend(set(legend_vals))
                        return [
                            gd,
                            err_msg,
                            dash.no_update,
                            nodes,
                            legend
                        ]
                elif input_id == 'delete_button':
                    to_delete = self.parse_edit(selected)
                    if 'name' in to_delete:
                        to_delete = to_delete['name']
                        new_graph = self.data.copy()
                        new_graph.remove_node(to_delete)
                        self.data = new_graph
                    else:
                        new_graph = self.data.copy()
                        source = to_delete['source']
                        target = to_delete['target']
                        new_graph.remove_edge(source, target)
                        self.data = new_graph

                    nodes = list(self.data.nodes())
                    legend_vals = list(self.data.nodes.data())
                    legend_vals = [x[1]['node_type'] for x in legend_vals]
                    legend = makeLegend(set(legend_vals))
                    return [
                        nx.readwrite.cytoscape_data(self.data)['elements'],
                        '',
                        '',
                        nodes,
                        legend
                    ]

        @app.callback(
            Output('graph_table', 'data'),
            Output('graph_table', 'columns'),
            Input('toggle_nodes', 'n_clicks'),
            Input('toggle_edges', 'n_clicks')
        )
        def show_nodes(toggleN, toggleE):
            ctx = dash.callback_context
            if not ctx.triggered:
                return [self.edge_table, self.edge_columns]
            else:
                input_id = ctx.triggered[0]['prop_id'].split('.')[0]
                # print(input_id)
                if input_id == 'toggle_nodes':
                    return [self.node_table, self.node_columns]
                elif input_id == 'toggle_edges':
                    return [self.edge_table, self.edge_columns]

        # EDIT #
        @app.callback(
            Output('selected_element', 'children'),
            Output('graph', 'tapNodeData'),
            Output('graph', 'tapEdgeData'),
            Output('last_clicked', 'data'),
            Input('graph', 'tapNodeData'),
            Input('graph', 'tapEdgeData'),
        )
        def update_selection(tapped_node, tapped_edge):
            ctx = dash.callback_context
            input_id = ctx.triggered[0]['prop_id'].split('.')[1]

            if tapped_node is None and tapped_edge is None:
                raise PreventUpdate
            elif input_id == 'tapNodeData':
                parsed = json.loads(tapped_node['data'])
                out = getSelectedNodeMenu(
                    parsed,
                    self.templates[tapped_node['data']['type']]
                )
                val = tapped_node['data'].copy()
                return [out, None, None, val]
            elif input_id == 'tapEdgeData':
                parsed = json.loads(tapped_edge['data'])
                out = getSelectedEdgeMenu(
                    parsed,
                    self.data.nodes,
                    ['Quantum', 'Classical']
                )
                val = tapped_edge['data'].copy()
                return [out, None, None, val]
            else:
                out = html.Pre('Select a graph element to view')
                return [out, dash.no_update, dash.no_update, dash.no_update]

        @app.callback(
            Output('edge_properties', 'children'),
            Input('edge_type_menu', 'value'),
        )
        def make_edge_properties_menu(edgeType):
            if edgeType == 'Quantum':
                return quantum_edge
            elif edgeType == 'Classical':
                return classic_edge
            else:
                return dash.no_update

        @app.callback(
            Output('template_properties', 'children'),
            Output('save_state', 'children'),
            Output('comp_temp', 'data'),
            Output('detec_opts', 'data'),

            Input('template_type_menu', 'value'),
            Input('save_template', 'n_clicks'),

            State('template_properties', 'children'),
            State('template_type_menu', 'value'),
            State('template_name', 'value')
        )
        def template_menu(edgeType, save_click, temp, temp_type, temp_name):
            ctx = dash.callback_context
            input_id = ctx.triggered[0]['prop_id'].split('.')[0]
            if input_id == 'template_type_menu':
                if edgeType == 'Quantum_Router':
                    opts = list(self.templates['Memory'].keys())
                    return [router_template, '', opts, '']
                elif edgeType == 'Protocol':
                    return [protocol_template, '', '', '']
                elif edgeType == 'Memory':
                    return [quantum_memory_template, '', '', '']
                elif edgeType == 'Detector':
                    return [detector_template, '', '', '']
                elif edgeType == 'BSM_node':
                    opts = list(self.templates['Detector'].keys())
                    return [bsm_template, '', '', opts]
            elif input_id == 'save_template':
                if temp is None or temp_name is None:
                    return [dash.no_update, '', '', '']
                else:
                    new_templates = self.templates.copy()
                    parsed = {temp_name: self.parse_node(temp)}
                    new_templates[temp_type].update(parsed)
                    self.templates = new_templates
                    return [dash.no_update, 'Template Saved', '', '']
            else:
                opts = list(self.templates['Memory'].keys())
                return [router_template, '', opts, '']

        @app.callback(
            Output('running', 'disabled'),
            Output('runtime', 'children'),
            Output('simtime', 'children'),
            Output('results_out', 'children'),

            Input('run_sim', 'n_clicks'),
            Input('running', 'n_intervals'),

            State('runtime', 'children'),
            State('time_units_sim', 'value'),
            State('sim_time_in', 'value'),
            State('logging_verbosity', 'value'),
            State('sim_name', 'value')
        )
        def run_sim(clicks, n, runtime, units, time_to_run, logging, sim_name):
            ctx = dash.callback_context
            input_id = ctx.triggered[0]['prop_id'].split('.')[0]

            if input_id == 'run_sim':
                if time_to_run is None or units is None or sim_name is None:
                    return [dash.no_update, '', '', '']
                else:
                    if(not self.simulation.timeline.is_running):
                        self.simulation = GUI_Sim(
                            int(time_to_run),
                            int(units),
                            logging,
                            sim_name,
                            self
                        )
                        self.simulation.init_logging()
                        self.simulation.random_request_simulation()
                        func = self.simulation.timeline.run
                        toRun = threading.Thread(
                            target=func,
                            name="run_simulation"
                        )
                        toRun.start()
                        print('start')
                        return [False, '00:00:00', '', '']
                    else:
                        self.simulation.timeline.stop()
                        print('stop')
                        return [True, '', '', '']
            elif input_id == 'running':
                if self.simulation.timeline.is_running:
                    h, m, s = runtime.split(':')
                    current_time = int(
                        datetime.timedelta(
                            hours=int(h),
                            minutes=int(m),
                            seconds=int(s)
                        ).total_seconds()
                    )
                    current_time += 1
                    str_time = time.gmtime(current_time)
                    new_runtime = time.strftime('%H:%M:%S', str_time)
                    new_simtime = self.simulation.getSimTime()

                    return [dash.no_update, new_runtime, new_simtime, '']
                else:
                    self.simulation.write_to_file()
                    sim_results = self.simulation.sim_name + '_results.txt'

                    with open(DIRECTORY + '/'+sim_results, 'r') as outfile:
                        sim_results = outfile.read()
                    outfile.close()
                    return [True, dash.no_update, dash.no_update, sim_results]
            else:
                return [True, '', '', '']

        @app.callback(
            Output("download", "data"),
            Input('export_all', 'n_clicks'),
            Input('export_topo', 'n_clicks'),
            Input('export_templ', 'n_clicks'),
            Input('export_sim', 'n_clicks'),
            prevent_initial_call=True,
        )
        def export_data(all, top, temp, sim):
            ctx = dash.callback_context
            input_id = ctx.triggered[0]['prop_id'].split('.')[0]
            self.clean_directory()

            if input_id == 'export_all':
                path = self.save_all(DIRECTORY)

                shutil.make_archive(
                    base_name=DIRECTORY+'/sequence_data',
                    format='zip',
                    root_dir=path,
                )
                shutil.rmtree(path)
                return dcc.send_file(DIRECTORY + '/sequence_data.zip')
            elif input_id == 'export_topo':
                return dcc.send_file(self.save_topology(DIRECTORY))
            elif input_id == 'export_templ':
                return dcc.send_file(self.save_templates(DIRECTORY))
            elif input_id == 'export_sim':
                return dcc.send_file(self.save_simulation(DIRECTORY))

        @app.callback(
            [Output(f"tab-{i}", "style") for i in range(len(tab_ids))],
            Output('side_click', 'data'),
            Output('page-content', 'style'),
            Output('project_name', 'style'),
            Output('refresh', 'style'),
            
            Input("btn_sidebar", "n_clicks"),

            State('side_click', 'data')
        )
        def toggle_sidebar(n, nclick):
            ctx = dash.callback_context
            input_id = ctx.triggered[0]['prop_id'].split('.')[0]
            if input_id == 'btn_sidebar':
                if nclick == "SHOW":
                    styles = [MENU_STYLE for i in range(len(tab_ids))]
                    styles.append('HIDDEN')
                    styles.append(GRAPH_DIV_STYLE)
                    styles.append(PROJECT)
                    styles.append(REFRESH)
                else:
                    styles = [MENU_STYLE_H for i in range(len(tab_ids))]
                    styles.append('SHOW')
                    styles.append(GRAPH_DIV_STYLE_H)
                    styles.append(PROJECT_H)
                    styles.append(REFRESH_H)
            else:
                styles = [MENU_STYLE for i in range(len(tab_ids))]
                styles.append('HIDDEN')
                styles.append(GRAPH_DIV_STYLE)
                styles.append(PROJECT)
                styles.append(REFRESH)

            return styles

        @app.callback(
            Output("from_node", "options"),
            Output("to_node", "options"),
            Input('all_nodes', 'data'),
        )
        def updateNodeMenus(nodes):
            options = makeDropdownOptions(nodes)
            return [options, options]

        @app.callback(
            Output("selected_template", "options"),
            Input('selected_node_type', 'value'),
        )
        def updateNodeTypeMenu(type_in):
            templates = list(self.templates[type_in].keys())
            return makeDropdownOptions(templates)

        @app.callback(
            Output("add_template_menu", "options"),
            Output("add_template_menu", "value"),
            Input('type_menu', 'value'),
        )
        def updateNodeTempMenu(type_in):
            templates = list(self.templates[type_in].keys())
            return [makeDropdownOptions(templates), templates[0]]

        @app.callback(
            Output("mem_type", "options"),
            Output("mem_type", "value"),
            Input('comp_temp', 'data'),
            prevent_initial_call=True,
        )
        def updateTypeMenu(data):
            return [makeDropdownOptions(data), data[0]]

        @app.callback(
            Output("detec_type", "options"),
            Input('detec_opts', 'data'),
            prevent_initial_call=True,
        )
        def updateTypeMenu(data):
            return makeDropdownOptions(data)

        return app
