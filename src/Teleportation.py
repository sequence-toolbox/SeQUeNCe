import topology
from timeline import Timeline
from entity import Entity
from process import Process
from event import Event


class Teleportation(Entity):
    def __init__(self, name, timeline, **kwargs):
        super().__init__(name, timeline)
        self.role = kwargs.get("role", -1)

        self.quantum_delay = 0
        self.classical_delay = 0
        self.light_time = 0
        self.start_time = 0
        self.node = None
        self.parent = None
        self.another_bob = None
        self.another_charlie = None
        self.quantum_state = [complex(1), complex(0)]
        self.sample_size = 0

    def init(self):
        pass

    def assign_node(self, node):
        self.node = node
        cchannel = node.components.get("cchannel")
        qchannel = node.components.get("qchannel")
        self.classical_delay = cchannel.delay
        self.quantum_delay = int(round(qchannel.distance / qchannel.light_speed))

    def add_parent(self, parent):
        self.parent = parent

    def emit_photons(self, state, num_photons):
        # current node bob: send photons
        self.node.send_photons(state, num_photons, "lightsource")
        self.light_time = num_photons / self.node.components["lightsource"].frequency
        self.start_time = self.timeline.now()

        # tell charlie that we're sending photons
        self.node.send_message("sending_photons {} {}".format(self.start_time, self.light_time))

    def end_photons(self):
        res = self.node.components["bsm"].get_bsm_res()
        self.node.send_message("bsm_res {}".format(res), "cc_b")

    def received_message(self):
        message = self.node.message.split(" ")

        if message[0] == "sending_photons":  # (current node is Charlie): schedule sending of bsm measurements
            self.light_time = float(message[2])

            process = Process(self, "end_photons", [])
            event = Event(int(message[1]) + self.quantum_delay + round(self.light_time * 1e12), process)
            self.timeline.schedule(event)

        if message[0] == "bsm_res":  # (current node is Bob): get bits w/ bell state measure
            frequency = self.node.components["lightsource"].frequency
            bsm_res = [-1] * int(round(self.light_time * frequency))

            # calculate bit values
            # invert bits
            # calculate error

    def send_state(self, quantum_state, sample_size):
        self.quantum_state = quantum_state
        self.sample_size = sample_size
        self.another_bob.sample_size = sample_size
        lightsource = self.node.components["lightsource"]

        start_time = max(0, self.another_bob.quantum_delay - self.quantum_delay)
        bob_start_time = max(0, self.quantum_delay - self.another_bob.quantum_delay)

        # schedule self to emit photons
        num_photons = round(self.sample_size / lightsource.mean_photon_num)
        process = Process(self.node, "send_photons", [self.quantum_state, num_photons, "lightsource"])
        event = Event(start_time, process)
        self.timeline.schedule(event)

        # schedule bob to emit photons
        process = Process(self.another_bob, "emit_photons", [self.quantum_state, num_photons])
        event = Event(bob_start_time, process)
        self.timeline.schedule(event)


# TODO: find a better way to implement
class BSMAdapter(Entity):
    def __init__(self, timeline, **kwargs):
        super().__init__("", timeline)
        self.receiver = kwargs.get("bsm", None)
        self.photon_type = kwargs.get("photon_type", -1)

    def init(self):
        pass

    def get(self, photon):
        self.receiver.get(photon, self.photon_type)


if __name__ == "__main__":
    tl = Timeline(1e12)

    qc_ac = topology.QuantumChannel("qc_ac", tl)
    qc_bc = topology.QuantumChannel("qc_bc", tl)
    cc_ac = topology.ClassicalChannel("cc_ac", tl)
    cc_bc = topology.ClassicalChannel("cc_bc", tl)

    # Alice
    ls = topology.LightSource("alice.lightsource", tl)
    components = {"lightsource": ls, "qc": qc_ac, "cc": cc_ac}

    alice = topology.Node("alice", tl, components=components)

    qc_ac.set_sender(ls)
    cc_ac.add_end(alice)

    # Bob
    internal_cable = topology.QuantumChannel("bob.internal_cable", tl)  # for adding delay to detector
    spdc = topology.SPDCSource("bob.lightsource", tl)
    detector = topology.Detector(tl)
    components = {"lightsource": spdc, "detector": detector, "qc": qc_bc, "cc": cc_bc}

    bob = topology.Node("bob", tl, components=components)

    qc_bc.set_sender(spdc)
    cc_bc.add_end(bob)

    # Charlie
    bsm = topology.BSM("charlie.bsm", tl)
    a0 = BSMAdapter(tl, photon_type=0, bsm=bsm)
    a1 = BSMAdapter(tl, photon_type=1, bsm=bsm)
    components = {"bsm": bsm, "qc_a": qc_ac, "qc_b": qc_bc, "cc_a": cc_ac, "cc_b": cc_bc}
    charlie = topology.Node("charlie", tl, components=components)

    qc_ac.set_receiver(a0)
    qc_bc.set_receiver(a1)
    cc_ac.add_end(charlie)
    cc_bc.add_end(charlie)

