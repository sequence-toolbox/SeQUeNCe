import sys
import json
import timeline
import topology

def create_timelines(config_file, nTimelines=1):
    timelines = []
    #TODO
    for n in range(nTimelines):
        tl = timeline.Timeline()
        timelines.append(tl)
    return timelines

def create_entities(config_file, timelines):
    entities = []
    #TODO
    if config_file:
        with open(config_file, 'r') as f:
            data = json.load(f)
            #print (config_file)
            #print (data)
            TopoFile = data["TopoFile"]
            topo = topology.Topology()
            topo.read_topology(TopoFile)
            topo.print_topology()

    return entities

def create_events(config_file, timelines):
    pass

def print_metrics_res(config_file, entities):
    pass

if __name__ == "__main__":
    if len(sys.argv)<2:
        print ("Error: No command argument provided...")
        exit()

    config_file = sys.argv[1]
    timelines = create_timelines(config_file)
    entities = create_entities(config_file, timelines)
    for tl in timelines:
        tl.init()
    create_events(config_file, timelines)
    for tl in timelines:
        tl.run()
    print_metrics_res(config_file, entities)

