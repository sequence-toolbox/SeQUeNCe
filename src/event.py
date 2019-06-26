import math

class Event:
    def __init__(self, timestamp, process, priority=math.inf):
        self.timestamp = timestamp
        self.priority = priority
        self.process = process

    def __eq__(self, anotherEvent):
        return (self.timestamp == anotherEvent.timestamp) and (self.priority == anotherEvent.priority)

    def __ne__(self, anotherEvent):
        return (self.timestamp != anotherEvent.timestamp) or (self.priority !=anotherEvent.priority)

    def __gt__(self, anotherEvent):
        return (self.timestamp > anotherEvent.timestamp) or (self.timestamp == anotherEvent.timestamp and self.priority < anotherEvent.priority)

    def __lt__(self, anotherEvent):
        return (self.timestamp < anotherEvent.timestamp)  or (self.timestamp == anotherEvent.timestamp and self.priority > anotherEvent.priority)
