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
        self.nodes = {}
        self.qchannels = []
        self.cchannels = []

    def load_config(self, config_file):
        topo_config = json5.load(open(config_file))

        # create nodes
        for node_params in topo_config["nodes"]:
            name = node_params["name"]
            node_type = node_params["type"]
            del node_params["name"]
            del node_params["type"]

            if node_type == "qkd":
                node = QKDNode(name, self.timeline, **node_params)
            else:
                node = Node(name, self.timeline)
            
            self.add_node(node)

        # create quantum connections
        for qchannel_params in topo_config["qconnections"]:
            node1 = qchannel_params["node1"]
            node2 = qchannel_params["node2"]
            del qchannel_params["node1"]
            del qchannel_params["node2"]
            
            self.add_quantum_connection(node1, node2, **qchannel_params)

        # create classical connections
        for cchannel_params in topo_config["cconnections"]:
            node1 = cchannel_params["node1"]
            node2 = cchannel_params["node2"]
            del cchannel_params["node1"]
            del cchannel_params["node2"]

            self.add_classical_connection(node1, node2, **cchannel_params)

    def add_node(self, node: "Node"):
        self.nodes[node.name] = node

    def add_quantum_connection(self, node1: str, node2: str, **kwargs):
        assert node1 in self.nodes and node2 in self.nodes

        name = "_".join(["qc", node1, node2])
        qchannel = QuantumChannel(name, self.timeline, **kwargs)
        qchannel.set_ends(self.nodes[node1], self.nodes[node2])
        self.qchannels.append(qchannel)

    def add_classical_connection(self, node1: "Node", node2: "Node", **kwargs):
        assert node1 in self.nodes and node2 in self.nodes

        name = "_".join(["cc", node1, node2])
        cchannel = ClassicalChannel(name, self.timeline, **kwargs)
        cchannel.set_ends(self.nodes[node1], self.nodes[node2])
        self.cchannels.append(cchannel)

    def populate_protocols(self):
        # TODO: add higher-level protocols not added by nodes
        pass


class LegacyTopology:
    def __init__(self, config_file, timelines):
        self.nodes = {}
        self.quantum_channel = {}
        self.entities = []

        topo_config = json5.load(open(config_file))
        nodes_config = topo_config['nodes']
        self.create_nodes(nodes_config, timelines)
        self.create_qchannel(topo_config['QChannel'], timelines)
        self.create_cchannel(topo_config['CChannel'], timelines)
        self.create_protocols(nodes_config, timelines)

    def create_nodes(self, nodes_config, timelines):
        for node_config in nodes_config:
            components = {}

            for component_config in node_config['components']:
                if component_config['name'] in components:
                    raise Exception('two components have same name')

                # get component_name, timeline, and name
                # then delete entries in component_config dictionary to prevent conflicting values
                component_name = component_config['name']
                name = node_config['name'] + '.' + component_name
                tl = timelines[component_config['timeline']]
                del component_config['name']
                del component_config['timeline']

                # light source instantiation
                if component_config["type"] == 'LightSource':
                    ls = LightSource(name, tl, **component_config)
                    components[component_name] = ls
                    self.entities.append(ls)

                # detector instantiation
                elif component_config["type"] == 'QSDetector':
                    detector = QSDetector(name, tl, **component_config)
                    components[component_name] = detector
                    self.entities.append(detector)

                else:
                    raise Exception('unknown device type')

            node = Node(node_config['name'], timelines[node_config['timeline']], components=components)

            for protocol_config in node_config['protocols']:
                protocol_name = protocol_config['name']
                name = node_config['name'] + '.' + protocol_name
                tl = timelines[protocol_config['timeline']]
                del protocol_config['name']
                del protocol_config['timeline']

                if protocol_config["protocol"] == 'BB84':
                    bb84 = BB84(name, tl, **protocol_config)
                    bb84.assign_node(node)
                    node.protocol = bb84
                    self.entities.append(bb84)

                # add cascade config

            self.entities.append(node)

            if node.name in self.nodes:
                raise Exception('two nodes have same name')

            self.nodes[node.name] = node

    def create_qchannel(self, channel_config, timelines):
        for config in channel_config:
            name = config['name']
            tl = timelines[config['timeline']]
            sender = self.find_entity_by_name(config['sender'])
            receiver = self.find_entity_by_name(config['receiver'])
            del config['name']
            del config['timeline']
            del config['sender']
            del config['receiver']

            chan = QuantumChannel(name, tl, **config)
            chan.set_sender(sender)
            sender.direct_receiver = chan
            chan.set_receiver(receiver)
            self.entities.append(chan)

    # TODO: use add_end function for classical channel
    def create_cchannel(self, channel_config, timelines):
        for config in channel_config:
            name = config['name']
            tl = timelines[config['timeline']]
            del config['name']
            del config['timeline']

            chan = ClassicalChannel(name, tl, **config)
            self.entities.append(chan)

    # TODO: populate
    def create_protocols(self, nodes_config, timelines):
        pass

    def print_topology(self):
        pass

    def to_json5_file(self):
        pass

    def find_entity_by_name(self, name):
        for e in self.entities:
            if e.name == name:
                return e
        raise Exception('unknown entity name',name)

    def find_node_by_name(self, name):
        pass

    def find_qchannel_by_name(self, name):
        pass

