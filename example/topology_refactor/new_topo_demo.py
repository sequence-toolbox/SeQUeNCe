"""BDCZ Quantum Repeater Simulation - Research Prototype.

Network topology:
    r1 (Yb, 980nm) -- m12 (QFC+BSM) -- r2 (Er, 1550nm) -- m23 (QFC+BSM) -- r3 (Yb, 980nm)

Based on: Briegel, Dür, Cirac, Zoller (1998) - Quantum Repeaters for Communication.

Research phase — pending integration:
    - QFCBSMNode:                  local subclass → BSMNode._qfc_map + BsmNetworkImpl wiring
    - QFC:                         local mock     → sequence/components/
    - HeterogeneousBsmNetworkImpl: local subclass → BsmNetworkImpl
"""

from sequence.topology.topology import Topology
from sequence.topology.network_impls import BsmNetworkImpl
from sequence.topology.node import BSMNode
from sequence.topology.const_topo import BSM_NODE, QUANTUM_ROUTER, NAME, SEED
from sequence.kernel.entity import Entity
from sequence.resource_management.rule_manager import Rule
from sequence.resource_management.action_condition_set import eg_rule_condition
from sequence.entanglement_management.generation import EntanglementGenerationA

PLATFORM_WAVELENGTHS = {"Yb": 980, "Er": 1550}
BSM_NATIVE_WL        = 1550


class QFC(Entity):
    """Mock Quantum Frequency Converter.

    Converts photons from input_wl to output_wl with a given efficiency.
    Failed conversions drop the photon.

    Pending graduation to sequence/components/.
    """

    def __init__(self, name, timeline, input_wl, output_wl, efficiency=1.0):
        Entity.__init__(self, name, timeline)
        self.input_wl       = input_wl
        self.output_wl      = output_wl
        self.efficiency     = efficiency
        self.photon_counter = 0

    def init(self): pass

    def get(self, photon, **kwargs):
        self.photon_counter += 1
        if self.get_generator().random() < self.efficiency:
            photon.wavelength = self.output_wl
            self._receivers[0].get(photon, **kwargs)


class QFCBSMNode(BSMNode):
    """BSMNode with a per-src QFC routing table.

    _qfc_map is populated externally by HeterogeneousBsmNetworkImpl based on
    the 'platforms' config field. This class carries no platform awareness.

    Pending integration: _qfc_map slot + receive_qubit override → BSMNode,
    QFC wiring → BsmNetworkImpl._create_node.
    """

    def receive_qubit(self, src: str, qubit) -> None:
        if src in self._qfc_map:
            self._qfc_map[src].get(qubit)
        else:
            self.components[self.first_component_name].get(qubit)


def _eg_action_request(memories_info, args):
    memory   = memories_info[0].memory
    protocol = EntanglementGenerationA.create(
        None, "EGA." + memory.name, args["mid"], args["other"], memory)
    req_args = {"remote_node": args["self_name"], "memory_indices": args["memory_indices"]}
    return protocol, [args["other"]], [_eg_match], [req_args]


def _eg_match(protocols, args):
    for p in protocols:
        if isinstance(p, EntanglementGenerationA) and p.remote_node_name == args["remote_node"]:
            return p


def _eg_action_await(memories_info, args):
    memory   = memories_info[0].memory
    protocol = EntanglementGenerationA.create(
        None, "EGA." + memory.name, args["mid"], args["other"], memory)
    return protocol, [None], [None], [None]


