import random
from sequence.kernel.timeline import Timeline
from sequence.components.optical_channel import QuantumChannel
from sequence.components.detector import Detector
from sequence.protocol import Protocol
from sequence.topology.node import Node
from sequence.components.light_source import LightSource
from sequence.utils.encoding import absorptive, single_atom
from sequence.components.photon import Photon
import sequence.utils.log as log
from sequence.kernel.entity import Entity
from typing import List, Callable, TYPE_CHECKING
from abc import ABC, abstractmethod
from sequence.components.photon import Photon
import matplotlib.pyplot as plt
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.components.memory import Memory
from sequence.components.optical_channel import QuantumChannel
from sequence.components.detector import Detector



NUM_TRIALS = 10
FREQUENCY = 1e9
PERIOD = int(1e12 / FREQUENCY)
START_TIME=0
EFFICIENCY=0.5


#Questo è il trasduttore usando protocolli, funziona con l'auentare del tempo, ma comunque il numero di trial è 1


class Transducer(Entity): #se uso entity ho automaticamente una lista di receivers
    def __init__(self, owner: "Node", name: str, timeline: "Timeline", efficiency=1):
        Entity.__init__(self, name, timeline)
        #super().__init__(name, timeline)
        self.name = name
        self.owner = owner
        self.timeline = timeline
        self.efficiency = efficiency

    def init(self): #funzione necessaria
        assert len(self._receivers) == 2
   

    def add_output(self, outputs: List): 
        #funzione per riempire la lista di recivers (che il tradsuttore ha essendo una entity)
        #la funzione rimpie la lista con degli oggetti di una lista oggetti che ci si aspetta apparterranno alla classe Detectors 
        # quindi andrà cambiata, nel caso dell'implemntazione protocollo dovranno essere dei canali, quindi forse andrà spostata fuori dalla classe transducer
        for i in outputs:
              self.add_receiver(i) 


class UpConversionProtocol(Protocol):
    def __init__(self, own: "Node", name: str, transducer=Transducer):
        super().__init__(own, name)    

    def start(self) -> None: 
        transducer=node1.get_components_by_type("Transducer")[0]
        if random.random() < EFFICIENCY:
            print("Successful conversion")
            photon = Photon(f"photon", tl)
            transducer._receivers[0].get(photon)
         
        else:
            print("NO successful conversion")
            photon = Photon(f"photon", tl)
            transducer._receivers[1].get(photon)
   
    def received_message(self, src: str, msg):
             pass
    

class Counter:
    def __init__(self):
        self.count = 0

    def trigger(self, detector, info):
        self.count += 1
        

class MyNode(Node):
    def __init__(self, name, timeline): #inizializzazione, cioè nuova istanza di una classe
        super().__init__(name, timeline) #quello che prende dalla classe nodo, solo name e timeline

        # hardware setup
        self.transducer_name = name + ".transducer"
        transducer = Transducer(name=self.transducer_name,owner=self,timeline=timeline, efficiency=EFFICIENCY) #non metto scr_list perchè voglio un solo ingresso
        self.add_component(transducer)
        transducer.attach(self)
        self.set_first_component(self.transducer_name)
         
        detector_name = name + ".detector1"
        detector = Detector(detector_name, timeline, efficiency=1)
        self.add_component(detector)
        self.set_first_component(detector_name)

        detector_name2 = name + ".detector2"
        detector2 = Detector(detector_name2, timeline, efficiency=1)
        self.add_component(detector2)
        self.set_first_component(detector_name2)

        transducer.add_output([detector, detector2])

        #protocols
        self.upconversion_protocol = UpConversionProtocol(self, name + ".upconversion_protocol")

        
        #print(detector.photon_counter)
        #print(detector2.photon_counter) 
        #verifica che prima del primo trial non siano già stati ricevuti fotoni dai detector    

        self.counter = Counter()
        self.counter2 = Counter()

        detector.attach(self.counter)
        detector2.attach(self.counter2)

    def get_component(self, component_name: str):
            for component in self.components:
                if component.name == component_name:
                    return component
            raise ValueError(f"No component named {component_name}")


        
        
    


if __name__ == "__main__":
    
    runtime = 1000
    tl = Timeline(runtime)
    node1 = MyNode("node2", tl)


    tl.init()
    
    for trial in range(NUM_TRIALS):     

        
        #detector = node2.get_components_by_type("Detector")[0]
        #detector2 = node2.get_components_by_type("Detector")[1]


        process = Process(node1.upconversion_protocol,"start", [])
        event = Event(START_TIME, process)
        tl.schedule(event)
       
    
    tl.run()

    
        
    

    



    