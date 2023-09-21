"""
Contains reusable elements for the gui, primarily menus,
as well as some functions for generating widely used menus,
such as unit dropdowns
"""

import os
import base64
from dash import dcc
from dash import html
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
from dash import dash_table
from .css_styles import *


"""
Mapping of all types in the GUI to their representative colors
"""
TYPE_COLORS = {
    'QuantumRepeater': '#4d9de0',
    'QuantumRouter': '#e15554',
    'PhotonSource': '#e1bc29',
    'Detector': '#3bb273',
    'QuantumErrorCorrection': '#7768ae',
    'BSMNode': '#ffc857',
    'Quantum': '#8634eb',
    'Classical': '#345feb',
    'Memory': '#8a34ab',
    'Temp': '#084c61',
    'QKDNode': '#cc99ff'
}


"""
Default node type options for dropdown menus
"""

OPTIONS_NODE = [
    {
        'label': 'Quantum Router',
        'value': 'QuantumRouter'
    },
    {
        'label': 'BSM Node',
        'value': 'BSMNode'
    },
    {
        'label': 'QKD Node',
        'value': 'QKDNode'
    }
]

OPTIONS_TEMPLATE = [
    {
        'label': 'Quantum Router',
        'value': 'QuantumRouter'
    },
    {
        'label': 'Quantum Memory',
        'value': 'Memory'
    },
    {
        'label': 'Detector',
        'value': 'Detector'
    },
    {
        'label': 'BSM Node',
        'value': 'BSMNode'
    },
    {
        'label': 'Photon Source',
        'value': 'PhotonSource'
    },
    {
        'label': 'QKD Node',
        'value': 'QKDNode'
    }
]

DIRECTORY, _ = os.path.split(__file__)

def getInputField(
    value_in: str,
    label: str,
    input_id: str,
    out_type: str,
    style_in=None,
    place=None
):
    return dbc.Row(
        [
            dbc.Col(dbc.Label(label), width=4),
            dbc.Col(dbc.Input(
                id=input_id,
                value=value_in,
                className=out_type,
                placeholder=place
                ),
                width=8
            ),
        ],
        style=style_in
    )


def makeDropdownOptions(possible_inputs):
    out = []
    for x in possible_inputs:
        out.append({'label': x, 'value': x})
    return out


def getDropdownField(
    value_in: str,
    all_vals: "list[str]",
    label: str,
    input_id: str,
    out_type: str,
    style_in=None
):

    return dbc.Row(
        [
            dbc.Col(dbc.Label(label), width=4),
            dbc.Col(dcc.Dropdown(
                id=input_id,
                options=all_vals,
                value=value_in,
                className=out_type
            ), width=8),
        ],
        style=style_in
    )


def getLogo(filename, width, link=None):
    image_filename = os.path.join(DIRECTORY, 'assets', filename)
    encoded_image = base64.b64encode(open(image_filename, 'rb').read())
    image = html.Img(
        src='data:image/png;base64,{}'.format(encoded_image.decode()),
        width=width,
        style={'border-radius': '20%'})
    if link is None:
        return image
    else:
        return html.A(image, href=link)


def getSelectedNodeMenu(values, templates):
    out = []
    out.append(
        getInputField(
            values['name'],
            'Name:',
            'selected_name',
            'name'
        )
    )
    out.append(
        getDropdownField(
            values['type'],
            OPTIONS_NODE,
            'Node Type:',
            'selected_node_type',
            'type'
        )
    )
    out.append(
        getDropdownField(
            values['template'],
            makeDropdownOptions(templates),
            'Template:',
            'selected_template',
            'template'
        )
    )

    return dbc.Form(out)


def getSelectedEdgeMenu(values, nodes, link_types):
    return dbc.Form(
        [
            getDropdownField(
                values['source'],
                makeDropdownOptions(nodes),
                'Source:',
                'selected_source',
                'source'
            ),
            getDropdownField(
                values['target'],
                makeDropdownOptions(nodes),
                'Target:',
                'selected_target',
                'target'
            ),
            getDropdownField(
                values['link_type'],
                makeDropdownOptions(link_types),
                'Link Type:',
                'selected_link_type',
                'link_type'
            ),
            getInputField(
                values['attenuation'],
                'Attenuation (dB/m):',
                'selected_attenuation',
                'attenuation'
            ),
            getInputField(
                values['distance'],
                'Distance (m):',
                'selected_distance',
                'distance'
            )
        ]
    )


