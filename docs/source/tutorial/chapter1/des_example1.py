from sequence.kernel.timeline import Timeline
from sequence.kernel.event import Event
from sequence.kernel.process import Process


class Store(object):
    def __init__(self, tl: Timeline):
        self.opening = False
        self.timeline = tl

    def open(self) -> None:
        self.opening = True

    def close(self) -> None:
        self.opening = False


tl = Timeline()
tl.show_progress = False

store = Store(tl)

# open store at 7:00
open_proc = Process(store, 'open', [])
open_event = Event(7, open_proc)
tl.schedule(open_event)

tl.run()

print(tl.time, store.opening)

# close store at 19:00
close_proc = Process(store, 'close', [])
close_event = Event(19, close_proc)
tl.schedule(close_event)

tl.run()

print(tl.time, store.opening)

# what if we schedule two events before run simulation

tl.time = 0
tl.schedule(open_event)
tl.schedule(close_event)
tl.run()
print(tl.time, store.opening)


# what if we swap the order of scheduling two events

tl.time = 0
tl.schedule(open_event)
tl.schedule(close_event)
tl.run()
print(tl.time, store.opening)
