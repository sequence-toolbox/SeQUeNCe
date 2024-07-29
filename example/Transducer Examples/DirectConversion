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
from sequence.components.photon import Photon
import matplotlib.pyplot as plt
from sequence.utils.encoding import fock
from typing import List
import math
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.components.memory import Memory
from sequence.components.optical_channel import QuantumChannel
from sequence.components.detector import Detector
from sequence.topology.node import Node
import sequence.utils.log as log


# General
NUM_TRIALS = 1000
FREQUENCY = 1e9
PERIOD = int(1e12 / FREQUENCY)
START_TIME=0

# Source
WAVELENGTH=1550
MEAN_PHOTON_NUM = 10 #settare meglio questo

# Transducer
EFFICIENCY_UP = 0.5
EFFICIENCY_DOWN = 1

# Fock Detector
MICROWAVE_DETECTOR_EFFICIENCY_Rx = 1
MICROWAVE_DETECTOR_EFFICIENCY_Tx = 1
OPTICAL_DETECTOR_EFFICIENCY = 1

# Channel
ATTENUATION = 0
DISTANCE = 1e3



class FockDetector(Detector):
    def __init__(self, name: str, timeline: "Timeline", efficiency=1, wavelength=1550, encoding_type=fock):
        super().__init__(name, timeline, efficiency)
        self.name = name
        self.photon_counter = 0
        self.wavelength = wavelength
        self.encoding_type = encoding_type
        self.timeline = timeline
        self.efficiency = efficiency
    
    def init(self):
        pass


    def get(self, photon=None, **kwargs) -> None:
        """Method to receive a photon for measurement.

        Args:
            photon (Photon): photon to detect (currently unused)

        Side Effects:
           
        """
    
        if random.random() < self.efficiency:
                self.photon_counter += 1
        else:
            pass


class Transducer(Entity):  # se uso entity ho automaticamente una lista di receivers
    def __init__(self, owner: "Node", name: str, timeline: "Timeline", efficiency=1, photon_counter=int):  # efficinecy =1 lo metto come valore di default
        Entity.__init__(self, name, timeline)
        self.name = name
        self.owner = owner
        self.timeline = timeline
        self.efficiency = efficiency
        self.photon_counter = 0
        

    def init(self):  # funzione necessaria
        assert len(self._receivers) == 2

    def add_output(self, ouputs: List):  # qui va cambiato il nome della funzione
        for i in ouputs:
            self.add_receiver(i)
    
    def receive_photon_from_source(self, photon: "Photon") -> None:
        if lightsource.photon_counter >= 0: 
            self.photon_counter += lightsource.photon_counter
        else:
            self.photon_counter += 0
            print("NO photon emitted by the Source")
    
    def receive_photon_from_channel(self, photon: "Photon") -> None:
        self.photon_counter += 1
        
    def up_conversion(self, photon: "Photon") -> None: 
        if self.photon_counter > 0:
            if random.random() < self.efficiency:
                print("Successful up-conversion")
                self._receivers[0].receive_qubit(self, photon)
            else:
                print("NO successful up-conversion")
                self._receivers[1].get(photon)
        else:
            print("NO photon received: error")
            

    def down_conversion(self, photon: "Photon") -> None:  
        if self.photon_counter > 0:
            if random.random() < self.efficiency:
                print("Successful down-conversion")
                self._receivers[0].get(photon)
            else:
                print("NO successful down-conversion")
                self._receivers[1].get(photon)
        else:
            pass

class Counter:
    def __init__(self):
        self.count = 0

    def trigger(self, detector, info):
        self.count += 1

class SenderNode(Node):  # nodo con il tradsuttore (che dovrebbe ricevere fisicamente il fotone) e un detector
    def __init__(self, name, timeline, node2):  # espliciti l'owner
        super().__init__(name, timeline)  # passare oggetto

        # Hardware setup

        # istanzio il componente sorgente nel nodo
        self.lightsource_name = name + ".lightsource"
        lightsource = LightSource(name + ".lightsource", timeline, frequency=FREQUENCY, wavelength=WAVELENGTH,
                                  bandwidth=0, mean_photon_num=MEAN_PHOTON_NUM, encoding_type=fock, phase_error=0)
        self.add_component(lightsource)
        self.set_first_component(self.lightsource_name)
        lightsource.photon_counter = 0

        # istanzio il componente trasduttore nel nodo
        self.transducer_name = name + ".transducer"
        transducer = Transducer(name=self.transducer_name, owner=self, timeline=timeline, efficiency=EFFICIENCY_UP)  # non metto scr_list perchè voglio un solo ingresso
        self.add_component(transducer)
        transducer.attach(self)
        self.counter = Counter()
        transducer.attach(self.counter)
        self.set_first_component(self.transducer_name)

        lightsource.add_receiver(transducer)

        #Istanzio il componente Microwave detector nel nodo
        detector_name = name + ".fockdetector1"
        detector = FockDetector(detector_name, timeline, efficiency=MICROWAVE_DETECTOR_EFFICIENCY_Tx)
        self.add_component(detector)
        self.set_first_component(detector_name)
        self.counter = Counter()
        detector.attach(self.counter)

        transducer.add_output([node2, detector])

