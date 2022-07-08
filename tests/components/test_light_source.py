from sequence.components.light_source import LightSource
from sequence.components.optical_channel import QuantumChannel
from sequence.kernel.timeline import Timeline
from sequence.topology.node import Node
from sequence.utils.encoding import polarization


class FakeNode(Node):
    def __init__(self, name, tl, ls):
        Node.__init__(self, name, tl)
        self.lightsource = ls
        self.lightsource.owner = self


def test_light_source():
    class Receiver(Node):
        def __init__(self, name, tl):
            Node.__init__(self, name, tl)
            self.log = []

        def receive_qubit(self, src: str, qubit) -> None:
            self.log.append((self.timeline.now(), src, qubit))

    tl = Timeline()
    FREQ, MEAN = 1e8, 0.1
    ls = LightSource("ls", tl, frequency=FREQ, mean_photon_num=MEAN)
    sender = FakeNode("sender", tl, ls)
    sender.set_seed(0)

    assert sender.lightsource.frequency == FREQ and sender.lightsource.mean_photon_num == MEAN

    receiver = Receiver("receiver", tl)
    qc = QuantumChannel("qc", tl, distance=1e5, attenuation=0)
    qc.set_ends(sender, receiver.name)
    state_list = []
    STATE_LEN = 1000
    for _ in range(STATE_LEN):
        basis = sender.get_generator().integers(2)
        bit = sender.get_generator().integers(2)
        state_list.append(polarization["bases"][basis][bit])

    tl.init()
    ls.emit(state_list, "receiver")
    tl.run()

    assert (len(receiver.log) / STATE_LEN) - MEAN < 0.1
    for time, src, qubit in receiver.log:
        index = int(qubit.name)
        assert state_list[index] == qubit.quantum_state.state
        assert time == index * (1e12 / FREQ) + qc.delay
        assert src == "sender"