def getFreqUnits(id_extra):
    return dcc.Dropdown(
        id='frequency_units_'+id_extra,
        options=[
            {'label': 'mHz', 'value': 1e6},
            {'label': 'kHz', 'value': 1e3},
            {'label': 'hz', 'value': 1},
        ],
        value=1,
        style={'margin-bottom': '15px'}
    )


def getTimeUnits(id_extra):
    return dcc.Dropdown(
        id='time_units_'+id_extra,
        options=[
            {'label': 's', 'value': 1e12},
            {'label': 'ms', 'value': 1e9},
            {'label': 'ns', 'value': 1e3},
            {'label': 'ps', 'value': 1},
        ],
        value=1,
    )


classic_edge = [
    getInputField(
        '',
        'Distance (m):',
        'distance_input',
        ''
    ),
    getInputField(
        '',
        'Attenuation (dB/m):',
        'attenuation_input',
        ''
    )
]

quantum_edge = [
    getInputField(
        '',
        'Distance (m):',
        'distance_input',
        ''
    ),
    getInputField(
        '',
        'Attenuation (dB/m):',
        'attenuation_input',
        ''
    )
]

router_template = [
    dbc.Label('Memory Size'),
    dbc.Input(
        id='mem_size',
        className='memo_size',
        placeholder='Memory Array Size',
        type='number'
    ),
    dbc.Label('Memory Type'),
    dcc.Dropdown(
        id='mem_type',
        className='mem_type',
        value='',
        options=[]
    ),
]

quantum_memory_template = [
    dbc.Label('Coherence Time'),
    dbc.Row(
        [
            dbc.Col(dbc.Input(
                id='coh_time_in',
                className='coherence_time',
                placeholder='1.3e12'),
                width=10
            ),
            dbc.Col(getTimeUnits('coh'), width=2)
        ],
        className="g-0"
    ),

    dbc.Label('Frequency'),
    dbc.Row(
        [
            dbc.Col(dbc.Input(
                id='mem_freq_in',
                className='frequency',
                placeholder='2000'),
                width=10
            ),
            dbc.Col(getFreqUnits('mem'), width=2)
        ],
        className="g-0"
    ),

    dbc.Label('Efficiency'),
    dbc.Input(id='mem_eff_in', className='efficiency', placeholder='0.75'),

    dbc.Label('Fidelity'),
    dbc.Input(id='fidelity_in', className='fidelity', placeholder='0.85'),
]

detector_template = [
    dbc.Label('Dark Count Rate'),
    dbc.Input(
        id='dark_count_in',
        className='dark_count',
        placeholder='0'
    ),
    dbc.Label('Efficiency'),
    dbc.Input(
        id='detector_efficiency_in',
        className='efficiency',
        placeholder='0.8'
    ),
    dbc.Label('Count Rate'),
    dbc.Input(
        id='count_rate_in',
        className='count_rate',
        placeholder='5.7e3'
    ),
    dbc.Label('Resolution'),
    dbc.Input(
        id='resolution_in',
        className='resolution',
        placeholder='1e2'
    )
]

bsm_template = [
    dbc.Label('Detector 1 Type'),
    dcc.Dropdown(
        id='detec_type_1',
        className='detector_type',
        value='',
        options=[]
    ),
    dbc.Label('Detector 2 Type'),
    dcc.Dropdown(
        id='detec_type_2',
        className='detector_type',
        value='',
        options=[]
    ),
]

qkd_template = [
    dbc.Label('Photon Encoding'),
    dcc.Dropdown(
        id='encoding_in',
        className='encoding',
        value='',
        options=["polarization", "time_bin"]
    ),
    dbc.Label('Protocol Stack Size'),
    dcc.Dropdown(
        id='stack_size_in',
        className='stack_size',
        value='',
        options=[1, 2, 3, 4, 5]
    ),
]

# New #

tab_ids = [f"tab-{i}" for i in range(9)]


