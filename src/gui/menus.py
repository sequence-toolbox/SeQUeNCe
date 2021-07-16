"""
Contains reusable elements for the gui, primarily menus,
as well as some functions for generating widely used menus,
such as unit dropdowns
"""

import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc

def getInputField(value_in:str, label:str, input_id:str):
    return dbc.Row(
        [
            dbc.Col(dbc.Label(label), width=2),
            dbc.Col(dbc.Input(
                id=input_id, 
                value=value_in), 
                width= 10)
        ]
    )

def makeDropdownOptions(possible_inputs):
    out = []
    for x in possible_inputs:
        out.append([{'label',x},{'value',x}])
    return out

def getDropdownField(value_in:str, all_vals:"list[str]", label:str, input_id:str):
    opts = makeDropdownOptions(all_vals)
    return dbc.Row(
        [
            dbc.Col(dbc.Label(label), width=2),
            dbc.Col(dcc.Dropdown(
                id=input_id,
                options=opts,
                value=value_in
            ),width=10),
        ]
    )

def getSelectedNodeMenu(values, templates):
    return dbc.Form(
        [
            getInputField(values['name'], 'Name:', 'selected_name'),
            getDropdownField(
                values['template'],
                templates, 'Template:',
                'selected_template'
            ),
            getDropdownField(
                values['type'],
                templates, 'Node Type:',
                'selected_node_type'
            )
        ]
    )

def getSelectedEdgeMenu(values, templates):
    return dbc.Form(
        [
            getInputField(values['name'], 'Name:', 'selected_name'),
            getDropdownField(
                values['template'],
                templates, 'Template:',
                'selected_template'
            ),
            getDropdownField(
                values['type'],
                templates, 'Node Type:',
                'selected_node_type'
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
        style={'margin-bottom': '15px'}
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
    dbc.FormGroup(
        [
            dbc.Col(dbc.Input(
                id='coh_time_in',
                className='coherence_time',
                placeholder='1.3e12'),
                width=10
            ),
            dbc.Col(getTimeUnits('coh'), width=2)
        ],
        row=True,
        className='compound'
    ),

    dbc.Label('Frequency'),
    dbc.FormGroup(
        [
            dbc.Col(dbc.Input(
                id='mem_freq_in',
                className='frequency',
                placeholder='2000'),
                width=10
            ),
            dbc.Col(getFreqUnits('mem'), width=2)
        ],
        row=True,
        className='compound'
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
