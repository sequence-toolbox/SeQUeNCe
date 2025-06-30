from typing import TYPE_CHECKING, Any

from .base import QSDetector, Detector
from ..beam_splitter import BeamSplitter
from ..photon import Photon

if TYPE_CHECKING:
    from ...kernel.timeline import Timeline


class QSDetectorPolarization(QSDetector):
    """QSDetector to measure polarization encoded qubits.

    There are two detectors.
    Detectors[0] and detectors[1] are directly connected to the beamsplitter.

    Attributes:
        name (str): label for QSDetector instance.
        timeline (Timeline): timeline for simulation.
        detectors (list[Detector]): list of attached detectors (length 2).
        trigger_times (list[list[int]]): tracks simulation time of detection events for each detector.
        splitter (BeamSplitter): internal beamsplitter object.
    """

    def __init__(self, name: str, timeline: "Timeline"):
        QSDetector.__init__(self, name, timeline)
        for i in range(2):
            d = Detector(name + ".detector" + str(i), timeline)
            self.detectors.append(d)
            d.attach(self)
        self.splitter = BeamSplitter(name + ".splitter", timeline)
        self.splitter.add_receiver(self.detectors[0])
        self.splitter.add_receiver(self.detectors[1])
        self.trigger_times = [[], []]

        self.components = [self.splitter] + self.detectors

    def init(self) -> None:
        """Implementation of Entity interface (see base class)."""

        assert len(self.detectors) == 2
        super().init()

    def get(self, photon: "Photon", **kwargs) -> None:
        """Method to receive a photon for measurement.

        Forwards the photon to the internal polarization beamsplitter.

        Arguments:
            photon (Photon): photon to measure.

        Side Effects:
            Will call `get` method of attached beamsplitter.
        """

        self.splitter.get(photon)

    def get_photon_times(self):
        times = self.trigger_times
        self.trigger_times = [[], []]
        return times

    def set_basis_list(self, basis_list: list[int], start_time: int, frequency: float) -> None:
        self.splitter.set_basis_list(basis_list, start_time, frequency)

    def update_splitter_params(self, arg_name: str, value: Any) -> None:
        self.splitter.__setattr__(arg_name, value)
