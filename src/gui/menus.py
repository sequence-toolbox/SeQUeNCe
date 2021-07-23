"""
Contains reusable elements for the gui, primarily menus,
as well as some functions for generating widely used menus,
such as unit dropdowns
"""

import os
import base64
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import dash_cytoscape as cyto
import dash_table
from .css_styles import *

DIRECTORY, _ = os.path.split(__file__)

MENUS = [
    'Delete',
    'Template',
    'View',
    'CCD',
    'TDM'
]


def getInputField(value_in: str, label: str, input_id: str, out_type: str):
    return dbc.Row(
        [
            dbc.Col(dbc.Label(label), width=3),
            dbc.Col(dbc.Input(
                id=input_id,
                value=value_in,
                className=out_type
                ),
                width=9
            )
        ]
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
    out_type: str
):

    opts = makeDropdownOptions(all_vals)
    return dbc.Row(
        [
            dbc.Col(dbc.Label(label), width=3),
            dbc.Col(dcc.Dropdown(
                id=input_id,
                options=opts,
                value=value_in,
                className=out_type
            ), width=9),
        ]
    )


def getLogo():
    image_filename = os.path.join(DIRECTORY, 'assets', 'sequence.jpg')
    encoded_image = base64.b64encode(open(image_filename, 'rb').read())
    return html.Img(
        src='data:image/png;base64,{}'.format(encoded_image.decode()),
        width='80px',
        style={'border-radius': '20%'}
    ),


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
            values['template'],
            templates,
            'Template:',
            'selected_template',
            'template'
        )
    )
    out.append(
        getDropdownField(
            values['type'],
            templates,
            'Node Type:',
            'selected_node_type',
            'type'
        )
    )
    return dbc.Form(out)


