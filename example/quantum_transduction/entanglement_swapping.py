"""Quantum transduction via entanglement swapping
"""

import sys
sys.path.append('.')
from fock_quantum_channel import FockQuantumChannel
from sequence.kernel.timeline import Timeline
from sequence.topology.node import Node
from sequence.components.photon import Photon
from sequence.kernel.event import Event
from sequence.kernel.process import Process
import matplotlib.pyplot as plt
from sequence.components.transducer import Transducer, UpConversionProtocol
from sequence.components.detector import FockDetector
from sequence.components.transmon import Transmon, EmittingProtocol
from sequence.components.beam_splitter import FockBeamSplitter2
from sequence.constants import KET0, KET1
from example.quantum_transduction.swapping_protocols import Swapping, Measure


class Counter:
    def __init__(self):
        self.count = 0

    def trigger(self, detector, info):
        self.count += 1


# GENERAL
NUM_TRIALS = 100


FREQUENCY = 1e9
MICROWAVE_WAVELENGTH = 999308 # nm
OPTICAL_WAVELENGTH = 1550 # nm
MEAN_PHOTON_NUM = 1

# Timeline
START_TIME = 0
#EMISSION_DURATION = 1 # ms
#ENTANGLEMENT_GENERATION_DURATION = 10 #ps
#SWAPPING_DUARTION = 1 # ps
MEASURE_DURATION = 0.00000001 # ms
PERIOD = 1 #ms
#PERIOD = ENTANGLEMENT_GENERATION_DURATION + SWAPPING_DUARTION + MEASURE_DURATION + EMISSION_DURATION

# Transmon
state_list= [KET1, KET0] 
TRANSMON_EFFICIENCY = 1

# Transducer
EFFICIENCY_UP = 0.1


# Fock Detector
OPTICAL_DETECTOR_EFFICIENCY = 0.25

# Channel
ATTENUATION = 0.95
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
    def __init__(self, name, timeline):    
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

        self.emitting_protocol = EmittingProtocol(self, name + ".emitting_protocol", timeline, transmon0, transducer)
        transducer.up_conversion_protocol = UpConversionProtocol(self, name + "up_conversion_protocol", timeline, transducer)
        
    

class EntangleNode(Node):
    """The node in the middle for entanglement swapping"""
    def __init__(self, name, timeline, src_list: list[str]):
        super().__init__(name, timeline)

        # Hardware setup
        self.fock_beam_splitter_name = name + ".FockBeamSplitter"
        fock_beam_splitter = FockBeamSplitter2(name=self.fock_beam_splitter_name, owner=self, timeline=timeline, efficiency=0.5, photon_counter=0, src_list=src_list)
        self.add_component(fock_beam_splitter)
        
        self.set_first_component(self.fock_beam_splitter_name)

        detector_name = name + ".detector1"
        detector = FockDetector(detector_name, timeline, efficiency=OPTICAL_DETECTOR_EFFICIENCY)
        self.add_component(detector)

        detector_name2 = name + ".detector2"
        detector2 = FockDetector(detector_name2, timeline, efficiency=OPTICAL_DETECTOR_EFFICIENCY)
        self.add_component(detector2)

        fock_beam_splitter.add_outputs([detector, detector2])

        self.counter = Counter()
        self.counter2 = Counter()

        detector.attach(self.counter)
        detector2.attach(self.counter2)
        
        self.swapping_protocol = Swapping(self, name + ".swapping_protocol", timeline, fock_beam_splitter)
        self.measure_protocol = Measure(self, name + ".measure_protocol", timeline, fock_beam_splitter)

        fock_beam_splitter.swapping_protocol = self.swapping_protocol

    
    def receive_qubit(self, src: str, photon: Photon):
        self.components[self.fock_beam_splitter_name].get(src, photon)

    


