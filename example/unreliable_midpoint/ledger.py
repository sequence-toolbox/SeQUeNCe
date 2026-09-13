"""Record of which single-heralded rounds were backed by a real two-photon
detection at the midpoint, keyed by (midpoint node name, herald time).

Only unbacked heralds are recorded. A backed round writes nothing, so an honest
run does not touch the ledger and reproduces the library. The herald time joins
a delivery to the round that produced it: the midpoint emits at the photon
arrival time, which equals the end node's expected_time.
"""


class PhysicsLedger:
    """Timeline-level record of unbacked single-heralded rounds."""

    def __init__(self):
        self.unbacked = {}          # midpoint name -> set of herald times
        self.false_positive = 0     # counters, for the example's read-out
        self.dropped = 0
        self.honest = 0

    def mark_unbacked(self, midpoint, time):
        """Record that the midpoint emitted a herald with no real detection.

        Args:
            midpoint (str): name of the midpoint (BSM) node.
            time (int): herald time.
        """
        self.unbacked.setdefault(midpoint, set()).add(int(time))

    def is_unbacked(self, midpoint, time):
        """Return whether a herald at this midpoint and time was unbacked.

        Args:
            midpoint (str): name of the midpoint node.
            time (int): herald time to check.

        Returns:
            bool: True if the herald was recorded as unbacked.
        """
        return int(time) in self.unbacked.get(midpoint, ())


def get_ledger(timeline):
    """Return the timeline's physics ledger, creating it once.

    Args:
        timeline (Timeline): the simulation timeline.

    Returns:
        PhysicsLedger: the ledger stored on the timeline.
    """
    if not hasattr(timeline, "physics_ledger"):
        timeline.physics_ledger = PhysicsLedger()
    return timeline.physics_ledger
