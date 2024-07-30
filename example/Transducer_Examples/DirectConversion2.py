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
from example.Transducer_Examples.TransductionComponent import Trasmon
from example.Transducer_Examples.TransductionComponent import Counter
from sequence.components.detector import Detector
from example.Transducer_Examples.ConversionProtocols import UpConversionProtocol
from example.Transducer_Examples.ConversionProtocols import DownConversionProtocol
from example.Transducer_Examples.ConversionProtocols import EmittingProtocol
from sequence.kernel.quantum_manager import QuantumManager


#GENERAL

NUM_TRIALS = 10
FREQUENCY = 1e9
MICROWAVE_WAVELENGTH = 999308 # nm
OPTICAL_WAVELENGTH = 1550 # nm
MEAN_PHOTON_NUM=1

# Timeline
START_TIME = 0
EMISSION_DURATION = 10 # ps
CONVERSION_DURATION = 10 # ps
PERIOD = EMISSION_DURATION + CONVERSION_DURATION + CONVERSION_DURATION


# Transducer
EFFICIENCY_UP = 0.5
EFFICIENCY_DOWN = 0.8

# Fock Detector
MICROWAVE_DETECTOR_EFFICIENCY_Rx = 1
MICROWAVE_DETECTOR_EFFICIENCY_Tx = 1
OPTICAL_DETECTOR_EFFICIENCY = 1

# Channel
ATTENUATION = 0
DISTANCE = 1e3


#state = (0.0 + 0.0j, 0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j) #statevector
state = (0.0 + 0.0j, 1.0 + 0.0j) #statevector #meno preciso

#questo è lo statevector 1, quindi il transducer deve emettere. si potrebbe fare anche con lo zero ma in quel caso errore e non errore sono diversi.  Non penso ne valga la pena
#state_list = [state] * NUM_TRIALS #lista di stati di fock, abbiamo un insieme di state_vector per il numero totale di trials





#NODES OF THE NETWORK 

