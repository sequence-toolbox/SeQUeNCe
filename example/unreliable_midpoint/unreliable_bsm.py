"""A single-heralded midpoint whose classical heralds may not match its photon
detections, for studies of unreliable classical channels.

The decision is taken once both photons have arrived, in the same draw order as
SingleHeraldedBSM.get, so with both probabilities zero the honest path is
unchanged. A round in which only one memory emitted (Memory.excite skips a
round when the previous photon has not cleared) reaches only one arrival and
gets no decision.
"""
from sequence.components.bsm import BSM, SingleHeraldedBSM
from .ledger import get_ledger


@BSM.register("unreliable_single_heralded")
class UnreliableSingleHeraldedBSM(SingleHeraldedBSM):
    """SingleHeraldedBSM with per-round false-positive and drop behaviour.

    Args:
        p_false_positive (float): probability, on a round with no real
            detection, of emitting a herald anyway.
        p_drop (float): probability, on a round with a real detection, of
            emitting no herald.
    """

    def __init__(self, name, timeline, phase_error=0, detectors=None,
                 success_rate=0.5, p_false_positive=0.0, p_drop=0.0):
        super().__init__(name, timeline, phase_error, detectors, success_rate)
        self.p_false_positive = float(p_false_positive)
        self.p_drop = float(p_drop)

    def _emit_herald(self, time):
        for res in (0, 1):
            self.notify({'entity': 'BSM', 'info_type': 'BSM_res',
                         'res': res, 'time': int(time)})

    def get(self, photon, **kwargs):
        BSM.get(self, photon)
        if len(self.photons) < 2:
            return
        now = self.timeline.now()
        gen = self.get_generator()
        ledger = get_ledger(self.timeline)

        detected = False
        if gen.random() <= self.success_rate:
            p0, p1 = self.photons
            if gen.random() > p0.loss and gen.random() > p1.loss:
                detected = True

        if detected:
            if self.p_drop > 0 and gen.random() < self.p_drop:
                ledger.dropped += 1
                return
            ledger.honest += 1
            for idx, ph in enumerate(self.photons):
                self.detectors[idx].get(ph)
            return

        if self.p_false_positive > 0 and gen.random() < self.p_false_positive:
            ledger.false_positive += 1
            ledger.mark_unbacked(self.owner.name, now)
            self._emit_herald(now)
