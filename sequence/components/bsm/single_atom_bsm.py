from typing import Any

from .base import BSM
from ..circuit import Circuit
from ..detector.base import Detector
from ...kernel.quantum_manager import KET_STATE_FORMALISM, DENSITY_MATRIX_FORMALISM, QuantumManager
from ...utils import log

from numpy import outer, add, zeros, array_equal

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
                        _set_state_with_fidelity(keys, BSM._psi_minus, p0.encoding_type["raw_fidelity"],
                                                 self.get_generator(), qm)
                    else:
                        _set_state_with_fidelity(keys, BSM._psi_plus, p0.encoding_type["raw_fidelity"],
                                                 self.get_generator(), qm)
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