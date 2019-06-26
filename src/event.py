import math

class Event:
    def __init__(self, time, process, priority=math.inf):
        self.time = time
        self.priority = priority
        self.process = process

    def __eq__(self, anotherEvent):
        return (self.time == anotherEvent.time) and (self.priority == anotherEvent.priority)

    def __ne__(self, anotherEvent):
        return (self.time != anotherEvent.time) or (self.priority !=anotherEvent.priority)

    def __gt__(self, anotherEvent):
        return (self.time > anotherEvent.time) or (self.time == anotherEvent.time and self.priority > anotherEvent.priority)

    def __lt__(self, anotherEvent):
        return (self.time < anotherEvent.time)  or (self.time == anotherEvent.time and self.priority < anotherEvent.priority)
