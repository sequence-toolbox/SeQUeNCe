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
from sequence.components.detector import Detector
from example.Transducer_Examples.ConversionProtocols import UpConversionProtocol
from example.Transducer_Examples.ConversionProtocols import DownConversionProtocol
from example.Transducer_Examples.ConversionProtocols import EmittingProtocol

# General
NUM_TRIALS = 5
FREQUENCY = 1e9
START_TIME = 0
PERIOD = int(1e12 / FREQUENCY)

# Source
WAVELENGTH = 1550
MEAN_PHOTON_NUM = 10

# Transducer
EFFICIENCY_UP = 0.5


# Fock Detector
MICROWAVE_DETECTOR_EFFICIENCY = 1
OPTICAL_DETECTOR_EFFICIENCY = 1 #poi nel caso li distinguo anche tra 1 e 2

# Channel
ATTENUATION = 0
DISTANCE = 1e3






class MyFockComponent(Entity):
        def __init__(self, name: str, timeline: "Timeline", src_list: List, prob: int = 0.5):  
            #aggiungo una lista di scr, che sarebbero i miei inpu (sono canali, da riempire??)
            #inserisco prob che attuamente è 0.5, ovvero ho un beam splitter 50/50. Se voglio cambiarla dovrò cambirare anche la funzione get

            Entity.__init__(self, name, timeline)
            self.name = name
            self.timeline = timeline
            src_list = [] #aggiungo la lista degli input, per ora una lista vuota che vado a riempire con i canali
            self.first_component_name = self


        def init(self):  # ci metto due ricevitori come il trasducer
             assert len(self._receivers) == 2

        def add_input(self, inputs, src: "QuantumChannel") -> None:
            for i in inputs:
                self.receive_qubit(i)

        def add_detectors(self, ouputs: List):  #riempio i due ricevitori (questa volta sono due detector)
            for i in ouputs:
                self.add_receiver(i)

        #def receive_photon_from_channel(self, photon: "Photon") -> None:
            #....
            #da mettere se nodo sentangled riceve un sifnifica che si richiama questa funzione
            
            #puoi mettere una seire di if, se il componente ne riceve 1, 0 o 2, 
            # in particolare se ne riceve 2 puoi usare la fock interaction

        def Fock_interaction(self, photon: "Photon", **kwargs) -> None:
            detector_num = self.get_generator().choice([0, 1])
            self._receivers[detector_num].get(photon)







class Counter:
    def __init__(self):
        self.count = 0

    def trigger(self, detector, info):
        self.count += 1




class SenderNode(Node):
    def __init__(self, name, timeline, node2):
        super().__init__(name, timeline)

        # Hardware setup

        #Istanzio componenet trasduttore
        self.transducer_name = name + ".transducer"
        transducer = Transducer(name=self.transducer_name, owner=self, timeline=timeline, efficiency=EFFICIENCY_UP)
        self.add_component(transducer)
        transducer.attach(self)
        transducer.photon_counter = 0
        self.counter = Counter()
        transducer.attach(self.counter)
        self.set_first_component(self.transducer_name)

        #Istanzio componente microwave detector nel Tx
        detector_name = name + ".fockdetector1"
        detector = FockDetector(detector_name, timeline, efficiency=MICROWAVE_DETECTOR_EFFICIENCY)
        self.add_component(detector)
        self.set_first_component(detector_name)
        self.counter = Counter()
        detector.attach(self.counter)

        #output del trasduttore
        transducer.add_output([node2, detector])

        #Istanzio il protocollo di upconversion
        self.upconversion_protocol = UpConversionProtocol(self, name + ".upconversion_protocol")



class EntangleNode(Node):
    def __init__(self, name, timeline):
        super().__init__(name, timeline)

        # Hardware setup
        self.myfockcomponent_name = name + ".mycomponent"
        myfockcomponent = MyFockComponent(name=myfockcomponent.name, timeline=timeline)  # non metto scr_list perchè voglio un solo ingresso
        self.add_component(MyFockComponent)
        myfockcomponent.attach(self)
        self.set_first_component(self.myfockcomponent_name)
            
        detector_name2 = name + ".fockdetector2"
        detector2 = FockDetector(detector_name2, timeline, efficiency=OPTICAL_DETECTOR_EFFICIENCY)
        self.add_component(detector2)
        self.counter2 = Counter()
        detector2.attach(self.counter2)

        detector_name3 = name + ".fockdetector3"
        detector3 = FockDetector(detector_name3, timeline, efficiency=OPTICAL_DETECTOR_EFFICIENCY)
        self.add_component(detector3)
        self.counter3 = Counter()
        detector3.attach(self.counter3)

        myfockcomponent.add_detectors([detector2, detector3])

def receive_photon(self, src, photon):
        self.components[self.myfockcomponent_name].receive_photon_from_channel(photon)

if __name__ == "__main__":

    runtime = 1e12
    tl = Timeline(runtime)
   
    node2 = EntangleNode("node2", tl)
    node1 = SenderNode("node1", tl, node2)
    node3 = SenderNode("node3", tl, node2)

    qc1 = QuantumChannel("qc.node1.node2", tl, attenuation=ATTENUATION, distance=DISTANCE)
    qc2 = QuantumChannel("qc.node3.node2", tl, attenuation=ATTENUATION, distance=DISTANCE)
    qc1.set_ends(node1, node2.name)
    qc2.set_ends(node3, node2.name)

    if EFFICIENCY_UP >= 0 and EFFICIENCY_UP <= 1:
        pass
    else:
        print("Error: the efficiency must be between 0 and 1")
        exit(1)
    
   
    tl.init()

    print(f"--------------------")
    #print(f"Simulation started with period {PERIOD} ps")
    
    total_photons_successful=0

    for trial in range(NUM_TRIALS): 
        print(f"Trial {trial}:")


        tl.run() #se metto qua il tl.run il primo trial non richiama la funzione, ho sempre 0 e 0

        detector = node1.get_components_by_type("FockDetector")[0]
        detector_count = detector.photon_counter #DETECTOR A MICROONDE NODE1


        process1 = Process(node1.upconversion_protocol, "start", [])
        event1 = Event(START_TIME + PERIOD * trial, process1) #incrementa il periodo che qua è 1
        tl.schedule(event1)

        
        #tl.run() #se metto qua il tl.run mi "scala" nel tempo i fotoni ricevuti da detector e detector2
    
    
        #print(f"Number of photons converted at time {tl.time} ps: {detector2_count}") #sistema queste unità di misura
        #print(f"Number of NOT converted photons at time {tl.time} ps: {detector_count}")

        #reset dei detector e contatori trasduttore
        detector.photon_counter = 0
    

        #incremento del conteggio per calcolare la percentuale finale
        #total_photons_successful += detector2_count


        
        


    