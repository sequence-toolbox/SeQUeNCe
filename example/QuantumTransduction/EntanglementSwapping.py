"""Quantum transduction via entanglement swapping

NOTE: Work in progress
"""

import sys
sys.path.append('.')

from sequence.kernel.timeline import Timeline
from sequence.components.optical_channel import QuantumChannel
from sequence.topology.node import Node
from sequence.components.photon import Photon
from typing import List
from sequence.kernel.event import Event
from sequence.kernel.process import Process
import matplotlib.pyplot as plt
from sequence.components.transducer import Transducer
from sequence.components.detector import FockDetector
from sequence.components.transmon import Transmon
from sequence.components.beam_splitter import FockBeamSplitter2
from sequence.constants import KET0, KET1

from example.QuantumTransduction.SwappingProtocols import Swapping, Measure, EmittingProtocol, UpConversionProtocol


class Counter:
    def __init__(self):
        self.count = 0

    def trigger(self, detector, info):
        self.count += 1


# GENERAL
NUM_TRIALS = 50
FREQUENCY = 1e9
MICROWAVE_WAVELENGTH = 999308 # nm
OPTICAL_WAVELENGTH = 1550 # nm
MEAN_PHOTON_NUM = 1

# Timeline
START_TIME = 0
EMISSION_DURATION = 10 # ps
ENTANGLEMENT_GENERATION_DURATION = 10 #ps
SWAPPING_DUARTION = 1 # ps
MEASURE_DURATION = 9 # ps
PERIOD = ENTANGLEMENT_GENERATION_DURATION + SWAPPING_DUARTION + MEASURE_DURATION + EMISSION_DURATION

# Transmon
state_list= [KET1, KET0] 
TRANSMON_EFFICIENCY = 1

# Transducer
EFFICIENCY_UP = 0.5

# Fock Detector
MICROWAVE_DETECTOR_EFFICIENCY_Rx = 1
MICROWAVE_DETECTOR_EFFICIENCY_Tx = 1
OPTICAL_DETECTOR_EFFICIENCY = 1

# Channel
ATTENUATION = 0
DISTANCE = 1e3


# NODES OF THE NETWORK

class SenderNode(Node):
    """The end nodes.

    Attributes:
        transmon0_name (str): the name of the transmon that emits
        transducer_name (str): the name of the transducer
        transmon_name (str): the name of the transmon
        emitting_protocol (EmittingProtocol):
        upconversion_protocol (UpConversionProtocol):
    """
    def __init__(self, name, timeline, node2):
        super().__init__(name, timeline)

        self.transmon0_name = name + ".transmon0"
        transmon0 = Transmon(name=self.transmon0_name, owner=self, timeline=timeline, wavelengths=[MICROWAVE_WAVELENGTH, OPTICAL_WAVELENGTH], photon_counter=0, efficiency=1, photons_quantum_state= state_list)
        self.add_component(transmon0)

        self.transducer_name = name + ".transducer"
        transducer = Transducer(name=self.transducer_name, owner=self, timeline=timeline, efficiency=EFFICIENCY_UP)
        self.add_component(transducer)
        transducer.attach(self)
        transducer.photon_counter = 0
        self.counter = Counter()
        transducer.attach(self.counter)

        transmon0.add_receiver(transducer)

        self.transmon_name = name + ".transmon"
        transmon = Transmon(name=self.transmon_name, owner=self, timeline=timeline, wavelengths=[MICROWAVE_WAVELENGTH, OPTICAL_WAVELENGTH], photon_counter=0, efficiency=1, photons_quantum_state= state_list)
        self.add_component(transmon)

        transducer.add_outputs([node2, transmon])  # NOTE node2 shouldn't be receiver, the quantum channel is skipped

        self.emitting_protocol = EmittingProtocol(self, name + ".emitting_protocol", timeline, transmon0, transducer)
        self.upconversion_protocol = UpConversionProtocol(self, name + ".upconversion_protocol", timeline, transducer, node2, transmon)


