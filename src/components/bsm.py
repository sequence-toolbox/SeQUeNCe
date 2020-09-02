"""Models for simulating bell state measurement.

This module defines a template bell state measurement (BSM) class, as well as implementations for polarization, time bin, and memory encoding schemes.
Also defined is a function to automatically construct a BSM of a specified type.
"""

from abc import abstractmethod
from typing import Any, Dict

from numpy import random

from .detector import Detector
from .photon import Photon
from ..kernel.entity import Entity
from ..kernel.event import Event
from ..kernel.process import Process
from ..utils.encoding import *
from ..utils.quantum_state import QuantumState


def make_bsm(name, timeline, encoding_type='time_bin', phase_error=0, detectors=[]):
    """Function to construct BSM of specified type.

    Arguments:
        name (str): name to be used for BSM instance.
        timeline (Timeline): timeline to be used for BSM instance.
        encoding_type (str): type of BSM to generate (default "time_bin").
        phase_error (float): error to apply to incoming qubits (default 0).
        detectors (List[Dict[str, any]): list of detector objects given as dicts (default []).
    """

    if encoding_type == "polarization":
        return PolarizationBSM(name, timeline, phase_error, detectors)
    elif encoding_type == "time_bin":
        return TimeBinBSM(name, timeline, phase_error, detectors)
    elif encoding_type == "single_atom":
        return SingleAtomBSM(name, timeline, phase_error, detectors)
    else:
        raise Exception("invalid encoding {} given for BSM {}".format(encoding_type, name))


class BSM(Entity):
    """Parent class for bell state measurement devices.

    Attributes:
        name (str): label for BSM instance.
        timeline (Timeline): timeline for simulation.
        phase_error (float): phase error applied to measurement.
        detectors (List[Detector]): list of attached photon detection devices.
        resolution (int): maximum time resolution achievable with attached detectors.
    """

    def __init__(self, name, timeline, phase_error=0, detectors=[]):
        """Constructor for base BSM object.

        Args:
            name (str): name of the beamsplitter instance.
            timeline (Timeline): simulation timeline.
            phase_error (float): Phase error applied to polarization photons (default 0).
            detectors (List[Dict[str, Any]]): List of parameters for attached detectors, in dictionary format (default []).
        """

        super().__init__(name, timeline)
        self.phase_error = phase_error
        self.photons = []
        self.photon_arrival_time = -1

        self.detectors = []
        for d in detectors:
            if d is not None:
                detector = Detector("", timeline, **d)
                detector.attach(self)
            else:
                detector = None
            self.detectors.append(detector)

        # get resolution
        self.resolution = max(d.time_resolution for d in self.detectors)

        # define bell basis vectors
        self.bell_basis = ((complex(sqrt(1 / 2)), complex(0), complex(0), complex(sqrt(1 / 2))),
                           (complex(sqrt(1 / 2)), complex(0), complex(0), -complex(sqrt(1 / 2))),
                           (complex(0), complex(sqrt(1 / 2)), complex(sqrt(1 / 2)), complex(0)),
                           (complex(0), complex(sqrt(1 / 2)), -complex(sqrt(1 / 2)), complex(0)))

    def init(self):
        """Implementation of Entity interface (see base class)."""

        pass

    @abstractmethod
    def get(self, photon):
        """Method to receive a photon for measurement (abstract).

        Arguments:
            photon (Photon): photon to measure.
        """
        # check if photon arrived later than current photon
        if self.photon_arrival_time < self.timeline.now():
            # clear photons
            self.photons = [photon]
            # set arrival time
            self.photon_arrival_time = self.timeline.now()

        # check if we have a photon from a new location
        if not any([reference.location == photon.location for reference in self.photons]):
            self.photons.append(photon)

    @abstractmethod
    def trigger(self, detector: Detector, info: Dict[str, Any]):
        """Method to receive photon detection events from attached detectors (abstract).

        Arguments:
            detector (Detector): the source of the detection message.
            info (Dict[str, Any]): the message from the source detector.
        """

        pass

    def notify(self, info: Dict[str, Any]):
        for observer in self._observers:
            observer.bsm_update(self, info)

    def update_detectors_params(self, arg_name: str, value: Any) -> None:
        """Updates parameters of attached detectors."""
        for detector in self.detectors:
            detector.__setattr__(arg_name, value)