class HeterogeneousBsmNetworkImpl(BsmNetworkImpl):
    """Yb/Er heterogeneous platform support via QFC-wired BSM nodes.

    Reads a 'platforms' dict from each BSM node config, creates QFCs for any
    side whose wavelength differs from BSM_NATIVE_WL, and wires them in.

    Config convention: first key in 'platforms' = initiating router.

    Pending integration: platform wiring → BsmNetworkImpl._create_node,
    QFC → sequence/components/, QFCBSMNode → BSMNode + BsmNetworkImpl.
    """

    def __init__(self):
        super().__init__()
        self._router_nodes: dict = {}
        self._bsm_links:    list = []

    def _create_node(self, node, node_type, template, tl, nodes, bsm_to_router_map):
        if node_type == BSM_NODE:
            platforms = node.get("platforms", {})
            others    = list(platforms.keys())
            bsm_node  = QFCBSMNode(node[NAME], tl, others, component_templates=template)
            bsm       = bsm_node.get_components_by_type("SingleAtomBSM")[0]

            bsm_node._qfc_map = {}
            for router_name, platform in platforms.items():
                wl = PLATFORM_WAVELENGTHS[platform]
                if wl != BSM_NATIVE_WL:
                    qfc = QFC(f"{node[NAME]}.QFC.{router_name}", tl,
                              input_wl=wl, output_wl=BSM_NATIVE_WL,
                              efficiency=node.get("qfc_efficiency", 1.0))
                    bsm_node.add_component(qfc)
                    qfc.add_receiver(bsm)
                    bsm_node._qfc_map[router_name] = qfc

            initiator, responder = others[0], others[1]
            self._bsm_links.append((initiator, responder, node[NAME]))
            bsm_node.set_seed(node[SEED])
            nodes[node_type].append(bsm_node)

        else:
            super()._create_node(node, node_type, template, tl, nodes, bsm_to_router_map)
            if node_type == QUANTUM_ROUTER:
                self._router_nodes[node[NAME]] = nodes[QUANTUM_ROUTER][-1]

    def _add_protocols(self):
        for initiator_name, responder_name, mid_name in self._bsm_links:
            initiator    = self._router_nodes[initiator_name]
            responder    = self._router_nodes[responder_name]
            memo_array   = initiator.get_components_by_type("MemoryArray")[0]
            memo_indices = set(range(len(memo_array.memories)))
            cond_args    = {"memory_indices": memo_indices}

            initiator.resource_manager.load(Rule(10, _eg_action_request, eg_rule_condition,
                {"mid": mid_name, "other": responder_name,
                 "self_name": initiator_name, "memory_indices": memo_indices},
                cond_args))

            responder.resource_manager.load(Rule(10, _eg_action_await, eg_rule_condition,
                {"mid": mid_name, "other": initiator_name},
                cond_args))


class BDCZHeterogeneousTopo(Topology):
    """Topology for BDCZ repeater chains with heterogeneous Yb/Er platform nodes.

    BSM midpoints are automatically equipped with QFCs on any arm whose platform
    wavelength differs from the BSM native wavelength (1550nm telecom). Platform
    assignments are declared per-node in the config via the 'platforms' field.

    Attributes:
        router_nodes (dict[str, Node]): router nodes keyed by name.
        bsm_links (list): (initiator_name, responder_name, mid_name) per link.
        tl (Timeline): simulation timeline.
    """

    def __init__(self, conf_file_name: str):
        impl = HeterogeneousBsmNetworkImpl()
        super().__init__(conf_file_name, impl)
        self.router_nodes = impl._router_nodes
        self.bsm_links    = impl._bsm_links

    def _link_counts(self):
        counts = {}
        for initiator, responder, _ in self.bsm_links:
            for name in (initiator, responder):
                counts[name] = counts.get(name, 0) + 1
        return counts

    @property
    def end_nodes(self):
        return [self.router_nodes[n] for n, c in self._link_counts().items() if c == 1]

    @property
    def repeater_nodes(self):
        return [self.router_nodes[n] for n, c in self._link_counts().items() if c > 1]

    def get_qfc_stats(self):
        stats = {}
        for _, _, mid_name in self.bsm_links:
            node = self.tl.get_entity_by_name(mid_name)
            for comp in node.components.values():
                if isinstance(comp, QFC):
                    stats[comp.name] = comp.photon_counter
        return stats


if __name__ == "__main__":
    topo = BDCZHeterogeneousTopo("example/topology_refactor/new_topo_demo.json")
    topo.tl.init()
    topo.tl.run()

    for node in topo.end_nodes + topo.repeater_nodes:
        print(f"\n{node.name} memories:")
        print("Index\tEntangled Node\tFidelity\tEntanglement Time")
        for info in node.resource_manager.memory_manager:
            print(f"{info.index}\t{info.remote_node}\t{info.fidelity}\t"
                  f"{info.entangle_time * 1e-12 if info.entangle_time else None}")

    print("\nQFC photon counts:")
    for name, count in topo.get_qfc_stats().items():
        print(f"  {name}: {count}")
