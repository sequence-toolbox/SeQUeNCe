from typing import TYPE_CHECKING

import json5

if TYPE_CHECKING:
    from ..kernel.timeline import Timeline

from .node import *
from ..components.optical_channel import QuantumChannel, ClassicalChannel


class Topology():
    def __init__(self, name: str, timeline: "Timeline"):
        self.name = name
        self.timeline = timeline
        self.nodes = {}      # internal node dictionary {node_name : node}
        self.graph = {}      # internal quantum graph representation {node_name : {adjacent_name : distance}}
        self.qchannels = []  # list of quantum channels
        self.cchannels = []  # list of classical channels

    def load_config(self, config_file: str) -> None:
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

        # create qconnections
        for qchannel_params in topo_config["qconnections"]:
            node1 = qchannel_params.pop("node1")
            node2 = qchannel_params.pop("node2")
            self.add_quantum_connection(node1, node2, **qchannel_params)

        # create cconnections (if discrete present, otherwise generate from table
        if "cconnections" in topo_config:
            for cchannel_params in topo_config["cconnections"]:
                node1 = cchannel_params.pop("node1")
                node2 = cchannel_params.pop("node2")
                self.add_classical_connection(node1, node2, **cchannel_params)
        else:
            table_type = topo_config["cconnections_table"].get("type", "RT")
            assert table_type == "RT", "non-RT tables not yet supported"
            labels = topo_config["cconnections_table"]["labels"]
            table = topo_config["cconnections_table"]["table"]
            assert len(labels) == len(table)                 # check that number of rows is correct
            
            for i in range(len(table)):
                assert len(table[i]) == len(labels)          # check that number of columns is correct
                for j in range(i + 1, len(table)):
                    if table[i][j] == 0 or table[j][i] == 0: # skip if have 0 entries
                        continue
                    delay = (table[i][j] + table[j][i]) / 2
                    cchannel_params = {"delay": delay, "distance": 1e3}
                    self.add_classical_connection(labels[i], labels[j], **cchannel_params)

    def add_node(self, node: "Node") -> None:
        self.nodes[node.name] = node
        self.graph[node.name] = {}

    def add_quantum_connection(self, node1: str, node2: str, **kwargs) -> None:
        assert node1 in self.nodes, node1 + " not a valid node"
        assert node2 in self.nodes, node2 + " not a valid node"

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
            self.qchannels.append(qchannel)

            # edit graph
            self.graph[node1][node2] = kwargs["distance"]
            self.graph[node2][node1] = kwargs["distance"]

    def add_classical_connection(self, node1: str, node2: str, **kwargs) -> None:
        assert node1 in self.nodes and node2 in self.nodes

        # update params
        kwargs["attenuation"] = 0

        name = "_".join(["cc", node1, node2])
        cchannel = ClassicalChannel(name, self.timeline, **kwargs)
        cchannel.set_ends(self.nodes[node1], self.nodes[node2])
        self.cchannels.append(cchannel)

    def get_nodes_by_type(self, node_type: str) -> [Node]:
        return [node for name, node in self.nodes.items() if type(node).__name__ == node_type]

    def generate_forwarding_table(self, starting_node: str) -> dict:
        '''
        generates a mapping of destination nodes to next node for routing using Dijkstra's algorithm
        node: string (name of node for which to generate table)
        '''
        # set up priority queue and track previous nodes
        nodes = list(self.nodes.keys())
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

        # find forwarding neighbor for each destination
        next_node = {k: v for k, v in previous.items() if v} # remove nodes whose previous is None (starting, not connected)
        for node, prev in next_node.items():
            if prev is starting_node:
                next_node[node] = node
            else:
                while prev not in self.graph[starting_node]:
                    prev = next_node[prev]
                    next_node[node] = prev

        # modify forwarding table to bypass middle nodes
        for node, dst in next_node.items():
            if type(self.nodes[dst]) == MiddleNode:
                adjacent_nodes = list(self.graph[dst].keys())
                proper_dst = None
                for adjacent in adjacent_nodes:
                    if adjacent != starting_node:
                        proper_dst = adjacent
                next_node[node] = proper_dst

        return next_node

    def populate_protocols(self):
        # TODO: add higher-level protocols not added by nodes
        raise NotImplementedError("populate_protocols has not been added")