class PolarizationBSM(BSM):
    """Class modeling a polarization BSM device.

    Measures incoming photons according to polarization and manages entanglement.

    Attributes:
        name (str): label for BSM instance.
        timeline (Timeline): timeline for simulation.
        phase_error (float): phase error applied to measurement.
        detectors (List[Detector]): list of attached photon detection devices.
        resolution (int): maximum time resolution achievable with attached detectors.
    """

    def __init__(self, name, timeline, phase_error=0, detectors=[]):
        """Constructor for Polarization BSM.

        Args:
            name (str): name of the beamsplitter instance.
            timeline (Timeline): simulation timeline.
            phase_error (float): phase error applied to polarization photons (default 0).
            detectors (List[Dict]): list of parameters for attached detectors, in dictionary format (must be of length 4) (default []).
        """

        super().__init__(name, timeline, phase_error, detectors)
        self.last_res = [-2 * self.resolution, -1]
        assert len(self.detectors) == 4

    def get(self, photon):
        """See base class.

        This method adds additional side effects not present in the base class.

        Side Effects:
            May call get method of one or more attached detector(s).
            May alter the quantum state of photon and any stored photons.
        """

        super().get(photon)

        if len(self.photons) != 2:
            return

        # entangle photons to measure
        self.photons[0].entangle(self.photons[1])

        # measure in bell basis
        res = Photon.measure_multiple(self.bell_basis, self.photons)

        # check if we've measured as Phi+ or Phi-; these cannot be measured by the BSM
        if res == 0 or res == 1:
            return

        # measured as Psi+
        # photon detected in corresponding detectors
        if res == 2:
            detector_num = random.choice([0, 2])
            self.detectors[detector_num].get()
            self.detectors[detector_num + 1].get()

        # measured as Psi-
        # photon detected in opposite detectors
        elif res == 3:
            detector_num = random.choice([0, 2])
            self.detectors[detector_num].get()
            self.detectors[3 - detector_num].get()

        else:
            raise Exception("Invalid result from photon.measure_multiple")

    def trigger(self, detector: Detector, info: Dict[str, Any]):
        """See base class.

        This method adds additional side effects not present in the base class.

        Side Effects:
            May send a further message to any attached entities.
        """

        detector_num = self.detectors.index(detector)
        time = info["time"]

        # check if matching time
        if abs(time - self.last_res[0]) < self.resolution:
            detector_last = self.last_res[1]

            # Psi-
            if detector_last + detector_num == 3:
                info = {'entity': 'BSM', 'info_type': 'BSM_res', 'res': 1, 'time': time}
                self.notify(info)
            # Psi+
            elif abs(detector_last - detector_num) == 1:
                info = {'entity': 'BSM', 'info_type': 'BSM_res', 'res': 0, 'time': time}
                self.notify(info)

        self.last_res = [time, detector_num]


class TimeBinBSM(BSM):
    """Class modeling a time bin BSM device.

    Measures incoming photons according to time bins and manages entanglement.

    Attributes:
        name (str): label for BSM instance
        timeline (Timeline): timeline for simulation
        detectors (List[Detector]): list of attached photon detection devices
        resolution (int): maximum time resolution achievable with attached detectors  
    """

    def __init__(self, name, timeline, phase_error=0, detectors=[]):
        """Constructor for the time bin BSM class.

        Args:
            name (str): name of the beamsplitter instance.
            timeline (Timeline): simulation timeline.
            phase_error (float): phase error applied to polarization qubits (unused) (default 0).
            detectors (List[Dict]): list of parameters for attached detectors, in dictionary format (must be of length 2) (default []).
        """

        super().__init__(name, timeline, phase_error, detectors)
        self.encoding_type = time_bin
        self.last_res = [-1, -1]
        assert len(self.detectors) == 2

    def get(self, photon):
        """See base class.

        This method adds additional side effects not present in the base class.

        Side Effects:
            May call get method of one or more attached detector(s).
            May alter the quantum state of photon and any stored photons.
        """

        super().get(photon)

        if len(self.photons) != 2:
            return

        if random.random_sample() < self.phase_error:
            self.photons[1].apply_phase_error()
        # entangle photons to measure
        self.photons[0].entangle(self.photons[1])

        # measure in bell basis
        res = Photon.measure_multiple(self.bell_basis, self.photons)

        # check if we've measured as Phi+ or Phi-; these cannot be measured by the BSM
        if res == 0 or res == 1:
            return

        early_time = self.timeline.now()
        late_time = early_time + self.encoding_type["bin_separation"]

        # measured as Psi+
        # send both photons to the same detector at the early and late time
        if res == 2:
            detector_num = random.choice([0, 1])

            process = Process(self.detectors[detector_num], "get", [])
            event = Event(int(round(early_time)), process)
            self.timeline.schedule(event)
            process = Process(self.detectors[detector_num], "get", [])
            event = Event(int(round(late_time)), process)
            self.timeline.schedule(event)

        # measured as Psi-
        # send photons to different detectors at the early and late time
        elif res == 3:
            detector_num = random.choice([0, 1])

            process = Process(self.detectors[detector_num], "get", [])
            event = Event(int(round(early_time)), process)
            self.timeline.schedule(event)
            process = Process(self.detectors[1 - detector_num], "get", [])
            event = Event(int(round(late_time)), process)
            self.timeline.schedule(event)

        # invalid result from measurement
        else:
            raise Exception("Invalid result from photon.measure_multiple")

    def trigger(self, detector: Detector, info: Dict[str, Any]):
        """See base class.

        This method adds additional side effects not present in the base class.

        Side Effects:
            May send a further message to any attached entities.
        """

        detector_num = self.detectors.index(detector)
        time = info["time"]

        # check if valid time
        if round((time - self.last_res[0]) / self.encoding_type["bin_separation"]) == 1:
            # if time - self.last_res[0] < self.resolution + self.encoding_type["bin_separation"]:
            # pop result message
            # Psi+
            if detector_num == self.last_res[1]:
                info = {'entity': 'BSM', 'info_type': 'BSM_res', 'res': 0, 'time': time}
                self.notify(info)
            # Psi-
            else:
                info = {'entity': 'BSM', 'info_type': 'BSM_res', 'res': 1, 'time': time}
                self.notify(info)

        self.last_res = [time, detector_num]