if __name__ == "__main__":
    runtime = 10e12
    tl = Timeline(runtime)

    node1 =SenderNode("node1", tl)
    node3 =SenderNode("node3", tl)
   
    qc1 = FockQuantumChannel("qc.node1.node2", tl, attenuation=ATTENUATION, distance=DISTANCE)
    qc2 = FockQuantumChannel("qc.node3.node2", tl, attenuation=ATTENUATION, distance=DISTANCE)
    
    src_list = [qc1, qc2]
    node2 = EntangleNode("node2", tl, src_list)

    qc1.set_ends(node1, node2)
    qc2.set_ends(node3, node2)

    print(f"First component name of Entangle Node {node2.first_component_name}")

    tl.init()

    cumulative_time = START_TIME

    # list to store results
    times = []
    detector_photon_counters_real = []
    spd_reals = []
    detector_photon_counters_ideal = [] 
    spd_ideals = []
    total_emitted_photons = NUM_TRIALS  

    # Node1 and Node3 (Sender nodes)
    
    transmon0 = node1.get_components_by_type("Transmon")[0]
    
    transducer = node1.get_components_by_type("Transducer")[0]
    transducer_count = transducer.photon_counter 
    
    transmon = node1.get_components_by_type("Transmon")[1]
    transmon_count = transmon.photon_counter 

    transmon0.add_receiver(transducer)
    transducer.add_outputs([qc1, transmon]) 

    transmon1 = node3.get_components_by_type("Transmon")[0]

    transducer2 = node3.get_components_by_type("Transducer")[0]
    transducer2_count = transducer2.photon_counter
    
    transmon2 = node3.get_components_by_type("Transmon")[1]
    transmon2_count = transmon2.photon_counter 

    transmon.add_receiver(transducer2)
    transducer2.add_outputs([qc2, transmon2]) 

    # Node2 (Entangle node)
    fock_beam_splitter = node2.get_components_by_type("FockBeamSplitter2")[0]
    fock_beam_splitter_count = fock_beam_splitter.photon_counter
   
    detector1 = node2.get_components_by_type("FockDetector")[0]   
    detector1_count = detector1.photon_counter
    detector1_count2 = detector1.photon_counter2
    
    detector2 = node2.get_components_by_type("FockDetector")[1]
    detector2_count = detector2.photon_counter
    detector2_count2 = detector2.photon_counter2

    print(f"--------------------")
    cumulative_detector_photon_counter_real = 0
    cumulative_spd_real = 0
    cumulative_detector_photon_counter_ideal = 0
    cumulative_spd_ideal = 0

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

        # Scheduling of the events
        process0 = Process(node1.emitting_protocol, "start", [])
        event_time0 = (cumulative_time) 
        event0 = Event(event_time0, process0)
        tl.schedule(event0)

        process2 = Process(node3.emitting_protocol, "start", []) 
        event2 = Event(event_time0, process2)
        tl.schedule(event2)

        process3 = Process(node2.measure_protocol, "start", [])
        event_time3 = (event_time0 + MEASURE_DURATION)
        event3 = Event(event_time3, process3)
        tl.schedule(event3)

        # run the simulation
        tl.run()

        detector_photon_counter_ideal = node2.measure_protocol.detector_photon_counter_ideal
        spd_ideal = node2.measure_protocol.spd_ideal
        detector_photon_counter_real = node2.measure_protocol.detector_photon_counter_real
        spd_real = node2.measure_protocol.spd_real

        print(f"Trial {trial} - Cumulative PNRD Ideal: {detector_photon_counter_ideal}")
        print(f"Trial {trial} - Cumulative SPD Ideal: {spd_ideal}")
        print(f"Trial {trial} - Cumulative PNRD Real: {detector_photon_counter_real}")
        print(f"Trial {trial} - Cumulative SPD Real: {spd_real}")

        # Append results
        times.append(trial * PERIOD)  # Time for each trial
        detector_photon_counters_real.append(detector_photon_counter_real)
        spd_reals.append(spd_real)
        detector_photon_counters_ideal.append(detector_photon_counter_ideal)
        spd_ideals.append(spd_ideal)

        cumulative_time += PERIOD

        
    # Calculate and print the percentage of ideal detector counters
    percentage_detector_counters_ideal = (detector_photon_counter_ideal / total_emitted_photons) * 100
    print(f"Percentage of Entangled pairs generated (PNRD IDEAL): {percentage_detector_counters_ideal:.2f}%")
        
    percentage_detector_counters_real = (detector_photon_counter_real / total_emitted_photons) * 100
    print(f"Percentage of Entangled pairs detected by PNRD real: {percentage_detector_counters_real:.2f}%") 

    percentage_spd_ideal = (spd_ideal / total_emitted_photons) * 100
    print(f"Percentage of Entangled detected by SPD IDEAL: {percentage_spd_ideal:.2f}%")
          
    percentage_spd_real = (spd_real / total_emitted_photons) * 100
    print(f"Percentage of Entangled detected by SPD real: {percentage_spd_real:.2f}%")

    # Plot

    color_blu = '#0047AB'
    color_red = '#FF0000'

    plt.figure(figsize=(14, 7))

    # SPD (Single Photon Detector) counts
    plt.plot(times, spd_ideals, 'o-', color='darkblue', label='SPD Ideal', markersize=4)  # blu pieno
    plt.plot(times, spd_reals, 'o-', color='darkblue', markerfacecolor='white', label='SPD Real', markersize=4)  # blu vuoto

    # PNRD (Photon Number Resolving Detector) counts
    plt.plot(times, detector_photon_counters_ideal, 'o-', color='#FF00FF', label='PNRD Ideal', markersize=4)  # fucsia pieno
    plt.plot(times, detector_photon_counters_real, 'o-', color='#FF00FF', markerfacecolor='white', label='PNRD Real', markersize=4)  # fucsia vuoto

    # Labels and title
    plt.xlabel(r"Time ($\mu$s)", fontsize=32)
    plt.ylabel('Counts', fontsize=32)
    plt.title('Ideal vs Real Counts Over Time', fontsize=34, fontweight='bold')

    # Legend and grid
    plt.legend(fontsize=26)
    # plt.grid(True)

    # Tick size
    plt.tick_params(axis='both', which='major', labelsize=28)

    # Show the plot
    plt.show()
