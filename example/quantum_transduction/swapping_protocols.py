"""Protocols for Quantum Transduction via Entanglement Swapping
"""

import random
from sequence.kernel.timeline import Timeline
from sequence.protocol import Protocol
from sequence.topology.node import Node
from sequence.components.photon import Photon
from sequence.components.photon import Photon   
from sequence.components.beam_splitter import FockBeamSplitter2
from sequence.kernel.event import Event
from sequence.kernel.process import Process

MICROWAVE_WAVELENGTH = 999308 # nm
OPTICAL_WAVELENGTH = 1550 # nm



class Swapping(Protocol):

    """Entanglement swapping in the middle."""
    
    def __init__(self, own: Node, name: str, tl: Timeline, FockBS: FockBeamSplitter2):
        super().__init__(own, name)
        self.owner = own
        self.name = name
        self.tl = tl
        self.FockBS = FockBS
       

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
        
        if photon_count == 1:
            print("UN SOLO FOTONE")
            selected_receiver = random.choice(receivers)
            print("RECEIVER SELEZIONATO: ", selected_receiver)
            
            selected_receiver.get(photon)
            selected_receiver.get_2(photon) 

        elif photon_count == 2:
            print("DUE FOTONI")

            selected_receiver = random.choice(receivers)
            print("RECEIVER SELEZIONATO: ", selected_receiver)

            selected_receiver.get(photon)
            selected_receiver.get(photon)
            selected_receiver.get_2(photon) 
            selected_receiver.get_2(photon)

            future_time = self.tl.now() + 1  
            process = Process(selected_receiver, "measure", [photon])
            event = Event(future_time, process)
            self.tl.schedule(event)

    def received_message(self, src: str, msg):
        pass 
    
   

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

        if self.FockBS._receivers[0].photon_counter2 == 1 or self.FockBS._receivers[1].photon_counter2 == 1:
           self.detector_photon_counter_ideal += 1
            

        if self.FockBS._receivers[0].photon_counter2 >= 1 or self.FockBS._receivers[1].photon_counter2 >= 1:
            self.spd_ideal += 1


        if self.FockBS._receivers[0].photon_counter == 1 or self.FockBS._receivers[1].photon_counter == 1:
            self.detector_photon_counter_real += 1
           
        if self.FockBS._receivers[0].photon_counter >= 1 or self.FockBS._receivers[1].photon_counter >= 1:
            self.spd_real += 1
    
        return self.detector_photon_counter_ideal, self.spd_ideal, self.detector_photon_counter_real, self.spd_real 

    
    def received_message(self, src: str, msg):
        pass