class ReceiverNode(Node):  # nodo con il tradsuttore (che dovrebbe ricevere fisicamente il fotone) e un detector
    def __init__(self, name, timeline):  # espliciti l'owner
        super().__init__(name, timeline)  # passare oggetto

        # Hardware setup

        # istanzio il componente trasduttore nel nodo (downconversion)
        self.transducer_name = name + ".transducer"
        transducer = Transducer(name=self.transducer_name, owner=self, timeline=timeline, efficiency=EFFICIENCY_DOWN)  # non metto scr_list perchè voglio un solo ingresso
        self.add_component(transducer)
        transducer.attach(self)
        self.counter = Counter()
        transducer.attach(self.counter)
        self.set_first_component(self.transducer_name)

        # istanzio icomponenti detector nel nodo, uno a microonde (detector2) e uno ottico (detector3)

        #Istanzio il componente Microwave detector nel nodo
        detector_name2 = name + ".fockdetector2"
        detector2 = FockDetector(detector_name2, timeline, efficiency=OPTICAL_DETECTOR_EFFICIENCY)
        self.add_component(detector2)
        self.counter2 = Counter()
        detector2.attach(self.counter2)

        #Istanzio il componente Optical detector nel nodo
        detector_name3 = name + ".fockdetector3"
        detector3 = FockDetector(detector_name3, timeline, efficiency=MICROWAVE_DETECTOR_EFFICIENCY_Rx)
        self.add_component(detector3)
        self.counter3 = Counter()
        detector3.attach(self.counter3)

        transducer.add_output([detector2, detector3])

    def receive_qubit(self, src, qubit):
        self.components[self.transducer_name].receive_photon_from_channel(photon)

if __name__ == "__main__":
    runtime = 1e12
    tl = Timeline(runtime)
   
    tl.init()

    node2 = ReceiverNode("node2", tl)
    node1 = SenderNode("node1", tl, node2)

    qc1 = QuantumChannel("qc.node1.node2", tl, attenuation=ATTENUATION, distance=DISTANCE)
    qc1.set_ends(node1, node2.name)

    #tl.run() 
    #Questo si può commentare o meno, questo sinifica che con il tempo non ci stiamo facendo assolutamente nulla :)(

    if EFFICIENCY_UP >= 0 and EFFICIENCY_DOWN >= 0:
         pass
    else:
        print("Error: the efficiency must be between 0 and 1")
        exit(1)

    state = (0.0 + 0.0j, 1.0 + 0.0j)
    print(f"Fock states emitted by the LightSource: {state}")
    state_list = [state] * NUM_TRIALS

    total_photons_emitted = 0
    total_photons_to_be_converted = 0
    total_photons_successful = 0

    print(f"--------------------")

    for trial in range(NUM_TRIALS):
        print(f"Trial {trial + 1}:")

        #emissione dei fotoni da parte della sorgente
        lightsource = node1.get_components_by_type("LightSource")[0]
        lightsource.photon_counter = 0
        lightsource.emit([state_list[trial]])
        print(f"Number of photons emitted in trial {trial + 1}: {lightsource.photon_counter}")
        total_photons_emitted += lightsource.photon_counter

        total_photons_to_be_converted += 1
        #print(f"{total_photons_to_be_converted}") 
        #verifica che stia incremnetando correttamente

        #i fotoni raggiungono il tradsuttore
        transducer = node1.get_components_by_type("Transducer")[0]
        photon = Photon(f"photon_{trial}", tl)
        transducer.receive_photon_from_source(photon)
        print(f"Photons received by Transducer at Tx for up-conversion: {transducer.photon_counter}")

        transducer.up_conversion(photon)
        transducer.photon_counter = 0

        detector = node1.get_components_by_type("FockDetector")[0]
        detector_count_1 = detector.photon_counter
        print(f"Photons received by Microwave Detector: {detector_count_1}")

        if detector.photon_counter > 0:
            print(f"--------------------")
            detector.photon_counter = 0
            continue

        detector.photon_counter = 0

        transducer2 = node2.get_components_by_type("Transducer")[0]
        photon = Photon(f"photon_{trial}", tl)
        print(f"Photons received by Transducer at Rx for down-conversion: {transducer2.photon_counter}")

        transducer2.down_conversion(photon)
        transducer2.photon_counter = 0

        detector2 = node2.get_components_by_type("FockDetector")[0]
        detector_count_2 = detector2.photon_counter
        print(f"Photons received by Microwave Detector at Rx: {detector_count_2}")
        total_photons_successful += detector2.photon_counter
        detector2.photon_counter = 0

        detector3 = node2.get_components_by_type("FockDetector")[1]
        detector_count_3 = detector3.photon_counter
        print(f"Photons received by Optical Detector at Rx: {detector_count_3}")
        detector3.photon_counter = 0

    
        print(f"--------------------")


    conversion_percentage = (total_photons_successful / total_photons_to_be_converted) * 100 if total_photons_to_be_converted > 0 else 0
    print(f"Conversion efficiency of DQT protocol: {conversion_percentage:.2f}%")
    #protocllo senza considerare le non idealità del trasmone

    conversion_percentage_NoIdeal = (total_photons_successful / total_photons_emitted) * 100 if total_photons_emitted > 0 else 0
    print(f"Conversion efficiency of DQT protocol with Trasmon No-Idealities: {conversion_percentage_NoIdeal:.2f}%")
    #questa è con le non idealità del trasmone

