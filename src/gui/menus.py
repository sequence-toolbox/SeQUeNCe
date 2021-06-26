"""
Contains reusable elements for the gui, primarily menus,
as well as some functions for generating widely used menus,
such as unit dropdowns
"""

import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc

def getFreqUnits(id_extra):
    return dcc.Dropdown(
        id='frequency_units_'+id_extra,
        options=[
            {'label': 'mHz', 'value': 1e6},
            {'label': 'kHz', 'value': 1e3},
            {'label': 'hz', 'value': 1},
        ],
        value=1,
        style={'margin-bottom':'15px'}
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
        style={'margin-bottom':'15px'}
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
    dbc.Label('Memory Size'),
    dbc.Input(id='mem_size', placeholder='Memory Array Size'),
    dbc.Label('Memory Type'),
    dbc.Input(id='mem_type', placeholder='Memory Type'),
    dbc.Label('Detector Type'),
    dbc.Input(id='detector_type', placeholder='Detector Type'),
]

quantum_memory_template = [
    dbc.Label('Coherence Time'),
    dbc.FormGroup(
        [
            dbc.Col(dbc.Input(id='coh_time_in', placeholder='1.3e12'), width=10),
            dbc.Col(getTimeUnits('coh'), width=2)
        ],
        row=True
    ),

    dbc.Label('Frequency'),
    dbc.FormGroup(
        [
            dbc.Col(dbc.Input(id='mem_freq_in', placeholder='2000'),width=10),
            dbc.Col(getFreqUnits('mem'), width=2)
        ],
        row=True
    ),

    dbc.Label('Efficiency'),
    dbc.Input(id='mem_eff_in', placeholder='0.75'),

    dbc.Label('Cooperativity'),
    dbc.Input(id='mem_coop_in', placeholder='500'),
]

detector_template = [
    dbc.Label('Dark Count Rate'),
    dbc.Input(id='dark_count_in', placeholder='0'),
    dbc.Label('Efficiency'),
    dbc.Input(id='detector_efficiency_in', placeholder='0.8'),
    dbc.Label('Count Rate'),
    dbc.Input(id='count_rate_in', placeholder='5.7e'),
    dbc.Label('Resolution'),
    dbc.Input(id='resolution_in', placeholder='1e2')
]

bsm_template = [

]


protocol_template = [

]