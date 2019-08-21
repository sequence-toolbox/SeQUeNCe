"""
Network Topology:

(ALICE)===(CHARLIE)===(BOB)

ALICE:
    Detector

CHARLIE:
    2 SPDC Sources
    BSM
    2 Quantum Memories

BOB:
    Detector
"""

from sequence import encoding
from sequence.process import Process
from sequence.entity import Entity
from sequence.event import Event
from sequence.timeline import Timeline
from sequence import topology


# Protocol
class Swap(Entity):
    def __init__(self, name, timeline, **kwargs):
        super().__init__(name, timeline)
        self.classical_delay = 0
        self.quantum_delay = 0
        self.start_time = 0
        self.light_time = 0
        self.node = None
        self.parent = None
        self.another_alice = None
        self.another_bob = None
        self.another_charlie = None
        self.sample_size = 0

    def init(self):
        pass

    def assign_node(self, node):
        self.node = node
        cchannel = node.components.get("cchannel")
        qchannel = node.components.get("qchannel")
        if cchannel is not None:
            self.classical_delay = cchannel.delay
        if qchannel is not None:
            self.quantum_delay = int(round(qchannel.distance / qchannel.light_speed))

    def received_message(self):
        pass

    def start_protocol(self, sample_size):
        # assert that start_protocol is called from Charlie (middle node)
        assert self.another_charlie is None

        self.another_alice.sample_size = sample_size
        self.another_bob.sample_size = sample_size

        # notify Alice and Bob that we are starting entanglement swap


if __name__ == "__main__":
    tl = Timeline()

    # Channels
    qc_alice_charlie = topology.QuantumChannel("qc_ac", tl)
    qc_bob_charlie = topology.QuantumChannel("qc_bc", tl)
    cc_alice_charlie = topology.ClassicalChannel("cc_ac", tl)
    cc_bob_charlie = topology.ClassicalChannel("cc_bc", tl)

    # Alice
    spdc_alice = topology.SPDCSource("alice.ls", tl)
    bsm_alice = topology.BSM("alice.bsm", tl)
    detector_alice = topology.QSDetector("alice.qsd", tl)
    alice = topology.Node("alice", tl)

    # Bob
    spdc_bob = topology.SPDCSource("bob.ls", tl)
    bsm_bob = topology.BSM("bob.bsm", tl)
    detector_bob = topology.QSDetector("bob.qsd", tl)
    bob = topology.Node("bob", tl)

    # Charlie
    spdc_charlie_1 = topology.SPDCSource("charlie.ls_1", tl)
    spdc_charlie_2 = topology.SPDCSource("charlie.ls_2", tl)
    bsm_charlie = topology.BSM("charlie.bsm", tl)
    mem_charlie_1 = topology.Memory("charlie.mem_1", tl)
    mem_charlie_2 = topology.Memory("charlie.mem_2", tl)
    charlie = topology.Node("charlie", tl)
