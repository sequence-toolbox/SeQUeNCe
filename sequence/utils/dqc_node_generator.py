from ..topology.dqc_net_topo import DQCNetTopo
from ..topology.topology import Topology
def generate_quantum_dqc_nodes(router_names: str, memo_size: int, data_memo_size: int, template: str = '', gate_fidelity: float = 1, measurement_fidelity: float = 1) -> list:
    """generate a list of node configs for quantum nodes
    """
    nodes = []
    for i, name in enumerate(router_names):
        config = {Topology.NAME: name,
                  Topology.TYPE: DQCNetTopo.DQC_NODE,
                  Topology.SEED: i,
                  DQCNetTopo.MEMO_ARRAY_SIZE: memo_size,
                  DQCNetTopo.DATA_MEMO_ARRAY_SIZE: data_memo_size}
        if template:
            config[Topology.TEMPLATE] = template
        if gate_fidelity:
            config[Topology.GATE_FIDELITY] = gate_fidelity
        if measurement_fidelity:
            config[Topology.MEASUREMENT_FIDELITY] = measurement_fidelity
        nodes.append(config)
    return nodes
