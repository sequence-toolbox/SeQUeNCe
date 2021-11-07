"""Definition of the Topology class.

This module provides a definition of the Topology class, which can be used to manage a network's structure.
Topology instances automatically perform many useful network functions.
"""

from typing import TYPE_CHECKING

import json5

if TYPE_CHECKING:
    from ..kernel.timeline import Timeline

from .node import *
from ..components.optical_channel import QuantumChannel, ClassicalChannel


class Topology():
    """Class for managing network topologies.

    The topology class provies a simple interface for managing the nodes and connections in a network.
    A network may also be generated using an external json file.

    Attributes:
        name (str): label for topology.
        timeline (Timeline): timeline to be used for all objects in network.
        nodes (Dict[str, Node]): mapping of node names to node objects.
        qchannels (List[QuantumChannel]): list of quantum channel objects in network.
        cchannels (List[ClassicalChannel]): list of classical channel objects in network.
        graph: (Dict[str, Dict[str, float]]): internal representation of quantum graph.
    """

    def __init__(self, name: str, timeline: "Timeline"):
        """Constructor for topology class.

        Args:
            name (str): label for topology.
            timeline (Timeline): timeline for simulation.
        """

        self.name = name
        self.timeline = timeline
        self.nodes = {}           # internal node dictionary {node_name : node}
        self.qchannels = []       # list of quantum channels
        self.cchannels = []       # list of classical channels

        self.graph = {}           # internal quantum graph representation {node_name : {adjacent_name : distance}}
        self.graph_no_middle = {} # internal quantum graph without bsm nodes {node_name : {adjacent_name : distance}}
        self._cc_graph = {}       # internal classical graph representation {node_name : {adjacent_name : delay}}

    def load_config(self, config_file: str) -> None:
        """Method to load a network configuration file.

        Network should be specified in json format.
        Will populate nodes, qchannels, cchannels, and graph fields.
        Will also generate and install forwarding tables for quantum router nodes.

        Args:
            config_file (str): path to json file specifying network.

        Side Effects:
            Will modify graph, graph_no_middle, qchannels, and cchannels attributes.
        """

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

        # create discrete cconnections (two way classical channel)
        if "cconnections" in topo_config:
            for cchannel_params in topo_config["cconnections"]:
                node1 = cchannel_params.pop("node1")
                node2 = cchannel_params.pop("node2")
                self.add_classical_connection(node1, node2, **cchannel_params)

        # create discrete cchannels
        if "cchannels" in topo_config:
            for cchannel_params in topo_config["cchannels"]:
                node1 = cchannel_params.pop("node1")
                node2 = cchannel_params.pop("node2")
                self.add_classical_channel(node1, node2, **cchannel_params)

        # create cchannels from a RT table
        if "cchannels_table" in topo_config:
            table_type = topo_config["cchannels_table"].get("type", "RT")
            assert table_type == "RT", "non-RT tables not yet supported"
            labels = topo_config["cchannels_table"]["labels"]
            table = topo_config["cchannels_table"]["table"]
            assert len(labels) == len(table)                 # check that number of rows is correct

            for i in range(len(table)):
                assert len(table[i]) == len(labels)          # check that number of columns is correct
                for j in range(len(table[i])):
                    if table[i][j] == 0:                     # skip if have 0 entries
                        continue
                    delay = table[i][j] / 2                  # divide RT time by 2
                    cchannel_params = {"delay": delay, "distance": 1e3}
                    self.add_classical_channel(labels[i], labels[j], **cchannel_params)

        # create qconnections (two way quantum channel)
        if "qconnections" in topo_config:
            for qchannel_params in topo_config["qconnections"]:
                node1 = qchannel_params.pop("node1")
                node2 = qchannel_params.pop("node2")
                self.add_quantum_connection(node1, node2, **qchannel_params)
        
        # create qchannels
        if "qchannels" in topo_config:
            for qchannel_params in topo_config["qchannels"]:
                node1 = qchannel_params.pop("node1")
                node2 = qchannel_params.pop("node2")
                self.add_quantum_channel(node1, node2, **qchannel_params)

        # generate forwarding tables
        for node in self.get_nodes_by_type("QuantumRouter"):
            table = self.generate_forwarding_table(node.name)
            for dst, next_node in table.items():
                node.network_manager.protocol_stack[0].add_forwarding_rule(dst, next_node)

    def add_node(self, node: "Node") -> None:
        """Method to add a node to the network.

        Args:
            node (Node): node to add.
        """

        self.nodes[node.name] = node
        self.graph[node.name] = {}
        if type(node) != BSMNode:
            self.graph_no_middle[node.name] = {}
        self._cc_graph[node.name] = {}

    def add_quantum_connection(self, node1: str, node2: str, **kwargs) -> None:
        """Method to add a two-way quantum channel connection between nodes.

        NOTE: kwargs are passed to constructor for quantum channel, may be used to specify channel parameters.

        Args:
            node1 (str): first node in pair to connect.
            node2 (str): second node in pair to connect.
        """

        assert node1 in self.nodes, node1 + " not a valid node"
        assert node2 in self.nodes, node2 + " not a valid node"

        if (type(self.nodes[node1]) == QuantumRouter) and (type(self.nodes[node2]) == QuantumRouter):
            # update non-middle graph
            self.graph_no_middle[node1][node2] = kwargs["distance"]
            self.graph_no_middle[node2][node1] = kwargs["distance"]

            # add middle node
            name_middle = "_".join(["middle", node1, node2])
            middle = BSMNode(name_middle, self.timeline, [node1, node2])
            self.add_node(middle)

            # update distance param
            kwargs["distance"] = kwargs["distance"] / 2

            # add quantum channels
            for node in [node1, node2]:
                self.add_quantum_channel(node, name_middle, **kwargs)

            self.nodes[node1].add_bsm_node(middle.name, node2)
            self.nodes[node2].add_bsm_node(middle.name, node1)

            # update params
            del kwargs["attenuation"]
            if node1 in self._cc_graph and node2 in self._cc_graph[node1]:
                kwargs["delay"] = (self._cc_graph[node1][node2] +
                                   self._cc_graph[node2][node1]) / 4

            # add classical channels (for middle node connectivity)
            for node in [node1, node2]:
                self.add_classical_connection(name_middle, node, **kwargs)

        else:
            self.add_quantum_channel(node1, node2, **kwargs)
            self.add_quantum_channel(node2, node1, **kwargs)

    def add_quantum_channel(self, node1: str, node2: str, **kwargs) -> None:
        """Method to add a one-way quantum channel connection.

        NOTE: kwargs are passed to constructor for quantum channel, may be used to specify channel parameters.

        Args:
            node1 (str): first node in pair to connect (sender).
            node2 (str): second node in pair to connect (receiver).
        """

        name = "_".join(["qc", node1, node2])
        qchannel = QuantumChannel(name, self.timeline, **kwargs)
        qchannel.set_ends(self.nodes[node1], node2)
        self.qchannels.append(qchannel)

        # edit graph
        self.graph[node1][node2] = kwargs["distance"]
        if type(self.nodes[node1]) != BSMNode and type(self.nodes[node2]) != BSMNode:
            self.graph_no_middle[node1][node2] = kwargs["distance"]

    def add_classical_connection(self, node1: str, node2: str, **kwargs) -> None:
        """Method to add a two-way classical channel between nodes.

        NOTE: kwargs are passed to constructor for classical channel, may be used to specify channel parameters.

        Args:
            node1 (str): first node in pair to connect.
            node2 (str): second node in pair to connect.
        """

        self.add_classical_channel(node1, node2, **kwargs)
        self.add_classical_channel(node2, node1, **kwargs)

    def add_classical_channel(self, node1: str, node2: str, **kwargs) -> None:
        """Method to add a one-way classical channel between nodes.

        NOTE: kwargs are passed to constructor for classical channel, may be used to specify channel parameters.

        Args:
            node1 (str): first node in pair to connect.
            node2 (str): second node in pair to connect.
        """

        assert node1 in self.nodes and node2 in self.nodes

        name = "_".join(["cc", node1, node2])
        cchannel = ClassicalChannel(name, self.timeline, **kwargs)
        cchannel.set_ends(self.nodes[node1], node2)
        self.cchannels.append(cchannel)

        # edit graph
        self._cc_graph[node1][node2] = cchannel.delay 

    def get_nodes_by_type(self, node_type: str) -> [Node]:
        return [node for name, node in self.nodes.items() if type(node).__name__ == node_type]

    def generate_forwarding_table(self, starting_node: str) -> dict:
        """Method to create forwarding table for static routing protocol.

        Generates a mapping of destination nodes to next node for routing using Dijkstra's algorithm.

        Args:
            node (str): name of node for which to generate table.
        """

        # set up priority queue and track previous nodes
        nodes = list(self.nodes.keys())
        costs = {node: float("inf") for node in nodes}
        previous = {node: None for node in nodes}
        costs[starting_node] = 0

        # Dijkstra's
        while len(nodes) > 0:
            current = min(nodes, key=lambda node: costs[node])
            if type(self.nodes[current]) == BSMNode:
                nodes.remove(current)
                continue
            if costs[current] == float("inf"):
                break
            for neighbor in self.graph_no_middle[current]:
                distance = self.graph_no_middle[current][neighbor]
                new_cost = costs[current] + distance
                if new_cost < costs[neighbor]:
                    costs[neighbor] = new_cost
                    previous[neighbor] = current
            nodes.remove(current)

        # find forwarding neighbor for each destination
        next_node = {k: v for k, v in previous.items() if v} # remove nodes whose previous is None (starting, not connected)
        for node, prev in next_node.items():
            if prev is starting_node:
                next_node[node] = node
            else:
                while prev not in self.graph_no_middle[starting_node]:
                    prev = next_node[prev]
                    next_node[node] = prev

        return next_node

    def populate_protocols(self):
        # TODO: add higher-level protocols not added by nodes
        raise NotImplementedError("populate_protocols has not been added")


