"""This module defines common functions for the config generation files.
Examples of using this module is in https://github.com/sequence-toolbox/SeQUeNCe/tree/master/utils/json_config_generators
"""

from sequence.constants import *

def add_default_args(parser):
    """Adds arguments to argument parser.

    Args:
        parser (argparse.ArgumentParser)

    Returns:
        argparse.ArgumentParser
    """
    parser.add_argument('memo_size', type=int, help='number of communication memories per node')
    parser.add_argument('qc_length', type=float, help='distance between nodes (in km)')
    parser.add_argument('qc_atten', type=float, help='quantum channel attenuation (in dB/m)')
    parser.add_argument('cc_delay', type=float, help='classical channel delay (in ms)')
    parser.add_argument('-f', '--formalism', type=str, default='ket_vector', help='the formalism of the quantum state. Options: ket_vector, density_matrix, bell_diagonal')
    parser.add_argument('-d', '--directory', type=str, default='.', help='name of output directory')
    parser.add_argument('-o', '--output', type=str, default='out.json', help='name of output config file')
    parser.add_argument('-s', '--stop', type=float, default=float('inf'), help='stop time (in s)')
    parser.add_argument('-gf', '--gate_fidelity', type=float, help='fidelity of two-qubit gates')
    parser.add_argument('-mf', '--measurement_fidelity', type=float, help='fidelity of measurements')
    return parser



def generate_nodes(router_names: list, memo_size: int, template: str = None, gate_fidelity: float = None, measurement_fidelity: float = None) -> list:
    """generate a list of node configs for quantum routers
    """
    nodes = []
    for i, name in enumerate(router_names):
        config = {NAME: name,
                  TYPE: QUANTUM_ROUTER,
                  SEED: i,
                  MEMO_ARRAY_SIZE: memo_size}
        if template:
            config[TEMPLATE] = template
        if gate_fidelity:
            config[GATE_FIDELITY] = gate_fidelity
        if measurement_fidelity:
            config[MEASUREMENT_FIDELITY] = measurement_fidelity
        nodes.append(config)
    return nodes


def generate_quantum_dqc_nodes(router_names: str, memo_size: int, data_memo_size: int, template: str = None, gate_fidelity: float = None, measurement_fidelity: float = None) -> list:
    """generate a list of node configs for quantum nodes
    """
    nodes = []
    for i, name in enumerate(router_names):
        config = {NAME: name,
                  TYPE: DQC_NODE,
                  SEED: i,
                  MEMO_ARRAY_SIZE: memo_size,
                  DATA_MEMO_ARRAY_SIZE: data_memo_size}
        if template:
            config[TEMPLATE] = template
        if gate_fidelity:
            config[GATE_FIDELITY] = gate_fidelity
        if measurement_fidelity:
            config[MEASUREMENT_FIDELITY] = measurement_fidelity
        nodes.append(config)
    return nodes


def generate_bsm_links(graph, parsed_args, bsm_naming_func):
    cchannels = []
    qchannels = []
    bsm_nodes = []

    for i, node_pair in enumerate(graph.edges):
        node1, node2 = node_pair
        bsm_name = bsm_naming_func(node1, node2)
        bsm_node = {NAME: bsm_name,
                    TYPE: BSM_NODE,
                    SEED: i,}
        bsm_nodes.append(bsm_node)

        for node in node_pair:
            qchannels.append({SRC: node,
                              DST: bsm_name,
                              DISTANCE: parsed_args.qc_length * 500,
                              ATTENUATION: parsed_args.qc_atten})

        for node in node_pair:
            cchannels.append({SRC: bsm_name,
                              DST: node,
                              DELAY: parsed_args.cc_delay * 1e9})

            cchannels.append({SRC: node,
                              DST: bsm_name,
                              DELAY: parsed_args.cc_delay * 1e9})

    return cchannels, qchannels, bsm_nodes


# generate classical network connections
def generate_classical(router_names: list, cc_delay: int) -> list:
    cchannels = []
    for node1 in router_names:
        for node2 in router_names:
            if node1 == node2:
                continue
            cchannels.append({SRC: node1,
                              DST: node2,
                              DELAY: int(cc_delay * MILLISECOND)})
    return cchannels


# add final touches to config dict: 1) stop_time, 2) formalism
def final_config(output_dict, parsed_args):
    output_dict[STOP_TIME] = int(parsed_args.stop * SECOND)
    output_dict[FORMALISM] = parsed_args.formalism


def router_name_func(i) -> str:
    """a function that returns the name of the router"""
    return f"router_{i}"


def bsm_name_func(i, j) -> str:
    """a function that returns the name of the BSM node"""
    return f"BSM_{i}_{j}"
