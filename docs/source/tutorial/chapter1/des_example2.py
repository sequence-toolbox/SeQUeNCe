from sequence.kernel.timeline import Timeline
from sequence.kernel.event import Event
from sequence.kernel.process import Process

class Store(object):
    def __init__(self, tl: Timeline):
        self.opening = False
        self.timeline = tl

    def open(self) -> None:
        self.opening = True
        process = Process(self, 'close', [])
        event = Event(self.timeline.now() + 12, process)
        self.timeline.schedule(event)

    def close(self) -> None:
        self.opening = False
        process = Process(self, 'open', [])
        event = Event(self.timeline.now() + 12, process)
        self.timeline.schedule(event)


tl = Timeline(60)
tl.show_progress = False
store = Store(tl)
print(tl.now())

process = Process(store, 'open', [])
event = Event(7, process)
tl.schedule(event)

tl.run()
print(store.opening)
