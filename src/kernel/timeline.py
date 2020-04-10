import math

from .eventlist import EventList


class Timeline:

    def __init__(self, stop_time=math.inf):
        self.events = EventList()
        self.entities = []
        self.time = 0
        self.stop_time = stop_time
        self.event_counter = 0

    def now(self):
        return self.time

    def schedule(self, event):
        self.event_counter+=1
        return self.events.push(event)

    def init(self):
        for entity in self.entities:
            entity.init()

    def run(self):
        # log = {}
        while len(self.events)>0:
            event = self.events.pop()
            if event.time > self.stop_time: break
            assert self.time <= event.time, "invalid event time for process scheduled on " + str(event.process.owner)
            self.time = event.time
            # if not event.process.activation in log:
            #     log[event.process.activation] = 0
            # log[event.process.activation]+=1
            event.process.run()
        print('number of event',self.event_counter)
        #print('log:',log)

    def stop(self):
        self.stop_time = self.now()
