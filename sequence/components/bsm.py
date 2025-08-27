"""Models for simulating bell state measurement.

This module defines a template bell state measurement (BSM) class,
as well as implementations for polarization, time bin, and memory encoding schemes.
Also defined is a function to automatically construct a BSM of a specified type.
"""

from abc import abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..kernel.quantum_manager import QuantumManager
    from ..kernel.quantum_state import State
    from ..kernel.timeline import Timeline

from numpy import outer, add, zeros, array_equal

from .circuit import Circuit
from .detector import Detector
from .photon import Photon
from ..kernel.entity import Entity
from ..kernel.event import Event
from ..kernel.process import Process
from ..kernel.quantum_manager import KET_STATE_FORMALISM, DENSITY_MATRIX_FORMALISM
from ..utils.encoding import *
from ..utils import log


def make_bsm(name, timeline: "Timeline", encoding_type='time_bin', phase_error=0, detectors=[]):
    """Function to construct BSM of specified type.

    Arguments:
        name (str): name to be used for BSM instance.
        timeline (Timeline): timeline to be used for BSM instance.
        encoding_type (str): type of BSM to generate (default "time_bin").
        phase_error (float): error to apply to incoming qubits (default 0).
        detectors (list[dict[str, any]): list of detector objects given as dicts (default []).
    """

    if encoding_type == "polarization":
        return PolarizationBSM(name, timeline, phase_error, detectors)
    elif encoding_type == "time_bin":
        return TimeBinBSM(name, timeline, phase_error, detectors)
    elif encoding_type == "single_atom":
        return SingleAtomBSM(name, timeline, phase_error, detectors)
    elif encoding_type == "absorptive":
        return AbsorptiveBSM(name, timeline, phase_error, detectors)
    else:
        raise Exception("invalid encoding {} given for BSM {}".format(encoding_type, name))


def _set_state_with_fidelity(keys: list[int], desired_state: list[complex], fidelity: float, rng, qm: "QuantumManager"):
    possible_states = [BSM._phi_plus, BSM._phi_minus,
                       BSM._psi_plus, BSM._psi_minus]
    assert desired_state in possible_states

    if qm.formalism == KET_STATE_FORMALISM:
        probabilities = [(1 - fidelity) / 3] * 4
        probabilities[possible_states.index(desired_state)] = fidelity
        state_ind = rng.choice(4, p=probabilities)
        qm.set(keys, possible_states[state_ind])

    elif qm.formalism == DENSITY_MATRIX_FORMALISM:
        multipliers = [(1 - fidelity) / 3] * 4
        multipliers[possible_states.index(desired_state)] = fidelity
        state = zeros((4, 4))
        for mult, pure in zip(multipliers, possible_states):
            state = add(state, mult * outer(pure, pure))
        qm.set(keys, state)

    else:
        raise Exception("Invalid quantum manager with formalism {}".format(qm.formalism))


def _set_pure_state(keys: list[int], ket_state: list[complex], qm: "QuantumManager"):
    if qm.formalism == KET_STATE_FORMALISM:
        qm.set(keys, ket_state)
    elif qm.formalism == DENSITY_MATRIX_FORMALISM:
        state = outer(ket_state, ket_state)
        qm.set(keys, state)
    else:
        raise NotImplementedError("formalism of quantum state {} is not "
                                  "implemented in the set_pure_quantum_state "
                                  "function of bsm.py".format(qm.formalism))


def _eq_psi_plus(state: "State", formalism: str):
    if formalism == KET_STATE_FORMALISM:
        return array_equal(state.state, BSM._psi_plus)
    elif formalism == DENSITY_MATRIX_FORMALISM:
        d_state = outer(BSM._phi_plus, BSM._psi_plus)
        return array_equal(state.state, d_state)
    else:
        raise NotImplementedError("formalism of quantum state {} is not "
                                  "implemented in the eq_phi_plus "
                                  "function of bsm.py".format(formalism))


