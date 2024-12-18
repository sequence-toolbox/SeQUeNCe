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
from example.Transducer_Examples.TransductionComponent import *

from example.Transducer_Examples.ConversionProtocols import EmittingProtocol
from example.Transducer_Examples.ConversionProtocols import UpConversionProtocol
from example.Transducer_Examples.ConversionProtocols import DownConversionProtocol

from sequence.kernel.quantum_manager import QuantumManager
import sequence.components.circuit as Circuit


#GENERAL

NUM_TRIALS = 50
FREQUENCY = 1e9
MICROWAVE_WAVELENGTH = 999308 # nm
OPTICAL_WAVELENGTH = 1550 # nm
MEAN_PHOTON_NUM=1

# Timeline
START_TIME = 0
EMISSION_DURATION = 10 # ps
CONVERSION_DURATION = 10 # ps
PERIOD = EMISSION_DURATION + CONVERSION_DURATION + CONVERSION_DURATION

#Transmon
ket1 = (0.0 + 0.0j, 1.0 + 0.0j) 
ket0 = (1.0 + 0.0j, 0.0 + 0.0j) 
state_list= [ket1, ket0] 
TRANSMON_EFFICIENCY = 1

# Transducer
EFFICIENCY_UP = 0.5
EFFICIENCY_DOWN = 0.5

# Fock Detector
MICROWAVE_DETECTOR_EFFICIENCY_Rx = 1
MICROWAVE_DETECTOR_EFFICIENCY_Tx = 1
OPTICAL_DETECTOR_EFFICIENCY = 1

# Channel
ATTENUATION = 0
DISTANCE = 1e3







#NODES OF THE NETWORK 


class SenderNode(Node):
    def __init__(self, name, timeline, node2):
        super().__init__(name, timeline)


        #Hardware setup

        self.transmon_name = name + ".transmon"
        transmon = Transmon(name=self.transmon_name, owner=self, timeline=timeline, wavelength=[MICROWAVE_WAVELENGTH, OPTICAL_WAVELENGTH], photon_counter=0, efficiency=TRANSMON_EFFICIENCY, photons_quantum_state= state_list)
        self.add_component(transmon)
        self.set_first_component(self.transmon_name)


        self.transducer_name = name + ".transducer"
        transducer = Transducer(name=self.transducer_name, owner=self, timeline=timeline, efficiency=EFFICIENCY_UP)
        self.add_component(transducer)
        transducer.attach(self)
        transducer.photon_counter = 0
        self.counter = Counter()
        transducer.attach(self.counter)
        self.set_first_component(self.transducer_name)


        transmon.add_receiver(transducer)


        detector_name = name + ".fockdetector1"
        detector = FockDetector(detector_name, timeline, wavelength=MICROWAVE_WAVELENGTH, efficiency=MICROWAVE_DETECTOR_EFFICIENCY_Tx)
        self.add_component(detector)
        self.set_first_component(detector_name)
        self.counter = Counter()
        detector.attach(self.counter)

        transducer.add_output([node2, detector])

        self.emitting_protocol = EmittingProtocol(self, name + ".emitting_protocol", timeline, transmon, transducer)
        self.upconversion_protocol = UpConversionProtocol(self, name + ".upconversion_protocol", timeline, transducer, node2, transmon)




class ReceiverNode(Node):
    def __init__(self, name, timeline):
        super().__init__(name, timeline)

        self.transducer2_name = name + ".transducer2"
        transducer2 = Transducer(name=self.transducer2_name, owner=self, timeline=timeline, efficiency=EFFICIENCY_DOWN)
        self.add_component(transducer2)
        transducer2.attach(self)
        transducer2.photon_counter = 0
        self.counter = Counter()
        transducer2.attach(self.counter)
        self.set_first_component(self.transducer2_name)

        detector2_name = name + ".fockdetector2"
        detector2 = FockDetector(detector2_name, timeline, wavelength=OPTICAL_WAVELENGTH, efficiency=OPTICAL_DETECTOR_EFFICIENCY)
        self.add_component(detector2)
        self.counter2 = Counter()
        detector2.attach(self.counter2)

        self.transmon_name2 = name + ".transmon2"
        transmon2 = Transmon(name=self.transmon_name2, owner=self, timeline=timeline, wavelength=[MICROWAVE_WAVELENGTH, OPTICAL_WAVELENGTH], photons_quantum_state= state_list, photon_counter=0, efficiency=1)
        self.add_component(transmon2)
        self.set_first_component(self.transmon_name2)
        
        transducer2.add_output([transmon2,detector2])
        print(f"Transducer2 output: {transducer2._receivers}")

        self.downconversion_protocol = DownConversionProtocol(self, name + ".downconversion_protocol", timeline, transducer2, transmon2)

    def receive_photon(self, src, photon):
        self.components[self.transducer2_name].receive_photon_from_channel(photon)


#MAIN

