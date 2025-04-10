"""Protocols for Quantum Transduction via Entanglement Swapping

NOTE: work in progress
"""
import random
from sequence.kernel.timeline import Timeline
from sequence.protocol import Protocol
from sequence.topology.node import Node
from sequence.components.photon import Photon
from sequence.components.photon import Photon   
from sequence.components.beam_splitter import FockBeamSplitter2
from sequence.components.transducer import Transducer
from sequence.components.transmon import Transmon
from sequence.components.optical_channel import OpticalChannel
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.utils import log

MICROWAVE_WAVELENGTH = 999308 # nm
OPTICAL_WAVELENGTH = 1550 # nm



class EmittingProtocol(Protocol):

    """Protocol for emission of single microwave photon by transmon"""

    def __init__(self, own: Node, name: str, tl: Timeline, transmon: Transmon, transducer: Transducer):
        super().__init__(own, name)
        self.owner = own
        self.name = name
        self.tl = tl
        self.transmon = transmon
        self.transducer = transducer

    def start(self) -> None:

        self.transducer.photon_counter += 1 
        #print(f"Microwave photons emitted by {self.name}: {self.transducer.photon_counter}")

    def received_message(self, src: str, msg):
        pass


class Swapping(Protocol):

    """Entanglement swapping in the middle."""
    
    def __init__(self, own: Node, name: str, tl: Timeline, FockBS: FockBeamSplitter2):
        super().__init__(own, name)
        self.owner = own
        self.name = name
        self.tl = tl
        self.FockBS = FockBS
        #self.FockBS.delay= delay
        #self.measurement_protocol = measure_protocol

    def start(self, photon: Photon) -> None:
        pass

    

    def swap(self, photon: Photon) -> None:
        
        receivers = self.FockBS._receivers
        photon_count = self.FockBS.photon_counter
        
        self.detector_photon_counter_real = 0
        self.spd_real= 0  

        self.detector_photon_counter_ideal = 0
        self.spd_ideal= 0 

        print("ENTANGLEMENT SWAPPING PROTOCOL STARTS AT time: ", self.tl.now())
        #print(f"Detector efficiency is: ", self.FockBS._receivers[0].efficiency)
        #print(f"Detector efficiency is: ", self.FockBS._receivers[1].efficiency)

        #PROVAAAAAAAA

       
        if photon_count == 1:
            print("UN SOLO FOTONE")
            selected_receiver = random.choice(receivers)
            print("RECEIVER SELEZIONATO: ", selected_receiver)
            
            selected_receiver.get(photon)
            selected_receiver.get_2(photon) 

            #selected_receiver.photon_counter2=+1 #ideal
            
            #if random.random() < selected_receiver.efficiency: #real
                #selected_receiver.photon_counter += 1 
            
            #self.measurement_protocol.measure(photon)  # Chiamata al protocollo measure

        elif photon_count == 2:
            print("DUE FOTONI")

            selected_receiver = random.choice(receivers)
            print("RECEIVER SELEZIONATO: ", selected_receiver)

            selected_receiver.get(photon)
            selected_receiver.get(photon)
            selected_receiver.get_2(photon) 
            selected_receiver.get_2(photon)
            #future_time = self.timeline.now() + self.FockBS.delay

            future_time = self.tl.now() + 1  # Delay opzionale
            #QUI CI VUOLE UN IF IN QUALCHE MODO
            process = Process(selected_receiver, "measure", [photon])
            event = Event(future_time, process)
            self.tl.schedule(event)

        #return  self.detector_photon_counter_real, self.spd_real, self.detector_photon_counter_ideal, self.spd_ideal
        
    
    def received_message(self, src: str, msg):
        pass 
    
        #selected_receiver.photon_counter2=+2 #ideal

        #print("MEASUREMENT PROTOCOL STARTS AT time: ", self.tl.now())

        #ITALIANOOOOOOO
    



class Measure(Protocol):
    def __init__(self, own: Node, name: str, tl: Timeline, FockBS: FockBeamSplitter2):
        super().__init__(own, name)
        self.owner = own
        self.name = name
        self.tl = tl
        self.FockBS = FockBS

        self.detector_photon_counter_real = 0
        self.spd_real = 0  

        self.detector_photon_counter_ideal = 0
        self.spd_ideal = 0 

    def start(self) -> None:
        
        print("MEASUREMENT PROTOCOL STARTS AT time: ", self.tl.now())
        print("--------")
        #print("CASO DETECTOR IDEALE")

        print("IL PRIMO RICEVITORE è ", self.FockBS._receivers[0])
        print("IL SECONDO RICEVITORE è ", self.FockBS._receivers[1])


        print("il conteggio del PRIMO RICEVITORE è: ", self.FockBS._receivers[0].photon_counter)
        print("il conteggio del SEONCONDO ricevitore è : ", self.FockBS._receivers[1].photon_counter)

        print("il conteggio del PRIMO RICEVITORE IDEALE: ", self.FockBS._receivers[0].photon_counter2)
        print("il conteggio del SECONDO RICEVITORE IDEALE: ", self.FockBS._receivers[1].photon_counter2)
        print("Fock beams photon counter: ", self.FockBS.photon_counter)
        print("--------")

        #if self.FockBS._receivers[0].photon_counter2 == 0 and self.FockBS._receivers[1].photon_counter2 == 0:
        #    print("No photon reach the beam splitter")
        


        




    
        if self.FockBS._receivers[0].photon_counter2 == 1 or self.FockBS._receivers[1].photon_counter2 == 1:
           self.detector_photon_counter_ideal += 1
            

        if self.FockBS._receivers[0].photon_counter2 >= 1 or self.FockBS._receivers[1].photon_counter2 >= 1:
            self.spd_ideal += 1


        if self.FockBS._receivers[0].photon_counter == 1 or self.FockBS._receivers[1].photon_counter == 1:
            self.detector_photon_counter_real += 1
           
        if self.FockBS._receivers[0].photon_counter >= 1 or self.FockBS._receivers[1].photon_counter >= 1:
            self.spd_real += 1
        

        print("il conteggio del PRIMO RICEVITORE è: ", self.FockBS._receivers[0].photon_counter)
        print("il conteggio del SEONCONDO ricevitore è : ", self.FockBS._receivers[1].photon_counter)

        print("il conteggio del PRIMO RICEVITORE IDEALE: ", self.FockBS._receivers[0].photon_counter2)
        print("il conteggio del SECONDO RICEVITORE IDEALE: ", self.FockBS._receivers[1].photon_counter2)
        print("Fock beams photon counter: ", self.FockBS.photon_counter)
        print("--------")
        

        return self.detector_photon_counter_ideal, self.spd_ideal, self.detector_photon_counter_real, self.spd_real 

    
    #def get_detector_photon_counter_ideal(self):
    #    return self.detector_photon_counter_ideal

    #def get_spd_ideal(self):
    #    return self.spd_ideal
    
    #def get_detector_photon_counter_real(self):
    #    return self.detector_photon_counter_real

    #def get_spd_real(self):
    #    return self.spd_real
    
    def received_message(self, src: str, msg):
        pass
