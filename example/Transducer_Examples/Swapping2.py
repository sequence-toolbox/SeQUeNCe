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
from example.Transducer_Examples.ConversionProtocols import DownConversionProtocol
from example.Transducer_Examples.ConversionProtocols import EmittingProtocol

from example.Transducer_Examples.SwappingProtocols import UpConversionProtocolEntangle
from example.Transducer_Examples.SwappingProtocols import Swapping
from example.Transducer_Examples.SwappingProtocols import Measure

from sequence.kernel.quantum_manager import QuantumManager
import sequence.components.circuit as Circuit


# GENERAL

NUM_TRIALS = 10
FREQUENCY = 1e9
MICROWAVE_WAVELENGTH = 999308 # nm
OPTICAL_WAVELENGTH = 1550 # nm
MEAN_PHOTON_NUM = 1

# Timeline
START_TIME = 0

ENTANGLEMENT_GENERATION_DURATION = 10 # ps
SWAPPING_DUARTION = 10 # ps
MEASURE_DURATION = 1 # ps
PERIOD = ENTANGLEMENT_GENERATION_DURATION + SWAPPING_DUARTION + MEASURE_DURATION
# Trasmon
ket1 = (0.0 + 0.0j, 1.0 + 0.0j) 
ket0 = (1.0 + 0.0j, 0.0 + 0.0j) 
state_list= [ket1, ket0] # Il trasmone in questo caso voglio che generi lo stato 10 (voglio un fotone alle microonde e 0 ottico)
# state_list= [ket1, ket0] stato 01 (0 fotoni alle microonde, 1 ottico)


# Transducer
EFFICIENCY_UP = 1

# Fock Detector
MICROWAVE_DETECTOR_EFFICIENCY_Rx = 1
MICROWAVE_DETECTOR_EFFICIENCY_Tx = 1
OPTICAL_DETECTOR_EFFICIENCY = 1

# Channel
ATTENUATION = 0
DISTANCE = 1e3


# NODES OF THE NETWORK

class SenderNode(Node):
    def __init__(self, name, timeline, node2):
        super().__init__(name, timeline)

        # Hardware setup

        # Trasmone se vogliamo usare l'emissione con la microonda a partire da un trasmone
        # self.trasmon_name = name + ".trasmon"
        # trasmon = Trasmon(name=self.trasmon_name, owner=self, timeline=timeline, wavelength=[MICROWAVE_WAVELENGTH, OPTICAL_WAVELENGTH], photon_counter=0, efficiency=1, photons_quantum_state= state_list)
        # self.add_component(trasmon)
        # self.set_first_component(self.trasmon_name)

        self.transducer_name = name + ".transducer"
        transducer = Transducer(name=self.transducer_name, owner=self, timeline=timeline, efficiency=EFFICIENCY_UP)
        self.add_component(transducer)
        transducer.attach(self)
        transducer.photon_counter = 0
        self.counter = Counter()
        transducer.attach(self.counter)
        self.set_first_component(self.transducer_name)

        # trasmon.add_receiver(transducer)

        detector_name = name + ".fockdetector1"
        detector = FockDetector(detector_name, timeline, wavelength=MICROWAVE_WAVELENGTH, efficiency=MICROWAVE_DETECTOR_EFFICIENCY_Tx)
        self.add_component(detector)
        self.set_first_component(detector_name)
        self.counter = Counter()
        detector.attach(self.counter)

        transducer.add_output([node2, detector])

        # self.emitting_protocol = EmittingProtocol(self, name + ".emitting_protocol", timeline, trasmon, transducer)
        # questo se vogliamo usare il protocollo di emissione con il transducer. Qui invece supponiamo l'emissione incorporata

        self.upconversionentangle_protocol = UpConversionProtocolEntangle(self, name + ".upconversion_protocol", timeline, transducer, node2)