class EntangleNode(Node):
    """The node in the middle for entanglement swapping
    """
    def __init__(self, name, timeline, src_list: List[str]):
        super().__init__(name, timeline)

        # Hardware setup
        self.fock_beam_splitter_name = name + ".FockBeamSplitter"
        fock_beam_splitter = FockBeamSplitter2(name=self.fock_beam_splitter_name, owner=self, timeline=timeline, efficiency=0.5, photon_counter=0, src_list=src_list)        
        self.add_component(fock_beam_splitter)
        self.set_first_component(self.fock_beam_splitter_name)

        detector_name = name + ".detector1"
        detector = FockDetector(detector_name, timeline, efficiency=0.25)
        self.add_component(detector)

        detector_name2 = name + ".detector2"
        detector2 = FockDetector(detector_name2, timeline, efficiency=0.25)
        self.add_component(detector2)

        fock_beam_splitter.add_outputs([detector, detector2])

        self.counter = Counter()
        self.counter2 = Counter()

        detector.attach(self.counter)
        detector2.attach(self.counter2)
        
        self.swapping_protocol = Swapping(self, name + ".swapping_protocol", timeline, fock_beam_splitter)
        self.measure_protocol = Measure(self, name + ".measure_protocol", timeline, fock_beam_splitter)

    def receive_photon(self, photon: Photon, src_list: List[str]):
        self.components[self.fock_beam_splitter_name].receive_photon_from_scr(photon, src_list)



if __name__ == "__main__":
    runtime = 10e12
    tl = Timeline(runtime)

    node1_name = "Node1"
    node3_name = "Node3"
    src_list = [node1_name, node3_name]

    node2 = EntangleNode("node2", tl, src_list)
    node1 = SenderNode(node1_name, tl, node2)
    node3 = SenderNode(node3_name, tl, node2)

    qc1 = QuantumChannel("qc.node1.node2", tl, attenuation=ATTENUATION, distance=DISTANCE)
    qc2 = QuantumChannel("qc.node1.node3", tl, attenuation=ATTENUATION, distance=DISTANCE)
    qc1.set_ends(node1, node2.name)
    qc2.set_ends(node1, node3.name)

    tl.init()

    cumulative_time = START_TIME

    # List to store results
    times = []
    detector_photon_counters_real = []
    spd_reals = []
    detector_photon_counters_ideal = [] 
    spd_ideals = []
    total_emitted_photons = NUM_TRIALS  

    # Node1 and Node3
    transducer = node1.get_components_by_type("Transducer")[0]
    transducer_count = transducer.photon_counter
    transducer2 = node3.get_components_by_type("Transducer")[0]
    transducer2_count = transducer2.photon_counter
    transmon0 = node1.get_components_by_type("Transmon")[0]
    transmon_count = transmon0.photon_counter                   # NOTE transmon_count is not used anywhere
    transmon = node1.get_components_by_type("Transmon")[1]
    transmon_count = transmon.photon_counter  

    # Node2
    fock_beam_splitter = node2.get_components_by_type("FockBeamSplitter2")[0]
    fock_beam_splitter_count = fock_beam_splitter.photon_counter
    detector1 = node2.get_components_by_type("FockDetector")[0]
    detector1_count = detector1.photon_counter
    detector1_count2 = detector1.photon_counter2
    detector2 = node2.get_components_by_type("FockDetector")[1]
    detector2_count = detector2.photon_counter
    detector2_count2 = detector2.photon_counter2

    print(f"--------------------")

    for trial in range(NUM_TRIALS): 
        print(f"--------------------")
        print(f"Trial {trial}:")

        # Reset timeline
        tl.time = 0
        tl.init()

        # Reset counters
        transducer.photon_counter=0
        transducer2.photon_counter=0
        fock_beam_splitter.photon_counter = 0
        detector1.photon_counter = 0
        detector2.photon_counter = 0
        detector1.photon_counter2 = 0
        detector2.photon_counter2 = 0

        # Process scheduling
        # Node 1 & 3
        process0 = Process(node1.emitting_protocol, "start", [])
        event_time0 = (cumulative_time + EMISSION_DURATION) 
        event0 = Event(event_time0, process0)
        tl.schedule(event0)

        process2 = Process(node3.emitting_protocol, "start", []) 
        event2 = Event(event_time0, process2)
        tl.schedule(event2)

        process1 = Process(node1.upconversion_protocol, "start", [Photon])   # NOTE the parameter shouldn't be a class, it should be an object
        event_time1 = event_time0 + ENTANGLEMENT_GENERATION_DURATION
        event1 = Event(event_time1, process1)
        tl.schedule(event1)

        process3 = Process(node3.upconversion_protocol, "start", [Photon])   # NOTE the parameter shouldn't be a class, it should be an object
        event3 = Event(event_time1, process3)
        tl.schedule(event3)

        # Node 2
        process4 = Process(node2.swapping_protocol, "start", [Photon])   # NOTE the parameter shouldn't be a class, it should be an object
        event_time4 = event_time1 + SWAPPING_DUARTION
        event4 = Event(event_time4, process4)
        tl.schedule(event4)

        process5 = Process(node2.measure_protocol, "start", [Photon])   # NOTE the parameter shouldn't be a class, it should be an object
        event_time5 = event_time4 + MEASURE_DURATION
        event5 = Event(event_time5, process5)
        tl.schedule(event5)

        # run the simulation
        tl.run()

        detector_photon_counter_real = node2.measure_protocol.get_detector_photon_counter_real()
        spd_real = node2.measure_protocol.get_spd_real()
        detector_photon_counter_ideal =node2.measure_protocol.get_detector_photon_counter_ideal()
        spd_ideal = node2.measure_protocol.get_spd_ideal()

        print(f"CUMULATIVE: Detector photon counter with IDEAL (cumulative): {detector_photon_counter_ideal}")
        print(f"CUMULATIVE: SPD IDEAL: {spd_ideal}")

        print(f"CUMILATIVE Detector photon counter REAL : {detector_photon_counter_real}")
        print(f"CUMULATIVE SPD with eta NOT 1 REAL: {spd_real}")

        # Append results
        times.append(trial * PERIOD)  #Time for each trial
        detector_photon_counters_real.append(detector_photon_counter_real)
        spd_reals.append(spd_real)
        detector_photon_counters_ideal.append(detector_photon_counter_ideal)
        spd_ideals.append(spd_ideal)

        cumulative_time += PERIOD

    # Calculate and print the percentage of ideal detector counters
    percentage_detector_counters_ideal = (detector_photon_counter_ideal / total_emitted_photons) * 100
    print(f"Percentage of Entangled pairs generated (PHOTON COUNTER IDEAL): {percentage_detector_counters_ideal:.2f}%")
    
    percentage_spd_ideal= (spd_ideal / total_emitted_photons) * 100
    print(f"Percentage of Entangled detected by SPD IDEAL: {percentage_spd_ideal:.2f}%")

    percentage_detector_counters_real = (detector_photon_counter_real / total_emitted_photons) * 100
    print(f"Percentage of Entangled pairs detected by photon counter real: {percentage_detector_counters_real:.2f}%")
    
    percentage_spd_real= (spd_real / total_emitted_photons) * 100
    print(f"Percentage of Entangled detected by SPD real: {percentage_spd_real:.2f}%")