add_node_form = html.Div(
    dbc.Form(
        [
            html.H3('Add Node'),
            getInputField(
                '',
                'Name:',
                'node_to_add_name',
                '',
                place='Enter Node ID'
            ),
            getDropdownField(
                'QuantumRouter',
                OPTIONS_NODE,
                'Type:',
                'type_menu',
                ''
            ),
            getDropdownField(
                '',
                [],
                'Template:',
                'add_template_menu',
                '',
                style_in={'margin-bottom': '10px'}
            ),
            html.Div(
                [
                    dbc.Button('Add Node', color='primary', id='add_node')
                ],
                className="d-grid"
            ),
            html.P(id='make_node_error', style={'color': 'red'})
        ]
    ),
    style=MENU_STYLE,
    id=tab_ids[0]
)

add_edge = html.Div(
    [
        html.H3('Add Edge'),
        getDropdownField(
            '',
            [],
            'From:',
            'from_node',
            ''
        ),
        getDropdownField(
            '',
            [],
            'To:',
            'to_node',
            ''
        ),
        getDropdownField(
            '',
            [
                {
                    'label': 'Quantum Connection',
                    'value': 'Quantum'
                },
                {
                    'label': 'Classical Connection',
                    'value': 'Classical'
                },
            ],
            'Link Type:',
            'edge_type_menu',
            'Quantum'
        ),
        dbc.Row(
            id='edge_properties'
        ),
        html.P(id='make_edge_error', style={'color': 'red'}),
        html.Div(
            [
                dbc.Button('Add Edge', color='primary', id='add_edge'),
            ],
            className="d-grid"
        ),
    ],
    style=MENU_STYLE,
    id=tab_ids[1]
)

delete_menu = html.Div(
    dbc.Form(
        [
            html.H3('Delete'),
            dbc.Row(
                [
                    html.P(
                        'Select an element and press the button to remove it'
                    ),
                    html.Div(
                        [
                            dbc.Button(
                                'Delete',
                                color='primary',
                                id='delete_button',
                            ),
                        ],
                        className="d-grid"
                    ),
                ]
            )
        ],
    ),
    style=MENU_STYLE,
    id=tab_ids[2]
)


make_new_template = html.Div(
    dbc.Form(
        [
            html.H3('Template'),
            getInputField(
                '',
                'ID:',
                'template_name',
                '',
                place='Enter ID'
            ),
            getDropdownField(
                'QuantumRouter',
                OPTIONS_TEMPLATE,
                'Type:',
                'template_type_menu',
                ''
            ),
            dbc.Row(
                id='template_properties'
            ),
            html.Div(
                [
                    dbc.Button(
                        'Save',
                        color='primary',
                        id='save_template',
                    ),
                ],
                className="d-grid"
            ),
            html.P(id='save_state', style={'color': 'blue'})
        ]
    ),
    style=MENU_STYLE,
    id=tab_ids[3]
)


def getTopoTable(data, columns):
    return html.Div(
        dbc.Form(
            [
                html.H3('View'),
                dbc.ButtonGroup(
                    [
                        dbc.Button(
                            'Nodes',
                            id='toggle_nodes',
                            color='primary',
                            style={
                                'padding': '5px 65px',
                            }
                        ),
                        dbc.Button(
                            'Edges',
                            id='toggle_edges',
                            color='primary',
                            style={
                                'padding': '5px 65px'
                            }
                        )
                    ],
                    style={
                        'margin-bottom': '10px',
                    }
                ),
                dbc.Form(
                    [
                        dash_table.DataTable(
                            id='graph_table',
                            data=data,
                            columns=columns,
                            fixed_rows={'headers': True},
                            page_size=20,
                            style_table={
                                # 'height': '300px',
                                'overflowY': 'auto',
                                'overflowX': 'auto'
                            },
                            style_cell={'minWidth': 150, 'width': 150},
                            filter_action='native',
                            editable=True
                        )
                    ]
                )
            ]
        ),
        style=MENU_STYLE,
        id=tab_ids[4]
    )


