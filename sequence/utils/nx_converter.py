"""
Convert an arbitrary NetworkX graph object to a SeQUeNCe topology using QuantumRouters in MIM configuration
"""

import json
from pathlib import Path

import networkx as nx
from sequence.constants import SECOND
from sequence.utils.config_generator import router_name_func, generate_nodes, bsm_name_func, generate_classical
from ..topology.router_net_topo import RouterNetTopo as Topology

def generate_config(g: nx.Graph, qc_length: float, qc_attn: float, cc_delay: int, output_file: str, output_directory: str, stop_time: float, formalism: str, node_template: dict, meas_fid: float=0.995, gate_fid: float=0.99):
    """Create a sequence config file from an arbitrary graph for MIM entanglement generation"""
    output_dict = {Topology.ALL_TEMPLATES: node_template}

    cc_delay_ps = cc_delay * 1e9
    to_bsm_dist: float = qc_length * 1000 / 2  # Convert to meters, get middle


    router_names = [router_name_func(i) for i in range(len(g.nodes))]
    nodes: list[dict] = generate_nodes(router_names, 1, 'perfect_router', measurement_fidelity=meas_fid, gate_fidelity=gate_fid)
    graph_to_name = {graph_node: router_names[i] for i, graph_node in enumerate(g.nodes)}
    for sequence_node, graph_node in zip(nodes, g.nodes):
        sequence_node[Topology.MEMO_ARRAY_SIZE] = g.degree(graph_node)

    bsm_nodes = []
    qlinks = []
    clinks = []
    for i, (left, right) in enumerate(g.edges()):
        left_name = graph_to_name[left]
        right_name = graph_to_name[right]
        bsm_name = bsm_name_func(left_name, right_name)
        bsm_nodes.append({Topology.NAME: bsm_name, Topology.TYPE: Topology.BSM_NODE, Topology.SEED: i, Topology.TEMPLATE: 'perfect_bsm'})

        # Quantum Links (Node -> BSM <- Node)
        qlinks.append({Topology.SRC: left_name, Topology.DST: bsm_name, Topology.DISTANCE: to_bsm_dist, Topology.ATTENUATION: qc_attn})
        qlinks.append({Topology.SRC: right_name, Topology.DST: bsm_name, Topology.DISTANCE: to_bsm_dist, Topology.ATTENUATION: qc_attn})

        # Classical Links (Node <-> BSM <-> Node)
        clinks.append({Topology.SRC: left_name, Topology.DST: bsm_name, Topology.DISTANCE: to_bsm_dist, Topology.DELAY: cc_delay_ps})
        clinks.append({Topology.SRC: bsm_name, Topology.DST: left_name, Topology.DISTANCE: to_bsm_dist, Topology.DELAY: cc_delay_ps})
        clinks.append({Topology.SRC: right_name, Topology.DST: bsm_name, Topology.DISTANCE: to_bsm_dist, Topology.DELAY: cc_delay_ps})
        clinks.append({Topology.SRC: bsm_name, Topology.DST: right_name, Topology.DISTANCE: to_bsm_dist, Topology.DELAY: cc_delay_ps})


    output_dict[Topology.ALL_NODE] = nodes + bsm_nodes

    output_dict[Topology.ALL_Q_CHANNEL] = qlinks
    router_clinks = generate_classical(router_names, cc_delay)
    clinks += router_clinks
    output_dict[Topology.ALL_C_CHANNEL] = clinks
    output_dict[Topology.STOP_TIME] = int(stop_time * SECOND) if stop_time != float('inf') else int(1e18)
    output_dict[Topology.FORMALISM] = formalism

    output_dir = Path(output_directory)
    output_dir.mkdir(exist_ok=True)

    with open(output_dir / output_file, 'w') as f:
        json.dump(output_dict, f)

    return graph_to_name