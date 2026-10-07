import sequence as sq

class Store(object):
    def __init__(self, tl: sq.Timeline):
        self.opening = False
        self.timeline = tl

    def open(self) -> None:
        self.opening = True
        process = sq.Process(self, 'close', [])
        event = sq.Event(self.timeline.now() + 12, process)
        self.timeline.schedule(event)

    def close(self) -> None:
        self.opening = False
        process = sq.Process(self, 'open', [])
        event = sq.Event(self.timeline.now() + 12, process)
        self.timeline.schedule(event)


tl = sq.Timeline(60)
tl.show_progress = False
store = Store(tl)
print(tl.now())

process = sq.Process(store, 'open', [])
event = sq.Event(7, process)
tl.schedule(event)

tl.run()
print(store.opening)