class BSM(Entity):
    """Parent class for bell state measurement devices.

    Attributes:
        name (str): label for BSM instance.
        timeline (Timeline): timeline for simulation.
        phase_error (float): phase error applied to measurement.
        detectors (list[Detector]): list of attached photon detection devices.
        resolution (int): maximum time resolution achievable with attached detectors.
    """

    _phi_plus = [complex(sqrt(1 / 2)), complex(0), complex(0), complex(sqrt(1 / 2))]
    _phi_minus = [complex(sqrt(1 / 2)), complex(0), complex(0), -complex(sqrt(1 / 2))]
    _psi_plus = [complex(0), complex(sqrt(1 / 2)), complex(sqrt(1 / 2)), complex(0)]
    _psi_minus = [complex(0), complex(sqrt(1 / 2)), -complex(sqrt(1 / 2)), complex(0)]

    def __init__(self, name: str, timeline: "Timeline", phase_error: float = 0, detectors=None):
        """Constructor for base BSM object.

        Args:
            name (str): name of the beamsplitter instance.
            timeline (Timeline): simulation timeline.
            phase_error (float): Phase error applied to polarization photons (default 0).
            detectors (list[dict[str, Any]]): list of parameters for attached detectors,
                in dictionary format (default None).
        """

        super().__init__(name, timeline)
        self.encoding = "None"
        self.phase_error = phase_error
        self.photons = []
        self.photon_arrival_time = -1
        self.resolution = None

        self.detectors = []
        if detectors is not None:
            for i, d in enumerate(detectors):
                if d is not None:
                    detector = Detector("{}_{}".format(self.name, i), timeline, **d)
                    detector.attach(self)
                    detector.owner = self
                else:
                    detector = None
                self.detectors.append(detector)

        # define bell basis vectors
        self.bell_basis = ((complex(sqrt(1 / 2)), complex(0), complex(0), complex(sqrt(1 / 2))),
                           (complex(sqrt(1 / 2)), complex(0), complex(0), -complex(sqrt(1 / 2))),
                           (complex(0), complex(sqrt(1 / 2)), complex(sqrt(1 / 2)), complex(0)),
                           (complex(0), complex(sqrt(1 / 2)), -complex(sqrt(1 / 2)), complex(0)))


    def init(self):
        """Implementation of Entity interface (see base class)."""

        # get resolution
        self.resolution = max(d.time_resolution for d in self.detectors)

        self.photons = []
        self.photon_arrival_time = -1

    @abstractmethod
    def get(self, photon, **kwargs):
        """Method to receive a photon for measurement (abstract).

        Arguments:
            photon (Photon): photon to measure.
        """

        assert photon.encoding_type["name"] == self.encoding, \
            "BSM expecting photon with encoding '{}' received photon with encoding '{}'".format(
                self.encoding, photon.encoding_type["name"])

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
    def trigger(self, detector: Detector, info: dict[str, Any]):
        """Method to receive photon detection events from attached detectors (abstract).

        Arguments:
            detector (Detector): the source of the detection message.
            info (dict[str, Any]): the message from the source detector.
        """

        pass

    def notify(self, info: dict[str, Any]):
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
        detectors (list[Detector]): list of attached photon detection devices.
    """

    def __init__(self, name, timeline, phase_error=0, detectors=None):
        """Constructor for Polarization BSM.

        Args:
            name (str): name of the BSM instance.
            timeline (Timeline): simulation timeline.
            phase_error (float): phase error applied to polarization photons (default 0).
            detectors (list[dict]): list of parameters for attached detectors,
                in dictionary format (must be of length 4) (default None).
        """

        super().__init__(name, timeline, phase_error, detectors)
        self.encoding = "polarization"
        self.last_res = [None, None]
        assert len(self.detectors) == 4

    def init(self):
        super().init()
        self.last_res = [-2 * self.resolution, -1]

    def get(self, photon, **kwargs):
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
        self.photons[0].combine_state(self.photons[1])

        # measure in bell basis
        res = Photon.measure_multiple(self.bell_basis, self.photons, self.get_generator())

        # check if we've measured as Phi+ or Phi-; these cannot be measured by the BSM
        if res == 0 or res == 1:
            return

        # measured as Psi+
        # photon detected in corresponding detectors
        if res == 2:
            detector_num = self.get_generator().choice([0, 2])
            self.detectors[detector_num].get()
            self.detectors[detector_num + 1].get()

        # measured as Psi-
        # photon detected in opposite detectors
        elif res == 3:
            detector_num = self.get_generator().choice([0, 2])
            self.detectors[detector_num].get()
            self.detectors[3 - detector_num].get()

        else:
            raise Exception("Invalid result from photon.measure_multiple")

    def trigger(self, detector: Detector, info: dict[str, Any]):
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
        detectors (list[Detector]): list of attached photon detection devices
    """

    def __init__(self, name, timeline, phase_error=0, detectors=None):
        """Constructor for the time bin BSM class.

        Args:
            name (str): name of the beamsplitter instance.
            timeline (Timeline): simulation timeline.
            phase_error (float): phase error applied to polarization qubits (unused) (default 0).
            detectors (list[dict]): list of parameters for attached detectors,
                in dictionary format (must be of length 2) (default None).
        """

        super().__init__(name, timeline, phase_error, detectors)
        self.encoding = "time_bin"
        self.encoding_type = time_bin
        self.last_res = [-1, -1]
        assert len(self.detectors) == 2

    def get(self, photon, **kwargs):
        """See base class.

        This method adds additional side effects not present in the base class.

        Side Effects:
            May call get method of one or more attached detector(s).
            May alter the quantum state of photon and any stored photons.
        """

        super().get(photon)

        if len(self.photons) != 2:
            return

        if self.get_generator().random() < self.phase_error:
            self.photons[1].apply_phase_error()
        # entangle photons to measure
        self.photons[0].combine_state(self.photons[1])

        # measure in bell basis
        res = Photon.measure_multiple(self.bell_basis, self.photons, self.get_generator())

        # check if we've measured as Phi+ or Phi-; these cannot be measured by the BSM
        if res == 0 or res == 1:
            return

        early_time = self.timeline.now()
        late_time = early_time + self.encoding_type["bin_separation"]

        # measured as Psi+
        # send both photons to the same detector at the early and late time
        if res == 2:
            detector_num = self.get_generator().choice([0, 1])

            process = Process(self.detectors[detector_num], "get", [])
            event = Event(int(round(early_time)), process)
            self.timeline.schedule(event)
            process = Process(self.detectors[detector_num], "get", [])
            event = Event(int(round(late_time)), process)
            self.timeline.schedule(event)

        # measured as Psi-
        # send photons to different detectors at the early and late time
        elif res == 3:
            detector_num = self.get_generator().choice([0, 1])

            process = Process(self.detectors[detector_num], "get", [])
            event = Event(int(round(early_time)), process)
            self.timeline.schedule(event)
            process = Process(self.detectors[1 - detector_num], "get", [])
            event = Event(int(round(late_time)), process)
            self.timeline.schedule(event)

        # invalid result from measurement
        else:
            raise Exception("Invalid result from photon.measure_multiple")

    def trigger(self, detector: Detector, info: dict[str, Any]):
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
        phase_error (float): phase error applied to measurement.
        detectors (list[Detector]): list of attached photon detection devices
        resolution (int): maximum time resolution achievable with attached detectors  
    """
    _meas_circuit = Circuit(1)
    _meas_circuit.measure(0)

    def __init__(self, name, timeline, phase_error=0, detectors=None):
        """Constructor for the single atom BSM class.

        Args:
            name (str): name of the beamsplitter instance.
            timeline (Timeline): simulation timeline.
            phase_error (float): phase error applied to polarization qubits (unused) (default 0).
            detectors (list[dict]): list of parameters for attached detectors,
                in dictionary format (must be of length 2) (default None).
        """

        if detectors is None:
            detectors = [{}, {}]
        super().__init__(name, timeline, phase_error, detectors)
        self.encoding = "single_atom"
        assert len(self.detectors) == 2

    def get(self, photon, **kwargs):
        """See base class.

        This method adds additional side effects not present in the base class.

        Side Effects:
            May call get method of one or more attached detector(s).
            May alter the quantum state of photon and any stored photons, as well as their corresponding memories.
        """

        super().get(photon)
        log.logger.debug(self.name + " received photon")

        if len(self.photons) == 2:
            qm = self.timeline.quantum_manager
            p0, p1 = self.photons
            key0, key1 = p0.quantum_state, p1.quantum_state
            keys = [key0, key1]
            state0, state1 = qm.get(key0), qm.get(key1)
            meas0, meas1 = [qm.run_circuit(self._meas_circuit, [key], self.get_generator().random())[key]
                            for key in keys]

            log.logger.debug(self.name + " measured photons as {}, {}".format(meas0, meas1))

            if meas0 ^ meas1:  # meas0, meas1 = 1, 0 or 0, 1
                detector_num = self.get_generator().choice([0, 1])   # randomly select a detector number
                if len(state0.keys) == 1:
                    # if we're in stage 1: we set state to psi+/psi- to mark the
                    # first triggered detector
                    log.logger.info(self.name + " passed stage 1")
                    if detector_num == 0:
                        _set_pure_state(keys, BSM._psi_minus, qm)
                    else:
                        _set_pure_state(keys, BSM._psi_plus, qm)
                elif len(state0.keys) == 2:
                    # if we're in stage 2: check if the same detector is triggered
                    # twice to assign state to psi+ or psi-
                    log.logger.info(self.name + " passed stage 2")
                    if _eq_psi_plus(state0, qm.formalism) ^ detector_num:
                        _set_state_with_fidelity(keys, BSM._psi_minus, p0.encoding_type["raw_fidelity"], self.get_generator(), qm)
                    else:
                        _set_state_with_fidelity(keys, BSM._psi_plus, p0.encoding_type["raw_fidelity"], self.get_generator(), qm)
                else:
                    raise NotImplementedError("Unknown state")

                photon = p0 if meas0 else p1
                if self.get_generator().random() > photon.loss:
                    log.logger.info("Triggering detector {}".format(detector_num))
                    # middle BSM node notify two end nodes via EntanglementGenerationB.bsm_update()
                    self.detectors[detector_num].get()
                else:
                    log.logger.info(f'{self.name} lost photon p{meas1}')

            else:  # meas0, meas1 = 1, 1 or 0, 0
                if meas0 and self.get_generator().random() > p0.loss:
                    detector_num = self.get_generator().choice([0, 1])
                    self.detectors[detector_num].get()
                else:
                    log.logger.info(f'{self.name} lost photon p0')

                if meas1 and self.get_generator().random() > p1.loss:
                    detector_num = self.get_generator().choice([0, 1])
                    self.detectors[detector_num].get()
                else:
                    log.logger.info(f'{self.name} lost photon p1')

    def trigger(self, detector: Detector, info: dict[str, Any]):
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


class AbsorptiveBSM(BSM):
    """Class modeling a BSM device for absorptive quantum memories.

    Measures photons and manages entanglement state of entangled photons.

    Attributes:
        name (str): label for BSM instance
        timeline (Timeline): timeline for simulation
        detectors (list[Detector]): list of attached photon detection devices (length 2).
    """

    def __init__(self, name, timeline, phase_error=0, detectors=None):
        """Constructor for the AbsorptiveBSM class."""

        if detectors is None:
            detectors = [{}, {}]
        super().__init__(name, timeline, phase_error, detectors)
        self.encoding = "absorptive"
        assert len(self.detectors) == 2

    def get(self, photon, **kwargs):
        """"""

        super().get(photon)

        # get other photon, set to measured state
        key = photon.quantum_state
        state = self.timeline.quantum_manager.get(key)
        other_keys = state.keys[:]
        other_keys.remove(key)
        if photon.is_null:
            self.timeline.quantum_manager.set(other_keys, [complex(1), complex(0)])
        else:
            detector_num = self.get_generator().choice([0, 1])
            self.detectors[detector_num].get()
            self.timeline.quantum_manager.set(other_keys, [complex(0), complex(1)])

        if len(self.photons) == 2:
            null_0 = self.photons[0].is_null
            null_1 = self.photons[1].is_null
            is_valid = null_0 ^ null_1

            # check if we can set to entangled Psi+ state
            if is_valid:
                # get other photons to entangle
                key_0 = self.photons[0].quantum_state
                key_1 = self.photons[1].quantum_state
                state_0 = self.timeline.quantum_manager.get(key_0)
                state_1 = self.timeline.quantum_manager.get(key_1)
                other_keys_0 = state_0.keys[:]
                other_keys_1 = state_1.keys[:]
                other_keys_0.remove(key_0)
                other_keys_1.remove(key_1)
                assert len(other_keys_0) == 1 and len(other_keys_1) == 1

                # set to Psi+ state
                combined = other_keys_0 + other_keys_1
                self.timeline.quantum_manager.set(combined, BSM._psi_plus)

    def trigger(self, detector: Detector, info: dict[str, Any]):
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



class SingleHeraldedBSM(BSM):
    """Class modeling an abstract/simplified BSM device for single-heralded entanglement generation protocols.

    We assume that in the single-heralded entanglement generation protocols,
        two memories each emit one photon entangled with memory state,
        EG is successful only if both photons arrive at the BSM, 
        and conditioned on both arrivals there is 1/2 probability (assuming linear optics)
        that the BSM can give distinguishable output,
        in the end whether successful EG is heralded still depends on detection (efficiency / dark counts).

    In this relatively simplified model, we do not perform explicit measurement and communicate explicit outcome, 
        but assume that local correction based on classical feedforward is a ``free'' operation,
        and successfully generated EPR pair is in Phi+ form.
    This is to be aligned with analytical formulae, and note that the 4 BDS elements are in I, Z, X, Y order.
    The device manages entanglement of associated memories.

    Attributes:
        name (str): label for BSM instance.
        timeline (Timeline): timeline for simulation.
        detectors (list[Detector]): list of attached photon detection devices.
        resolution (int): maximum time resolution achievable with attached detectors.
    """

    def __init__(self, name: str, timeline: "Timeline", phase_error: float = 0, detectors: list[dict] = None, success_rate: float = 0.5):
        """Constructor for the single atom BSM class.

        Args:
            name (str): name of the BSM instance.
            timeline (Timeline): simulation timeline.
            phase_error (float): phase error applied to polarization qubits (unused) (default 0).
            detectors (list[dict]): list of parameters for attached detectors, in dictionary format; must be of length 2
                (default is None for default parameters).
        """

        if detectors is None:
            detectors = [{}, {}]
        else:
            assert len(detectors) == 2, f"length of detectors = {len(detectors)}, must be 2"
        super().__init__(name, timeline, phase_error, detectors)
        self.encoding = "single_heralded"
        assert len(self.detectors) == 2
        self.success_rate = success_rate

    def get(self, photon, **kwargs):
        """See base class.

        This method adds additional side effects not present in the base class.
        This implementation specifically is based on expectation that if both photons arrive at the BSM simultaneously,
            they will trigger both detectors simultaneously as well, if both succeed given detector efficiency,
            and then we can record both detection events in bsm_res of entanglement generation protocol,
            when update_memory is invoked at future_start_time both detector triggers should have been recorded.

        Side Effects:
            May call get method of one or more attached detector(s).
            May alter the quantum state of memories corresponding to the photons.
        """

        super().get(photon)
        log.logger.debug(self.name + " received photon")

        # assumed simultaneous arrival of both photons
        if len(self.photons) == 2:
            # at most 1/2 probability of success according to LO assumption
            if self.get_generator().random() > self.success_rate:
                log.logger.debug(f'{self.name}: photonic BSM failed')
            else:
                p0, p1 = self.photons
                # if both memory successfully emit the photon in this round (consider memory emission inefficiency)
                if self.get_generator().random() > p0.loss and self.get_generator().random() > p1.loss:
                    for idx, photon in enumerate(self.photons):
                        detector = self.detectors[idx]
                        detector.get(photon)
                else:
                    log.logger.debug(f'{self.name}: photon lost (memory or optical fiber)')

    def trigger(self, detector: Detector, info: dict[str, Any]):
        """See base class.

        This method adds additional side effects not present in the base class.

        We assume that the single-heralded EG requires both incoming photons be detected,
            thus two detector triggers are needed.
        We will thus store the first trigger and see if there will be a second trigger.
        Only when a trigger happens and there has been a trigger existing do we notify (bsm_update) the EG protocol.
        TODO: verify that in this way we can record if dark count has happened.

        Side Effects:
            May send a further message to any attached entities.
        """

        detector_num = self.detectors.index(detector)
        time = info["time"]

        res = detector_num
        info = {'entity': 'BSM', 'info_type': 'BSM_res', 'res': res, 'time': time}
        self.notify(info)

