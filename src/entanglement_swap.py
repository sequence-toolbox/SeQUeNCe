"""
Network Topology:

(ALICE)===(CHARLIE)===(BOB)

ALICE:
    SPDC Source
    BSM
    Detector

CHARLIE:
    2 SPDC Sources
    BSM
    2 Quantum Memories

BOB:
    SPDC Source
    BSM
    Detector
"""

from sequence import encoding
from sequence.process import Process
from sequence.entity import Entity
from sequence.event import Event
from sequence.timeline import Timeline
from sequence import topology


if __name__ == "__main__":
    tl = Timeline()

    # CHANNELS

    # ALICE
    spdc_alice = topology.SPDCSource("alice.ls", tl)
    bsm_alice = topology.BSM("alice.bsm", tl)
    detector_alice = topology.QSDetector("alice.qsd", tl)
    alice = topology.Node("alice", tl)

    # BOB
    spdc_bob = topology.SPDCSource("bob.ls", tl)
    bsm_bob = topology.BSM("bob.bsm", tl)
    detector_bob = topology.QSDetector("bob.qsd", tl)
    bob = topology.Node("bob", tl)

    # CHARLIE
    spdc_charlie_1 = topology.SPDCSource("charlie.ls_1", tl)
    spdc_charlie_2 = topology.SPDCSource("charlie.ls_2", tl)
    bsm_charlie = topology.BSM("charlie.bsm", tl)
    mem_charlie_1 = topology.Memory("charlie.mem_1", tl)
    mem_charlie_2 = topology.Memory("charlie.mem_2", tl)
    charlie = topology.Node("charlie", tl)
