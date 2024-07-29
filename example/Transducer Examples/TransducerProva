import random
from sequence.kernel.timeline import Timeline
from sequence.kernel.process import Process
from sequence.components.optical_channel import QuantumChannel
from sequence.components.detector import Detector
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


NUM_TRIALS = 1000
FREQUENCY = 1e9
PERIOD = int(1e12 / FREQUENCY)

#Questo è come se fosse il mio fockbsm, si potrebbe usare con lo swapping



class EmittingNode(Node): #da vedere se va usato
     def __init__(self, name, timeline):
        super().__init__(name, timeline)
        lightsource = LightSource(name + ".lightsource", timeline, frequency=FREQUENCY, wavelength=1550,
                                   bandwidth=0, mean_photon_num=0.001, encoding_type=absorptive, phase_error=0)
        self.add_component(lightsource)
        lightsource.add_receiver(self)
    
        #period = int(int(1e12 /lightsource.frequency))
        #print(f"Period of the light source: {period} ps")
        
        #num_photons_per_period = lightsource.mean_photon_num * period
        #print(f"Number of photons sent by the light source per period: {num_photons_per_period}")


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


    def transducer_method(self, photon:"Photon")-> None: #qua serve il receiver non il photon (per ora)
        """Transducer method to convert photon and send to receiver. This method is for direct conversion or entanglement generation.

        Args:
            photon (Photon): photon to measure 
             
        """
        if random.random() < self.efficiency:
            #print("Successful conversion")
            #print per verificare che la conversione sia andata a buon fine
            
            #print(self._receivers[0])
            #print(self._receivers[1])
            #print per verificare chi sono i due recivers (quindi i due detector nel nostro caso specifico)
            
            #self.owner.receive_qubit(self._receivers[0], photon)
            self._receivers[0].get(photon)
         
        else:
            #print("NO successful conversion")
            #print per verificare che la conversione NON sia andata a buon fine
            
            #self.owner.receive_qubit(self._receivers[0], photon)
            self._receivers[1].get(photon)

        #prova transducer più semplice, solo conversione diretta o no
        #if self.efficiency == 1:
        #    print("Photon received")
        #    print(self._receivers[0])
        #    print(self._receivers[1])
        #    #self.owner.receive_qubit(self._receivers[0], photon)
        #    self._receivers[0].get(photon)
        #else:
        #    print("NO Photon received")
        #    self._receivers[1].get(photon)

#class MyTransducer(Transducer):
   # def get(self, photon: "Photon", **kwargs) -> None:
    #    print(f"Photon {photon.name} received by {self.name}")

class Counter:
    def __init__(self):
        self.count = 0

    def trigger(self, detector, info):
        self.count += 1
        

class EndNode(Node):
    def __init__(self, name, timeline): #inizializzazione, cioè nuova istanza di una classe
        super().__init__(name, timeline) #quello che prende dalla classe nodo, solo name e timeline

        # hardware setup
        self.transducer_name = name + ".transducer"
        transducer = Transducer(name=self.transducer_name,owner=self,timeline=timeline, efficiency=0.5) #non metto scr_list perchè voglio un solo ingresso
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
        
        #print(detector.photon_counter)
        #print(detector2.photon_counter) 
        #verifica che prima del primo trial non siano già stati ricevuti fotoni dai detector    

        self.counter = Counter()
        self.counter2 = Counter()

        detector.attach(self.counter)
        detector2.attach(self.counter2)
        
        
    


if __name__ == "__main__":
    
    runtime = 1e12
    tl = Timeline(runtime)

    tl.init()

    node1 = EmittingNode("node1", tl)
    node2 = EndNode("node2", tl)
    qc1 = QuantumChannel("qc.node1.node2", tl, attenuation=0, distance=1)
    qc1.set_ends(node1, node2.name)
    
    total_photons = 0
    detector1_photons = 0
    detector2_photons = 0
    

    print(f"Number of trials: {NUM_TRIALS}")

    for trial in range(NUM_TRIALS):
        #print(f"Trial {trial+1}:")
        #print del trial che si sta considerando
        
        
        # Richiamare il metodo transducer_method per farlo attiavre per ogni trial 
        transducer = node2.get_components_by_type("Transducer")[0]
        transducer.transducer_method(Photon(f"photon_{trial}", tl))
        
        detector = node2.get_components_by_type("Detector")[0]
        detector2 = node2.get_components_by_type("Detector")[1]
    
        if trial == NUM_TRIALS - 1:
            # Stampa il numero totale di fotoni ricevuti dai due detector solo per l'ultimo trial
            #trial va da 0 a NUM_TRIALS - 1, quindi l'ultimo trial è NUM_TRIALS - 1
            

            detector_count_1 = detector.photon_counter 
            detector_count_2 = detector2.photon_counter 

            print(f"Total photons received by Microwave Detector: {detector_count_1}")
            print(f"Total photons received by Optical Detector: {detector_count_2}")




            #print della percentuale di fotoni ricevuti al termine del ciclo for
            total_photons += detector_count_1 + detector_count_2
            detector1_photons += detector_count_1
            detector2_photons += detector_count_2
    
    if total_photons > 0:
        percent_detector1 = (detector1_photons / total_photons) * 100
        percent_detector2 = (detector2_photons / total_photons) * 100
    else:
        percent_detector1 = 0
        percent_detector2 = 0
    print(f"Transducer efficiency: {transducer.efficiency*100}%")
    print(f"Percentage of photons detected by Microwave Detector: {percent_detector1:.2f}%")
    print(f"Percentage of photons detected by Optical Detector: {percent_detector2:.2f}%")



    