def getSelectedEdgeMenu(values, nodes, link_types):
    return dbc.Form(
        [
            getDropdownField(
                values['source'],
                nodes, 'Source:',
                'selected_source',
                'source'
            ),
            getDropdownField(
                values['target'],
                nodes, 'Target:',
                'selected_target',
                'target'
            ),
            getDropdownField(
                values['link_type'],
                link_types, 'Link Type:',
                'selected_link_type',
                'link_type'
            ),
            getInputField(
                values['attenuation'],
                'Attenuation:',
                'selected_attenuation',
                'attenuation'
            ),
            getInputField(
                values['distance'],
                'Distance:',
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
    dbc.Label("Distance"),
    dbc.Input(id='distance_input', value=""),
    dbc.Label("Attenuation"),
    dbc.Input(id="attenuation_input", value=""),
]

quantum_edge = [
    dbc.Label("Distance"),
    dbc.Input(id='distance_input', value=""),
    dbc.Label("Attenuation"),
    dbc.Input(id="attenuation_input", value=""),
]

router_template = [
    dbc.Label('Template Name'),
    dbc.Input(
        id='detector_name',
        className='name',
        placeholder='default_detector'
    ),
    dbc.Label('Memory Size'),
    dbc.Input(
        id='mem_size',
        className='memo_size',
        placeholder='Memory Array Size'
    ),
    dbc.Label('Memory Type'),
    dbc.Input(
        id='mem_type',
        className='mem_type',
        placeholder='Memory Type'
    ),
]

quantum_memory_template = [
    dbc.Label('Template Name'),
    dbc.Input(
        id='q_mem_name',
        className='name',
        placeholder='default_detector'
    ),
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
        no_gutters=True
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
        no_gutters=True
    ),

    dbc.Label('Efficiency'),
    dbc.Input(id='mem_eff_in', className='efficiency', placeholder='0.75'),

    dbc.Label('Fidelity'),
    dbc.Input(id='fidelity_in', className='fidelity', placeholder='500'),
]

detector_template = [
    dbc.Label('Template Name'),
    dbc.Input(
        id='detector_name',
        className='name',
        placeholder='default_detector'
    ),
    dbc.Label('Dark Count Rate'),
    dbc.Input(
        id='dark_count_in',
        className='dark_count',
        placeholder='0'
    ),
    dbc.Label('Efficiency'),
    dbc.Input(
        id='detector_efficiency_in',
        placeholder='0.8'
    ),
    dbc.Label('Count Rate'),
    dbc.Input(
        id='count_rate_in',
        className='count_rate',
        placeholder='5.7e'
    ),
    dbc.Label('Resolution'),
    dbc.Input(
        id='resolution_in',
        className='efficiency',
        placeholder='1e2'
    )
]

bsm_template = [

]


protocol_template = [

]

# New #

"""
Default node type options for dropdown menus
"""

OPTIONS = [
    {
        'label': 'Quantum Router',
        'value': 'Quantum_Router'
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
        'label': 'Protocol',
        'value': 'Protocol'
    },
    {
        'label': 'Quantum Repeater',
        'value': 'Quantum_Repeater'
    },
    {
        'label': 'BSM Node',
        'value': 'BSM_node'
    },
    {
        'label': 'Quantum Error Correction',
        'value': 'QuantumErrorCorrection'
    },
    {
        'label': 'Photon Source',
        'value': 'Photon_Source'
    },
    {
        'label': 'Temp',
        'value': 'Temp'
    }
]

tab_ids = [f"tab-{i}" for i in range(9)]


add_node_form = html.Div(
    dbc.Form(
        [
            html.H3('Add Node'),
            dbc.Label('Name'),
            dbc.Input(
                id='node_to_add_name',
                type='Name',
                placeholder='Enter node Name'
            ),
            html.P(id='make_node_error', style={'color': 'red'}),
            dbc.Label('Type'),
            dcc.Dropdown(
                id='type_menu',
                options=OPTIONS,
                value='Quantum_Router',
                style={'margin-bottom': '15px'}
            ),
            dbc.Button('Add Node', color='primary', id='add_node', block=True)
        ]
    ),
    style=MENU_STYLE,
    id=tab_ids[0]
)

add_edge = html.Div(
    [
        dbc.Row(
            [
                dbc.Col(dbc.Label('Node 1', html_for='from_node'), width=3),
                dbc.Col(dbc.Label(id='from_node')),
                dbc.Col(dbc.Button(
                    'select',
                    color='primary',
                    id='select_node_1',
                    block=True,
                    outline=False
                ), width=4)
            ],
        ),
        dbc.Row(
            [
                dbc.Col(dbc.Label('Node 2', html_for='to_node'), width=3),
                dbc.Col(dbc.Label(id='to_node')),
                dbc.Col(dbc.Button(
                    'select',
                    color='primary',
                    id='select_node_2',
                    block=True,
                    outline=False
                ), width=4)
            ],
        ),
        dcc.Dropdown(
            id='edge_type_menu',
            options=[
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
    ],
    style=MENU_STYLE,
    id=tab_ids[1]
)

delete_menu = html.Div(
    dbc.Form(
        [
            html.H3('Delete'),
            dbc.FormGroup(
                [
                    dbc.Button('Delete', color='primary', id='delete_button'),
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
            dbc.Label('Template Type'),
            dcc.Dropdown(
                id='template_type_menu',
                options=OPTIONS,
                value='Quantum_Router',
                style={'margin-bottom': '15px'}
            ),
            dbc.FormGroup(
                id='template_properties'
            ),
            dbc.Button(
                'Save',
                color='primary',
                id='save_template',
                block=True
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
                dbc.Form(
                    dbc.ButtonGroup(
                        [
                            dbc.Button(
                                'Nodes',
                                id='toggle_nodes',
                                color='primary'
                            ),
                            dbc.Button(
                                'Edges',
                                id='toggle_edges',
                                color='primary'
                            )
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
                            style_table={
                                # 'height': '300px',
                                'overflowY': 'auto',
                                'overflowX': 'auto'
                            },
                            style_cell={'minWidth': 150, 'width': 150},
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
                    editable=True
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
                html.H3('Quantum Channel TDM'),
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
                    editable=True
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


selection_menu = html.Div(
    [
        html.H3('Edit'),
        html.Div(id='selected_element'),
        dbc.Button(
            'Submit',
            id='submit_edit',
            block=True,
            color='primary'
        )
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
        html.H3('Run'),
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
            no_gutters=True
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
            no_gutters=True
        ),
        dbc.FormGroup(
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
        dbc.Button('Run', color='primary', id='run_sim', block=True),
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
                    dbc.Col(getLogo()),
                    dbc.Col(dbc.NavbarBrand(
                        "SeQUeNCe",
                        className="ml-2",
                        style={
                            'font-size': '50px'
                        }
                    )),
                ],
                align="center",
                no_gutters=True,
            ),
            href="https://github.com/sequence-toolbox",
            style={
                'position': 'relative',
                'top': '0px',
                'left': '0px'
            }
        ),
        dbc.Row(
            [
                dbc.NavLink(
                    'New Network',
                    id='new_network',
                    style={
                        'color': 'white'
                    }
                ),
                dbc.NavLink(
                    'Save',
                    id='save_network',
                    style={
                        'color': 'white'
                    }
                ),
                dbc.NavLink(
                    'Load',
                    id='load_network',
                    style={
                        'color': 'white'
                    }
                ),
                dbc.DropdownMenu(
                    [
                        dbc.DropdownMenuItem('All', id='export_all'),
                        dbc.DropdownMenuItem('Topology', id='export_topo'),
                        dbc.DropdownMenuItem('Templates', id='export_templ'),
                        dbc.DropdownMenuItem('Simulation', id='export_sim')
                    ],
                    label="Export",
                    group=True,
                    bs_size='sm',
                    nav=True,
                    in_navbar=True,
                    toggle_style={
                        'color': 'white'
                    }
                ),
                dbc.DropdownMenu(
                    children=[
                        dbc.DropdownMenuItem("Help"),
                        dbc.DropdownMenuItem("Report Issue"),
                    ],
                    nav=True,
                    group=True,
                    bs_size='sm',
                    in_navbar=True,
                    label="More",
                    right=True,
                    toggle_style={
                        'color': 'white'
                    }
                ),
            ],
            no_gutters=True,
            className="ml-auto flex-nowrap mt-3 mt-md-0",
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
                    'width': 100,
                    'height': 100,
                    'content': 'data(name)',
                    'text-valign': 'center',
                    'color': 'black',
                    # 'background-image': 'data(image)',
                    'background-color': 'data(color)'
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
    )
