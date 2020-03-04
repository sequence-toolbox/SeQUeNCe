import json5

from ..components.detector import QSDetector
from ..components.light_source import LightSource
from ..components.optical_channel import *
from ..protocols.qkd.BB84 import BB84
from ..topology.node import Node

"""
import pandas as pd
class TemperatureModel():
    df = pd.DataFrame()

    def read_temperature_file(self,filename):
        self.df = pd.read_csv(filename)
        print (filename,self.df)
        return self.df

    def temperature_from_time(self,time):
        ## TODO
        ## interpolation of time
        temperature = 60
        return temperature
"""


class Topology:
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

