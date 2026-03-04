""" Truly Naive demo (Apparently I'll be working on Erbium anyway this summer)
- special demo of qconnection expansion driven by endpoint properties.

This example shows the intended user-space extension path:
1. subclass built-in node types and register them under new names
2. use those custom type names directly in build_config
3. subclass the topology family and override its microhooks
   (small single-responsibility methods like _midpoint_type_for_qconnection,
   _midpoint_node_config, _build_node) to change how the pipeline behaves
   without rewriting the pipeline itself

Network topology:
    r1 (Yb) -- auto QFCBSMNode -- r2 (Er) -- auto BSMNode -- r3 (Er) -- auto QFCBSMNode -- r4 (Yb)
"""

from pathlib import Path

from sequence.topology.topology import Topology
from sequence.topology.topology_families import BsmTopologyFamily
from sequence.topology.node import BSMNode, Node, QuantumRouter
from sequence.topology.const_topo import ALL_NODE, NAME, SEED, TEMPLATE, TYPE
from sequence.kernel.entity import Entity
from sequence.resource_management.rule_manager import Rule
from sequence.resource_management.action_condition_set import eg_rule_condition
from sequence.entanglement_management.generation import EntanglementGenerationA

# In my naive imagination I forsee us having to accommodate for frequency differences with specific QFC support.
PLATFORM_WAVELENGTHS = {"Yb": 980, "Er": 1550}
BSM_NATIVE_WL        = 1550


""" Attaching platform properties as class attributes on registered node types
means the topology family can resolve hardware info from just a config string:
   Node._registry[node_type].operating_wavelength

- This means no if/elif chains, no hardcoded mappings.
"""
@Node.register("YbRouterNode")
class YbRouterNode(QuantumRouter):
    platform = "Yb"
    operating_wavelength = PLATFORM_WAVELENGTHS["Yb"]

@Node.register("ErRouterNode")
class ErRouterNode(QuantumRouter):
    platform = "Er"
    operating_wavelength = PLATFORM_WAVELENGTHS["Er"]