def delay_menu(data, columns):
    return html.Div(
        dbc.Form(
            [
                html.H3('Classical Channel Delays'),
                dash_table.DataTable(
                    id='delay_table',
                    data=data,
                    columns=columns,
                    fixed_rows={'headers': True},
                    # fixed_columns={'headers': True, 'data': 1},
                    page_size=20,
                    style_table={
                        # 'height': '300px',
                        'overflowY': 'auto',
                        'overflowX': 'auto'
                    },
                    style_cell={'minWidth': 150, 'width': 150},
                    editable=True,
                    filter_action='native',
                )
            ]
        ),
        style=MENU_STYLE,
        id=tab_ids[5]
    )


def tdm_menu(data, columns):
    return html.Div(
        dbc.Form(
            [
                html.H3('Quantum Channel TDM (WIP)'),
                dash_table.DataTable(
                    id='tdm_table',
                    data=data,
                    columns=columns,
                    fixed_rows={'headers': True},
                    # fixed_columns={'headers': True, 'data': 1},
                    page_size=20,
                    style_table={
                        # 'height': '300px',
                        'overflowY': 'auto',
                        'overflowX': 'auto'
                    },
                    style_cell={'minWidth': 150, 'width': 150},
                    editable=True,
                    filter_action='native',
                )
            ]
        ),
        style=MENU_STYLE,
        id=tab_ids[6]
    )


def TDM_menu(tdm_data, tdm_columns):
    new_tdm_data = tdm_data.copy()
    tdm_rows = []
    for x in tdm_columns:
        tdm_rows.append(x['id'])
    new_tdm_data.insert(loc=0, column='To', value=tdm_rows)
    tdm_columns.insert(0, {
        'id': 'To',
        'type': 'text',
        'name': 'To'
    })
    new_tdm_data = new_tdm_data.to_dict('records')
    return tdm_menu(new_tdm_data, tdm_columns)


def CCD_menu(delay_data, delay_columns):
    new_delay_data = delay_data.copy()
    delay_rows = []
    for x in delay_columns:
        delay_rows.append(x['id'])
    new_delay_data.insert(loc=0, column='To', value=delay_rows)
    delay_columns.insert(0, {
        'id': 'To',
        'type': 'text',
        'name': 'To'
    })
    new_delay_data = new_delay_data.to_dict('records')
    return delay_menu(new_delay_data, delay_columns)


def makeLegend(values):
    if values is None:
        return html.Div(
            hidden=True,
        )
    out = []
    for x in values:
        out.append(dbc.Row(
            [
                dbc.Col(
                    [
                        html.Span(
                            className='dot',
                            style={
                                'background-color': TYPE_COLORS[x],
                                'height': '25px',
                                'width': '25px',
                                'border-radius': '50%',
                                'display': 'inline-block',
                                'outline-style': 'solid',
                                'outline-color': '#fff',
                                'border': '2px solid black'
                            }
                        ),
                        dbc.Label(
                            x,
                            style={
                                'position': 'relative',
                                "top": '-5px',
                                "left": '7px',
                            }
                        ),
                    ],
                ),
            ],
            style={
                'margin': '5px 0px'
            }
        ))
    legend = html.Form(
        children=out,
        style={
            "width": "auto",
            "height": "auto",
        }
    )
    return legend


selection_menu = html.Div(
    [
        html.H3('Edit'),
        html.Div(id='selected_element'),
        html.Div(
            [
                dbc.Button(
                    'Submit',
                    id='submit_edit',
                    color='primary',
                    style={
                        'margin-top': '10px'
                    }
                )
            ],
            className="d-grid"
        ),
    ],
    id=tab_ids[7],
    style=MENU_STYLE
)

results_menu = dbc.Form(
    [
        html.H5("Results"),
        dbc.Card(
            [
                html.Pre(id='results_out'),
            ], style={
                'minHeight': '50vh',
                'maxHeight': '65vh',
                'overflowY': 'auto',
                'overflowX': 'auto'
                }
        )
    ]
)

