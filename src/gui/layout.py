"""
A Class which contains the layout of the dash application.
Can also be understood and the corresponding html for the
dash web app
"""

import os
import base64
import networkx as nx
from dash import dcc
from dash import html
import dash_bootstrap_components as dbc
from .menus import *
from .css_styles import *


def make_item(menu, label, num, icon):
    return dcc.Tab(
        children=menu,
        label=' '+label,
        value=num,
        className=icon,
        style={
            'background-color': 'transparent',
            'text-align': 'left',
            'font-size': '18px',
            'padding-right': '10px',
            'overflowX': 'hidden'
        }
    )


def getSidebar(graph, delays, tdm):
    return html.Div(
        [
            html.Div(
                [
                    dbc.Button(
                        children=[
                            html.I(
                                className='bi bi-list',
                                style={
                                    'font-size': '2rem',
                                }
                            ),
                        ],
                        outline=True,
                        color="secondary",
                        className="mr-1",
                        id="btn_sidebar",
                        style={
                            "margin-top": "10px",
                            "margin-bottom": "20px",
                        }
                    ),
                ],
                className="d-grid"
            ),
            
            dcc.Tabs(
                [
                    make_item(
                        add_node_form,
                        'Add Node',
                        '1',
                        'bi bi-plus-circle'
                    ),
                    make_item(
                        add_edge,
                        'Add Edge',
                        '2',
                        'bi bi-share-fill'
                    ),
                    make_item(
                        selection_menu,
                        'Edit',
                        '8',
                        'bi bi-pencil-square'
                    ),
                    make_item(
                        delete_menu,
                        'Delete',
                        '3',
                        'bi bi-trash'
                    ),
                    make_item(
                        make_new_template,
                        'Template',
                        '4',
                        'bi bi-input-cursor-text'
                    ),
                    make_item(
                        getTopoTable(graph[0], graph[1]),
                        'View',
                        '5',
                        'bi bi-table'
                    ),
                    make_item(
                        CCD_menu(delays[0], delays[1]),
                        'Latency',
                        '6',
                        'bi bi-clock'
                    ),
                    make_item(
                        TDM_menu(tdm[0], tdm[1]),
                        'Multiplexing',
                        '7',
                        'bi bi-clock-history'
                    ),
                    make_item(
                        simulation_menu,
                        'Run',
                        '9',
                        'bi bi-play'),
                ],
                vertical=True,
                id='tabs',
                value='1'
            ),
            html.Div(
                getLogo(
                    'argonne.png',
                    '150px',
                    'https://www.anl.gov/mcs/quantum-computing'

                ),
                id='argonne',
                style={
                    'position': 'relative',
                    'bottom': '-20px',
                    'left': '0px',
                    'overflow': 'auto'
                }
            )
        ],
        id="sidebar_select",
        style=SIDEBAR_SELECT_STYLE,
    )


def graph_element(graph, name):
    return html.Div(
        [
            html.H4(
                name,
                id='project_name',
                className="display-4",
                style=PROJECT
            ),
            dbc.Button(
                outline=True,
                color="secondary",
                className="bi bi-arrow-repeat",
                id="refresh",
                style=REFRESH
            ),
            html.Div(
                [
                    get_network(graph),
                ],
                id="page-content",
                style=GRAPH_DIV_STYLE,
            )
        ],
        # style=CONTENT_STYLE,
        id='test'
    )


# Constants #
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
    # 'QuantumErrorCorrection',
    'BSM_node',
    # 'Temp',
    'Memory',
    # 'Protocol'
]


"""
returns a dictionary mapping each GUI node type
to its corresponding image in the current directory
structure
"""


def genImages():
    images = {
        'Quantum_Repeater': 'repeater.png',
        'Quantum_Router': 'router.png',
        'Photon_Source': 'photonsource.png',
        'Detector': 'detector.png',
        'QuantumErrorCorrection': 'quantum.png',
        'BSM_node': 'bsmnode.png',
        'Temp': 'temp.png'
    }
    for key, value in images.items():
        path = os.path.join(DIRECTORY, 'assets', value)
        images[key] = path
    return images


"""
dictionary returned by running the genImages() function
"""
TYPE_IMAGES = genImages()


# HTML TEMPLATES #
def getNodeImage(node_type):
    image_filename = TYPE_IMAGES[node_type]
    encoded_image = base64.b64encode(open(image_filename, 'rb').read())
    return 'data:image/png;base64,{}'.format(encoded_image.decode())


# Generate HTML Layout #
def get_app_layout(
    graph_data,
    graph_table,
    delay_table,
    tdm_table,
    name
):
    graph = nx.readwrite.cytoscape_data(graph_data)['elements']
    return html.Div(
        [
            dcc.Download(id='download'),
            html.Div(hidden=True, id='hidden_processing'),
            dcc.Store(id='side_click'),
            dcc.Store(id='all_nodes'),
            dcc.Store(id='comp_temp'),
            dcc.Store(id='detec_opts'),
            dcc.Store(id='last_clicked'),
            navbar,
            html.Div(
                [
                    html.Div(
                        [
                            getSidebar(graph_table, delay_table, tdm_table),
                        ],
                        id='sidebar',
                        style=SIDEBAR_STYLE
                    ),
                    graph_element(graph, name),
                    html.Div(
                        id='legend',
                        style=LEGEND_STYLE
                    )
                ],
                style=PAGE
            )
        ],
    )
