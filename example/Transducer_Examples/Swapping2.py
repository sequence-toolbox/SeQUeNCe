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
from example.Transducer_Examples.TransductionComponent import FockBeamSplitter

from sequence.components.detector import Detector
from example.Transducer_Examples.ConversionProtocols import UpConversionProtocol
from example.Transducer_Examples.SwappingProtocols import UpConversionProtocolEntangle
from example.Transducer_Examples.ConversionProtocols import DownConversionProtocol
from example.Transducer_Examples.ConversionProtocols import EmittingProtocol
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
EMISSION_DURATION = 10 # ps
CONVERSION_DURATION = 10 # ps
PERIOD = EMISSION_DURATION + CONVERSION_DURATION + CONVERSION_DURATION

#Trasmon
ket1 = (0.0 + 0.0j, 1.0 + 0.0j) 
ket0 = (1.0 + 0.0j, 0.0 + 0.0j) 
state_list= [ket1, ket0] #Il trasmone in questo caso voglio che generi lo stato 10 (voglio un fotone alle microonde e 0 ottico)
#state_list= [ket1, ket0] stato 01 (0 fotoni alle microonde, 1 ottico)


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
        trasmon = Trasmon(name=self.trasmon_name, owner=self, timeline=timeline, wavelength=[MICROWAVE_WAVELENGTH, OPTICAL_WAVELENGTH], photon_counter=0, efficiency=1, photons_quantum_state= state_list)
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
        self.upconversion_protocol = UpConversionProtocolEntangle(self, name + ".upconversion_protocol", timeline, transducer, node2)




class EntangleNode(Node):
    def __init__(self, name, timeline, src_list: List[str]):
        super().__init__(name, timeline)
        
        # Hardware setup
        self.fock_beam_splitter_name = name + ".FockBeamSplitter"
        fock_beam_splitter = FockBeamSplitter(name=self.fock_beam_splitter_name, owner=self, timeline=timeline, efficiency=0.5, photon_counter=0, src_list=src_list)        
        self.add_component(fock_beam_splitter)
        self.set_first_component(self.fock_beam_splitter_name)
        
        detector_name = name + ".detector1"
        detector = Detector(detector_name, timeline, efficiency=1)
        self.add_component(detector)
        self.set_first_component(detector_name)

        detector_name2 = name + ".detector2"
        detector2 = Detector(detector_name2, timeline, efficiency=1)
        self.add_component(detector2)
        self.set_first_component(detector_name2)

        fock_beam_splitter.add_output([detector, detector2])
        
        self.counter = Counter()
        self.counter2 = Counter()

        detector.attach(self.counter)
        detector2.attach(self.counter2)
    
    def receive_photon(self, photon, src_list):
        self.components[self.fock_beam_splitter_name].receive_photon_from_scr(photon, src_list)


if __name__ == "__main__":

    runtime = 10e12
    tl = Timeline(runtime)
   
    
    nodoprimo_name = "Nodoo1"
    nodoterzo_name = "Nodoo3"
    
    src_list = [nodoprimo_name, nodoterzo_name]  # the list of sources, note the order

   

    node2 = EntangleNode("node2", tl, src_list)
    node1 = SenderNode(nodoprimo_name, tl, node2)
    node3 = SenderNode(nodoterzo_name, tl, node2)

    qc1 = QuantumChannel("qc.node1.node2", tl, attenuation=ATTENUATION, distance=DISTANCE)
    qc2= QuantumChannel("qc.node1.node3", tl, attenuation=ATTENUATION, distance=DISTANCE)
    qc1.set_ends(node1, node2.name)
    qc2.set_ends(node1, node3.name)

    tl.init()

    

    cumulative_time = START_TIME
    
    print(f"--------------------")

    print(f"Direct Quantum Transduction Protocol starts, the qubit that we are going to convert is: {ket1}")
    
    for trial in range(NUM_TRIALS): 

        print(f"--------------------")
        print(f"Trial {trial}:")

        tl.run()

        #Richiamo i vari componenti dai nodi per richiamre i contatoti di fotoni 
        #(mi servirà per printare i conteggi e poi per il reset)

        #componenti nodo1
        trasmon = node1.get_components_by_type("Trasmon")[0]
        trasmon_count = trasmon.photon_counter
        transducer = node1.get_components_by_type("Transducer")[0]
        transducer_count = transducer.photon_counter
        detector = node1.get_components_by_type("FockDetector")[0]
        detector_count = detector.photon_counter

        fock_beam_splitter = node2.get_components_by_type("FockBeamSplitter")[0]
        fock_beam_splitter_count = fock_beam_splitter.photon_counter
        #componenti nodo2
       

        #scheduling dei processi e degli eventi
        
        #process0 = Process(node1.emitting_protocol, "start", [])
        #event_time0 = (cumulative_time + EMISSION_DURATION) 
        #event0 = Event(event_time0, process0)
        #tl.schedule(event0)
    
        process1 = Process(node1.upconversion_protocol, "start", [Photon]) 
        event_time1 = (cumulative_time + CONVERSION_DURATION) 
        event1 = Event(event_time1, process1)
        tl.schedule(event1)

        #process2 = Process(node3.emitting_protocol, "start", [])
        #event2 = Event(event_time0, process2)
        #tl.schedule(event0)
    
        process3 = Process(node3.upconversion_protocol, "start", [Photon]) 
        event3 = Event(event_time1, process3)
        tl.schedule(event1)

        print(f"Photon count in FockBs: {fock_beam_splitter_count}")

        #possiamo anche farli emettere contemporaneamente, ma lasciamo che la ricezione sia a due istati diversi :)
        #(per ora)

    
    

        
        #reset timeline
        tl.time = 0
        tl.init()


        #Incremento del conteggio totale
        cumulative_time += PERIOD

        #reset dei contatori qui!
        trasmon.photon_counter = 0 

    #RESULTS

    print(f"- - - - - - - - - -")

  
    
    print(f"- - - - - - - - - -")

  
