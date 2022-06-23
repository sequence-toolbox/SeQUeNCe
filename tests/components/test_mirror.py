from random import randrange

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sequence.kernel.timeline import Timeline

from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.kernel.timeline import Timeline
from sequence.components.optical_channel import QuantumChannel
from sequence.topology.node import Node

from sequence.utils.encoding import *
from sequence.components.light_source import LightSource

from sequence.components.mirror import Mirror

NUM_TRIALS = 1000
FREQUENCY = 1e3
SEED = 1


class Counter:
    def __init__(self):
        self.count = 0

    def trigger(self, detector, info):
        self.count += 1


class EmittingNode(Node):
    def __init__(self, name, timeline):
        super().__init__(name, timeline)

        ls_name = name + ".ls"
        self.light_source = LightSource(ls_name, timeline, frequency=int(8e7), mean_photon_num=1)
        self.light_source.owner = self


class MiddleNode(Node):
    def __init__(self, name, timeline, mirror, receiver):
        super().__init__(name, timeline)
        self.mirror = mirror
        self.mirror.owner = self
        self.receiver = receiver

    def receive_qubit(self, src, qubit):
        # print("received something")
        if not qubit.is_null:
            self.mirror.get()

            if self.get_generator().random() < self.mirror.fidelity:
                process_photon = Process(self.mirror, "emit", [
                                         [qubit.quantum_state.state], self.receiver])

                time = self.timeline.now()
                period = int(round(1e12 / self.mirror.frequency))
                event = Event(time, process_photon)
                self.owner.timeline.schedule(event)
                time += period


class Receiver(Node):
    def __init__(self, name, tl):
        Node.__init__(self, name, tl)
        self.log = []

    def receive_qubit(self, src: str, qubit) -> None:
        self.log.append((self.timeline.now(), src, qubit))


def test_mirror():
    tl = Timeline()
    FID, FREQ, MEAN = 0.98, 8e7, 0.1

    sender = EmittingNode("sender", tl)
    receiver = Receiver("receiver", tl)
    mr = Mirror("mr", tl, fidelity=FID, frequency=8e7, mean_photon_num=MEAN)
    mid = MiddleNode("mid", tl, mr, receiver.name)
    mid.set_seed(SEED)

    assert mid.mirror.fidelity == FID
    assert mid.mirror.frequency == FREQ
    assert mid.mirror.mean_photon_num == MEAN

    qc1 = QuantumChannel("qc1", tl, distance=1e5, attenuation=0)
    qc2 = QuantumChannel("qc2", tl, distance=1e5, attenuation=0)
    qc1.set_ends(sender, mid.name)
    qc2.set_ends(mid, receiver.name)

    state_list = []
    STATE_LEN = 1000
    for _ in range(STATE_LEN):
        rng = mid.get_generator()
        basis = rng.integers(2)
        bit = rng.integers(2)
        state_list.append(polarization["bases"][basis][bit])

    tl.init()
    sender.light_source.emit(state_list, "mid")
    tl.run()

    assert abs((len(receiver.log) / STATE_LEN) - MEAN) < 0.1
    for time, src, qubit in receiver.log:
        index = int(qubit.name)
        assert state_list[index] == qubit.quantum_state.state
        assert time == index * (1e12 / FREQ) + qc1.delay + qc2.delay
        assert src == "sender"
