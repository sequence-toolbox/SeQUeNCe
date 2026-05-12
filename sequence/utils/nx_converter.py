"""
Convert an arbitrary NetworkX graph object to a SeQUeNCe topology using QuantumRouters in MIM configuration.
"""

import json
from pathlib import Path

import networkx as nx

from sequence.constants import MILLISECOND, SECOND

from ..topology.router_net_topo import RouterNetTopo as Topology

default_template = {
  "router_template": {
    "MemoryArray": {
      "frequency": 200000000.0,
      "coherence_time": 2,
      "efficiency": 1,
      "fidelity": 0.9
    }
  },
  "bsm_template": {
    "encoding_type": "single_heralded",
    "SingleHeraldedBSM": {
      "detectors": [
        {
          "efficiency": 1,
          "dark_count": 0,
          "time_resolution": 6,
          "count_rate": 100000000000.0
        },
        {
          "efficiency": 1,
          "dark_count": 0,
          "time_resolution": 6,
          "count_rate": 100000000000.0
        }
      ]
    }
  }
}

def router_name_func(i) -> str:
    """
    Gets the name of a QuantumRouter given its vertex index.
    Args:
        i: Graph vertex index

    Returns: Name of the router

    """
    return f'router_{i}'

def bsm_name_func(i, j) -> str:
    """
    Return the name of the BSM
    Args:
        i: Initiator node
        j: Responder node

    Returns: BSM name
    """
    return f'BSM_{i}_{j}'

def generate_classical(router_names: list, cc_delay: float) -> list:
    """
    Creates all-to-all links between routers in the topology.
    Args:
        router_names: List of routers
        cc_delay: Delay between the routers (ms)

    Returns: A list of the classical connections
    """
    cchannels: list = []
    for node1 in router_names:
        for node2 in router_names:
            if node1 == node2:
                continue
            cchannels.append({Topology.SRC: node1,
                              Topology.DST: node2,
                              Topology.DELAY: int(cc_delay * MILLISECOND)})
    return cchannels

def generate_nodes(router_names: list, memo_size: int, template: str = '', gate_fidelity: float = 1, measurement_fidelity: float = 1) -> list:
    """
    Generate a list of QuantumRouter Configs
    Args:
        router_names: Names of the QuantumRouters
        memo_size: Number of memories per QuantumRouter
        template: Name of the template to apply
        gate_fidelity: CNOT gate fidelity, default is 1
        measurement_fidelity: Measurement fidelity, default is 1

    Returns: List of QuantumRouter configurations
    """
    nodes = []
    for i, name in enumerate(router_names):
        config = {Topology.NAME: name,
                  Topology.TYPE: Topology.QUANTUM_ROUTER,
                  Topology.SEED: i,
                  Topology.MEMO_ARRAY_SIZE: memo_size}
        if template is not None:
            config[Topology.TEMPLATE] = template
        if gate_fidelity is not None:
            config[Topology.GATE_FIDELITY] = gate_fidelity
        if measurement_fidelity is not None:
            config[Topology.MEASUREMENT_FIDELITY] = measurement_fidelity
        nodes.append(config)
    return nodes


def generate_config(g: nx.Graph, cc_delay: float, memory_size: int=5, output_file: str='output.json',
                    output_directory: str='tmp', stop_time: float|None=None, formalism: str|None=None, node_template: dict|None=None,
                    meas_fid: float=1, gate_fid: float=1) -> tuple[dict, dict]:
    """Create a sequence config file from an arbitrary graph assuming meet-in-the-middle (MIM) entanglement generation
    
    Args:
        g: NetworkX graph object representing the network topology. Edges can have 'length' and 'attenuation' attributes for quantum channels.
        cc_delay: Classical communication delay in milliseconds for all classical links
        memory_size: Number of memories per QuantumRouter (default: 5)
        output_file: Name of the output JSON file (default: 'output.json')
        output_directory: Directory to save the output file (default: 'tmp')
        stop_time: Optional stop time for the simulation in seconds (default: None)
        formalism: Optional formalism for the simulation (default: None)
        node_template: Optional template for nodes (default: None)
        meas_fid: Measurement fidelity (default: 1)
        gate_fid: Gate fidelity (default: 1)
    
    Returns:
        A tuple containing two dictionaries: the first dictionary is the output configuration, 
                                             the second dictionary is the mapping from graph nodes to names.
    """
    # Configure and validate the template
    templates: dict = node_template or default_template
    if 'router_template' not in templates or 'bsm_template' not in templates:
        raise ValueError("Template must contain 'router_template' and 'bsm_template' keys.")
    output_dict: dict = {Topology.ALL_TEMPLATES: templates}

    if cc_delay < 0:
        cc_delay = 0

    router_names = [router_name_func(i) for i in range(len(g.nodes))]
    nodes: list[dict] = generate_nodes(router_names, memory_size, 'router_template',
                                       measurement_fidelity=meas_fid, gate_fidelity=gate_fid)
    graph_to_name = {graph_node: router_names[i] for i, graph_node in enumerate(g.nodes)}

    bsm_nodes = []
    qlinks = []
    clinks = []
    for i, (left, right, data) in enumerate(g.edges(data=True)):
        qc_length: float = data.get('length', 10.0)
        qc_attn: float = data.get('attenuation', 0.0002)
        to_bsm_dist: float = qc_length * 1000 / 2  # Convert to meters, get middle

        left_name = graph_to_name[left]
        right_name = graph_to_name[right]
        bsm_name = bsm_name_func(left_name, right_name)
        bsm_nodes.append({Topology.NAME: bsm_name, Topology.TYPE: Topology.BSM_NODE, Topology.SEED: i, Topology.TEMPLATE: 'bsm_template'})

        # Quantum Links (Node -> BSM <- Node)
        qlinks.append({Topology.SRC: left_name, Topology.DST: bsm_name, Topology.DISTANCE: to_bsm_dist, Topology.ATTENUATION: qc_attn})
        qlinks.append({Topology.SRC: right_name, Topology.DST: bsm_name, Topology.DISTANCE: to_bsm_dist, Topology.ATTENUATION: qc_attn})

        # Classical Links (Node <-> BSM <-> Node)
        clinks.append({Topology.SRC: left_name, Topology.DST: bsm_name, Topology.DISTANCE: to_bsm_dist, Topology.DELAY: int(cc_delay * MILLISECOND)})
        clinks.append({Topology.SRC: bsm_name, Topology.DST: left_name, Topology.DISTANCE: to_bsm_dist, Topology.DELAY: int(cc_delay * MILLISECOND)})
        clinks.append({Topology.SRC: right_name, Topology.DST: bsm_name, Topology.DISTANCE: to_bsm_dist, Topology.DELAY: int(cc_delay * MILLISECOND)})
        clinks.append({Topology.SRC: bsm_name, Topology.DST: right_name, Topology.DISTANCE: to_bsm_dist, Topology.DELAY: int(cc_delay * MILLISECOND)})


    output_dict[Topology.ALL_NODE] = nodes + bsm_nodes

    output_dict[Topology.ALL_Q_CHANNEL] = qlinks
    router_clinks = generate_classical(router_names, cc_delay)
    clinks += router_clinks
    output_dict[Topology.ALL_C_CHANNEL] = clinks
    if stop_time:
        output_dict[Topology.STOP_TIME] = int(stop_time * SECOND)
    if formalism:
        output_dict[Topology.FORMALISM] = formalism

    output_dir = Path(output_directory)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(output_dir / output_file, 'w') as f:
        json.dump(output_dict, f, indent=2)

    return output_dict, graph_to_name
