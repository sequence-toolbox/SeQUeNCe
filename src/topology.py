import json5
<<<<<<< HEAD


class Node:
    def __init__(self, name, timeline, *params):
        self.name = name
        self.timeline = timeline
        self.components = params[0]

    def send_photon(self, *params):
        print("node send_photon function")

    def get_photon_count(self):
        return self.components["detector"].photon_counter+1


class LightSource:
    def __init__(self, name, timeline, paramDict):
        self.name = name
        self.timeline = timeline
        self.photon_counter=0
        print("create ls")

    def emit(self, paramDict):
        print("ls emit")
        pass

    def get_photon_count(self):
        return self.photon_counter

class QChannel:
    def __init__(self, name, timeline, *params):
        self.name = name
        self.timeline = timeline
        print("create qc")

    def set_sender(self, paramsDict):
        print("set qc sender")

    def set_receiver(self, paramsDict):
        print("set qc receiver")


class Detector:
    def __init__(self, name, timeline, paramDict):
        self.name = name
        self.timeline = timeline
        self.photon_counter=0
=======
from Node import Node, LightSource, Detector
from OpticalChannel import OpticalChannel
>>>>>>> ac8f238ba9783324b570c3d0cd307accefafd1bb


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
                elif component_config["type"] == 'Detector':
                    detector = Detector(name, tl, **component_config)
                    components[component_name] = detector
                    self.entities.append(detector)

                else:
                    raise Exception('unknown device type')

            node = Node(node_config['name'], timelines[node_config['timeline']], **components)
            self.entities.append(node)

            if node.name in self.nodes:
                raise Exception('two nodes have same name')

            self.nodes[node.name] = node

    def create_qchannel(self, qchannel_config, timelines):
        for qc_config in qchannel_config:
            name = qc_config['name']
            tl = timelines[qc_config['timeline']]
            del qc_config['name']
            del qc_config['timeline']

            qc = OpticalChannel(name, tl, **qc_config)

            sender = self.find_entity_by_name(qc_config['sender'])
            receiver = self.find_entity_by_name(qc_config['receiver'])

            qc.set_sender(sender)
            sender.direct_receiver = qc
            qc.set_receiver(receiver)
            self.entities.append(qc)

    def print_topology(self):
        pass

    def to_json5_file(self):
        pass

    def find_entity_by_name(self, name):
        for e in self.entities:
            if e.name == name: return e
        raise Exception('unknown entity name')

    def find_node_by_name(self, name):
        pass

    def find_qchannel_by_name(self, name):
        pass

