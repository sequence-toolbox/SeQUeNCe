import math

from sequence.kernel.timeline import Timeline
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.components.memory import Memory
from sequence.components.optical_channel import QuantumChannel
from sequence.components.detector import Detector
from sequence.topology.node import Node


NUM_TRIALS = 1000
FREQUENCY = 1e3


class Counter():
    def __init__(self):
        self.count = 0

    def trigger(self, detector, info):
        self.count += 1


class SenderNode(Node):
    def __init__(self, name, timeline):
        super().__init__(name, timeline)
        self.memory = Memory(name + ".memory", tl, fidelity=1, frequency=0,
                             efficiency=1, coherence_time=0, wavelength=500)
        self.memory.owner = self


class ReceiverNode(Node):
    def __init__(self, name, timeline):
        super().__init__(name, timeline)
        self.detector = Detector(name + ".detector", tl, efficiency=1)
        self.detector.owner = self

    def receive_qubit(self, src, qubit):
        if not qubit.is_null:
            self.detector.get()


if __name__ == "__main__":
    runtime = 10e12 
    tl = Timeline(runtime)

    # nodes and hardware
    node1 = SenderNode("node1", tl)
    node2 = ReceiverNode("node2", tl)

    qc = QuantumChannel("qc", tl, attenuation=0, distance=1e3)
    qc.set_ends(node1, node2.name)

    # counter
    counter = Counter()
    node2.detector.attach(counter)

    # schedule events
    time_bin = int(1e12 / FREQUENCY)
    
    process1 = Process(node1.memory, "update_state", [[complex(math.sqrt(1/2)), complex(math.sqrt(1/2))]])
    process2 = Process(node1.memory, "excite", ["node2"])
    for i in range(NUM_TRIALS):
        event1 = Event(i * time_bin, process1)
        event2 = Event(i * time_bin + (time_bin / 2), process2)
        tl.schedule(event1)
        tl.schedule(event2)

    tl.init()
    tl.run()

    print("percent measured: {}%".format(100 * counter.count / NUM_TRIALS))

