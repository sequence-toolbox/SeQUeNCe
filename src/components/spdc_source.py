import math
import copy
import numpy

from sequence import encoding
from sequence.process import Process
from sequence.entity import Entity
from sequence.event import Event


class SPDCSource(LightSource):
    def __init__(self, name, timeline, **kwargs):
        super().__init__(name, timeline, **kwargs)
        self.another_receiver = kwargs.get("another_receiver", None)
        self.wavelengths = kwargs.get("wavelengths", [])

    def emit(self, state_list):
        time = self.timeline.now()

        for state in state_list:
            num_photon_pairs = numpy.random.poisson(self.mean_photon_num)

            if numpy.random.random_sample() < self.phase_error:
                state = numpy.multiply([1, -1], state)

            for _ in range(num_photon_pairs):
                new_photon0 = Photon(None, self.timeline,
                                     wavelength=self.wavelengths[0],
                                     location=self.direct_receiver,
                                     encoding_type=self.encoding_type)
                new_photon1 = Photon(None, self.timeline,
                                     wavelength=self.wavelengths[1],
                                     location=self.direct_receiver,
                                                             encoding_type=self.encoding_type)

                new_photon0.entangle(new_photon1)
                new_photon0.set_state([state[0], complex(0), complex(0), state[1]])

                process0 = Process(self.direct_receiver, "get", [new_photon0])
                process1 = Process(self.another_receiver, "get", [new_photon1])
                event0 = Event(int(round(time)), process0)
                event1 = Event(int(round(time)), process1)
                self.timeline.schedule(event0)
                self.timeline.schedule(event1)

                self.photon_counter += 1

            time += 1e12 / self.frequency

    def assign_another_receiver(self, receiver):
        self.another_receiver = receiver

