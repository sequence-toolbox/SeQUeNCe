from numpy import random
from sequence.components.light_source import LightSource
from sequence.kernel.timeline import Timeline
from sequence.utils.encoding import polarization

random.seed(0)


class Receiver:
    def __init__(self, timeline):
        self.timeline = timeline
        self.log = []

    def get(self, photon):
        self.log.append((self.timeline.now(), photon))


def test_light_source():
    tl = Timeline()
    FREQ, MEAN = 1e8, 0.1
    ls = LightSource("ls", tl, frequency=FREQ, mean_photon_num=MEAN)
    receiver = Receiver(tl)
    ls.add_receiver(receiver)

    state_list = []
    STATE_LEN = 1000
    for _ in range(STATE_LEN):
        basis = random.randint(2)
        bit = random.randint(2)
        state_list.append(polarization["bases"][basis][bit])

    tl.init()
    ls.emit(state_list)
    tl.run()

    assert (len(receiver.log) / STATE_LEN) - MEAN < 0.1
    for time, qubit in receiver.log:
        index = int(qubit.name)
        assert state_list[index] == qubit.quantum_state.state
        assert time == index * (1e12 / FREQ)
