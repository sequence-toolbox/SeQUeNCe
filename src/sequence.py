import sys
import json5
from timeline import Timeline
from node import Node
from light_source import LightSource
from detector import Detector
from quantum_channel import QChannel
from process import Process
from event import Event

def create_timelines(config_file):
    timelines = []
    max_tl_num = 0
    config = json5.load(open(config_file))
    topo_config = json5.load(open(config['Topo']))

    for node in topo_config['nodes']:
        max_tl_num = max(max_tl_num, node['timeline'])
        for component in node['components']:
            max_tl_num = max(max_tl_num, component['timeline'])

    for _ in range(max_tl_num+1):
        timelines.append(Timeline())

    return timelines

def find_entity_by_name(entities, name):
    for e in entities:
        if e.name == name: return e
    raise Exception('unkown entity name')


def create_entities(config_file, timelines):
    entities = []
    config = json5.load(open(config_file))
    topo_config = json5.load(open(config['Topo']))

    # create nodes
    for node_config in topo_config['nodes']:
        components = {}
        for component_config in node_config['components']:
            if component_config['name'] in components:
                raise Exception('two entites have same name')

            name = node_config['name'] + '.' + component_config['name']

            if component_config["type"] == 'LightSource':
                ls = LightSource(name, timelines[component_config['timeline']],
                        component_config['frequency'], component_config['wavelength'], component_config['mean_photon_num'],
                        component_config['encoding_type'], component_config['quantum_state'])
                components[component_config['name']] = ls
                entities.append(ls)

            elif component_config["type"] == 'Detector':
                detector = Detector(name, timelines[component_config['timeline']],
                        component_config['efficiency'], component_config['dark_count'], component_config['count_rate'], component_config['time_resolution'])
                components[component_config['name']] = detector
                entities.append(detector)
            else:
                raise Exception('unkown device type')

        entities.append(Node(node_config['name'], timelines[node_config['timeline']], components))

    # create quantum channels
    for qc_config in topo_config['QChannel']:
        qc = QChannel(qc_config['name'], timelines[qc_config['timeline']], qc_config['distance'], qc_config['temperature'], qc_config['fidelity'])
        sender = find_entity_by_name(entities, qc_config['sender'])
        receiver = find_entity_by_name(entities, qc_config['receiver'])
        qc.set_sender(sender)
        qc.set_receiver(receiver)
        entities.append(qc)

    return entities

def create_events(config_file, entities):
    config = json5.load(open(config_file))

    for action_config in config['Actions']:
        entity = find_entity_by_name(entities, action_config['actor'])
        process = Process(entity, action_config['action'], action_config['params'])
        entity.timeline.schedule(Event(action_config['start_time'], process))

def print_metrics_res(config_file, entities):
    pass

if __name__ == "__main__":
    config_file = sys.argv[1]
    print("get file name")
    timelines = create_timelines(config_file)
    print("created timelines")
    entities = create_entities(config_file, timelines)
    print("created entities")
    for tl in timelines:
        tl.init()
    print("created events")
    create_events(config_file, entities)
    for tl in timelines:
        tl.run()
    print("run tl finish")
    print_metrics_res(config_file, entities)
    print("print out metrics")
