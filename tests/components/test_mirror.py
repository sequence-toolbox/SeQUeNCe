#IN DEVELOPMENT
from numpy import random
from sequence.components.mirror import Mirror
from sequence.components.optical_channel import QuantumChannel
from sequence.kernel.timeline import Timeline
from sequence.topology.node import Node
from sequence.utils.encoding import polarization

random.seed(0)

class FakeNode(Node):
    def __init__(self, name, tl, ls):
        Node.__init__(self, name, tl)
        self.mirror = ls
        self.mirror.owner = self


def test_mirror():
    # count rate
    count_rate = 1e11
    interval = 1e12 / count_rate
    mirror, parent, tl = create_mirror(efficiency=1, count_rate=count_rate)
    arrive_times = [0, 2 * interval, 4 * interval, 4.5 * interval, 5.1 * interval]
    expect_len = [1, 2, 3, 3, 4]
    for time, log_len in zip(arrive_times, expect_len):
        tl.time = time
        detector.get()
        assert len(parent.log) == log_len

    # time_resolution
    time_resolution = 233
    mirror, parent, tl = create_mirror(efficiency=1, count_rate=1e12, time_resolution=time_resolution)
    times = random.randint(0, 1e12, 100, dtype=np.int64)
    times.sort()
    for t in times:
        tl.time = t
        detector.get()
        assert parent.log[-1][1] % time_resolution == 0

    class Receiver(Node):
        def __init__(self, name, tl):
            Node.__init__(self, name, tl)
            self.log = []

        def receive_qubit(self, src: str, qubit) -> None:
            self.log.append((self.timeline.now(), src, qubit))

    tl = Timeline()
    FREQ, MEAN = 1e8, 0.1
    ls = Mirror("mr", tl, frequency=FREQ, mean_photon_num=MEAN)
    sender = FakeNode("sender", tl, ls)

    assert sender.mirror.frequency == FREQ and sender.mirror.mean_photon_num == MEAN

    receiver = Receiver("receiver", tl)
    qc = QuantumChannel("qc", tl, distance=1e5, attenuation=0)
    qc.set_ends(sender, receiver)
    state_list = []
    STATE_LEN = 1000
    for _ in range(STATE_LEN):
        basis = random.randint(2)
        bit = random.randint(2)
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
