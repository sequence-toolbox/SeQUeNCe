import json5
import math

from ..components.detector import QSDetector
from ..components.light_source import LightSource
from ..components.optical_channel import *
from ..protocols.qkd.BB84 import BB84
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from ...kernel.timeline import Timeline

from .node import *
from ..components.optical_channel import QuantumChannel, ClassicalChannel

class Topology():
    def __init__(self, name, timeline: "Timeline"):
        self.timeline = timeline
        self.nodes = {}
        self.qchannels = []
        self.cchannels = []

    def load_config(self, config_file):
        topo_config = json5.load(open(config_file))

        repeater_separation = topo_config["global_params"].pop("repeater_separation")
        repeater_params = topo_config["global_params"]["repeater_params"]

        # create nodes
        for node_params in topo_config["nodes"]:
            name = node_params.pop("name")
            node_type = node_params.pop("type")

            if node_type == "QKDNode":
                node = QKDNode(name, self.timeline, **node_params)
            elif node_type == "QuantumRouter":
                node = QuantumRouter(name, self.timeline, **node_params)
            elif node_type == "MiddleNode":
                node = Middle(name, self.timeline, **node_params)
            else:
                node = Node(name, self.timeline)
            
            self.add_node(node)

        # create connections
        for connection_params in topo_config["connections"]:
            node1 = connection_params.pop("node1")
            node2 = connection_params.pop("node2")

            self.add_connection(node1, node2, repeater_separation, repeater_params, **connection_params)

    def add_node(self, node: "Node"):
        self.nodes[node.name] = node

    # creates a single quantum channel connection
    def add_quantum_connection(self, node1: str, node2: str, **kwargs):
        assert node1 in self.nodes and node2 in self.nodes

        name = "_".join(["qc", node1, node2])
        qchannel = QuantumChannel(name, self.timeline, **kwargs)
        qchannel.set_ends(self.nodes[node1], self.nodes[node2])
        self.qchannels.append(qchannel)

    # creates a single classical channel connection
    def add_classical_connection(self, node1: str, node2: str, **kwargs):
        assert node1 in self.nodes and node2 in self.nodes

        name = "_".join(["cc", node1, node2])
        cchannel = ClassicalChannel(name, self.timeline, **kwargs)
        cchannel.set_ends(self.nodes[node1], self.nodes[node2])
        self.cchannels.append(cchannel)

    # creates a quantum and classical connection with middle nodes/repeaters as needed
    def add_connection(self, node1: str, node2: str, repeater_separation=None, repeater_params={}, **kwargs):
        """
        node1, node2 : name of nodes to connect
        repeater_separation (default None) : max distance between repeaters (in m)
        repeater_params (default None) : dict of parameters for repeaters (if necessary)
        kwargs : dict of parameters for quantum, classical connections
        """
        assert node1 in self.nodes and node2 in self.nodes

        linear_node_list = []

        if repeater_separation is not None:
            num_links = math.ceil(kwargs["distance"] / repeater_separation)
            kwargs["distance"] = kwargs["distance"] / num_links # separation of repeaters (in m)

            # create repeaters (quantum router)
            for i in range(num_links - 1):
                name = "_".join([node1, node2, "repeater", str(i)])
                node = QuantumRouter(name, self.timeline, **repeater_params)
                self.add_node(node)
                linear_node_list.append(name)

        linear_node_list.insert(0, node1)
        linear_node_list.append(node2)

        # add middle nodes and repeater classical connections (if necessary)
        if type(self.nodes[node1]) == QuantumRouter:
            middle_nodes = []

            for i in range(len(linear_node_list) - 1):
                n1 = linear_node_list[i]
                n2 = linear_node_list[i + 1]
                self.add_classical_connection(n1, n2, **kwargs)

            for i in range(len(linear_node_list) - 1):
                name = "_".join([node1, node2, "middle", str(i)])
                others = linear_node_list[i:i+2]
                node = MiddleNode(name, self.timeline, others)
                self.add_node(node)
                middle_nodes.append(name)

            for i, node in enumerate(middle_nodes):
                linear_node_list.insert(2*i + 1, node)

            kwargs["distance"] = kwargs["distance"] / 2

        # add classical connections
        for i in range(len(linear_node_list) - 1):
            n1 = linear_node_list[i]
            n2 = linear_node_list[i + 1]
            self.add_classical_connection(n1, n2, **kwargs)

        # add quantum connections
        for i in range(len(linear_node_list) - 1):
            n1 = linear_node_list[i]
            n2 = linear_node_list[i + 1]
            self.add_quantum_connection(n1, n2, **kwargs)

    def populate_protocols(self):
        # TODO: add higher-level protocols not added by nodes
        raise NotImplementedError("populate_protocols has not been added")