# Plot

color_blu = '#0047AB'
color_red = '#FF0000'


plt.figure(figsize=(12, 6))
plt.plot(times, detector_photon_counters_real, 'o-', color='#FF00FF', label='PCD Real')
plt.plot(times, detector_photon_counters_ideal, 'o-', color='darkblue', label='PCD Ideal')
plt.xlabel(r"Time ($\mu$s)", fontsize=32)
plt.ylabel('PCD Counts', fontsize=32)
plt.legend(fontsize=30)
plt.tick_params(axis='both', which='major', labelsize=28)  

plt.grid(True)
plt.title('Ideal vs Real PCD Counts Over Time', fontsize=32, fontweight='bold')
plt.show()

plt.figure(figsize=(12, 6))
plt.plot(times, spd_reals, 'o-', color='#FF00FF', label='SPD Real')
plt.plot(times, spd_ideals, 'o-', color='darkblue', label='SPD Ideal')
plt.xlabel(r"Time ($\mu$s)", fontsize=32)
plt.ylabel('SPD Counts', fontsize=32)
plt.legend(fontsize=30)
plt.tick_params(axis='both', which='major', labelsize=28)  

plt.grid(True)
plt.title('Ideal vs Real SPD Counts Over Time', fontsize=32, fontweight='bold')
plt.show()



