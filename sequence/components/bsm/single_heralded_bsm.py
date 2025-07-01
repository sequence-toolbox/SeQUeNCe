from typing import Any

from .base import BSM
from ..detector.base import Detector
from ...utils import log

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...kernel.timeline import Timeline


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