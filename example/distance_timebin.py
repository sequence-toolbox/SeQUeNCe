import statistics

import pandas as pd
from sequence.components.optical_channel import ClassicalChannel, QuantumChannel
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.kernel.timeline import Timeline
from sequence.protocol import StackProtocol
from sequence.qkd.BB84 import pair_bb84_protocols
from sequence.topology.node import QKDNode, Node
from sequence.utils.encoding import time_bin


# dummy parent class to receive BB84 keys and initiate BB84
class Parent(StackProtocol):
    def __init__(self, own: "Node", keysize: int, role: str):
        super().__init__(own, "")
        self.upper_protocols = []
        self.lower_protocols = []
        self.keysize = keysize
        self.role = role

    def init(self):
        pass

    def pop(self, info):
        pass

    def push(self):
        self.lower_protocols[0].push(self.keysize, 10)

    def received_message(self, src, msg):
        pass


if __name__ == "__main__":
    runtime = 1e12
    keysize = 256
    distances = [1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]  # distances in km
    errors = []  # store error rates
    throughputs = []  # store throughputs


    for distance in distances:
        tl = Timeline(runtime)
        tl.show_progress = True

        qc0 = QuantumChannel("qc0", tl, distance=distance * 1e3, polarization_fidelity=0.97, attenuation=0.0002)
        qc1 = QuantumChannel("qc1", tl, distance=distance * 1e3, polarization_fidelity=0.97, attenuation=0.0002)
        cc0 = ClassicalChannel("cc0", tl, distance=distance * 1e3)
        cc1 = ClassicalChannel("cc1", tl, distance=distance * 1e3)

        # Alice
        ls_params = {"frequency": 80e6, "mean_photon_num": 0.1}
        alice = QKDNode("alice", tl, encoding=time_bin, stack_size=1)
        alice.set_seed(0)

        for name, param in ls_params.items():
            alice.update_lightsource_params(name, param)

        # Bob
        detector_params = [{"efficiency": 0.8, "dark_count": 1, "time_resolution": 10},
                           {"efficiency": 0.8, "dark_count": 1, "time_resolution": 10},
                           {"efficiency": 0.8, "dark_count": 1, "time_resolution": 10}] 
        bob = QKDNode("bob", tl, encoding=time_bin, stack_size=1)
        bob.set_seed(1)

        for i in range(len(detector_params)):
            for name, param in detector_params[i].items():
                bob.update_detector_params(i, name, param)

        qc0.set_ends(alice, bob.name)
        qc1.set_ends(bob, alice.name)
        cc0.set_ends(alice, bob.name)
        cc1.set_ends(bob, alice.name)

        # BB84 config
        pair_bb84_protocols(alice.protocol_stack[0], bob.protocol_stack[0])

        # add parent protocol for monitoring
        pa = Parent(alice, keysize, "alice")
        pb = Parent(bob, keysize, "bob")
        alice.protocol_stack[0].upper_protocols.append(pa)
        pa.lower_protocols.append(alice.protocol_stack[0])
        bob.protocol_stack[0].upper_protocols.append(pb)
        pb.lower_protocols.append(bob.protocol_stack[0])

        process = Process(pa, "push", [])
        event = Event(0, process)
        tl.schedule(event)

        tl.init()
        tl.run()

        errors.append(statistics.mean(alice.protocol_stack[0].error_rates))
        throughputs.append(statistics.mean(alice.protocol_stack[0].throughputs))

        print("completed distance {}".format(distance))

    print("distances: {}".format(distances))
    print("error rates: {}".format(errors))
    print("throughputs (bit/s): {}".format(throughputs))

    log = {'Distance': distances, 'Error_rate': errors, 'Throughput': throughputs}
    df = pd.DataFrame(log)
    df.to_csv('distance_timebin.csv')