class SingleAtomBSM(BSM):
    """Class modeling a single atom BSM device.

    Measures incoming photons and manages entanglement of associated memories.

    Attributes:
        name (str): label for BSM instance
        timeline (Timeline): timeline for simulation
        detectors (List[Detector]): list of attached photon detection devices
        resolution (int): maximum time resolution achievable with attached detectors  
    """

    def __init__(self, name, timeline, phase_error=0, detectors=[]):
        """Constructor for the single atom BSM class.

        Args:
            name (str): name of the beamsplitter instance.
            timeline (Timeline): simulation timeline.
            phase_error (float): phase error applied to polarization qubits (unused) (default 0).
            detectors (List[Dict]): list of parameters for attached detectors, in dictionary format (must be of length 2) (default []).
        """

        if detectors == []:
            detectors = [{}, {}]
        super().__init__(name, timeline, phase_error, detectors)
        assert len(self.detectors) == 2

    def get(self, photon):
        """See base class.

        This method adds additional side effects not present in the base class.

        Side Effects:
            May call get method of one or more attached detector(s).
            May alter the quantum state of photon and any stored photons, as well as their corresponding memories.
        """

        super().get(photon)

        memory = photon.encoding_type["memory"]

        # check if we're in first stage. If we are and not null, send photon to random detector
        if memory.previous_bsm == -1 and not photon.is_null:
            detector_num = random.choice([0, 1])
            memory.previous_bsm = detector_num
            self.detectors[detector_num].get()

        if len(self.photons) == 2:
            null_0 = self.photons[0].is_null
            null_1 = self.photons[1].is_null
            is_valid = null_0 ^ null_1
            if is_valid:
                memory_0 = self.photons[0].encoding_type["memory"]
                memory_1 = self.photons[1].encoding_type["memory"]
                # if we're in stage 1: null photon will need bsm assigned
                if null_0 and memory_0.previous_bsm == -1:
                    memory_0.previous_bsm = memory_1.previous_bsm
                elif null_1 and memory_1.previous_bsm == -1:
                    memory_1.previous_bsm = memory_0.previous_bsm
                # if we're in stage 2: send photon to same (opposite) detector for psi+ (psi-)
                else:
                    if memory_0.qstate not in memory_1.qstate.entangled_states:
                        memory_0.qstate.entangle(memory_1.qstate)
                    res = QuantumState.measure_multiple(self.bell_basis, [memory_0.qstate, memory_1.qstate])
                    if res == 2:  # Psi+
                        detector_num = memory_0.previous_bsm
                    elif res == 3:  # Psi-
                        detector_num = 1 - memory_0.previous_bsm
                    else:
                        # Happens if the memory is expired during photon transmission; randomly select a detector
                        detector_num = random.randint(2)
                    self.detectors[detector_num].get()

    def trigger(self, detector: Detector, info: Dict[str, Any]):
        """See base class.

        This method adds additional side effects not present in the base class.

        Side Effects:
            May send a further message to any attached entities.
        """

        detector_num = self.detectors.index(detector)
        time = info["time"]

        res = detector_num
        info = {'entity': 'BSM', 'info_type': 'BSM_res', 'res': res, 'time': time}
        self.notify(info)
