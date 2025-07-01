from typing import Any

from .base import BSM
from ..detector.base import Detector
from ..photon import Photon


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