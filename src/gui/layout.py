"""
A Class which contains the layout of the dash application.
Can also be understood and the corresponding html for the
dash web app
"""

import os
import base64
import pandas as pd
import networkx as nx
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
from collections import OrderedDict
import dash_cytoscape as cyto
import dash_table
import plotly.express as px
from .menus import getFreqUnits, getTimeUnits

### Constants ###
DEFAULT_COLOR = '#97C2FC'
DIRECTORY, _ = os.path.split(__file__)

"""
Constant containing all available class in the GUI
"""
TYPES = [
    'Quantum_Repeater',
    'Quantum_Router',
    'Photon_Source',
    'Detector',
    'QuantumErrorCorrection',
    'BSM_node',
    'Temp',
    'Memory',
    'Protocol'
]

"""
Mapping of all types in the GUI to their representative colors
"""
TYPE_COLORS = {
    'Quantum_Repeater':'#4D9DE0',
    'Quantum_Router':'#E15554',
    'Photon_Source':'#E1BC29',
    'Detector':'#3BB273',
    'QuantumErrorCorrection':'#7768AE ',
    'BSM_node':'#FFC857',
    'Quantum':'#8634eb',
    'Classical':'#345feb',
    'Temp':'#084C61'
}

"""
returns a dictionary mapping each GUI node type
to its corresponding image in the current directory
structure
"""
def genImages():
    images = {
        'Quantum_Repeater':'repeater.png',
        'Quantum_Router':'router.png',
        'Photon_Source':'photonsource.png',
        'Detector':'detector.png',
        'QuantumErrorCorrection':'quantum.png',
        'BSM_node':'bsmnode.png',
        'Temp':'temp.png'
    }
    for key, value in images.items():
        path = os.path.join(DIRECTORY, 'assets', value)
        images[key] = path
    return images

"""
dictionary returned by running the genImages() function
"""
TYPE_IMAGES = genImages()

### HTML TEMPLATES ###

def fetch_flex_row_style():
    return {'display': 'flex', 'flex-direction': 'row', 'justify-content': 'center', 'align-items': 'center'}

def create_row(children, style=fetch_flex_row_style(), tight=True):
    return dbc.Row(children,
                   style=style,
                   #className='column flex-display',
                   no_gutters=tight)

def getNodeTable(data,columns):
    return dbc.Form(
        [
            dbc.Label('Graph Components'),
            dbc.Form(
                dbc.ButtonGroup(
                    [
                        dbc.Button('Nodes', id='toggle_nodes', color='primary'), dbc.Button('Edges', id='toggle_edges', color='primary')
                    ]
                )
            ),
            dbc.Form(
                [
                    dash_table.DataTable(
                        id='graph_table',
                        data=data,
                        columns=columns,
                        fixed_rows={'headers': True},
                        page_size=20,
                        style_table={'height': '300px', 'width':'600px', 'overflowY': 'auto'},
                        style_cell={'minWidth': 150, 'width': 150},
                        editable=True
                    )
                ]
            )
        ]
    )

add_node_form = dbc.Form(
    [
        dbc.Label('Name'),
        dbc.Input(id='node_to_add_name',type='Name', placeholder='Enter node Name'),
        html.P(id='make_node_error', style={'color': 'red'}),
        dbc.Label('Type'),
        dcc.Dropdown(
            id='type_menu',
            options=[
                {'label': 'Quantum Router', 'value': 'Quantum_Router'},
                {'label': 'Quantum Repeater', 'value': 'Quantum_Repeater'},
                {'label': 'BSM Node', 'value': 'BSM_node'},
                {'label': 'Quantum Error Correction', 'value': 'QuantumErrorCorrection'},
                {'label': 'Photon Source', 'value': 'Photon_Source'},
                {'label': 'Detector', 'value': 'Detector'},
                {'label': 'Temp', 'value': 'Temp'}
            ],
            value='Quantum_Router',
            style={'margin-bottom':'15px'}
        ),
        dbc.Button('Add Node', color='primary', id='add_node', block=True)
    ]
)

delete_menu = dbc.Form(
    [  
        dbc.Label('Delete'),
        dbc.FormGroup(
            [
                dbc.Button('Delete', color='primary', id='delete_button'),
            ]
        )
    ],
)

add_edge = dbc.Form(
    [
        dbc.FormGroup(
            [
                dbc.Col(dbc.Label('Node 1', html_for='from_node'), width=2),
                dbc.Col(dbc.Label(id='from_node', children='From: ')),
                dbc.Col(dbc.Button('select', color='primary', id='select_node_1', active=False, block=True, outline=False), width=4)
            ],
            row=True
        ),
        dbc.FormGroup(
            [
                dbc.Col(dbc.Label('Node 2', html_for='to_node'), width=2),
                dbc.Col(dbc.Label(id='to_node', children='To: ')),
                dbc.Col(dbc.Button('select', color='primary', id='select_node_2', active=False, block=True, outline=False),width=4)
            ],
            row=True
        ),
        dcc.Dropdown(
            id='edge_type_menu',
            options=
            [
                {'label': 'Quantum Connection', 'value': 'Quantum'},
                {'label': 'Classical Connection', 'value': 'Classical'},
            ],
            value='Quantum'
        ),
        dbc.FormGroup(
            id='edge_properties'
        ),
        html.P(id='make_edge_error', style={'color': 'red'}),
        dbc.Button('Add Edge', color='primary', id='add_edge', block=True),
        
    ]
)

