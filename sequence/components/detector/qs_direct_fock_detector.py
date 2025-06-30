from typing import TYPE_CHECKING

from .base import QSDetector, Detector

if TYPE_CHECKING:
    from ...kernel.timeline import Timeline

from numpy import eye, sqrt
from scipy.linalg import fractional_matrix_power
from math import factorial
from ..photon import Photon

class QSDetectorFockDirect(QSDetector):
    """QSDetector to directly measure photons in Fock state.

    Usage: to measure diagonal elements of effective density matrix.

    Attributes:
        name (str): label for QSDetector instance.
        timeline (Timeline): timeline for simulation.
        src_list (list[str]): list of two sources which send photons to this detector (length 2).
        detectors (list[Detector]): list of attached detectors (length 2).
        trigger_times (list[list[int]]): tracks simulation time of detection events for each detector.
        arrival_times (list[list[int]]): tracks simulation time of Photon arrival at each input port
    """

    def __init__(self, name: str, timeline: "Timeline", src_list: list[str]):
        super().__init__(name, timeline)
        assert len(src_list) == 2
        self.src_list = src_list

        for i in range(2):
            d = Detector(name + ".detector" + str(i), timeline)
            self.detectors.append(d)
        self.components = self.detectors

        self.trigger_times = [[], []]
        self.arrival_times = [[], []]

        self.povms = [None] * 4

    def init(self):
        self._generate_povms()
        super().init()

    def _generate_povms(self):
        """Method to generate POVM operators corresponding to photon detector having 0 and 1 click
        Will be used to generated outcome probability distribution.
        """

        # assume using Fock quantum manager
        truncation = self.timeline.quantum_manager.truncation
        create, destroy = self.timeline.quantum_manager.build_ladder()

        create0 = create * sqrt(self.detectors[0].efficiency)
        destroy0 = destroy * sqrt(self.detectors[0].efficiency)
        series_elem_list = [((-1)**i) * fractional_matrix_power(create0, i+1).dot(
            fractional_matrix_power(destroy0, i+1)) / factorial(i+1) for i in range(truncation)]
        povm0_1 = sum(series_elem_list)
        povm0_0 = eye(truncation+1) - povm0_1

        create1 = create * sqrt(self.detectors[1].efficiency)
        destroy1 = destroy * sqrt(self.detectors[1].efficiency)
        series_elem_list = [((-1) ** i) * fractional_matrix_power(create1, i + 1).dot(
            fractional_matrix_power(destroy1, i + 1)) / factorial(i + 1) for i in range(truncation)]
        povm1_1 = sum(series_elem_list)
        povm1_0 = eye(truncation + 1) - povm0_1

        self.povms = [povm0_0, povm0_1, povm1_0, povm1_1]

    def get(self, photon: "Photon", **kwargs):
        src = kwargs["src"]
        assert photon.encoding_type["name"] == "fock", "Photon must be in Fock representation."
        input_port = self.src_list.index(src)  # determine at which input the Photon arrives, an index

        # record arrival time
        arrival_time = self.timeline.now()
        self.arrival_times[input_port].append(arrival_time)

        key = photon.quantum_state  # the photon's key pointing to the quantum state in quantum manager
        samp = self.get_generator().random()  # random measurement sample
        if input_port == 0:
            result = self.timeline.quantum_manager.measure([key], self.povms[0:2], samp)
        elif input_port == 1:
            result = self.timeline.quantum_manager.measure([key], self.povms[2:4], samp)
        else:
            raise Exception("too many input ports for QSDFockDirect {}".format(self.name))

        assert result in list(range(len(self.povms))), "The measurement outcome is not valid."
        if result == 1:
            # trigger time recording will be done by SPD
            self.detectors[input_port].record_detection()

    def get_photon_times(self) -> list[list[int]]:
        trigger_times = self.trigger_times
        self.trigger_times = [[], []]
        return trigger_times

    # does nothing for this class
    def set_basis_list(self, basis_list: list[int], start_time: int, frequency: int) -> None:
        pass