class QFC(Entity):
    """Mock Quantum Frequency Converter.

    Converts photons from input_wl to output_wl with a given efficiency.
    Failed conversions drop the photon.

    just a placeholder device I created for this demo, very naive.
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


@Node.register("QFCBSMNode")
class QFCBSMNode(BSMNode):
    """BSMNode with a per-src QFC routing table.

    _qfc_map is populated externally by QfcBsmFamily based on
    endpoint node wavelengths. This class carries no platform awareness itself.
    """

    def __init__(self, name, timeline, other_nodes, seed=None, component_templates=None):
        super().__init__(name, timeline, other_nodes, seed=seed, component_templates=component_templates)
        self._qfc_map = {}

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


class QfcBsmFamily(BsmTopologyFamily):
    """Auto-select midpoint type based on endpoint wavelength compatibility.

    Mixed-wavelength links generate `QFCBSMNode`; native telecom links use the
    default `BSMNode`. This demonstrates qconnection expansion driven by
    endpoint properties rather than by manually declared midpoint nodes.
    """

    def _configure_family(self, config: dict, templates: dict) -> None:
        self._node_specs = {node[NAME]: node for node in config[ALL_NODE]}
        self._router_nodes: dict[str, QuantumRouter] = {}
        self._bsm_links: list[tuple[str, str, str]] = []

    def _endpoint_wavelength(self, node_name: str) -> int:
        node_type = self._node_specs[node_name][TYPE]
        node_cls = Node._registry[node_type]
        return node_cls.operating_wavelength
    # microhook: called by _expand_qconnection to decide what midpoint type to generate
    def _midpoint_type_for_qconnection(self, q_connect: dict) -> str:
        node1 = q_connect["node1"]
        node2 = q_connect["node2"]
        wavelengths = {self._endpoint_wavelength(node1), self._endpoint_wavelength(node2)}
        if wavelengths == {BSM_NATIVE_WL}:
            return "BSMNode"
        return "QFCBSMNode"

    # microhook: called by _expand_qconnection to build the midpoint's config dict
    def _midpoint_node_config(self, node1: str, node2: str, q_connect: dict) -> dict:
        midpoint = super()._midpoint_node_config(node1, node2, q_connect)
        if midpoint[TYPE] == "BSMNode":
            return midpoint
        midpoint[TEMPLATE] = q_connect.get(TEMPLATE, None)
        midpoint["others"] = [node1, node2]
        midpoint["qfc_efficiency"] = q_connect.get("qfc_efficiency", 1.0)
        return midpoint

    def _record_bsm_link(self, midpoint_name: str, others: list[str]) -> None:
        initiator, responder = others[0], others[1]
        self._bsm_links.append((initiator, responder, midpoint_name))

    def _add_qfc_components(self, bsm_node: QFCBSMNode, others: list[str], tl, efficiency: float) -> None:
        """Attach per-endpoint QFC components for non-native wavelengths."""
        bsm = bsm_node.get_components_by_type("SingleAtomBSM")[0]
        bsm_node._qfc_map = {}
        for router_name in others:
            wl = self._router_nodes[router_name].operating_wavelength
            if wl == BSM_NATIVE_WL:
                continue
            qfc = QFC(
                f"{bsm_node.name}.QFC.{router_name}",
                tl,
                input_wl=wl,
                output_wl=BSM_NATIVE_WL,
                efficiency=efficiency,
            )
            bsm_node.add_component(qfc)
            qfc.add_receiver(bsm)
            bsm_node._qfc_map[router_name] = qfc

    def _build_qfc_midpoint(self, node: dict, template: dict, tl, nodes: dict) -> None:
        """Construct a QFC midpoint node and record its generated link."""
        others = node.get("others", [])
        bsm_node = QFCBSMNode(node[NAME], tl, others, component_templates=template)
        self._add_qfc_components(
            bsm_node,
            others,
            tl,
            efficiency=node.get("qfc_efficiency", 1.0),
        )
        self._record_bsm_link(node[NAME], others)
        bsm_node.set_seed(node[SEED])
        nodes["QFCBSMNode"].append(bsm_node)

    def _record_standard_node(self, node: dict, node_type: str, nodes: dict, bsm_to_router_map: dict) -> None:
        """Track standard midpoint and router nodes built by the base family."""
        if node_type == "BSMNode":
            self._record_bsm_link(node[NAME], bsm_to_router_map[node[NAME]])
        else:
            self._router_nodes[node[NAME]] = nodes[node_type][-1]

    # microhook: called by _add_nodes to construct each node from its config
    def _build_node(self, node, node_type, template, tl, nodes, bsm_to_router_map):
        if node_type == "QFCBSMNode":
            self._build_qfc_midpoint(node, template, tl, nodes)

        else:
            super()._build_node(node, node_type, template, tl, nodes, bsm_to_router_map)
            self._record_standard_node(node, node_type, nodes, bsm_to_router_map)

    def _attach_protocols(self):
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


class HeteroNetTopo(Topology):
    """Topology for heterogeneous chains with auto-selected midpoint hardware.

    Attributes:
        router_nodes (dict[str, Node]): router nodes keyed by name.
        bsm_links (list): (initiator_name, responder_name, mid_name) per link.
        tl (Timeline): simulation timeline.
    """

    def __init__(self, conf_file_name: str):
        family = QfcBsmFamily()
        super().__init__(conf_file_name, family)
        self.router_nodes = family._router_nodes
        self.bsm_links    = family._bsm_links

    #NOTICE: how the Topology subclass layer is meant to house querying/simulation-monitoring functions.
    #        actual behavior doesn't go here.

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
    config_path = Path(__file__).with_name("heterogeneous_midpoints.json")
    topo = HeteroNetTopo(str(config_path))
    topo.tl.init()
    topo.tl.run()

    print("Endpoint node types:")
    for node in topo.end_nodes + topo.repeater_nodes:
        print(f"  {node.name}: {node.__class__.__name__} @ {node.operating_wavelength} nm")

    print("\nAuto-generated midpoint node types:")
    for node_type, node_list in topo.get_nodes().items():
        if node_type in ("QFCBSMNode", "BSMNode"):
            for node in node_list:
                print(f"  {node.name}: {node_type}")

    for node in topo.end_nodes + topo.repeater_nodes:
        print(f"\n{node.name} memories:")
        print("Index\tEntangled Node\tFidelity\tEntanglement Time")
        for info in node.resource_manager.memory_manager:
            print(f"{info.index}\t{info.remote_node}\t{info.fidelity}\t"
                  f"{info.entangle_time * 1e-12 if info.entangle_time else None}")

    print("\nQFC photon counts:")
    for name, count in topo.get_qfc_stats().items():
        print(f"  {name}: {count}")
