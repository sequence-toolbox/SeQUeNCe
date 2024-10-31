import random
from sequence.kernel.timeline import Timeline
from sequence.components.optical_channel import QuantumChannel
from sequence.protocol import Protocol
from sequence.topology.node import Node
from sequence.components.light_source import LightSource
from sequence.utils.encoding import absorptive, single_atom
from sequence.components.photon import Photon
from sequence.kernel.entity import Entity
from typing import List, Callable, TYPE_CHECKING
from abc import ABC, abstractmethod
from sequence.components.memory import Memory
from sequence.utils.encoding import fock
import math
from sequence.kernel.event import Event
from sequence.kernel.process import Process
import sequence.utils.log as log
import matplotlib.pyplot as plt
from example.Transducer_Examples.TransductionComponent import Transducer
from example.Transducer_Examples.TransductionComponent import FockDetector
from example.Transducer_Examples.TransductionComponent import Transmon
from example.Transducer_Examples.TransductionComponent import Counter
from example.Transducer_Examples.TransductionComponent import FockBeamSplitter

from sequence.components.detector import Detector

from example.Transducer_Examples.SwappingProtocols import UpConversionProtocolEntangle
from example.Transducer_Examples.SwappingProtocols import Swapping
from example.Transducer_Examples.SwappingProtocols import Measure

from sequence.kernel.quantum_manager import QuantumManager
import sequence.components.circuit as Circuit


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
SWAPPING_DUARTION = 10 # ps
MEASURE_DURATION = 10 # ps
PERIOD = ENTANGLEMENT_GENERATION_DURATION + SWAPPING_DUARTION + MEASURE_DURATION + EMISSION_DURATION

#Transmon
ket1 = (0.0 + 0.0j, 1.0 + 0.0j) 
ket0 = (1.0 + 0.0j, 0.0 + 0.0j) 
state_list= [ket1, ket0] 
TRANSMON_EFFICIENCY = 1


# Transducer
EFFICIENCY_UP = 0.8

# Fock Detector
MICROWAVE_DETECTOR_EFFICIENCY_Rx = 1
MICROWAVE_DETECTOR_EFFICIENCY_Tx = 1
OPTICAL_DETECTOR_EFFICIENCY = 1

# Channel
ATTENUATION = 0
DISTANCE = 1e3




class EmittingProtocol(Protocol):

    "Protocol for emission of single microwave photon by transmon"

    def __init__(self, own: "Node", name: str, tl: "Timeline", transmon="Transmon", transducer="Transducer"):
        super().__init__(own, name)
        self.owner = own
        self.name = name
        self.tl = tl
        self.transmon = transmon
        self.transducer = transducer


    def start(self) -> None:

        self.transducer.photon_counter += 1 
            
        print(f"Microwave photons emitted by the Transmon at Tx: {self.transducer.photon_counter}")


    def received_message(self, src: str, msg):
        pass




class UpConversionProtocol(Protocol):
    def __init__(self, own: "Node", name: str, tl: "Timeline", transducer: "Transducer", node: "Node", transmon: "Transmon"):
        super().__init__(own, name)
        self.owner = own
        self.name = name
        self.tl = tl
        self.transducer = transducer
        self.transmon = transmon
        self.node = node


    def start(self, photon: "Photon") -> None:
        

        #print(f"Trasduduttore receiver[0] {self.transducer._receivers[0]}")
        #print(f"Transduttore receiver[1] {self.transducer._receivers[1]}")  

        if self.transducer.photon_counter > 0:

            if random.random() < self.transducer.efficiency:
                self.transducer._receivers[0].receive_photon(self.node, photon)
                print("Successful up-conversion")
            else:
                self.transducer._receivers[1].receive_photon_from_transducer(photon)
                print("FAILED up-conversion")
        else:
            print("No photon to up-convert")

    def received_message(self, src: str, msg):
        pass


# NODES OF THE NETWORK

class SenderNode(Node):
    def __init__(self, name, timeline, node2):
        super().__init__(name, timeline)

        self.transmon0_name = name + ".transmon0"
        transmon0 = Transmon(name=self.transmon0_name, owner=self, timeline=timeline, wavelength=[MICROWAVE_WAVELENGTH, OPTICAL_WAVELENGTH], photon_counter=0, efficiency=1, photons_quantum_state= state_list)
        self.add_component(transmon0)
        self.set_first_component(self.transmon0_name)

        self.transducer_name = name + ".transducer"
        transducer = Transducer(name=self.transducer_name, owner=self, timeline=timeline, efficiency=EFFICIENCY_UP)
        self.add_component(transducer)
        transducer.attach(self)
        transducer.photon_counter = 0
        self.counter = Counter()
        transducer.attach(self.counter)
        self.set_first_component(self.transducer_name)

        transmon0.add_receiver(transducer)

        self.transmon_name = name + ".transmon"
        transmon = Transmon(name=self.transmon_name, owner=self, timeline=timeline, wavelength=[MICROWAVE_WAVELENGTH, OPTICAL_WAVELENGTH], photon_counter=0, efficiency=1, photons_quantum_state= state_list)
        self.add_component(transmon)
        self.set_first_component(self.transmon_name)

        transducer.add_output([node2, transmon])

        self.emitting_protocol = EmittingProtocol(self, name + ".emitting_protocol", timeline, transmon0, transducer)
        self.upconversion_protocol = UpConversionProtocol(self, name + ".upconversion_protocol", timeline, transducer, node2, transmon)


