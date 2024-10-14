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

NUM_TRIALS = 10
FREQUENCY = 1e9
MICROWAVE_WAVELENGTH = 999308 # nm
OPTICAL_WAVELENGTH = 1550 # nm
MEAN_PHOTON_NUM=1

# Timeline
START_TIME = 0
EMISSION_DURATION = 10 # ms (scelta io)
CONVERSION_DURATION = 10 # ms
PERIOD = EMISSION_DURATION + CONVERSION_DURATION + CONVERSION_DURATION

#Trasmon
ket1 = (0.0 + 0.0j, 1.0 + 0.0j) 
ket0 = (1.0 + 0.0j, 0.0 + 0.0j) 
state_list= [ket1, ket0] 
TRASMON_EFFICIENCY = 0.9

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

        self.trasmon_name = name + ".trasmon"
        trasmon = Trasmon(name=self.trasmon_name, owner=self, timeline=timeline, wavelength=[MICROWAVE_WAVELENGTH, OPTICAL_WAVELENGTH], photon_counter=0, efficiency=TRASMON_EFFICIENCY, photons_quantum_state= state_list)
        self.add_component(trasmon)
        self.set_first_component(self.trasmon_name)


        self.transducer_name = name + ".transducer"
        transducer = Transducer(name=self.transducer_name, owner=self, timeline=timeline, efficiency=EFFICIENCY_UP)
        self.add_component(transducer)
        transducer.attach(self)
        transducer.photon_counter = 0
        self.counter = Counter()
        transducer.attach(self.counter)
        self.set_first_component(self.transducer_name)


        trasmon.add_receiver(transducer)


        detector_name = name + ".fockdetector1"
        detector = FockDetector(detector_name, timeline, wavelength=MICROWAVE_WAVELENGTH, efficiency=MICROWAVE_DETECTOR_EFFICIENCY_Tx)
        self.add_component(detector)
        self.set_first_component(detector_name)
        self.counter = Counter()
        detector.attach(self.counter)

        transducer.add_output([node2, detector])

        self.emitting_protocol = EmittingProtocol(self, name + ".emitting_protocol", timeline, trasmon, transducer)
        self.upconversion_protocol = UpConversionProtocol(self, name + ".upconversion_protocol", timeline, transducer, node2, trasmon)



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

        self.trasmon_name2 = name + ".trasmon2"
        trasmon2 = Trasmon(name=self.trasmon_name2, owner=self, timeline=timeline, wavelength=[MICROWAVE_WAVELENGTH, OPTICAL_WAVELENGTH], photons_quantum_state= state_list, photon_counter=0, efficiency=1)
        self.add_component(trasmon2)
        self.set_first_component(self.trasmon_name2)
        
        transducer2.add_output([trasmon2,detector2])
        print(f"Transducer2 output: {transducer2._receivers}")

        self.downconversion_protocol = DownConversionProtocol(self, name + ".downconversion_protocol", timeline, transducer2, trasmon2)

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



        trasmon = node1.get_components_by_type("Trasmon")[0]
        trasmon_count = trasmon.photon_counter
        transducer = node1.get_components_by_type("Transducer")[0]
        transducer_count = transducer.photon_counter
        detector = node1.get_components_by_type("FockDetector")[0]
        detector_count = detector.photon_counter

        transducer2 = node2.get_components_by_type("Transducer")[0]
        trasmon2 = node2.get_components_by_type("Trasmon")[0]
        trasmon2_count = trasmon2.photon_counter
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
        successful_conversions.append(trasmon2_count)

        

        print(f"Number of photons converted at time {tl.time}: {trasmon2_count}") 
        
        #reset timeline
        tl.time = 0
        tl.init()


        total_photons_successful += trasmon2_count
        total_transducer_count += transducer_count
        cumulative_time += PERIOD

        ideal_photons.append(trial + 1)
        emitted_photons.append(total_transducer_count)
        converted_photons.append(total_photons_successful)
        
        trasmon.photon_counter = 0 
        trasmon2.photon_counter = 0 
        transducer.photon_counter = 0
        detector.photon_counter = 0
        detector2.photon_counter = 0
        transducer2.photon_counter = 0


    #RESULTS

    print(f"- - - - - - - - - -")
    print(PERIOD)

    total_photons_to_be_converted = NUM_TRIALS
    print(f"Total number of photons converted: {total_photons_successful}")
    print(f"Total number of photons EMITTED: {total_transducer_count}")
    
    conversion_percentage = (total_photons_successful / total_photons_to_be_converted) * 100 if total_photons_to_be_converted > 0 else 0
    print(f"Conversion efficiency of DQT protocol with no-idealities of trasmon: {conversion_percentage:.2f}%")


    conversion_percentage_2 = (total_photons_successful / total_transducer_count) * 100 if total_photons_to_be_converted > 0 else 0
    print(f"Conversion efficiency of DQT protocol: {conversion_percentage_2:.2f}%")



    

    
    print(f"- - - - - - - - - -")

    time_points = [i * PERIOD for i in range(NUM_TRIALS)]

    trials = list(range(NUM_TRIALS))
    plt.plot(time_points, failed_up_conversions,  'r-', label="Failed UpConversions")
    plt.plot(time_points, failed_down_conversions, 'b-', label="Failed DownConversions")
    plt.plot(time_points, successful_conversions, 'g-', label="Successful Conversions")

    plt.xticks(fontsize=12)  
    plt.yticks(fontsize=12) 
    plt.legend(fontsize=12, loc='best')

    plt.xlabel("Time (ps)", fontsize=14)

    plt.ylabel("Number of Conversions", fontsize=14)
    plt.title("Conversion over Time", fontsize=16, fontweight='bold')
    plt.legend()
    plt.show()





# Supponendo che queste variabili siano già definite nel tuo codice
# time_points, ideal_photons, emitted_photons, converted_photons
plt.plot(time_points, ideal_photons, 'o-', label="Ideal conversion", color='#1E90FF')  # Verde smeraldo
plt.plot(time_points, emitted_photons, 'o-', label="Microwave Photons Emitted", color='#FF00FF')  # Magenta
plt.plot(time_points, converted_photons, 'o-g', label="Successfully Converted Photons")  # Blu dodger

plt.xlabel("Time (ps)", fontsize=14)
plt.ylabel("Photon Number", fontsize=14)
plt.title("Photon Conversion over Time", fontsize=16, fontweight='bold')
plt.legend(fontsize=12, loc='upper left')
plt.grid(True)  # Aggiunge una griglia per migliorare la leggibilità

plt.xticks(fontsize=12)  # Ingrandisce le etichette dell'asse x
plt.yticks(fontsize=12)  # Ingrandisce le etichette dell'asse y

plt.show()






#da poter aggiungere: andamento rispetto al tempo con parallelizzazione degli eventi