class EntangleNode(Node):
    def __init__(self, name, timeline, src_list: List[str], entanglement_count):
        super().__init__(name, timeline)

        # Hardware setup
        self.fock_beam_splitter_name = name + ".FockBeamSplitter"
        fock_beam_splitter = FockBeamSplitter(name=self.fock_beam_splitter_name, owner=self, timeline=timeline, efficiency=0.5, photon_counter=0, src_list=src_list)        
        self.add_component(fock_beam_splitter)
        self.set_first_component(self.fock_beam_splitter_name)

        detector_name = name + ".detector1"
        detector = FockDetector(detector_name, timeline, efficiency=0.2)
        self.add_component(detector)
        self.set_first_component(detector_name)

        detector_name2 = name + ".detector2"
        detector2 = FockDetector(detector_name2, timeline, efficiency=1)
        self.add_component(detector2)
        self.set_first_component(detector_name2)

        fock_beam_splitter.add_output([detector, detector2])

        self.counter = Counter()
        self.counter2 = Counter()

        detector.attach(self.counter)
        detector2.attach(self.counter2)

        self.swapping_protocol = Swapping(self, name + ".swapping_protocol", timeline, fock_beam_splitter)
        self.measure_protocol = Measure(self, name + ".measure_protocol", timeline, fock_beam_splitter, entanglement_count)

    def receive_photon(self, photon, src_list):
        self.components[self.fock_beam_splitter_name].receive_photon_from_scr(photon, src_list)


if __name__ == "__main__":
    runtime = 10e12
    tl = Timeline(runtime)

    nodoprimo_name = "Nodoo1"
    nodoterzo_name = "Nodoo3"

    src_list = [nodoprimo_name, nodoterzo_name]  # the list of sources, note the order

    entanglement_count = 0

    node2 = EntangleNode("node2", tl, src_list, entanglement_count)
    node1 = SenderNode(nodoprimo_name, tl, node2)
    node3 = SenderNode(nodoterzo_name, tl, node2)

    qc1 = QuantumChannel("qc.node1.node2", tl, attenuation=ATTENUATION, distance=DISTANCE)
    qc2 = QuantumChannel("qc.node1.node3", tl, attenuation=ATTENUATION, distance=DISTANCE)
    qc1.set_ends(node1, node2.name)
    qc2.set_ends(node1, node3.name)

    tl.init()

    cumulative_time = START_TIME

    print(f"--------------------")

    for trial in range(NUM_TRIALS): 
        print(f"--------------------")
        print(f"Trial {trial}:")

        tl.run()

        # Richiamo i vari componenti dai nodi per richiamare i contatori di fotoni 
        # (mi servirà per printare i conteggi e poi per il reset)

        #
        # Componenti nodo1
        transducer = node1.get_components_by_type("Transducer")[0]
        transducer_count = transducer.photon_counter
        detector = node1.get_components_by_type("FockDetector")[0]
        detector_count = detector.photon_counter  # può servire per la percentuale dei falliti
        
        # Componenti nodo2
        fock_beam_splitter = node2.get_components_by_type("FockBeamSplitter")[0]
        fock_beam_splitter_count = fock_beam_splitter.photon_counter
        detector2 = node2.get_components_by_type("FockDetector")[0]
        detector2_count = detector2.photon_counter
        detector3 = node2.get_components_by_type("FockDetector")[1]
        detector3_count = detector3.photon_counter

        # Scheduling dei processi e degli eventi
        process1 = Process(node1.upconversionentangle_protocol, "start", [Photon]) 
        event_time1 = cumulative_time + ENTANGLEMENT_GENERATION_DURATION 
        event1 = Event(event_time1, process1)
        tl.schedule(event1)

        process3 = Process(node3.upconversionentangle_protocol, "start", [Photon]) 
        event3 = Event(event_time1, process3)
        tl.schedule(event3)

        process4 = Process(node2.swapping_protocol, "start", [Photon])
        event_time4 = event_time1 + SWAPPING_DUARTION
        event4 = Event(event_time4, process4)
        tl.schedule(event4)

        process5 = Process(node2.measure_protocol, "start", [Photon])
        event_time5 = event_time4 + MEASURE_DURATION
        event5 = Event(event_time5, process5)
        tl.schedule(event5)

        print(f"Photon count in FockBeamSplitter: {fock_beam_splitter_count}")
        print(f"Photon count in detector1: {detector2_count}")
        print(f"Photon count in detector2: {detector3_count}")

        # Reset timeline
        tl.time = 0
        tl.init()

        # Reset dei contatori
        fock_beam_splitter.photon_counter = 0
        detector2.photon_counter = 0
        detector3.photon_counter = 0

        # Incremento del conteggio totale
        cumulative_time += PERIOD

    # RESULTS
   
    print(f"Numero di entanglement generati: {entanglement_count}")
    print(f"- - - - - - - - - -")

   
