from typing import Any

from .base import BSM
from ..detector.base import Detector


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