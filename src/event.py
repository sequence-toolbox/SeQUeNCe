
class Event:
    def __init__(self, timestamp, process, priority=0):
        self.timestamp = timestamp
        self.priority = priority
        self.process = process

    def __eq__(self, anotherEvent):
        return self.timestamp == anotherEvent.timestamp

    def __ne__(self, anotherEvent):
        return self.timestamp != anotherEvent.timestamp

    def __gt__(self, anotherEvent):
        return self.timestamp > anotherEvent.timestamp

    def __lt__(self, anotherEvent):
        return self.timestamp < anotherEvent.timestamp


class Stack:
    def __init__(self):
        self.stack = []

    def pop(self):
        if len(self.stack) < 1:
            return None
        return self.stack.pop()

    def push(self, item):
        self.stack.append(item)

    def size(self):
        return len(self.stack)

    def isempty(self): ## do we need this??
        return len(self.stack)==0


class EventList:
    def __init__(self):
        self.priority_queue = Stack()

    def pop(self):
        return self.priority_queue.pop()

    def push(self, event):
        self.priority_queue.push(event)

    def size(self):
        return self.priority_queue.size()

    def isempty(self): ## empty() or isempty()??
        return self.priority_queue.isempty()

    def operation(self):
        return
