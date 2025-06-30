from typing import TYPE_CHECKING

from .base import Detector
from ..photon import Photon
from ...utils.encoding import fock

if TYPE_CHECKING:
    from ...kernel.timeline import Timeline

class FockDetector(Detector):
    """Class modeling a Fock detector.

    A Fock detector can detect the number of photons in a given mode.

    See https://arxiv.org/abs/2411.11377

    Attributes:
        name (str): name of the detector
        timeline (Timeline): the simulation timeline
        efficiency (float): the efficiency of the detector
        wavelength (int): wave length in nm
        photon_counter (int): counting photon for the non-ideal detector
        photon_counter2 (int): counting photon for the ideal detector
    """

    def __init__(self, name: str, timeline: "Timeline", efficiency: float, wavelength: int = 0):
        super().__init__(name, timeline, efficiency)
        self.name = name
        self.photon_counter = 0
        self.photon_counter2 = 0
        self.wavelength = wavelength
        self.encoding_type = fock
        self.timeline = timeline
        self.efficiency = efficiency
        self.measure_protocol = None

    def init(self):
        pass

    def get(self, photon: Photon = None, **kwargs) -> None:
        """Not ideal detector, there is a chance for photon loss.

        Args:
            photon (Photon): photon
        """
        if self.get_generator().random() < self.efficiency:
            self.photon_counter += 1
            return self.photon_counter

    def get_2(self, photon: Photon = None, **kwargs) -> None:  # IDEAL
        """Ideal detector, no photon loss

        Args:
            photon (Photon): photon
        """
        self.photon_counter2 += 1
        return self.photon_counter2

    def getx2(self, photon: Photon = None, **kwargs) -> None:
        if self.get_generator().random() < self.efficiency:
            self.photon_counter += 1
        if self.get_generator().random() < self.efficiency:
            self.photon_counter += 1
        return self.photon_counter

    def get_2x2(self, photon: Photon = None, **kwargs) -> None:  # IDEAL
        self.photon_counter2 += 2
        return self.photon_counter2

    def measure(self, photon: Photon) -> None:
        self.detector_photon_counter_ideal = 0
        self.spd_ideal = 0
        self.detector_photon_counter_real = 0
        self.spd_real = 0

        if self.photon_counter2 == 1 or self.photon_counter2 == 1:
            self.detector_photon_counter_ideal += 1

        if self.photon_counter2 >= 1 or self.photon_counter2 >= 1:
            self.spd_ideal += 1

        if self.photon_counter == 1 or self.photon_counter == 1:
            self.detector_photon_counter_real += 1

        if self.photon_counter >= 1 or self.photon_counter >= 1:
            self.spd_real += 1

        return self.detector_photon_counter_ideal, self.spd_ideal, self.detector_photon_counter_real, self.spd_real

    def received_message(self, src: str, msg):
        pass