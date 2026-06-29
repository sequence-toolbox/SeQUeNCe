from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sequence.kernel.timeline import Timeline

from sequence.kernel.timeline import Timeline
from sequence.topology.node import Node
from sequence.utils.encoding import *
from sequence.components.optical_channel import QuantumChannel
from sequence.components.light_source import LightSource
from sequence.components.mirror import Mirror


class EmittingNode(Node):
    def __init__(self, name, timeline, light_source):
        super().__init__(name, timeline)
        self.light_source = light_source
        self.light_source.owner = self
        light_source.add_receiver(self)

    def get(self, photon, **kwargs):
        self.send_qubit("mid", photon)


class MiddleNode(Node):
    def __init__(self, name, timeline, mirror):
        super().__init__(name, timeline)
        self.mirror = mirror
        self.mirror.owner = self

    def receive_qubit(self, src, qubit):
        self.mirror.get(qubit)


class Receiver(Node):
    def __init__(self, name, tl):
        Node.__init__(self, name, tl)
        self.log = []

    def receive_qubit(self, src: str, qubit) -> None:
        self.log.append((self.timeline.now(), src, qubit))


def test_mirror():
    STATE_LEN = 1000
    FIDELITY = 0.98
    LS_FREQ = 8e7
    MEAN = 0.1

    tl = Timeline()

    ls = LightSource("ls", tl, frequency=LS_FREQ, mean_photon_num=MEAN)
    sender = EmittingNode("sender", tl, ls)
    receiver = Receiver("receiver", tl)
    mr = Mirror("mr", tl, fidelity=FIDELITY, destination=receiver.name)
    mid = MiddleNode("mid", tl, mr)

    sender.set_seed(0)
    mid.set_seed(1)
    receiver.set_seed(2)

    assert mid.mirror.fidelity == FIDELITY

    qc1 = QuantumChannel("qc1", tl, distance=1e5, attenuation=0)
    qc2 = QuantumChannel("qc2", tl, distance=1e5, attenuation=0)
    qc1.set_ends(sender, mid.name)
    qc2.set_ends(mid, receiver.name)

    state_list = []
    rng = mid.get_generator()
    for _ in range(STATE_LEN):
        basis = rng.integers(2)
        bit = rng.integers(2)
        state_list.append(polarization["bases"][basis][bit])

    tl.init()
    sender.light_source.emit(state_list)
    tl.run()

    assert abs((len(receiver.log) / STATE_LEN) - (MEAN * FIDELITY)) < 0.1
    for time, src, qubit in receiver.log:
        index = int(qubit.name)
        assert state_list[index] == qubit.quantum_state.state
        assert time == index * (1e12 / LS_FREQ) + qc1.delay + qc2.delay
