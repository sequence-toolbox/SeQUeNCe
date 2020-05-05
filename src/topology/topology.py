import json5

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
        self.nodes = {} # internal node dictionary {node_name : node}
        self.graph = {} # internal quantum graph representation {node_name : {adjacent_name : distance}}

    def load_config(self, config_file):
        topo_config = json5.load(open(config_file))

        # create nodes
        for node_params in topo_config["nodes"]:
            name = node_params.pop("name")
            node_type = node_params.pop("type")

            if node_type == "QKDNode":
                node = QKDNode(name, self.timeline, **node_params)
            elif node_type == "QuantumRouter":
                node = QuantumRouter(name, self.timeline, **node_params)
            else:
                node = Node(name, self.timeline)
            
            self.add_node(node)

        # create connections
        for qchannel_params in topo_config["qconnections"]:
            node1 = qchannel_params.pop("node1")
            node2 = qchannel_params.pop("node2")
            self.add_quantum_connection(node1, node2, **qchannel_params)

        for cchannel_params in topo_config["cconnections"]:
            node1 = cchannel_params.pop("node1")
            node2 = cchannel_params.pop("node2")
            self.add_classical_connection(node1, node2, **cchannel_params)

    def add_node(self, node: "Node"):
        self.nodes[node.name] = node
        self.graph[node.name] = {}

    def add_quantum_connection(self, node1: str, node2: str, **kwargs):
        assert node1 in self.nodes and node2 in self.nodes

        if (type(self.nodes[node1]) == QuantumRouter) and (type(self.nodes[node2]) == QuantumRouter):
            # add middle node
            name_middle = "_".join(["middle", node1, node2])
            middle = MiddleNode(name_middle, self.timeline, [node1, node2])
            self.add_node(middle)

            # update params
            kwargs["distance"] = kwargs["distance"] / 2

            # add quantum channels
            for node in [node1, node2]:
                self.add_quantum_connection(node, name_middle, **kwargs)

            # also add classical channels
            for node in [node1, node2]:
                self.add_classical_connection(node, name_middle, **kwargs)

        else:
            # add quantum channel
            name = "_".join(["qc", node1, node2])
            qchannel = QuantumChannel(name, self.timeline, **kwargs)
            qchannel.set_ends(self.nodes[node1], self.nodes[node2])

            # edit graph
            self.graph[node1][node2] = kwargs["distance"]
            self.graph[node2][node1] = kwargs["distance"]

    def add_classical_connection(self, node1: str, node2: str, **kwargs):
        assert node1 in self.nodes and node2 in self.nodes

        # update params
        kwargs["attenuation"] = 0

        name = "_".join(["cc", node1, node2])
        cchannel = ClassicalChannel(name, self.timeline, **kwargs)
        cchannel.set_ends(self.nodes[node1], self.nodes[node2])

    def _get_connections(self):


    def generate_forwarding_table(self, starting_node: str):
        '''
        generates a mapping of destination nodes to next node for routing using Dijkstra's algorithm
        node: string (name of node for which to generate table)
        '''
        # set up priority queue and track previous nodes
        nodes = self.nodes.keys()
        costs = {node: float("inf") for node in nodes}
        previous = {node: None for node in nodes}
        costs[starting_node] = 0

        # Dijkstra's
        while len(nodes) > 0:
            current = min(nodes, key=lambda node: costs[node])
            if costs[current] == float("inf"):
                break
            for neighbor in self.graph[current]:
                distance = self.graph[current][neighbor]
                new_cost = costs[current] + distance
                if new_cost < costs[neighbor]:
                    costs[neighbor] = new_cost
                    previous[neighbor] = current
            nodes.remove(current)

        # find forwarding nieghbor for each destination
        for node, prev in previous.items():
            if prev is None:
                del previous[prev]
            elif prev is starting_node:
                previous[node] = node
            else:
                while prev not in self.graph[starting_node]:
                    prev = previous[prev]
                    previous[node] = prev

        return previous

    def populate_protocols(self):
        # TODO: add higher-level protocols not added by nodes
        raise NotImplementedError("populate_protocols has not been added")


