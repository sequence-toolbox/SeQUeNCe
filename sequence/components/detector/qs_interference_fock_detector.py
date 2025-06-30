from typing import TYPE_CHECKING

from .base import QSDetector, Detector

if TYPE_CHECKING:
    from ...kernel.timeline import Timeline

from numpy import eye, sqrt, kron, exp
from math import factorial

from scipy.linalg import fractional_matrix_power


class QSDetectorFockInterference(QSDetector):
    """QSDetector with two input ports and two photon detectors behind beamsplitter.

    The detectors will physically measure the two beamsplitter output  photonic modes' Fock states, respectively.
    POVM operators which apply to pre-beamsplitter photonic state are used.
    NOTE: in the current implementation, to realize interference, we require that Photons arrive at both input ports
    simultaneously, and at most 1 Photon instance can be input at an input port at a time.

    Usage: to realize Bell state measurement (BSM) and to measure off-diagonal elements of the effective density matrix.

    Attributes:
        name (str): label for QSDetector instance.
        timeline (Timeline): timeline for simulation.
        src_list (list[str]): list of two sources which send photons to this detector (length 2).
        detectors (list[Detector]): list of attached detectors (length 2).
        phase (float): relative phase between two input optical paths.
        trigger_times (list[list[int]]): tracks simulation time of detection events for each detector.
        detect_info (list[list[dict]]): tracks detection information, including simulation time of detection events
            and detection outcome for each detector.
        arrival_times (list[list[int]]): tracks simulation time of arrival of photons at each input mode.

        temporary_photon_info (list[dict]): temporary list of information of Photon arriving at each input port.
            Specific to current implementation. At most 1 Photon's information will be recorded in a dictionary.
            When there are 2 non-empty dictionaries,
            e.g. [{"photon":Photon1, "time":arrival_time1}, {"photon":Photon2, "time":arrival_time2}],
            the entangling measurement will be carried out. After measurement, the temporary list will be reset.
    """

    def __init__(self, name: str, timeline: "Timeline", src_list: list[str], phase: float = 0):
        super().__init__(name, timeline)
        assert len(src_list) == 2
        self.src_list = src_list
        self.phase = phase

        for i in range(2):
            d = Detector(name + ".detector" + str(i), timeline)
            self.detectors.append(d)
        self.components = self.detectors

        self.trigger_times = [[], []]
        self.detect_info = [[], []]
        self.arrival_times = [[], []]
        self.temporary_photon_info = [{}, {}]

        self.povms = [None] * 4

    def init(self):
        self._generate_povms()
        super().init()

    def _generate_transformed_ladders(self):
        """Method to generate transformed creation/annihilation operators by the beamsplitter.

        Will be used to construct POVM operators.
        """

        truncation = self.timeline.quantum_manager.truncation
        identity = eye(truncation + 1)
        create, destroy = self.timeline.quantum_manager.build_ladder()
        phase = self.phase
        efficiency1 = sqrt(self.detectors[0].efficiency)
        efficiency2 = sqrt(self.detectors[1].efficiency)

        # Modified mode operators in Heisenberg picture by beamsplitter transformation
        # considering inefficiency and ignoring relative phase
        create1 = (kron(efficiency1*create, identity) + exp(1j*phase)*kron(identity, efficiency2*create)) / sqrt(2)
        destroy1 = create1.conj().T
        create2 = (kron(efficiency1*create, identity) - exp(1j*phase)*kron(identity, efficiency2*create)) / sqrt(2)
        destroy2 = create2.conj().T

        return create1, destroy1, create2, destroy2

    def _generate_povms(self):
        """Method to generate POVM operators corresponding to photon detector having 00, 01, 10 and 11 click(s).

        Will be used to generated outcome probability distribution.
        """

        # assume using Fock quantum manager
        truncation = self.timeline.quantum_manager.truncation
        create1, destroy1, create2, destroy2 = self._generate_transformed_ladders()

        # for detector1 (index 0)
        series_elem_list1 = [(-1)**i * fractional_matrix_power(create1, i+1).dot(
            fractional_matrix_power(destroy1, i+1)) / factorial(i+1) for i in range(truncation)]
        povm1_1 = sum(series_elem_list1)
        povm0_1 = eye((truncation+1) ** 2) - povm1_1
        # for detector2 (index 1)
        series_elem_list2 = [(-1)**i * fractional_matrix_power(create2, i+1).dot(
            fractional_matrix_power(destroy2, i+1)) / factorial(i+1) for i in range(truncation)]
        povm1_2 = sum(series_elem_list2)
        povm0_2 = eye((truncation+1) ** 2) - povm1_2

        # POVM operators for 4 possible outcomes
        # Note: povm01 and povm10 are relevant to BSM
        povm00 = povm0_1 @ povm0_2
        povm01 = povm0_1 @ povm1_2
        povm10 = povm1_1 @ povm0_2
        povm11 = povm1_1 @ povm1_2

        self.povms = [povm00, povm01, povm10, povm11]

    def get(self, photon, **kwargs):
        src = kwargs["src"]
        assert photon.encoding_type["name"] == "fock", "Photon must be in Fock representation."
        input_port = self.src_list.index(src)  # determine at which input the Photon arrives, an index
        # record arrival time
        arrival_time = self.timeline.now()
        self.arrival_times[input_port].append(arrival_time)
        # record in temporary photon list
        assert not self.temporary_photon_info[input_port], \
            "At most 1 Photon instance should arrive at an input port at a time."
        self.temporary_photon_info[input_port]["photon"] = photon
        self.temporary_photon_info[input_port]["time"] = arrival_time

        # judge if there have already been two input Photons arriving simultaneously
        dict0 = self.temporary_photon_info[0]
        dict1 = self.temporary_photon_info[1]
        # if both two dictionaries are non-empty
        if dict0 and dict1:
            assert dict0["time"] == dict1["time"], "To realize interference photons must arrive simultaneously."
            photon0 = dict0["photon"]
            photon1 = dict1["photon"]
            key0 = photon0.quantum_state
            key1 = photon1.quantum_state

            # determine the outcome
            samp = self.get_generator().random()  # random measurement sample
            result = self.timeline.quantum_manager.measure([key0, key1], self.povms, samp)

            assert result in list(range(len(self.povms))), "The measurement outcome is not valid."
            if result == 0:
                # no click for either detector, but still record the zero outcome
                # record detection information
                detection_time = self.timeline.now()
                info = {"time": detection_time, "outcome": 0}
                self.detect_info[0].append(info)
                self.detect_info[1].append(info)

            elif result == 1:
                # detector 1 has a click
                # trigger time recording will be done by SPD
                self.detectors[1].record_detection()
                # record detection information
                detection_time = self.timeline.now()
                info0 = {"time": detection_time, "outcome": 0}
                info1 = {"time": detection_time, "outcome": 1}
                self.detect_info[0].append(info0)
                self.detect_info[1].append(info1)

            elif result == 2:
                # detector 0 has a click
                # trigger time recording will be done by SPD
                self.detectors[0].record_detection()
                # record detection information
                detection_time = self.timeline.now()
                info0 = {"time": detection_time, "outcome": 1}
                info1 = {"time": detection_time, "outcome": 0}
                self.detect_info[0].append(info0)
                self.detect_info[1].append(info1)

            elif result == 3:
                # both detectors have a click
                # trigger time recording will be done by SPD
                self.detectors[0].record_detection()
                self.detectors[1].record_detection()
                # record detection information
                detection_time = self.timeline.now()
                info = {"time": detection_time, "outcome": 1}
                self.detect_info[0].append(info)
                self.detect_info[1].append(info)

            self.temporary_photon_info = [{}, {}]

        else:
            pass

        """
        # check if we have non-null photon
        if not photon.is_null:
            state = self.timeline.quantum_manager.get(photon.quantum_state)

            # if entangled, apply phase gate
            if len(state.keys) == 2:
                self.timeline.quantum_manager.run_circuit(self._circuit, state.keys)

            self.beamsplitter.get(photon)
        """

    def get_photon_times(self) -> list[list[int]]:
        """Method to get detector trigger times and detection information.
        Will clear `trigger_times` and `detect_info`.
        """
        trigger_times = self.trigger_times
        # detect_info = self.detect_info
        self.trigger_times = [[], []]
        self.detect_info = [[], []]
        # return trigger_times, detect_info
        return trigger_times

    # does nothing for this class
    def set_basis_list(self, basis_list: list[int], start_time: int, frequency: float) -> None:
        pass

    def set_phase(self, phase: float):
        self.phase = phase
        self._generate_povms()