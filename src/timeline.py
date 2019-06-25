from eventlist import EventList
import math

class Timeline:

    def __init__(self, stop_time=math.inf):
        self.events = EventList()
        self.entities = []
        self.time = 0
        self.stop_time = stop_time

    def now(self):
        return self.time

    def schedule(self, event):
        return self.events.push(event)

    def init(self):
        for event in self.events:
            event.init()

    def assign_entity(self, entities):
        self.entities = entities
        for entity in self.entities:
            entity.timeline = self

    def run(self):
        while self.events.size()>0:
            event = self.events.pop()
            if event.time > self.stop_time: break
            self.time = event.time
            #TODO: run process in event
            print("run")


