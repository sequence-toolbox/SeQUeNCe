from numpy import random, outer, zeros, multiply

from random import randrange
from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from sequence.kernel.timeline import Timeline

from sequence.kernel.entity import Entity

from sequence.kernel.timeline import Timeline
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.components.light_source import polarization
from sequence.components.optical_channel import QuantumChannel
from sequence.components.detector import Detector
from sequence.topology.node import Node

from sequence.kernel.entity import Entity
from sequence.utils.encoding import *
from sequence.components.photon import Photon
from sequence.components.light_source import LightSource

from ipywidgets import interact
from matplotlib import pyplot as plt

from sequence.components.mirror import Mirror


NUM_TRIALS = 1000
FREQUENCY = 1e3


class Counter():
    def __init__(self):
        self.count = 0

    def trigger(self, detector, info):
        self.count += 1


class EmittingNode(Node):
    def __init__(self, name, timeline):
        super().__init__(name, timeline)
        self.light_source = LightSource(
            name, timeline, frequency=80000000, mean_photon_num=1)
        self.light_source.owner = self


class MiddleNode(Node):

    def __init__(self, name, timeline):
        super().__init__(name, timeline)
        self.mirror = Mirror(name, timeline)
        self.mirror.owner = self
    #src = node1

    def receive_qubit(self, src, qubit):
        #print("received something")
        if not qubit.is_null:
            self.mirror.get()

            y = randrange(100)
            if not (self.mirror.fidelity * 100) < y:
                process_photon = Process(self.mirror, "emit", [
                                         [qubit.quantum_state.state], "node3"])

                time = self.timeline.now()
                period = int(round(1e12 / self.mirror.frequency))
                event = Event(time, process_photon)
                self.owner.timeline.schedule(event)
                time += period
                #print("receiving mirror")


class ReceiverNode(Node):
    def __init__(self, name, timeline):
        super().__init__(name, timeline)
        self.detector = Detector(name + ".detector", tl, efficiency=1)
        self.detector.owner = self

    def receive_qubit(self, src, qubit):
        #print("received something")
        if not qubit.is_null:
            self.detector.get()
            #print("receiving detector")


if __name__ == "__main__":
    runtime = 10e12
    tl = Timeline(runtime)

    # nodes and hardware
    node1 = EmittingNode("node1", tl)
    node2 = MiddleNode("node2", tl)
    node3 = ReceiverNode("node3", tl)

    qc1 = QuantumChannel("qc", tl, attenuation=0, distance=1e3)
    qc2 = QuantumChannel("qc", tl, attenuation=0, distance=1e3)
    qc1.set_ends(node1, node2)
    qc2.set_ends(node2, node3)

    # counter
    counter = Counter()
    node3.detector.attach(counter)

    # schedule events
    time_bin = int(1e12 / FREQUENCY)

    # Process

    process1 = Process(node1.light_source, "emit", [[((1 + 0j), 0j)], "node2"])

    for i in range(NUM_TRIALS):
        event1 = Event(i * time_bin, process1)
        tl.schedule(event1)

    tl.init()
    tl.run()

    print("percent measured: {}%".format(100 * counter.count / NUM_TRIALS))