make_new_template = dbc.Form(
    [
        dbc.Label('Template Type'),
        dcc.Dropdown(
            id='template_type_menu',
            options=[
                {'label': 'Quantum Router', 'value': 'Quantum_Router'},
                #{'label': 'Quantum Repeater', 'value': 'Quantum_Repeater'},
                #{'label': 'BSM Node', 'value': 'BSM_node'},
                #{'label': 'Quantum Error Correction', 'value': 'QuantumErrorCorrection'},
                #{'label': 'Photon Source', 'value': 'Photon_Source'},
                {'label': 'Detector', 'value': 'Detector'},
                {'label': 'Protocol', 'value': 'Protocol'},
                {'label': 'Quantum Memory', 'value': 'Memory'},
            ],
            value='Quantum_Router',
            style={'margin-bottom':'15px'}
        ),
        dbc.FormGroup(
            id='template_properties'
        ),
        dbc.Button('Save', color='primary', id='save_template', block=True),
        html.P(id='save_state', style={'color': 'blue'})
    ]
)

def delay_menu(data, columns):  
    return dbc.Form(
        [
            dbc.Form(
                    [
                        dash_table.DataTable(
                            id='delay_table',
                            data=data,
                            columns=columns,
                            fixed_rows={'headers': True},
                            #fixed_columns={'headers': True, 'data': 1},
                            page_size=20,
                            style_table={'height': '300px', 'width':'600px', 'overflowY': 'auto'},
                            style_cell={'minWidth': 150, 'width': 150},
                            editable=True
                        )
                    ]
                )
        ]
)

def tdm_menu(data, columns):  
    return dbc.Form(
        [
            dbc.Form(
                    [
                        dash_table.DataTable(
                            id='tdm_table',
                            data=data,
                            columns=columns,
                            fixed_rows={'headers': True},
                            #fixed_columns={'headers': True, 'data': 1},
                            page_size=20,
                            style_table={'height': '300px', 'width':'600px', 'overflowY': 'auto'},
                            style_cell={'minWidth': 150, 'width': 150},
                            editable=True
                        )
                    ]
                )
        ]
)

def manipulate_menu(delay_data, delay_columns, tdm_data, tdm_columns): 
    return dbc.Form(
        [   
            html.H5('Network'),
            dbc.Card(
                dbc.Tabs(
                [
                    dbc.Tab(add_node_form, label='Add Node'),
                    dbc.Tab(add_edge, label='Add Edge'),
                    dbc.Tab('This tabs content is never seen', label='Delete', disabled=True),
                    dbc.Tab(make_new_template, label='Templates'),
                    dbc.Tab(delay_menu(delay_data, delay_columns),label='Delay Times'),
                    dbc.Tab(tdm_menu(tdm_data, tdm_columns),label='TDM Times')
                ]
                )
            )
        ]
)

results_menu = dbc.Card(
            [
                html.H1("Results"),
                html.Pre(id='results_out'),
            ], style={'height': '600px', 'overflowY': 'auto'}
        )

simulation_menu = dbc.Form(
    [
        html.H5('Simulations'),
        dbc.Card(
            [
                dbc.Row(
                    [
                        dbc.Col(dbc.Input(id='sim_time', placeholder='Enter simulation time'), width=10),
                        dbc.Col(getTimeUnits('sim'), width=2),
                    ]
                ),
                
                dbc.Button('Run', color='primary', id='run_sim', block=True)
            ]
        ),
        results_menu
    ], className='card', style={'padding': '5px', 'background': '#e5e5e5'}
)
    

def getLogoHeader():
    image_filename = os.path.join(DIRECTORY, 'assets', 'sequence.jpg')
    encoded_image = base64.b64encode(open(image_filename, 'rb').read())
    return create_row([html.Img(src='data:image/png;base64,{}'.format(encoded_image.decode()), width='80px', style={'border-radius':'20%'}),  html.H1('SeQUeNCe', style={'font-family':'helvetica'})], tight=False)

def getNodeImage(node_type):
    image_filename = TYPE_IMAGES[node_type]
    encoded_image = base64.b64encode(open(image_filename, 'rb').read())
    return 'data:image/png;base64,{}'.format(encoded_image.decode())

### Generate HTML Layout ###
def get_app_layout(graph_data, graph_table, delay_table, tdm_table, vis_opts=None):
    return html.Div([
            getLogoHeader(),
            create_row([
                # setting panel
                dbc.Col([
                    dbc.Form([
                        # ---- Manipulation section ----
                        manipulate_menu(delay_table[0], delay_table[1], tdm_table[0], tdm_table[1]),
                        # ---- Node Table section ----
                        getNodeTable(graph_table[0], graph_table[1])
                    ], className='card', style={'padding': '5px', 'background': '#e5e5e5'}),
                ],width=3, style={'display': 'flex', 'justify-content': 'left', 'align-items': 'center'}),
                # graph
                dbc.Col(
                    cyto.Cytoscape(
                        id='graph',
                        layout={'name': 'cose',
                                'animate': True},
                        style={'width': '100%', 'height': '800px'},
                        elements=nx.readwrite.cytoscape_data(graph_data)['elements'],
                        stylesheet=[
                            {
                                'selector': 'node',
                                'style': {
                                    'width': 100,
                                    'height': 100,
                                    'content': 'data(name)',
                                    'text-valign': 'center',
                                    'color': 'black',
                                    #'background-image':'data(image)',
                                    'background-color' : 'data(color)'
                                }
                            },
                            {
                                'selector': 'edge',
                                'style': {
                                    'width': 20,
                                    'mid-target-arrow-shape': 'vee',
                                    'mid-target-arrow-color': '#9dbaea'
                                }
                            },

                        ]
                    ),
                width=6),
                # simulation panel
                dbc.Col(
                    [
                        simulation_menu
                    ],
                    width=3
                )
        ], style=fetch_flex_row_style())
    ])