simulation_menu = html.Div(
    [
        html.H3('Run (WIP)'),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Label('Name'),
                    width=2
                ),
                dbc.Col(dbc.Input(
                    id='sim_name',
                    placeholder='Ex: Test_1'
                ), width=10)
            ],
            className="g-0"
        ),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Label('Time'),
                    width=2
                ),
                dbc.Col(dbc.Input(
                    id='sim_time_in',
                    placeholder='Enter simulation time'
                ), width=8),
                dbc.Col(
                    getTimeUnits('sim'),
                    width=2,
                ),
            ],
            className="g-0"
        ),
        dbc.Row(
            [
                dbc.Label("Logging Options", width=6),
                dbc.Col(
                    dbc.RadioItems(
                        id='logging_verbosity',
                        options=[
                            {"label": 'Critical', 'value': 'CRITICAL'},
                            {"label": 'Error', 'value': 'ERROR'},
                            {"label": 'Warning', 'value': 'WARNING'},
                            {"label": 'Info', 'value': 'INFO'},
                            {"label": 'Debug', 'value': 'DEBUG'},
                            {'label': 'None', 'value': 'NOTSET'},
                        ],
                        value='NOTSET',
                        inline=True
                    ),
                    width=12,
                ),
            ],
        ),
        html.Div(
            [
                dbc.Button('Run', color='primary', id='run_sim'),
            ],
            className="d-grid"
        ),
        
        dcc.Interval(
            id='running',
            interval=1000,
            n_intervals=0,
            disabled=True
        ),
        html.Pre(id='runtime'),
        html.Pre(id='simtime'),
        results_menu
    ],
    id=tab_ids[8],
    style=MENU_STYLE
)

navbar = dbc.Navbar(
    children=[
        html.A(
            dbc.Row(
                [
                    dbc.Col(getLogo('sequence.jpg', '80px')),
                    dbc.Col(dbc.NavbarBrand(
                        "SeQUeNCe",
                        className="ml-2",
                        style={
                            'font-size': '50px'
                        }
                    )),
                ],
                align="center",
                className="g-0"
            ),
            href="https://github.com/sequence-toolbox",
            style={
                'position': 'relative',
                'top': '0px',
                'left': '10px'
            }
        ),
        dbc.Row(
            [
                dbc.NavLink(
                    'New Network',
                    id='new_network',
                    style={
                        'color': 'white'
                    },
                ),
                # dbc.NavLink(
                #     'Save',
                #     id='save_network',
                #     style={
                #         'color': 'white'
                #     }
                # ),
                # dbc.NavLink(
                #     'Load',
                #     id='load_network',
                #     style={
                #         'color': 'white'
                #     }
                # ),
                dbc.DropdownMenu(
                    [
                        dbc.DropdownMenuItem('All', id='export_all'),
                        dbc.DropdownMenuItem('Topology', id='export_topo'),
                        dbc.DropdownMenuItem('Templates', id='export_templ'),
                        dbc.DropdownMenuItem('Simulation', id='export_sim')
                    ],
                    label="Export",
                    group=True,
                    size='sm',
                    nav=True,
                    in_navbar=True,
                    toggle_style={
                        'color': 'white'
                    }
                ),
                dbc.DropdownMenu(
                    children=[
                        dbc.DropdownMenuItem(
                            "Help",
                            href='https://sequence-toolbox.github.io/',
                        ),
                        dbc.DropdownMenuItem(
                            'Report Issue',
                            href='https://github.com/sequence-toolbox/SeQUeNCe/issues',  # nopep8
                        ),
                    ],
                    label="More",
                    group=True,
                    size='sm',
                    nav=True,
                    in_navbar=True,
                    # right=True,
                    toggle_style={
                        'color': 'white'
                    }
                ),
            ],
            className="ml-auto flex-nowrap mt-3 mt-md-0 g-0",
            align="center",
        )
    ],
    color="dark",
    dark=True,
)


def get_network(elements_in):
    return cyto.Cytoscape(
        id='graph',
        layout={
            'name': 'cose',
            'animate': True
        },
        zoomingEnabled=True,
        responsive=True,
        style={'width': '100%', 'height': '100vh'},
        elements=elements_in,
        stylesheet=[
            {
                'selector': 'node',
                'style': {
                    'width': 50,
                    'height': 50,
                    'content': 'data(name)',
                    'text-valign': 'center',
                    'font-size': '8',
                    'color': 'black',
                    # 'background-image': 'data(image)',
                    'background-color': 'data(color)'
                }
            },
            {
                'selector': 'edge',
                'style': {
                    'curve-style': 'bezier',
                    'width': 5,
                    'arrow-scale': 1,
                    # 'target-arrow-shape': 'vee',
                }
            },
        ]
    )
