import sys

def create_timelines(config_file):
    timelines = []
    #TODO
    return timelines

def create_entities(config_file):
    entities = []
    #TODO
    return entities

def create_events(config_file, timelines):
    pass

def print_metrics_res(config_file, entities):
    pass

if __name__ == "__main__":
    config_file = sys.argv[1]
    timelines = create_timelines(config_file)
    eneitites = create_entities(config_file, timelines)
    for tl in timelines:
        tl.init()
    create_events(config_file, timelines)
    for tl in timelines:
        tl.run()
    print_metrics_res(config_file, entities)
