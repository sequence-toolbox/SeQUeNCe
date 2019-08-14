import numpy as np
import math

from teleportation import Teleportation, BSMAdapter
import topology
from timeline import Timeline
from process import Process
from event import Event
import encoding

if __name__ == "__main__":
    states = ["0", "1", "+", "-"]
    phase_error = 0.033
    sample_size = 100
    random_seeds = np.linspace(1, 10, 10)
    bases = [0, 1]

    for state in states:
        for basis in bases:
            for seed in random_seeds:
                np.random.seed(int(seed))

                if state == "0":
                    alice_state = [complex(1), complex(0)]
                elif state == "1":
                    alice_state = [complex(0), complex(1)]
                elif state == "+":
                    alice_state = [complex(math.sqrt(1 / 2)), complex(math.sqrt(1 / 2))]
                elif state == "-":
                    alice_state = [complex(math.sqrt(1 / 2)), complex(-math.sqrt(1 / 2))]
                else:
                    raise Exception("invalid state")

                if basis == 0:
                    bob_basis = "Z"
                elif basis == 1:
                    bob_basis = "X"
                else:
                    raise Exception("incorrect basis for Bob")

                alice_length = 6.2e3
                bob_length = 11.1e3

                # initialize timeline and channels
                tl = Timeline(math.inf)

                qc_ac = topology.QuantumChannel("qc_ac", tl, distance=alice_length, attenuation=0.000986)
                qc_bc = topology.QuantumChannel("qc_bc", tl, distance=bob_length, attenuation=0.000513)
                cc_ac = topology.ClassicalChannel("cc_ac", tl, distance=alice_length)
                cc_bc = topology.ClassicalChannel("cc_bc", tl, distance=bob_length)

                # Alice
                ls = topology.LightSource("alice.lightsource", tl,
                                          frequency=80e6, mean_photon_num=0.014, encoding_type=encoding.time_bin,
                                          direct_receiver=qc_ac, phase_error=0)
                components = {"lightsource": ls, "qchannel": qc_ac, "cchannel": cc_ac}

                alice = topology.Node("alice", tl, components=components)

                qc_ac.set_sender(ls)
                cc_ac.add_end(alice)

                # Bob
                internal_cable = topology.QuantumChannel("bob.internal_cable", tl,
                                                         distance=bob_length + 10, attenuation=0.0002)
                spdc = topology.SPDCSource("bob.lightsource", tl,
                                           frequency=80e6, mean_photon_num=0.045, encoding_type=encoding.time_bin,
                                           direct_receiver=qc_bc, another_receiver=internal_cable,
                                           wavelengths=[1532, 795],
                                           phase_error=0)
                # (change this to change measurement basis)
                if basis == 0:
                    detectors = [{"efficiency": 0.65, "dark_count": 100, "time_resolution": 100},
                                 None,
                                 None]
                elif basis == 1:
                    detectors = [None,
                                 {"efficiency": 0.65, "dark_count": 100, "time_resolution": 100},
                                 {"efficiency": 0.65, "dark_count": 100, "time_resolution": 100}]
                interferometer = {"path_difference": encoding.time_bin["bin_separation"]}
                switch = {"state": basis}
                qsd = topology.QSDetector("bob.qsdetector", tl,
                                          encoding_type=encoding.time_bin, detectors=detectors,
                                          interferometer=interferometer,
                                          switch=switch)
                internal_cable.set_sender(spdc)
                internal_cable.set_receiver(qsd)
                components = {"lightsource": spdc, "detector": qsd, "qchannel": qc_bc, "cchannel": cc_bc}

                bob = topology.Node("bob", tl, components=components)

                qc_bc.set_sender(spdc)
                cc_bc.add_end(bob)

                # Charlie
                detectors = [{"efficiency": 0.7, "dark_count": 100, "time_resolution": 150, "count_rate": 25000000},
                             {"efficiency": 0.7, "dark_count": 100, "time_resolution": 150, "count_rate": 25000000}]
                bsm = topology.BSM("charlie.bsm", tl,
                                   encoding_type=encoding.time_bin, detectors=detectors, phase_error=phase_error)
                a0 = BSMAdapter(tl, photon_type=0, bsm=bsm)
                a1 = BSMAdapter(tl, photon_type=1, bsm=bsm)
                components = {"bsm": bsm, "qc_a": qc_ac, "qc_b": qc_bc, "cc_a": cc_ac, "cc_b": cc_bc}
                charlie = topology.Node("charlie", tl, components=components)

                qc_ac.set_receiver(a0)
                qc_bc.set_receiver(a1)
                cc_ac.add_end(charlie)
                cc_bc.add_end(charlie)

                tl.entities.append(alice)
                tl.entities.append(bob)
                tl.entities.append(charlie)
                for key in alice.components:
                    tl.entities.append(alice.components[key])
                for key in bob.components:
                    tl.entities.append(bob.components[key])
                for key in charlie.components:
                    tl.entities.append(charlie.components[key])

                # Teleportation
                ta = Teleportation("ta", tl, role=0)
                tb = Teleportation("tb", tl, role=1)
                tc = Teleportation("tc", tl, role=2)

                ta.assign_node(alice)
                tb.assign_node(bob)
                tb.measurement_delay = int(round(internal_cable.distance / internal_cable.light_speed))
                tc.assign_node(charlie)
                tc.quantum_delay = int(round(qc_bc.distance / qc_bc.light_speed))

                ta.another_bob = tb
                ta.another_charlie = tc
                tb.another_alice = ta
                tb.another_charlie = tc
                tc.another_alice = ta
                tc.another_bob = tb

                alice.protocol = ta
                bob.protocol = tb
                charlie.protocol = tc

                # Run
                process = Process(ta, "send_state", [alice_state, sample_size])
                event = Event(0, process)
                tl.schedule(event)

                print("Sending {} qubits with parameters:".format(sample_size))
                print("\tRandom Seed: " + str(int(seed)))
                print("\tSent State: " + state)
                print("\tMeasurement Basis: " + bob_basis)
                tl.init()
                tl.run()
                print("\n")
