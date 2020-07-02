from _thread import start_new_thread
from math import inf
from sys import stdout
from time import time_ns, sleep
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .event import Event

from .eventlist import EventList


class Timeline:

    def __init__(self, stop_time=inf):
        self.events = EventList()
        self.entities = []
        self.time = 0
        self.stop_time = stop_time
        self.event_counter = 0
        self.show_progress = False

    def now(self) -> int:
        return self.time

    def schedule(self, event: "Event") -> None:
        self.event_counter += 1
        return self.events.push(event)

    def init(self) -> None:
        for entity in self.entities:
            entity.init()

    def run(self) -> None:
        if self.show_progress:
            def print_time():
                start_time = time_ns()
                while 1:
                    exe_time = self.ns_to_human_time(time_ns() - start_time)
                    sim_time = self.ns_to_human_time(self.time / 1e3)
                    stop_time = self.ns_to_human_time(self.stop_time / 1e3)
                    process_bar = f'execution time: {exe_time};     simulation time: {sim_time} / {stop_time}\r'
                    print(f'{process_bar}', end="")
                    stdout.flush()
                    sleep(3)

            start_new_thread(print_time, ())

        # log = {}
        while len(self.events) > 0:
            event = self.events.pop()
            if event.time >= self.stop_time:
                self.schedule(event)
                break
            assert self.time <= event.time, "invalid event time for process scheduled on " + str(event.process.owner)
            self.time = event.time
            # if not event.process.activation in log:
            #     log[event.process.activation] = 0
            # log[event.process.activation]+=1
            event.process.run()
        # print('number of event', self.event_counter)
        # print('log:',log)

    def stop(self) -> None:
        self.stop_time = self.now()

    def remove_event(self, event: "Event") -> None:
        self.events.remove(event)

    def update_event_time(self, event: "Event", time: int) -> None:
        self.events.remove(event)
        event.time = time
        self.schedule(event)

    def ns_to_human_time(self, nanosec: int) -> str:
        if nanosec >= 1e6:
            ms = nanosec / 1e6
            nanosec = nanosec % 1e6
            if ms >= 1e3:
                second = ms / 1e3
                if second >= 60:
                    minute = second // 60
                    second = second % 60
                    if minute >= 60:
                        hour = minute // 60
                        minute = minute % 60
                        return '%d hour: %d min: %.2f sec' % (hour, minute, second)
                    return '%d min: %.2f sec' % (minute, second)
                return '%.2f sec' % (second)
            return "%d ms, %.2f ns" % (ms, nanosec)
        return '%d ns' % nanosec
