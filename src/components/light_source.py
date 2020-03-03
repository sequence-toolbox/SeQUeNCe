import math
import copy
import numpy

from sequence import encoding
from sequence.process import Process
from sequence.entity import Entity
from sequence.event import Event


class LightSource(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.frequency = kwargs.get("frequency", 0)  # measured in Hz
        self.wavelength = kwargs.get("wavelength", 1550)  # measured in nm
        self.linewidth = kwargs.get("bandwidth", 0)  # st. dev. in photon wavelength (nm)
        self.mean_photon_num = kwargs.get("mean_photon_num", 0)
        self.encoding_type = kwargs.get("encoding_type", encoding.polarization)
        self.direct_receiver = kwargs.get("direct_receiver", None)
        self.phase_error = kwargs.get("phase_error", 0)
        self.photon_counter = 0
        # for BB84
        # self.basis_lists = []
        # self.basis_list = []
        # self.bit_lists = []
        # self.bit_list = []
        # self.is_on = False
        # self.pulse_id = 0

    def init(self):
        pass

    # for general use
    def emit(self, state_list):
        time = self.timeline.now()
        period = int(round(1e12 / self.frequency))

        for i, state in enumerate(state_list):
            num_photons = numpy.random.poisson(self.mean_photon_num)

            if numpy.random.random_sample() < self.phase_error:
                state = numpy.multiply([1, -1], state)

            for _ in range(num_photons):
                wavelength = self.linewidth * numpy.random.randn() + self.wavelength
                new_photon = Photon(None, self.timeline,
                                    wavelength=wavelength,
                                    location=self.direct_receiver,
                                    encoding_type=self.encoding_type,
                                    quantum_state=state)
                process = Process(self.direct_receiver, "get", [new_photon])
                event = Event(time, process)
                self.timeline.schedule(event)

                self.photon_counter += 1

            time += period

    def assign_receiver(self, receiver):
        self.direct_receiver = receiver

        
