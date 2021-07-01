"""
A Class which contains all of the logic and data for the GUI
"""

import dash, os, json5
from .menus import *
from .simulator_bindings import gui_sim
import pandas as pd
import numpy as np
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import networkx as nx
from collections import OrderedDict
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State
from .graph_comp import GraphNode
from .layout import get_app_layout, getNodeImage, DEFAULT_COLOR, TYPE_COLORS, TYPE_IMAGES, TYPES

EDGE_DICT_ORDER = OrderedDict({'source' : '', 'target' : '', 'distance' : '', 'attenuation' : '', 'link_type':''})

DIRECTORY, _ = os.path.split(__file__)

#---------Miscelaneous Methods---------#
def convert_columns(columns, case_norm=True):
    column_data=[]
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
def get_graph_table_nodes(graph):
    nodes = list(graph.nodes.data())
    columns = list(nodes[0][1]['data'].keys())
    values=[]
    for node in nodes:
        values.append(list(node[1]['data'].values()))

    values=np.transpose(np.array(values)).tolist()
    to_build=[]
    for x in range(len(columns)):
        to_build.append((columns[x],values[x]))

    table_data = pd.DataFrame(OrderedDict(to_build))
    column_data = convert_columns(columns)

    return [table_data, column_data]

# returns the data and columns for the edges table
def get_graph_table_edges(graph):
    edges = list(graph.edges.data())
    columns = list(edges[0][2]['data'].keys())
    values=[]
    for edge in edges:
        values.append(list(edge[2]['data'].values()))

    values=np.transpose(np.array(values)).tolist()
    to_build=[]
    for x in range(len(columns)):
        to_build.append((columns[x],values[x]))

    table_data = pd.DataFrame(OrderedDict(to_build))
    column_data = []

    for column in columns:
        column_data.append({
            'id': column,
            'name': column.capitalize(),
            'type': 'text'
        })

    return [table_data, column_data]

