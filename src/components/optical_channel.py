import heapq as hq
from typing import TYPE_CHECKING

import numpy

if TYPE_CHECKING:
    from ..kernel.timeline import Timeline
    from ..topology.node import Node
    from ..components.photon import Photon
    from ..protocols.message import Message

from ..kernel.entity import Entity
from ..kernel.event import Event
from ..kernel.process import Process


class OpticalChannel(Entity):
    def __init__(self, name: str, timeline: "Timeline", attenuation: float, distance: int, **kwargs):
        Entity.__init__(self, name, timeline)
        self.ends = []
        self.attenuation = attenuation
        self.distance = distance  # (measured in m)
        self.polarization_fidelity = kwargs.get("polarization_fidelity", 1)
        self.light_speed = kwargs.get("light_speed",
                                      2 * 10 ** -4)  # used for photon timing calculations (measured in m/ps)
        # self.chromatic_dispersion = kwargs.get("cd", 17)  # measured in ps / (nm * km)

    def init(self) -> None:
        pass

    def set_distance(self, distance: int) -> None:
        self.distance = distance


class QuantumChannel(OpticalChannel):
    def __init__(self, name: str, timeline: "Timeline", attenuation: float, distance: int, **kwargs):
        super().__init__(name, timeline, attenuation, distance, **kwargs)
        self.delay = 0
        self.loss = 1
        self.frequency = kwargs.get("frequency", 8e7)  # frequency at which send qubits (measured in Hz)
        self.send_bins = []

    def init(self) -> None:
        self.delay = round(self.distance / self.light_speed)
        self.loss = 1 - 10 ** (self.distance * self.attenuation / -10)

    def set_ends(self, end1: "Node", end2: "Node") -> None:
        self.ends.append(end1)
        self.ends.append(end2)
        end1.assign_qchannel(self, end2.name)
        end2.assign_qchannel(self, end1.name)

    def transmit(self, qubit: "Photon", source: "Node") -> None:
        assert self.delay != 0 and self.loss != 1, "QuantumChannel forgets to run init() function"

        # remove lowest time bin
        if len(self.send_bins) > 0:
            time = -1
            while time < self.timeline.now():
                time_bin = hq.heappop(self.send_bins)
                time = int((time_bin * 1e12) / self.frequency)
            assert time == self.timeline.now(), "qc {} transmit method called at invalid time".format(self.name)

        # check if photon kept
        if (numpy.random.random_sample() > self.loss) or qubit.is_null:
            if source not in self.ends:
                raise Exception("no endpoint", source)

            receiver = None
            for e in self.ends:
                if e != source:
                    receiver = e

            # schedule receiving node to receive photon at future time determined by light speed
            future_time = self.timeline.now() + self.delay
            process = Process(receiver, "receive_qubit", [source.name, qubit])
            event = Event(future_time, process)
            self.timeline.schedule(event)

        # if photon lost, exit
        else:
            pass

    def schedule_transmit(self, min_time: int) -> int:
        min_time = max(min_time, self.timeline.now())
        time_bin = int((min_time * self.frequency) / 1e12) + 1

        # find earliest available time bin
        while time_bin in self.send_bins:
            time_bin += 1
        hq.heappush(self.send_bins, time_bin)

        # calculate time
        time = int((time_bin * 1e12) / self.frequency)
        return time


class ClassicalChannel(OpticalChannel):
    def __init__(self, name: str, timeline: "Timeline", attenuation: float, distance: int, **kwargs):
        super().__init__(name, timeline, attenuation, distance, **kwargs)
        self.delay = kwargs.get("delay", (self.distance / self.light_speed))

    def set_ends(self, end1: "Node", end2: "Node") -> None:
        self.ends.append(end1)
        self.ends.append(end2)
        end1.assign_cchannel(self, end2.name)
        end2.assign_cchannel(self, end1.name)

    def transmit(self, message: "Message", source: "Node", priority: int) -> None:
        # get node that's not equal to source
        if source not in self.ends:
            raise Exception("no endpoint", source)

        receiver = None
        for e in self.ends:
            if e != source:
                receiver = e

        future_time = int(round(self.timeline.now() + int(self.delay)))
        process = Process(receiver, "receive_message", [source.name, message])
        event = Event(future_time, process, priority)
        self.timeline.schedule(event)
