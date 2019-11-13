import math
import copy
from typing import List, Any

import numpy
import json5

import sequence
from sequence import encoding
from sequence.process import Process
from sequence.entity import Entity
from sequence.event import Event
from sequence.BB84 import BB84



"""
import pandas as pd
class TemperatureModel():
    df = pd.DataFrame()

    def read_temperature_file(self,filename):
        self.df = pd.read_csv(filename)
        print (filename,self.df)
        return self.df

    def temperature_from_time(self,time):
        ## TODO
        ## interpolation of time
        temperature = 60
        return temperature
"""

# used for photon.measure_multiple
def swap_bits(num, pos1, pos2):
    bit1 = (num >> pos1) & 1
    bit2 = (num >> pos2) & 1
    x = bit1 ^ bit2
    x = (x << pos1) | (x << pos2)
    return num ^ x


class QuantumState():
    def __init__(self):
        self.state = [complex(1), complex(0)]
        self.entangled_states = [self]

    def entangle(self, another_state):
        entangled_states = self.entangled_states + another_state.entangled_states
        quantum_state = numpy.kron(self.state, another_state.state)

        for photon in entangled_photons:
            photon.entangled_photons = entangled_photons
            photon.quantum_state = quantum_state

    def random_noise(self):
        angle = numpy.random.random() * 2 * numpy.pi
        self.state = [complex(numpy.cos(angle)), complex(numpy.sin(angle))]

    def set_state(self, state):
        for qs in self.entangled_states:
            qs.state = state

    def measure(self, basis):
        state = numpy.array(self.state)
        u = numpy.array(basis[0], dtype=complex)
        v = numpy.array(basis[1], dtype=complex)
        # measurement operator
        M0 = numpy.outer(u.conj(), u)
        M1 = numpy.outer(v.conj(), v)

        projector0 = [1]
        projector1 = [1]
        for s in self.entangled_states:
            if s == self:
                projector0 = numpy.kron(projector0, M0)
                projector1 = numpy.kron(projector1, M1)
            else:
                projector0 = numpy.kron(projector0, numpy.identity(2))
                projector1 = numpy.kron(projector1, numpy.identity(2))

        # probability of measuring basis[0]
        prob_0 = (state.conj().transpose() @ projector0.conj().transpose() @ projector0 @ state).real

        result = 0
        if numpy.random.random_sample() > prob_0:
            result = 1

        if result:
            new_state = (projector1 @ state) / math.sqrt(1 - prob_0)
        else:
            new_state = (projector0 @ state) / math.sqrt(prob_0)

        for s in self.entangled_states:
            s.state = new_state

        return result

    @staticmethod
    def measure_multiple(basis, states):
        # ensure states are entangled
        # (must be entangled prior to calling measure_multiple)
        entangled_list = states[0].entangled_states
        for state in states[1:]:
            assert state in states[0].entangled_states
        # ensure basis and vectors in basis are the right size
        basis_dimension = 2 ** len(states)
        assert len(basis) == basis_dimension
        for vector in basis:
            assert len(vector) == len(basis)
            
        state = states[0].state

        # move states to beginning of entangled list and quantum state
        pos_state_0 = entangled_list.index(states[0])
        pos_state_1 = entangled_list.index(states[1])
        entangled_list[0], entangled_list[pos_state_0] = entangled_list[pos_state_0], entangled_list[0]
        entangled_list[1], entangled_list[pos_state_1] = entangled_list[pos_state_1], entangled_list[1]
        switched_state = numpy.array([complex(0)] * len(state))
        for i, coefficient in enumerate(state):
            switched_i = swap_bits(i, pos_state_0, pos_state_1)
            switched_state[switched_i] = coefficient

        state = switched_state

        # math for probability calculations
        length_diff = len(entangled_list) - len(states)

        # construct measurement operators, projectors, and probabilities of measurement
        projectors = [None] * basis_dimension
        probabilities = [0] * basis_dimension
        for i, vector in enumerate(basis):
            vector = numpy.array(vector, dtype=complex)
            M = numpy.outer(vector.conj(), vector)  # measurement operator
            projectors[i] = numpy.kron(M, numpy.identity(2 ** length_diff))  # projector
            probabilities[i] = (state.conj().transpose() @ projectors[i].conj().transpose() @ projectors[i] @ state).real
            if probabilities[i] < 0:
                probabilities[i] = 0

        possible_results = numpy.arange(0, basis_dimension, 1)
        # result gives index of the basis vector that will be projected to
        res = numpy.random.choice(possible_results, p=probabilities)
        # project to new state, then reassign quantum state and entangled photons
        new_state = (projectors[res] @ state) / math.sqrt(probabilities[res])
        for state in entangled_list:
            state.quantum_state = new_state
            state.entangled_photons = entangled_list

        return res