# class
class Quantum_GUI:
    def __init__(self, graph_in, templates=None, delays=None, tdm=None):
        self.data = graph_in
        self.net_delay_times = delays
        self.qc_tdm = tdm
        self.defaults = {}
        with open(DIRECTORY + '/default_params.json', 'r') as json_file:
            self.defaults = json5.load(json_file)
        if templates is None:
            if(os.path.exists(DIRECTORY + '/user_templates.json')):
                with open(DIRECTORY + '/user_templates.json', 'r') as json_file:
                    self.templates = json5.load(json_file)
            else:
                user_defaults = {}
                for x in TYPES:
                    user_defaults[x] = {}
                self.templates = user_defaults
                with open(DIRECTORY + '/user_templates.json', 'w') as outfile: 
                    json5.dump(user_defaults, outfile, quote_keys=True, sort_keys=True, indent=4, trailing_commas=False)

    @property
    def data(self):
        return self._data
    @data.setter
    def data(self, graph_in):
        self._data = self.colorImageGraph(graph_in)
        edges = get_graph_table_edges(self._data)
        nodes = get_graph_table_nodes(self._data)
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
            json5.dump(templates_in, outfile, quote_keys=True, sort_keys=True, indent=4, trailing_commas=False)

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

    def colorImageGraph(self, graph_in):
        colored_graph = graph_in.copy()
        nodes = list(colored_graph.nodes.data())
        edges = list(colored_graph.edges.data())
        node_colors={}
        edge_colors={}
        node_images={}
        for node in nodes:
            node_colors[node[0]] = TYPE_COLORS[node[1]['node_type']]
            #node_images[node[0]] = getNodeImage(node[1]['node_type'])
        for edge in edges:
            edge_colors[(edge[0], edge[1])] = TYPE_COLORS[edge[2]['data']['link_type']]

        nx.set_node_attributes(colored_graph, node_colors, 'color')
        nx.set_edge_attributes(colored_graph, edge_colors, 'color')
        #nx.set_node_attributes(colored_graph, node_images, 'image')
        return colored_graph

    def _callback_add_node(self, add_node_name, add_node_type):
        if add_node_name is None:
            raise PreventUpdate
        
        new_graph=self.data.copy()
        nodes = new_graph.nodes

        #Check to see if node with that name already exists
        #If it does, error
        for data in nodes:
            try:
                if data == add_node_name:
                    return [dash.no_update, 'Node already exists']
            except:
                continue
        
        new_node = GraphNode(add_node_name, add_node_type)
        new_graph.add_node(add_node_name, label=add_node_name, node_type=add_node_type, data=new_node.__dict__)
        self.data=new_graph
        return [nx.readwrite.cytoscape_data(self.data)['elements'], '']

    def _callback_add_edge(self, node_from, node_to, attributes):
        # Check if input was given, if not, silently do nothing
        if((node_from is None) or (node_to is None)):
            raise PreventUpdate
        
        # Check if given edges are already in the network, if yes give error
        if self.data.has_edge(node_from, node_to):
            return [dash.no_update, 'Edge already exists']

        new_graph=self.data.copy()
        new_graph.add_edge(node_from, node_to, data=attributes)
        self.data=new_graph

        return [nx.readwrite.cytoscape_data(self.data)['elements'], '']

    # Takes the 'children' value from a callback and returns it as a 
    # python dictionary that follows the format of a node in the graph
    def parse_children_to_node_data(self, from_node, to_node, type_in, children):
        if((from_node is None) or (to_node is None) or (children is None)):
            raise PreventUpdate
        output = EDGE_DICT_ORDER.copy()
        labels = []
        values = []

        for x in children:
            if(x['type']=='Input'):
                output['_'.join(x['props']['id'].split('_')[:-1])] = x['props']['value']
        output['source']=from_node[6:]
        output['target']=to_node[4:]
        output['link_type']=type_in
        return output

    def parse_children_to_form_data(self, children):
        values = {}

        if children is not None:
            for x in children:
                try:
                    if(x['props']['className']=='compound'):
                        parsed_val = 1
                        key = ''
                        for y in x['props']['children']:
                            try:
                                key = y['props']['children']['props']['className']
                            except:
                                continue
                            parsed_val*=float(y['props']['children']['props']['value'])
                        values[key]=parsed_val
                except:
                    continue
                if(x['type']=='Input'):
                    values[x['props']['className']]=x['props']['value']

            template_name = values['name']
            del values['name']
            output = {template_name:values}
            return output
        return('No Input')

    def _callback_delete_node(self, graph_data, remove_node_list):
        
        return graph_data

    def get_app(self, vis_opts=None):
        # create the app
        external_scripts = [

        ]
        app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP], external_scripts=external_scripts)

        # define layout
        table_data,table_columns = get_graph_table_nodes(self.data)
        table_data=table_data.to_dict('records')
        table_graph = (table_data,table_columns)

        table_data = self.net_delay_times.to_dict('records')
        table_columns = convert_columns(list(self.net_delay_times.columns), case_norm=False)
        table_delays= (table_data,table_columns)

        table_data = self.qc_tdm.to_dict('records')
        table_columns = convert_columns(list(self.qc_tdm.columns), case_norm=False)
        table_tdm = (table_data,table_columns)

        app.layout = get_app_layout(self.data, table_graph, table_delays, table_tdm, vis_opts=vis_opts)

        @app.callback(
            [Output('graph', 'elements'),
            Output('make_node_error', 'children'),
            Output('make_edge_error', 'children')],
            [Input('add_node', 'n_clicks'),
            Input('add_edge', 'n_clicks')],
            state=[
                State('node_to_add_name', 'value'),
                State('type_menu', 'value'),
                State('edge_properties','children'),
                State('from_node', 'children'),
                State('to_node', 'children'),
                State('edge_type_menu', 'value')
                ]
        )
        def edit_graph(add_node_submit_state, add_edge_submit_state, node_to_add_name, node_to_add_type, properties, from_node, to_node, edge_type):
            ctx = dash.callback_context
            if not ctx.triggered:
                #print("No trigger")
                return [nx.readwrite.cytoscape_data(self.data)['elements'], '', '']
            else:
                input_id = ctx.triggered[0]['prop_id'].split('.')[0]
                #print(input_id)
                if input_id == 'add_node':
                    info = self._callback_add_node(node_to_add_name, node_to_add_type)
                    graph_data = info[0]
                    err_msg = info[1]
                    return [graph_data, err_msg, dash.no_update]
                elif input_id == 'add_edge':
                    info = self._callback_add_edge(from_node[6:], to_node[4:], self.parse_children_to_node_data(from_node, to_node, edge_type, properties))
                    graph_data = info[0]
                    err_msg = info[1]
                    return [graph_data, dash.no_update, err_msg]
        
        @app.callback(
            Output('graph_table','data'),
            Output('graph_table','columns'),
            Input('toggle_nodes','n_clicks'),
            Input('toggle_edges','n_clicks')
        )
        def show_nodes(toggleN, toggleE):
            ctx = dash.callback_context
            if not ctx.triggered:
                return [self.edge_table,self.edge_columns]
            else:
                input_id = ctx.triggered[0]['prop_id'].split('.')[0]
                #print(input_id)
                if input_id == 'toggle_nodes':
                    return [self.node_table,self.node_columns]
                elif input_id =='toggle_edges':
                    return [self.edge_table,self.edge_columns]

        @app.callback(
            Output('select_node_1','active'),
            Output('select_node_2','active'),
            Input('select_node_1','n_clicks'),
            Input('select_node_2','n_clicks'),
            state=[State('select_node_1','active'),
            State('select_node_2','active'),]
        )
        def toggle_select_node_1(toggle_node_1, toggle_node_2, state_1, state_2):
            ctx = dash.callback_context
            if not ctx.triggered:
                return [False,False]
            else:
                input_id = ctx.triggered[0]['prop_id'].split('.')[0]
                if input_id == 'select_node_1':
                    new_state=not state_1
                    #print('p1'+str(new_state))
                    return [new_state,False]
                elif input_id == 'select_node_2':
                    new_state=not state_2
                    #print('p2'+str(new_state))
                    return [False,new_state]

        @app.callback(
            Output('from_node','children'),
            Output('to_node', 'children'),
            Input('graph', 'tapNodeData'),
            state=[
                State('select_node_1','active'),
                State('select_node_2','active')
            ])
        def update_selected_nodes(tapped_node, toggle1, toggle2):
            if toggle1:
                return ['From: '+tapped_node['label'], dash.no_update]
            elif toggle2:
                return [dash.no_update, 'To: '+tapped_node['label']]
            else:
                return [dash.no_update, dash.no_update]

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
            Input('template_type_menu', 'value'),
        )
        def make_template_properties_menu(edgeType):
            if edgeType == 'Quantum_Router':
                return [router_template, '']
            elif edgeType == 'Protocol':
                return [protocol_template, '']
            elif edgeType == 'Memory':
                return [quantum_memory_template, '']
            elif edgeType == 'Detector':
                return [detector_template, '']
            else:
                return [dash.no_update, dash.no_update]

        @app.callback(
            Output('results_out', 'children'),
            Input('run_sim', 'n_clicks'),
            state=[
                State('time_units_sim', 'value'),
                State('sim_time', 'value')
            ]
        )
        def run_sim(clicks, units, time):
            if time is None or units is None:
                return dash.no_update
            else:
                simulation = gui_sim(int(time), int(units), 'test', self)
                simulation.random_request_simulation()
                results = open(DIRECTORY+'/'+'test.txt', 'r')
                output = results.read()
                #print(output)
                results.close()
                return output

        @app.callback(
            Output('save_state', 'children'),
            Input('save_template', 'n_clicks'),
            state=[
                State('template_properties', 'children'),
                State('template_type_menu', 'value')
            ]
        )
        def save_template(clicks, template, template_type):
            if template is None:
                return ''
            else:
                new_templates = self.templates.copy()
                parsed = self.parse_children_to_form_data(template)
                new_templates[template_type].update(parsed)
                print(new_templates)
                self.templates = new_templates
                return 'Template Saved'
                    
        return app