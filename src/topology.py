import json5
from detector import Detector
from light_source import LightSource
from quantum_channel import QChannel
from node import Node

class Topology:

    def __init__(self, config_file, timelines):
        self.nodes = {}
        self.quantum_channel = {}
        self.entities = []

        topo_config = json5.load(open(config_file))
        nodes_config = topo_config['nodes']
        self.create_nodes(nodes_config, timelines)
        qchannel_config = topo_config['QChannel']
        self.create_qchannel(qchannel_config, timelines)

    def create_nodes(self, nodes_config, timelines):
        for node_config in nodes_config:
            components = {}
            for component_config in node_config['components']:
                if component_config['name'] in components:
                    raise Exception('two components have same name')

                name = node_config['name'] + '.' + component_config['name']

                # light source instantiatation
                if component_config["type"] == 'LightSource':
                    ls = LightSource(name, timelines[component_config['timeline']],
                            component_config['frequency'], component_config['wavelength'], component_config['mean_photon_num'],
                            component_config['encoding_type'], component_config['quantum_state'])
                    components[component_config['name']] = ls
                    self.entities.append(ls)

                # detector instantiatation
                elif component_config["type"] == 'Detector':
                    detector = Detector(name, timelines[component_config['timeline']],
                            component_config['efficiency'], component_config['dark_count'], component_config['count_rate'], component_config['time_resolution'])
                    components[component_config['name']] = detector
                    self.entities.append(detector)
                else:
                    raise Exception('unkown device type')

            node = Node(node_config['name'], timelines[node_config['timeline']], components)
            self.entities.append(node)

            if node.name in self.nodes:
                raise Exception('two nodes have same name')

            self.nodes[node.name] = node


    def create_qchannel(self, qchannel_config, timelines):
        for qc_config in qchannel_config:
            qc = QChannel(qc_config['name'], timelines[qc_config['timeline']], qc_config['distance'], qc_config['temperature'], qc_config['fidelity'])
            sender = self.find_entity_by_name(qc_config['sender'])
            receiver = self.find_entity_by_name(qc_config['receiver'])
            qc.set_sender(sender)
            qc.set_receiver(receiver)
            self.entities.append(qc)

        pass

    def print_topology(self):
        pass

    def to_json5_file(self):
        pass

    def find_entity_by_name(self, name):
        for e in self.entities:
            if e.name == name: return e
        raise Exception('unkown entity name')

    def find_node_by_name(self, name):
        pass

    def find_qchannel_by_name(self, name):
        pass

