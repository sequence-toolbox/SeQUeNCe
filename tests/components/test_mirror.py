from numpy import random, outer, zeros, multiply
from numpy.random import random_sample

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


#from sequence.components.mirror import Mirror
class Mirror(Entity):

    """Single photon reflecting device.
    This class models the reflection of a single photon, in the fashion of an experimental mirror.
    Can be attached to many different devices to enable different measurement options.
    Attributes:
        name (str): label for mirror instance.
        timeline (Timeline): timeline for simulation.
        fidelity (float): fraction of lost qubits on the reflective surface
        frequency (float): frequency (in Hz) of photon creation.
        wavelength (float): wavelength (in nm) of emitted photons.
        linewidth (float): st. dev. in photon wavelength (in nm).
        mean_photon_num (float): mean number of photons emitted each period.
        encoding_type (Dict[str, Any]): encoding scheme of emitted photons (as defined in the encoding module).
        phase_error (float): phase error applied to qubits.
    """

    def __init__(self, name: str, timeline: "Timeline", fidelity=0.98,
                 time_resolution=150, frequency=8e7, wavelength=1550,
                 bandwidth=0, mean_photon_num=0.1, encoding_type=polarization,
                 phase_error=0):

        Entity.__init__(self, name, timeline)
        self.fidelity = fidelity
        self.receivers = []
        # for BB84
        self.start_time = 0
        self.basis_list = []
        self.photon_counter = 0
        self.time_resolution = time_resolution  # measured in ps
        self.frequency = frequency  # measured in Hz
        self.wavelength = wavelength  # measured in nm
        self.linewidth = bandwidth  # st. dev. in photon wavelength (nm)
        self.mean_photon_num = mean_photon_num
        self.encoding_type = encoding_type
        self.phase_error = phase_error

    def init(self):

        pass

    def get(self, dark_get=False) -> None:

        self.photon_counter += 1
        now = self.timeline.now()
        time = round(now / self.time_resolution) * self.time_resolution

    def emit(self, state_list, dst: str) -> None:

        time = self.timeline.now()
        period = int(round(1e12 / self.frequency))

        for i, state in enumerate(state_list):

            num_photons = 1

            if random.random_sample() < self.phase_error:
                state = multiply([1, -1], state)

            for _ in range(num_photons):
                wavelength = self.linewidth * random.randn() + self.wavelength
                new_photon = Photon(str(i),
                                    wavelength=wavelength,
                                    location=self.owner,
                                    encoding_type=self.encoding_type,
                                    quantum_state=state)

                process = Process(self.owner, "send_qubit", [dst, new_photon])

                event = Event(time, process)
                self.owner.timeline.schedule(event)
                self.photon_counter += 1
                time += period

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