if __name__ == "__main__":

    runtime = 10e12
    tl = Timeline(runtime)
   
    node2 = ReceiverNode("node2", tl)
    node1 = SenderNode("node1", tl, node2)

    qc1 = QuantumChannel("qc.node1.node2", tl, attenuation=ATTENUATION, distance=DISTANCE)
    qc1.set_ends(node1, node2.name)

    if EFFICIENCY_UP >= 0 and EFFICIENCY_UP <= 1 and EFFICIENCY_DOWN >= 0 and EFFICIENCY_DOWN <= 1:
        pass
    else:
        print("Error: the efficiency must be between 0 and 1")
        exit(1)

    tl.init()

    total_photons_successful = 0
    total_transducer_count = 0
    

    #Plot1
    failed_up_conversions = []
    failed_down_conversions = []
    successful_conversions = [] 

    #Plot2
    ideal_photons = []
    emitted_photons = []  
    converted_photons = []
    

    cumulative_time = START_TIME
    
    print(f"--------------------")

    print(f"Direct Quantum Transduction Protocol starts, the qubit that we are going to convert is: {ket1}")
    
    for trial in range(NUM_TRIALS): 

        print(f"--------------------")
        print(f"Trial {trial}:")

        tl.run()


        #Node1
        transmon = node1.get_components_by_type("Transmon")[0]
        transmon_count = transmon.photon_counter
        transducer = node1.get_components_by_type("Transducer")[0]
        transducer_count = transducer.photon_counter
        detector = node1.get_components_by_type("FockDetector")[0]
        detector_count = detector.photon_counter

        #Node2
        transducer2 = node2.get_components_by_type("Transducer")[0]
        transmon2 = node2.get_components_by_type("Transmon")[0]
        transmon2_count = transmon2.photon_counter
        detector2 = node2.get_components_by_type("FockDetector")[0]
        detector2_count = detector2.photon_counter

        process0 = Process(node1.emitting_protocol, "start", [])
        event_time0 = (cumulative_time + EMISSION_DURATION) 
        event0 = Event(event_time0, process0)
        tl.schedule(event0)
    
        process1 = Process(node1.upconversion_protocol, "start", [Photon]) 
        event_time1 = (event_time0 + CONVERSION_DURATION) 
        event1 = Event(event_time1, process1)
        tl.schedule(event1)
    
        process2 = Process(node2.downconversion_protocol, "start", [Photon])
        event_time2 =(event_time1 + CONVERSION_DURATION) 
        event2 = Event(event_time2, process2)
        tl.schedule(event2)
        
        failed_up_conversions.append(detector_count)
        failed_down_conversions.append(detector2_count)
        successful_conversions.append(transmon2_count)

        print(f"Number of photons converted at time {tl.time}: {transmon2_count}") 
        
        #reset timeline
        tl.time = 0
        tl.init()

        total_photons_successful += transmon2_count
        total_transducer_count += transducer_count
        cumulative_time += PERIOD

        ideal_photons.append(trial + 1)
        emitted_photons.append(total_transducer_count)
        converted_photons.append(total_photons_successful)
        
        #Reset counters
        transmon.photon_counter = 0 
        transmon2.photon_counter = 0 
        transducer.photon_counter = 0
        detector.photon_counter = 0
        detector2.photon_counter = 0
        transducer2.photon_counter = 0


        


    #RESULTS

    print(f"- - - - - - - - - -")
    print(f"Period: {PERIOD}")

    total_photons_to_be_converted = NUM_TRIALS-1
    print(f"Total number of photons converted: {total_photons_successful}")
    print(f"Total number of photons EMITTED: {total_transducer_count}")
    
    conversion_percentage = (total_photons_successful / total_photons_to_be_converted) * 100 if total_photons_to_be_converted > 0 else 0
    print(f"Conversion efficiency of DQT protocol with no-idealities of transmon: {conversion_percentage:.2f}%")

    conversion_percentage_2 = (total_photons_successful / total_transducer_count) * 100 if total_photons_to_be_converted > 0 else 0
    print(f"Conversion efficiency of DQT protocol: {conversion_percentage_2:.2f}%")

    failed_down_conversions_adjusted = [x + 1 for x in failed_down_conversions]
    successful_conversions_adjusted = [y + 2 for y in successful_conversions]

    print(f"- - - - - - - - - -")

    time_points = [i * PERIOD for i in range(NUM_TRIALS)]




results_matrix = np.zeros((NUM_TRIALS, 3))
for i in range(NUM_TRIALS):
    if failed_up_conversions[i] != 0:
        results_matrix[i, 0] = 1  
    if failed_down_conversions[i] != 0:
        results_matrix[i, 1] = 1  
    if successful_conversions[i] != 0:
        results_matrix[i, 2] = 1  

fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True, figsize=(12, 8), gridspec_kw={'height_ratios': [4, 1]})

ax1.plot(time_points, ideal_photons, 'o-', label="Ideal Successfully Converted Photons", color='darkblue')
ax1.plot(time_points, converted_photons, 'o-', label="Successfully Converted Photons", color='#FF00FF')
ax1.set_ylabel("Photon Number", fontsize=24)
ax1.set_title("Photon Conversion over Time", fontsize=24, fontweight='bold')
ax1.legend(fontsize=24, loc='upper left')
ax1.grid(True)
ax1.tick_params(axis='both', labelsize=18)

ax2.bar(time_points, results_matrix[:, 0], color='#ED213C', label='Failed Up', alpha=0.7, width=PERIOD * 0.8)
ax2.bar(time_points, results_matrix[:, 1], color='blue', label='Failed Down', alpha=0.7, bottom=results_matrix[:, 0], width=PERIOD * 0.8)
ax2.bar(time_points, results_matrix[:, 2], color='#119B70', label='Successful', alpha=0.7, bottom=results_matrix[:, 0] + results_matrix[:, 1], width=PERIOD * 0.8)
ax2.set_xlabel(r"Time ($\mu$s)", fontsize=24)
ax2.legend(fontsize=18, loc='upper left')
ax2.tick_params(axis='both', labelsize=12)
ax2.yaxis.set_visible(False)  
ax2.legend(fontsize=12, loc='upper left')
ax2.tick_params(axis='both', labelsize=12)

plt.tight_layout()
plt.show()
