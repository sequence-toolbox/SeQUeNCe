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


class UpConversionProtocol(Protocol):


    def __init__(self, own: "Node", name: str, tl: "Timeline", transducer: "Transducer", node: "Node"):
    #def __init__(self, own: "Node", name: str, tl: "Timeline", transducer: "Transducer"):

        super().__init__(own, name)
        self.owner = own
        self.name = name
        self.tl = tl
        self.transducer = transducer
        #self.transmon = transmon
        self.node = node


    def start(self) -> None:
        """start the protocol  
        
        NOTE (caitao, 12/21/2024): this start() method should be empty. 
             The content of this function should be at a new convert() method that receives photons from the from the transducer

        Args:
            photon (Photon): photon from arrived at the transducer from the transmon
        """

    def convert(self, photon) -> None:

        #if self.transducer.photon_counter > 0:   # NOTE shouldn't use this photon_counter to determine
            #custom_gate = get_conversion_matrix(self.transducer.efficiency)

            #transmon_state_vector = np.array(self.transmon.input_quantum_state).reshape((4, 1))
            #photon_state = Qobj(transmon_state_vector, dims=[[4], [1]])

            #new_photon_state = custom_gate * photon_state
            #self.transducer.quantum_state = new_photon_state.full().flatten()

            #print(f"Transducer at Tx quantum state: {self.transducer.quantum_state}")
            print("Up-conversion starts")
            print(f"Transducer first receiver: {self.transducer._receivers[0]}")
            print(f"Transducer second receiver: {self.transducer._receivers[1]}")
            print("Transducer efficiency is: ", self.transducer.efficiency)


            if random.random() < self.transducer.efficiency:
                photon.wavelength = OPTICAL_WAVELENGTH
                print("Successful up-conversion")
                print(f"The photon is: {photon} with wavelength: {photon.wavelength}")
                #self.transducer.output_quantum_state = [0.0 + 0.0j, 0.0 + 0.0j, 1.0 + 0.0j, 0.0 + 0.0j]
                #print(f"State after successful up-conversion: {self.transducer.output_quantum_state}")
                print(f"Transducer receiver: {self.transducer._receivers[0]}")
                #self.transducer._receivers[0].receive(photon)  # Use self.transducer.src_list
                self.transducer._receivers[0].receive(photon, [self.node.name])
                

                #self.transducer._receivers[0].receive_qubit(photon, [self.node.name])
                # #ITALIANO: QUESTOOOOOO
                #self.transducer._receivers[0].transmit(photon)
                #self.transducer._receivers[0].transmit(photon, ["node"])  # Passa una lista con il nome del nodo sorgente
                #self.transducer._receivers[0].receive_photon(self.node, photon)  # NOTE the receiver should be the quantum channel OK DONE
            
            else:
                photon.wavelength = MICROWAVE_WAVELENGTH
                print("FAILED up-conversion")
                self.transducer._receivers[1].get(photon)
                pass

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
        #self.measurement_protocol = measure_protocol

    def start(self, photon: Photon) -> None:
        pass
    
    #def swap(self, photon: Photon) -> None:

        receivers = self.FockBS._receivers
        photon_count = self.FockBS.photon_counter

        print("ENTANGLEMENT SWAPPING PROTOCOL STARTS AT time: ", self.tl.now())
        print(f"Detector efficiency is: ", self.FockBS._receivers[0].efficiency)
        print(f"Detector efficiency is: ", self.FockBS._receivers[1].efficiency)


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

            #selected_receiver.photon_counter2=+2 #ideal
            
            #if random.random() < selected_receiver.efficiency: #real
            #    selected_receiver.photon_counter += 1

            
            #(photon) #IDEALE (quindi efficienza 1)
            #selected_receiver.get(photon)
            #selected_receiver.get_2(photon)
            #self.measurement_protocol.measure(photon)  # Chiamata al protocollo measure

     

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
        self.spd_real= 0  

        self.detector_photon_counter_ideal = 0
        self.spd_ideal= 0 

    def start(self, photon: Photon) -> None:
        
        print("MEASUREMENT PROTOCOL STARTS AT time: ", self.tl.now())
        #def measure(self, photon: Photon) -> None:

        #ITALIANOOOOOOO
        print("--------")
        print("CASO DETECTOR IDEALE")

        if self.FockBS._receivers[0].photon_counter2 == 0 and self.FockBS._receivers[1].photon_counter2 == 0:
            print("No photon reach the beam splitter")
    
        if self.FockBS._receivers[0].photon_counter2 == 1 or self.FockBS._receivers[1].photon_counter2 == 1:
            self.detector_photon_counter_ideal += 1
        #ITALIANOOOO
        #print("FATTO IL PRIMO IF")
        #print("Il conteggio del photon counter ideal è ", self.detector_photon_counter_ideal)

        if self.FockBS._receivers[0].photon_counter2 >= 1 or self.FockBS._receivers[1].photon_counter2 >= 1:
            self.spd_ideal += 1
        #print("FATTO IL SECONDO IF")
        #print("Il conteggio del single detecort ideal è ", self.spd_ideal)



        print("CASO DETECTOR REALE")
        print("efficinecy del primo receiver: ", self.FockBS._receivers[0].efficiency)
        print("efficinecy del secondo receiver: ", self.FockBS._receivers[1].efficiency)

        if self.FockBS._receivers[0].photon_counter == 1 or self.FockBS._receivers[1].photon_counter == 1:
            self.detector_photon_counter_real += 1

        if self.FockBS._receivers[0].photon_counter >= 1 or self.FockBS._receivers[1].photon_counter >= 1:
            self.spd_real += 1



    def get_detector_photon_counter_ideal(self):
        return self.detector_photon_counter_ideal

    def get_spd_ideal(self):
        return self.spd_ideal
    

    def get_detector_photon_counter_real(self):
        return self.detector_photon_counter_real

    def get_spd_real(self):
        return self.spd_real
    
   

    def received_message(self, src: str, msg):
        pass