class EntangleNode(Node):
    def __init__(self, name, timeline, src_list: List[str]):
        super().__init__(name, timeline)

        # Hardware setup
        self.fock_beam_splitter_name = name + ".FockBeamSplitter"
        fock_beam_splitter = FockBeamSplitter(name=self.fock_beam_splitter_name, owner=self, timeline=timeline, efficiency=0.5, photon_counter=0, src_list=src_list)        
        self.add_component(fock_beam_splitter)
        self.set_first_component(self.fock_beam_splitter_name)

        detector_name = name + ".detector1"
        detector = FockDetector(detector_name, timeline, efficiency=0.25)
        self.add_component(detector)
        self.set_first_component(detector_name)

        detector_name2 = name + ".detector2"
        detector2 = FockDetector(detector_name2, timeline, efficiency=0.25)
        self.add_component(detector2)
        self.set_first_component(detector_name2)

        fock_beam_splitter.add_output([detector, detector2])

        self.counter = Counter()
        self.counter2 = Counter()

        detector.attach(self.counter)
        detector2.attach(self.counter2)
        
        self.swapping_protocol = Swapping(self, name + ".swapping_protocol", timeline, fock_beam_splitter)
        self.measure_protocol = Measure(self, name + ".measure_protocol", timeline, fock_beam_splitter)

    def receive_photon(self, photon, src_list):
        self.components[self.fock_beam_splitter_name].receive_photon_from_scr(photon, src_list)


if __name__ == "__main__":
    runtime = 10e12
    tl = Timeline(runtime)

    nodoprimo_name = "Nodoo1"
    nodoterzo_name = "Nodoo3"

    src_list = [nodoprimo_name, nodoterzo_name]


    node2 = EntangleNode("node2", tl, src_list)
    node1 = SenderNode(nodoprimo_name, tl, node2)
    node3 = SenderNode(nodoterzo_name, tl, node2)

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

    print(f"--------------------")

    for trial in range(NUM_TRIALS): 
        print(f"--------------------")
        print(f"Trial {trial}:")

        tl.run()
        
        #Node1 and Node3
        transducer = node1.get_components_by_type("Transducer")[0]
        transducer_count = transducer.photon_counter
        transducer2 = node3.get_components_by_type("Transducer")[0]
        transducer2_count = transducer2.photon_counter
        transmon0 = node1.get_components_by_type("Transmon")[0]
        transmon_count = transmon0.photon_counter  
        transmon = node1.get_components_by_type("Transmon")[1]
        transmon_count = transmon.photon_counter  


        #Node2
        fock_beam_splitter = node2.get_components_by_type("FockBeamSplitter")[0]
        fock_beam_splitter_count = fock_beam_splitter.photon_counter
        detector1 = node2.get_components_by_type("FockDetector")[0]
        detector1_count = detector1.photon_counter
        detector1_count2 = detector1.photon_counter2
        detector2 = node2.get_components_by_type("FockDetector")[1]
        detector2_count = detector2.photon_counter
        detector2_count2 = detector2.photon_counter2



        #Process scheduling

        process0 = Process(node1.emitting_protocol, "start", [])
        event_time0 = (cumulative_time+EMISSION_DURATION) 
        event0 = Event(event_time0, process0)
        tl.schedule(event0)

        process2 = Process(node3.emitting_protocol, "start", []) 
        event2 = Event(event_time0, process2)
        tl.schedule(event2)

        process1 = Process(node1.upconversion_protocol, "start", [Photon]) 
        event_time1 = event_time0 + ENTANGLEMENT_GENERATION_DURATION
        event1 = Event(event_time1, process1)
        tl.schedule(event1)

        process3 = Process(node3.upconversion_protocol, "start", [Photon]) 
        event3 = Event(event_time1, process3)
        tl.schedule(event3)

        process4 = Process(node2.swapping_protocol, "start", [Photon])
        event_time4 = event_time1 + SWAPPING_DUARTION
        event4 = Event(event_time4, process4)
        tl.schedule(event4)

        process5 = Process(node2.measure_protocol, "start", [Photon])
        event_time5 = event_time4 + MEASURE_DURATION
        event5 = Event(event_time5, process5)
        tl.schedule(event5)

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


    
#Plot

color_blu = '#0047AB'
color_red = '#FF0000'


plt.figure(figsize=(12, 6))
plt.plot(times, detector_photon_counters_real, 'o-', color='#FF00FF', label='Detector Photon Counter Real')
plt.plot(times, detector_photon_counters_ideal, 'o-', color='darkblue', label='Detector Photon Counter Ideal')
plt.xlabel(r"Time ($\mu$s)", fontsize=24)
plt.ylabel('Detector Photon Counters', fontsize=24)
plt.legend(fontsize=24)
plt.grid(True)
plt.title('Ideal vs Real Detector Photon Counters Count Over Time', fontsize=24, fontweight='bold')
plt.show()

plt.figure(figsize=(12, 6))
plt.plot(times, spd_reals, 'o-', color='#FF00FF', label='SPD Real')
plt.plot(times, spd_ideals, 'o-', color='darkblue', label='SPD Ideal')
plt.xlabel(r"Time ($\mu$s)", fontsize=24)
plt.ylabel('SPD Values', fontsize=24)
plt.legend(fontsize=24)
plt.grid(True)
plt.title('Ideal vs Real SPD Count Over Time', fontsize=24, fontweight='bold')
plt.show()



