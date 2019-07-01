import math
from eventlist import EventList

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
        for entity in self.entities:
            entity.init()

    def assign_entity(self, entities):
        self.entities = entities

    def run(self):
        while len(self.events)>0:
            event = self.events.pop()
            if event.time > self.stop_time: break
            self.time = event.time
            event.process.run()
