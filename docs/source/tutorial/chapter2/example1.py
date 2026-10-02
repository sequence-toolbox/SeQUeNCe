import math

import sequence as sq
import sequence.utils.log as log

NUM_TRIALS = 1000
FREQUENCY = 1e3


class Counter:
    def __init__(self):
        self.count = 0

    def trigger(self, detector, info):
        self.count += 1


class Sender:
    def __init__(self, owner, memory_name):
        self.owner = owner
        self.memory = owner.components[memory_name]

    def start(self, period):
        process1 = sq.Process(self.memory, "update_state", [[complex(math.sqrt(1/2)), complex(math.sqrt(1/2))]])
        process2 = sq.Process(self.memory, "excite", ["node2"])
        for i in range(NUM_TRIALS):
            event1 = sq.Event(i * period, process1)
            event2 = sq.Event(i * period + (period / 10), process2)
            self.owner.timeline.schedule(event1)
            self.owner.timeline.schedule(event2)


class SenderNode(sq.Node):
    def __init__(self, name, timeline):
        super().__init__(name, timeline)
        memory_name = name + ".memory"
        memory = sq.Memory(memory_name, timeline, fidelity=1, frequency=0, efficiency=1, coherence_time=0, wavelength=500)
        self.add_component(memory)
        memory.add_receiver(self)

        self.sender = Sender(self, memory_name)

    def get(self, photon, **kwargs):
        self.send_qubit(kwargs['dst'], photon)


class ReceiverNode(sq.Node):
    def __init__(self, name, timeline):
        super().__init__(name, timeline)

        detector_name = name + ".detector"
        detector = sq.Detector(detector_name, timeline, efficiency=1)
        self.add_component(detector)
        self.set_first_component(detector_name)
        detector.owner = self

        self.counter = Counter()
        detector.attach(self.counter)

    def receive_qubit(self, src, qubit):
        self.components[self.first_component_name].get(qubit)


if __name__ == "__main__":

    runtime = 1e12
    tl = sq.Timeline(runtime)

    log_filename = 'chapter2_example1_log'
    log.set_logger(__name__, tl, log_filename)
    log.set_logger_level('DEBUG')
    modules = ['timeline']
    for module in modules:
        log.track_module(module)

    # nodes and hardware
    node1 = SenderNode("node1", tl)
    node2 = ReceiverNode("node2", tl)
    qc = sq.QuantumChannel("qc.node1.node2", tl, attenuation=0, distance=1e3)
    qc.set_ends(node1, node2.name)

    tl.init()

    # schedule events
    period = int(1e12 / FREQUENCY)
    print(f'period = {period:,} ps')
    node1.sender.start(period)

    tl.run()

    print("percent measured: {}%".format(100 * node2.counter.count / NUM_TRIALS))