class Photon(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.wavelength = kwargs.get("wavelength", 0)
        self.location = kwargs.get("location", None)
        self.encoding_type = kwargs.get("encoding_type", encoding.polarization)
        quantum_state = kwargs.get("quantum_state", [complex(1), complex(0)])
        self.quantum_state = QuantumState()
        self.quantum_state.state = quantum_state
        self.entangled_photons = [self]

    def init(self):
        pass

    def entangle(self, photon):
        self.quantum_state.entangle(photon.quantum_state)

    def random_noise(self):
        self.quantum_state.random_noise()
        # self.quantum_state += numpy.random.random() * 360  # add random angle, use 360 instead of 2*pi

    def set_state(self, state):
        self.quantum_state.set_state(state)
    # def measure(self, basis):
    #     alpha = numpy.dot(self.quantum_state, basis[0])  # projection onto basis vector
    #     if numpy.random.random_sample() < alpha ** 2:
    #         self.quantum_state = basis[0]
    #         return 0
    #     self.quantum_state = basis[1]
    #     return 1

    @staticmethod
    def measure(basis, photon):
        return photon.quantum_state.measure(basis)

    @staticmethod
    def measure_multiple(basis, photons):
        return QuantumState.measure_multiple(basis, [photon[0].quantum_state, photon[1].quantum_state])


class OpticalChannel(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.attenuation = kwargs.get("attenuation", 0)
        self.distance = kwargs.get("distance", 0)  # (measured in m)
        self.temperature = kwargs.get("temperature", 0)
        self.polarization_fidelity = kwargs.get("polarization_fidelity", 1)
        self.light_speed = kwargs.get("light_speed",
                                      3 * 10 ** -4)  # used for photon timing calculations (measured in m/ps)
        self.chromatic_dispersion = kwargs.get("cd", 17)  # measured in ps / (nm * km)

    def init(self):
        pass

    def set_distance(self, distance):
        self.distance = distance

    def distance_from_time(self, time):
        distance = self.distance
        ## TODO: distance as a function of temperature
        temperature = self.tModel.temperature_from_time(time)

        return distance

    # def set_temerature_model(self, filename):
    #     self.tModel = TemperatureModel()
    #     self.tModel.read_temperature_file(filename)


class QuantumChannel(OpticalChannel):
    def __init__(self, name, timeline, **kwargs):
        super().__init__(name, timeline, **kwargs)
        self.sender = None
        self.receiver = None
        self.depo_counter = 0
        self.photon_counter = 0

    def set_sender(self, sender):
        self.sender = sender

    def set_receiver(self, receiver):
        self.receiver = receiver

    def get(self, photon):
        # generate chance to lose photon
        loss = self.distance * self.attenuation
        chance_photon_kept = 10 ** (loss / -10)

        # check if photon kept
        if numpy.random.random_sample() < chance_photon_kept:
            self.photon_counter += 1

            # check if random polarization noise applied
            if numpy.random.random_sample() > self.polarization_fidelity and\
                    photon.encoding_type["name"] == "polarization":
                photon.random_noise()
                self.depo_counter+=1

            # schedule receiving node to receive photon at future time determined by light speed and dispersion
            future_time = self.timeline.now() + round(self.distance / self.light_speed)
            # dispersion_time = int(round(self.chromatic_dispersion * photon.wavelength * self.distance * 1e-3))

            process = Process(self.receiver, "get", [photon])
            event = Event(future_time, process)
            self.timeline.schedule(event)


class ClassicalChannel(OpticalChannel):
    def __init__(self, name, timeline, **kwargs):
        super().__init__(name, timeline, **kwargs)
        self.ends = []
        self.delay = kwargs.get("delay", (self.distance / self.light_speed))

    def add_end(self, node):
        if node in self.ends:
            Exception("already have endpoint", node)
        if len(self.ends) == 2:
            Exception("channel already has 2 endpoints")

        self.ends.append(node)

    def transmit(self, message, source):
        # get node that's not equal to source
        if source not in self.ends:
            Exception("no endpoint", source)

        receiver = None
        for e in self.ends:
            if e != source:
                receiver = e

        future_time = int(round(self.timeline.now() + self.delay))
        process = Process(receiver, "receive_message", [message])
        event = Event(future_time, process)
        self.timeline.schedule(event)


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
                event = Event(int(round(time)), process)
                self.timeline.schedule(event)

                self.photon_counter += 1

            time += 1e12 / self.frequency

    def assign_receiver(self, receiver):
        self.direct_receiver = receiver


class QSDetector(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.encoding_type = kwargs.get("encoding_type", encoding.polarization)

        detectors = kwargs.get("detectors", [])
        if (self.encoding_type["name"] == "polarization" and len(detectors) != 2) or\
                (self.encoding_type["name"] == "time_bin" and len(detectors) != 3):
            raise Exception("invalid number of detectors specified")
        self.detectors = []
        for d in detectors:
            if d is not None:
                detector = Detector(timeline, **d)
            else:
                detector = None
            self.detectors.append(detector)

        if self.encoding_type["name"] == "polarization":
            splitter = kwargs.get("splitter")
            self.splitter = BeamSplitter(timeline, **splitter)

        elif self.encoding_type["name"] == "time_bin":
            interferometer = kwargs.get("interferometer")
            self.interferometer = Interferometer(timeline, **interferometer)
            self.interferometer.detectors = self.detectors[1:]
            switch = kwargs.get("switch")
            self.switch = Switch(timeline, **switch)
            self.switch.receivers = [self.detectors[0], self.interferometer]

        else:
            raise Exception("invalid encoding type for QSDetector " + self.name)

    def init(self):
        for d in self.detectors:
            if d is not None:
                d.init()

    def get(self, photon):
        if self.encoding_type["name"] == "polarization":
            detector = self.splitter.get(photon)
            if detector == 0 or detector == 1:
                self.detectors[self.splitter.get(photon)].get()

        elif self.encoding_type["name"] == "time_bin":
            self.switch.get(photon)

    def clear_detectors(self):
        for d in self.detectors:
            if d is not None:
                d.photon_times = []

    def get_photon_times(self):
        times = []
        for d in self.detectors:
            if d is not None:
                times.append(d.photon_times)
            else:
                times.append([])
        return times

    def set_basis(self, basis):
        self.splitter.set_basis(basis)

    def turn_off_detectors(self):
        for d in self.detectors:
            d.on = False

    def turn_on_detectors(self):
        for d in self.detectors:
            if not d.on:
                d.init()
                d.on = True


class Detector(Entity):
    def __init__(self, timeline, **kwargs):
        Entity.__init__(self, "", timeline)  # Detector is part of the QSDetector, and does not have its own name
        self.efficiency = kwargs.get("efficiency", 1)
        self.dark_count = kwargs.get("dark_count", 0)  # measured in Hz
        self.count_rate = kwargs.get("count_rate", math.inf)  # measured in Hz
        self.time_resolution = kwargs.get("time_resolution", 1)  # measured in ps
        self.photon_times = []
        self.next_detection_time = 0
        self.photon_counter = 0
        self.on = True

    def init(self):
        self.add_dark_count()

    def get(self, dark_get=False):
        self.photon_counter += 1
        now = self.timeline.now()

        if (numpy.random.random_sample() < self.efficiency or dark_get) and now > self.next_detection_time:
            time = int(round(now / self.time_resolution)) * self.time_resolution
            self.photon_times.append(time)
            self.next_detection_time = now + (1e12 / self.count_rate)  # period in ps

    def add_dark_count(self):
        if self.on:
            time_to_next = int(numpy.random.exponential(1 / self.dark_count) * 1e12)  # time to next dark count
            time = time_to_next + self.timeline.now()  # time of next dark count

            process1 = Process(self, "add_dark_count", [])  # schedule photon detection and dark count add in future
            process2 = Process(self, "get", [True])
            event1 = Event(time, process1)
            event2 = Event(time, process2)
            self.timeline.schedule(event1)
            self.timeline.schedule(event2)


class BeamSplitter(Entity):
    def __init__(self, timeline, **kwargs):
        Entity.__init__(self, "", timeline)  # Splitter is part of the QSDetector, and does not have its own name
        basis = kwargs.get("basis", [[complex(1), complex(0)], [complex(0), complex(1)]])
        self.fidelity = kwargs.get("fidelity", 1)
        # for BB84
        self.start_time = 0
        self.frequency = 0
        self.basis_list = [basis]  # default value

    def init(self):
        pass

    def get(self, photon):
        if numpy.random.random_sample() < self.fidelity:
            index = int((self.timeline.now() - self.start_time) * self.frequency * 1e-12)
            if 0 <= index < len(self.basis_list):
                return Photon.measure(self.basis_list[index], photon)
            else:
                return Photon.measure(self.basis_list[0], photon)
        else:
            return -1

    def set_basis(self, basis):
        self.basis_list = [basis]


class Interferometer(Entity):
    def __init__(self, timeline, **kwargs):
        Entity.__init__(self, "", timeline)
        self.path_difference = kwargs.get("path_difference", 0)  # time difference in ps
        self.phase_error = kwargs.get("phase_error", 0)  # chance of measurement error in phase
        self.detectors = []

    def init(self):
        pass

    def get(self, photon):
        detector_num = numpy.random.choice([0, 1])
        quantum_state = photon.quantum_state
        time = 0
        random = numpy.random.random_sample()

        if quantum_state == [complex(1), complex(0)]:  # Early
            if random <= 0.5:
                time = 0
            else:
                time = self.path_difference
        if quantum_state == [complex(0), complex(1)]:  # Late
            if random <= 0.5:
                time = self.path_difference
            else:
                time = 2 * self.path_difference

        if numpy.random.random_sample() < self.phase_error:
            quantum_state = list(numpy.multiply([1, -1], quantum_state))

        if quantum_state == [complex(math.sqrt(1/2)), complex(math.sqrt(1/2))]:  # Early + Late
            if random <= 0.25:
                time = 0
            elif random <= 0.5:
                time = 2 * self.path_difference
            elif detector_num == 0:
                time = self.path_difference
            else:
                return
        if quantum_state == [complex(math.sqrt(1/2)), complex(-math.sqrt(1/2))]:  # Early - Late
            if random <= 0.25:
                time = 0
            elif random <= 0.5:
                time = 2 * self.path_difference
            elif detector_num == 1:
                time = self.path_difference
            else:
                return

        process = Process(self.detectors[detector_num], "get", [])
        event = Event(self.timeline.now() + time, process)
        self.timeline.schedule(event)


class Switch(Entity):
    def __init__(self, timeline, **kwargs):
        Entity.__init__(self, "", timeline)
        self.receivers = []
        self.start_time = 0
        self.frequency = 0
        self.state_list = [kwargs.get("state", 0)]

    def init(self):
        pass

    def add_receiver(self, entity):
        self.receivers.append(entity)

    def set_state(self, state):
        self.state_list = [state]

    def get(self, photon):
        index = int((self.timeline.now() - self.start_time) * self.frequency * 1e-12)
        if index < 0 or index >= len(self.state_list):
            index = 0

        receiver = self.receivers[self.state_list[index]]
        # check if receiver is detector, if we're using time bin, and if the photon is "late" to schedule measurement
        if isinstance(receiver, Detector):
            if photon.encoding_type["name"] == "time_bin" and Photon.measure(photon.encoding_type["bases"][0], photon):
                time = self.timeline.now() + photon.encoding_type["bin_separation"]
                process = Process(receiver, "get", [])
                event = Event(time, process)
                self.timeline.schedule(event)
            else:
                receiver.get()
        else:
            receiver.get(photon)


class BSM(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.encoding_type = kwargs.get("encoding_type", encoding.time_bin)
        self.phase_error = kwargs.get("phase_error", 0)

        # two detectors for time-bin encoding
        # four detectors for polarization encoding
        detectors = kwargs.get("detectors",[])
        if self.encoding_type["name"] == "polarization":
            assert len(detectors) == 4
        elif self.encoding_type["name"] == "time_bin":
            assert len(detectors) == 2

        self.detectors = []
        for d in detectors:
            if d is not None:
                detector = Detector(timeline, **d)
            else:
                detector = None
            self.detectors.append(detector)

        # assume BSM is connected to two quantum channel
        # self.target_end = None
        # self.signal_end = None

        self.photons = [None, None]
        self.photon_arrival_time = -1

        # define bell basis vectors
        self.bell_basis = [[complex(math.sqrt(1/2)), complex(0), complex(0), complex(math.sqrt(1/2))],
                           [complex(math.sqrt(1/2)), complex(0), complex(0), -complex(math.sqrt(1/2))],
                           [complex(0), complex(math.sqrt(1/2)), complex(math.sqrt(1/2)), complex(0)],
                           [complex(0), complex(math.sqrt(1/2)), -complex(math.sqrt(1/2)), complex(0)]]

    '''
    def assign_target_end(self, target_end):
        self.target_end = target_end

    def assign_signal_end(self, signal_end):
        self.signal_end = signal_end
    '''

    def init(self):
        pass

    def get(self, photon):
        if self.photon_arrival_time < self.timeline.now():
            # clear photons
            self.photons = [photon, None]
            # set arrival time
            self.photon_arrival_time = self.timeline.now()
        
        # if we have photons from same source, do nothing
        # otherwise, we have different photons arriving at the same time and can proceed
        if self.photons[0].location == photon.location:
            return
        else:
            self.photons[1] = photon
            self.send_to_detectors()

    def send_to_detectors(self):
        if numpy.random.random_sample() < self.phase_error:
            self.photons[1].apply_phase_error()

        # entangle photons to measure
        self.photons[0].entangle(self.photons[1])

        # measure in bell basis
        res = Photon.measure_multiple(self.bell_basis, self.photons)

        if self.encoding_type["name"] == "time_bin":
            # check if we've measured as Phi+ or Phi-; these cannot be measured by the BSM
            if res == 0 or res == 1:
                return

            early_time = self.timeline.now()
            late_time = early_time + self.encoding_type["bin_separation"]

            # measured as Psi+
            # send both photons to the same detector at the early and late time
            if res == 2:
                detector_num = numpy.random.choice([0, 1])

                process = Process(self.detectors[detector_num], "get", [])
                event = Event(int(round(early_time)), process)
                self.timeline.schedule(event)
                process = Process(self.detectors[detector_num], "get", [])
                event = Event(int(round(late_time)), process)
                self.timeline.schedule(event)

            # measured as Psi-
            # send photons to different detectors at the early and late time
            elif res == 3:
                detector_num = numpy.random.choice([0, 1])

                process = Process(self.detectors[detector_num], "get", [])
                event = Event(int(round(early_time)), process)
                self.timeline.schedule(event)
                process = Process(self.detectors[1 - detector_num], "get", [])
                event = Event(int(round(late_time)), process)
                self.timeline.schedule(event)

            # invalid result from measurement
            else:
                raise Exception("Invalid result from photon.measure_multiple")

        else:
            # TODO: polarization
            pass

    def get_bsm_res(self):
        # bsm_res = [ [timestamp of early photon, res] ]
        # res: 0 -> \phi_0; 1 -> \phi_1
        bsm_res = []
        if self.encoding_type["name"] == "time_bin":
            d0_times = self.detectors[0].photon_times
            d1_times = self.detectors[1].photon_times
            bin_separation = self.encoding_type["bin_separation"]
            time_resoultion = self.detectors[0].time_resolution
            while d0_times and d1_times:
                if abs(d0_times[0] - d1_times[0]) == time_resoultion * round(bin_separation / time_resoultion):
                    res = [min(d0_times[0], d1_times[0]), 0]
                    bsm_res.append(res)
                    d0_times.pop(0)
                    d1_times.pop(0)
                elif len(d0_times) > 1 and\
                        abs(d0_times[0] - d0_times[1]) == time_resoultion * round(bin_separation / time_resoultion):
                    res = [d0_times[0], 1]
                    bsm_res.append(res)
                    d0_times.pop(0)
                    d0_times.pop(0)
                elif len(d1_times) > 1 and\
                        abs(d1_times[0] - d1_times[1]) == time_resoultion * round(bin_separation / time_resoultion):
                    res = [d1_times[0], 1]
                    bsm_res.append(res)
                    d1_times.pop(0)
                    d1_times.pop(0)
                else:
                    if d0_times[0] < d1_times[0]:
                        d0_times.pop(0)
                    else:
                        d1_times.pop(0)

            while len(d0_times) > 1:
                if d0_times[1] - d0_times[0] == time_resoultion * round(bin_separation / time_resoultion):
                    res = [d0_times[0], 1]
                    bsm_res.append(res)
                    d0_times.pop(0)
                d0_times.pop(0)

            while len(d1_times) > 1:
                if d1_times[1] - d1_times[0] == time_resoultion * round(bin_separation / time_resoultion):
                    res = [d1_times[0], 1]
                    bsm_res.append(res)
                    d1_times.pop(0)
                d1_times.pop(0)

        else:
            # TODO: polariation
            pass
        return bsm_res

class SPDCLens(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.rate = kwargs.get("rate", 1)
        self.direct_receiver = kwargs.get("direct_receiver", None)

    def init(self):
        pass

    def get(self, photon):
        if numpy.random.random_sample() < self.rate:
            state = photon.quantum_state
            photon.wavelength /= 2
            new_photon = copy.deepcopy(photon)

            photon.entangle(new_photon)
            photon.set_state([state[0], complex(0), complex(0), state[1]])

            self.direct_receiver.get(photon)
            self.direct_receiver.get(new_photon)

    def assign_receiver(self, receiver):
        self.direct_receiver = receiver


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


# atomic ensemble memory for DLCZ/entanglement swapping
class Memory(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.fidelity = kwargs.get("fidelity", 1)
        self.efficiency = kwargs.get("efficiency", 1)
        self.direct_receiver = kwargs.get("direct_receiver", None)
        self.state = 0
        self.frequencies = kwargs.get("frequencies", [0, 0]) # first element is ground transition frequency, second is excited frequency
        # keep track of entanglement?

    def init(self):
        pass

    def write(self):
        if numpy.random.random_sample() < self.efficiency and self.state == 0:
            self.state = 1
            # send photon in certain state to direct receiver
            # TODO: specify new encoding_type
            photon = Photon("", self.timeline, wavelength=(1/self.frequencies[1]), location=self, encoding_type=None)
            self.direct_receiver.get(photon)
            # schedule decay based on frequency
            decay_time = self.timeline.now() + int(numpy.random.exponential(fidelity) * 1e12)
            process = Process(self, "read", [])
            event = Event(decay_time, process)
            self.timeline.schedule(event)

    def read(self):
        if numpy.random_random_sample() < self.fidelity and self.state == 1:
            self.state = 0
            # send photon in certain state to direct receiver
            photon = Photon("", self.timeline, wavelength=(1/self.frequencies[0]), location=self, encoding_type=None)
            self.direct_receiver.get(photon)


# array of atomic ensemble memories
class MemoryArray(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.memories = kwargs.get("memories", [])
        self.frequency = kwargs.get("frequency", 1)
        self.entangled_memories = [-1] * len(self.memories)
    
    def write(self):
        time = self.timeline.now()

        for mem in self.memories:
            process = Process(mem, "write", [])
            event = Event(time, process)
            self.timeline.schedule(event)
            time += 1e12 / self.frequency

    def read(self):
        time = self.timeline.now()
        
        for mem in self.memories:
            process = Process(mem, "read", [])
            event = Event(time, process)
            self.timeline.schedule(event)
            time += 1e12 / frequency
            

# class for photon memory
class Memory_EIT(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.fidelity = kwargs.get("fidelity", 1)
        self.efficiency = kwargs.get("efficiency", 1)
        self.photon = None

    def init(self):
        pass

    def get(self, photon):
        photon.location = self
        self.photon = photon

    def retrieve_photon(self):
        photon = self.photon
        self.photon = None
        return photon


class Node(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.components = kwargs.get("components", {})
        self.message = None  # temporary storage for message received through classical channel
        self.protocol = None

    def init(self):
        pass

    def send_qubits(self, basis_list, bit_list, source_name):
        encoding_type = self.components[source_name].encoding_type
        state_list = []
        for i, bit in enumerate(bit_list):
            state = (encoding_type["bases"][basis_list[i]])[bit]
            state_list.append(state)

        self.components[source_name].emit(state_list)

    def send_photons(self, state, num, source_name):
        state_list = [state] * num
        self.components[source_name].emit(state_list)

    def get_bits(self, light_time, start_time, frequency, detector_name):
        encoding_type = self.components[detector_name].encoding_type
        bits = [-1] * int(round(light_time * frequency))  # -1 used for invalid bits

        if encoding_type["name"] == "polarization":
            detection_times = self.components[detector_name].get_photon_times()

            # determine indices from detection times and record bits
            for time in detection_times[0]:  # detection times for |0> detector
                index = int(round((time - start_time) * frequency * 1e-12))
                if 0 <= index < len(bits):
                    bits[index] = 0

            for time in detection_times[1]:  # detection times for |1> detector
                index = int(round((time - start_time) * frequency * 1e-12))
                if 0 <= index < len(bits):
                    if bits[index] == 0:
                        bits[index] = -1
                    else:
                        bits[index] = 1

            return bits

        elif encoding_type["name"] == "time_bin":
            detection_times = self.components[detector_name].get_photon_times()
            bin_separation = encoding_type["bin_separation"]

            # single detector (for early, late basis) times
            for time in detection_times[0]:
                index = int(round((time - start_time) * frequency * 1e-12))
                if 0 <= index < len(bits):
                    if abs(((index * 1e12 / frequency) + start_time) - time) < bin_separation / 2:
                        bits[index] = 0
                    elif abs(((index * 1e12 / frequency) + start_time) - (time - bin_separation)) < bin_separation / 2:
                        bits[index] = 1

            # interferometer detector 0 times
            for time in detection_times[1]:
                time -= bin_separation
                index = int(round((time - start_time) * frequency * 1e-12))
                # check if index is in range and is in correct time bin
                if 0 <= index < len(bits) and\
                        abs(((index * 1e12 / frequency) + start_time) - time) < bin_separation / 2:
                    if bits[index] == -1:
                        bits[index] = 0
                    else:
                        bits[index] = -1

            # interferometer detector 1 times
            for time in detection_times[2]:
                time -= bin_separation
                index = int(round((time - start_time) * frequency * 1e-12))
                # check if index is in range and is in correct time bin
                if 0 <= index < len(bits) and\
                        abs(((index * 1e12 / frequency) + start_time) - time) < bin_separation / 2:
                    if bits[index] == -1:
                        bits[index] = 1
                    else:
                        bits[index] = -1

            return bits

        else:
            raise Exception("Invalid encoding type for node " + self.name)

    def set_bases(self, basis_list, start_time, frequency, detector_name):
        encoding_type = self.components[detector_name].encoding_type
        basis_start_time = start_time - 1e12 / (2 * frequency)

        if encoding_type["name"] == "polarization":
            splitter = self.components[detector_name].splitter
            splitter.start_time = basis_start_time
            splitter.frequency = frequency

            splitter_basis_list = []
            for b in basis_list:
                splitter_basis_list.append(encoding_type["bases"][b])
            splitter.basis_list = splitter_basis_list

        elif encoding_type["name"] == "time_bin":
            switch = self.components[detector_name].switch
            switch.start_time = basis_start_time
            switch.frequency = frequency
            switch.state_list = basis_list

        else:
            raise Exception("Invalid encoding type for node " + self.name)

    def get_source_count(self):
        source = self.components['lightsource']
        return source.photon_counter

    def send_message(self, msg, channel="cchannel"):
        self.components[channel].transmit(msg, self)

    def receive_message(self, msg):
        self.message = msg
        # signal to protocol that we've received a message
        self.protocol.received_message()


class Topology:
    def __init__(self, config_file, timelines):
        self.nodes = {}
        self.quantum_channel = {}
        self.entities = []

        topo_config = json5.load(open(config_file))
        nodes_config = topo_config['nodes']
        self.create_nodes(nodes_config, timelines)
        self.create_qchannel(topo_config['QChannel'], timelines)
        self.create_cchannel(topo_config['CChannel'], timelines)
        self.create_protocols(nodes_config, timelines)

    def create_nodes(self, nodes_config, timelines):
        for node_config in nodes_config:
            components = {}

            for component_config in node_config['components']:
                if component_config['name'] in components:
                    raise Exception('two components have same name')

                # get component_name, timeline, and name
                # then delete entries in component_config dictionary to prevent conflicting values
                component_name = component_config['name']
                name = node_config['name'] + '.' + component_name
                tl = timelines[component_config['timeline']]
                del component_config['name']
                del component_config['timeline']

                # light source instantiation
                if component_config["type"] == 'LightSource':
                    ls = LightSource(name, tl, **component_config)
                    components[component_name] = ls
                    self.entities.append(ls)

                # detector instantiation
                elif component_config["type"] == 'QSDetector':
                    detector = QSDetector(name, tl, **component_config)
                    components[component_name] = detector
                    self.entities.append(detector)

                else:
                    raise Exception('unknown device type')

            node = Node(node_config['name'], timelines[node_config['timeline']], components=components)

            for protocol_config in node_config['protocols']:
                protocol_name = protocol_config['name']
                name = node_config['name'] + '.' + protocol_name
                tl = timelines[protocol_config['timeline']]
                del protocol_config['name']
                del protocol_config['timeline']

                if protocol_config["protocol"] == 'BB84':
                    bb84 = BB84(name, tl, **protocol_config)
                    bb84.assign_node(node)
                    node.protocol = bb84
                    self.entities.append(bb84)

                # add cascade config

            self.entities.append(node)

            if node.name in self.nodes:
                raise Exception('two nodes have same name')

            self.nodes[node.name] = node

    def create_qchannel(self, channel_config, timelines):
        for config in channel_config:
            name = config['name']
            tl = timelines[config['timeline']]
            sender = self.find_entity_by_name(config['sender'])
            receiver = self.find_entity_by_name(config['receiver'])
            del config['name']
            del config['timeline']
            del config['sender']
            del config['receiver']

            chan = QuantumChannel(name, tl, **config)
            chan.set_sender(sender)
            sender.direct_receiver = chan
            chan.set_receiver(receiver)
            self.entities.append(chan)

    # TODO: use add_end function for classical channel
    def create_cchannel(self, channel_config, timelines):
        for config in channel_config:
            name = config['name']
            tl = timelines[config['timeline']]
            del config['name']
            del config['timeline']

            chan = ClassicalChannel(name, tl, **config)
            self.entities.append(chan)

    # TODO: populate
    def create_protocols(self, nodes_config, timelines):
        pass

    def print_topology(self):
        pass

    def to_json5_file(self):
        pass

    def find_entity_by_name(self, name):
        for e in self.entities:
            if e.name == name:
                return e
        raise Exception('unknown entity name',name)

    def find_node_by_name(self, name):
        pass

    def find_qchannel_by_name(self, name):
        pass

