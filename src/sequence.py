import sys
import json5
from timeline import Timeline
from process import Process
from event import Event
from topology import Topology

from numba import jit   ## speed up the python by 10x??

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

def create_topo(config_file, timelines):
    entities = []
    config = json5.load(open(config_file))
    topo_file = config['Topo']
    topo = Topology(topo_file, timelines)

    return topo

def create_events(config_file, entities):
    config = json5.load(open(config_file))

    for action_config in config['Actions']:
        entity = topo.find_entity_by_name(action_config['actor'])
        process = Process(entity, action_config['action'], action_config['params'])
        entity.timeline.schedule(Event(action_config['start_time'], process))

def print_metrics_res(config_file, entities):
    metrics = json5.load(open(config_file))["Metrics"]
    for m in metrics:
        entity_name = '.'.join(m.split('.')[:-1])
        attribute_name = m.split('.')[-1]
        print(m, ':', getattr(topo.find_entity_by_name(entity_name), attribute_name)())
    pass

if __name__ == "__main__":
    if len(sys.argv)<2:
        raise Exception('Error: No command argument provided...')

    config_file = sys.argv[1]
    print("get file name")
    timelines = create_timelines(config_file)
    print("created timelines")
    topo = create_topo(config_file, timelines)
    entities = topo.entities
    print("created topo")
    for tl in timelines:
        tl.init()
    print("created events")
    create_events(config_file, entities)
    for tl in timelines:
        tl.run()
    print("run tl finish")
    print_metrics_res(config_file, entities)
    print("print out metrics")