class SenderNode(Node):
    def __init__(self, name, timeline, node2):
        super().__init__(name, timeline)


        #Hardware setup

        self.trasmon_name = name + ".trasmon"
        trasmon = Trasmon(name=self.trasmon_name, owner=self, timeline=timeline, wavelength=MICROWAVE_WAVELENGTH, photon_counter=0, quantum_state=state, efficiency=1)
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
        self.upconversion_protocol = UpConversionProtocol(self, name + ".upconversion_protocol", timeline, transducer, node2)


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

        #detector_name2 = name + ".fockdetector2"
        #detector2 = FockDetector(detector_name2, timeline, wavelength=MICROWAVE_WAVELENGTH, efficiency=MICROWAVE_DETECTOR_EFFICIENCY_Rx)
        #self.add_component(detector2)
        #self.counter2 = Counter()
        #detector2.attach(self.counter2)

        detector3_name = name + ".fockdetector3"
        detector3 = FockDetector(detector3_name, timeline, wavelength=OPTICAL_WAVELENGTH, efficiency=OPTICAL_DETECTOR_EFFICIENCY)
        self.add_component(detector3)
        self.counter3 = Counter()
        detector3.attach(self.counter3)

        self.trasmon_name2 = name + ".trasmon2"
        trasmon2 = Trasmon(name=self.trasmon_name2, owner=self, timeline=timeline, wavelength=MICROWAVE_WAVELENGTH, photon_counter=0, quantum_state=state, efficiency=1)
        self.add_component(trasmon2)
        self.set_first_component(self.trasmon_name2)
        
        transducer2.add_output([trasmon2,detector3])
        print(f"Transducer2 output: {transducer2._receivers}")
        self.downconversion_protocol = DownConversionProtocol(self, name + ".downconversion_protocol", timeline, transducer2)

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
    
    failed_up_conversions = []
    failed_down_conversions = []
    successful_conversions = [] 


    cumulative_time = START_TIME
    
    for trial in range(NUM_TRIALS): 

        print(f"--------------------")
        print(f"Trial {trial}:")

        tl.run()

        #Richiamo i vari componenti dai nodi per richiamre i contatoti di fotoni

        trasmon = node1.get_components_by_type("Trasmon")[0]
        trasmon_count = trasmon.photon_counter
        transducer = node1.get_components_by_type("Transducer")[0]
        transducer_count = transducer.photon_counter
        detector = node1.get_components_by_type("FockDetector")[0]
        detector_count = detector.photon_counter

        transducer2 = node2.get_components_by_type("Transducer")[0]
        #detector2 = node2.get_components_by_type("FockDetector")[0]
        #detector2_count = detector2.photon_counter
        detector3 = node2.get_components_by_type("FockDetector")[0]
        detector3_count = detector3.photon_counter

        trasmon2 = node2.get_components_by_type("Trasmon")[0]
        trasmon2_count = trasmon2.photon_counter




        #scheduling dei processi e degli eventi
        
        process0 = Process(node1.emitting_protocol, "start", [])
        event_time0 = (cumulative_time + EMISSION_DURATION) 
        event0 = Event(event_time0, process0)
        tl.schedule(event0)
        

        print(f"Number of photons emitted: {trasmon_count}") 
        #print(f"Number of photons at the transducer: {transducer_count}")
        #non faccio questo secondo print perché la npn idealità non sta nella trasmissione da trasmone a trasduttore (bisogna capire se aggiungerla o meno), 
        #ma nel trasmone stesso che magari non emette nonostante il suo stato sia 1
    
        process1 = Process(node1.upconversion_protocol, "start", [Photon])
        event_time1 = (event_time0 + CONVERSION_DURATION) 
        event1 = Event(event_time1, process1)
        tl.schedule(event1)
    
        process2 = Process(node2.downconversion_protocol, "start", [Photon])
        event_time2 =(event_time1 + CONVERSION_DURATION) 
        event2 = Event(event_time2, process2)
        tl.schedule(event2)
        

        failed_up_conversions.append(detector_count)
        failed_down_conversions.append(detector3_count)
        successful_conversions.append(trasmon2_count)

        print(f"Number of photons converted at time {tl.time}: {trasmon2_count}") 
        #Chiedere questione tl_now
        
        #reset timeline
        tl.time = 0
        tl.init()

        #reset dei vari contatori per ogni trial
        trasmon.photon_counter = 0 
        trasmon2.photon_counter = 0 
        transducer.photon_counter = 0
        detector.photon_counter = 0
        #detector2.photon_counter = 0
        detector3.photon_counter = 0
        transducer2.photon_counter = 0

        total_photons_successful += trasmon2_count
        cumulative_time += PERIOD





    #RESULTS

    print(f"- - - - - - - - - -")

    total_photons_to_be_converted = NUM_TRIALS - 1
    print(f"Total number of photons converted: {total_photons_successful}")
    conversion_percentage = (total_photons_successful / total_photons_to_be_converted) * 100 if total_photons_to_be_converted > 0 else 0
    print(f"Conversion efficiency of DQT protocol: {conversion_percentage:.2f}%")
    #conversion_percentage = (total_photons_successful / total_photons_to_be_converted) * 100 if total_photons_to_be_converted > 0 else 0
    #print(f"Conversion efficiency of DQT protocol: {conversion_percentage:.2f}%")


    #if transducer.efficiency and transducer2.efficiency > 0.5:
        #print(f"Transducers features are good for the DQT protocol")
        #Percentuale di fotoni convertiti
        
    #Sarebbe carino dare anche qualche metrica per la EQT
   # elif transducer.efficiency < 0.5  and transducer2.efficiency > 0.5:
    #    print(f"Transducers features are good for the EQT protocol")
    #elif transducer.efficiency and transducer2.efficiency < 0.5 :
    #    print(f"Transducers features are not good for any protocol")


    
    
    print(f"- - - - - - - - - -")

    #Plot dell'andamento delle conversioni rispetto al numero di trials
    # trials = list(range(NUM_TRIALS))
    # plt.plot(trials, failed_up_conversions, label="Failed UpConversions")
    # plt.plot(trials, failed_down_conversions, label="Failed DownConversions")
    # plt.plot(trials, successful_conversions, label="Successful Conversions")
    # plt.xticks(range(0, NUM_TRIALS, 1))  # Mostra le etichette ogni 10 trial

    # plt.xlabel("Trial")
    # plt.ylabel("Number of Conversions")
    # plt.title("Photon Conversion over Trials")
    # plt.legend()
    # plt.show()

    #Plot rispetto al tempo?
