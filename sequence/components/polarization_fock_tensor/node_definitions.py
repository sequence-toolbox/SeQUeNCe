from typing import Callable
import numpy as np
import random
from copy import deepcopy

from sequence.kernel.timeline import Timeline
from sequence.components.photon import Photon
from sequence.topology.node import Node
from sequence.components.optical_channel import ClassicalChannel

from .optical_channel import QuantumChannel
from .light_source import SPDCSource
from .detector import QSDetectorFockDirect
from .rotator import Rotator
# from sequence.components.polarizationFock_Tensor.beam_splitter import Beamsplitter

from sequence.utils.encoding import polarizationFock


# retrieval efficiency as function of storage time for absorptive quantum memory, using exponential decay model
def add_quantum_channel(node1: Node, node2: Node, timeline: Timeline, **kwargs):
    name = "_".join(["qc", node1.name, node2.name])
    qc = QuantumChannel(name, timeline, **kwargs)
    qc.set_ends(node1, node2.name)
    return qc
def add_classical_channel(node1: Node, node2: Node, timeline: Timeline, **kwargs):
    name = "_".join(["cc", node1.name, node2.name])
    cc = ClassicalChannel(name, timeline, **kwargs)
    cc.set_ends(node1, node2.name)
    return cc


class PolarizationDistributionNode(Node):
    def __init__(self, name: str, timeline: "Timeline", signal_node_name, idler_node_name, params):
        super().__init__(name, timeline)

        self.num_emissions = params["MODE_NUM"]

        self.idler_node_name = idler_node_name
        self.signal_node_name = signal_node_name

        self.spdc_name = name + ".spdc_source"
        spdc = SPDCSource(self.spdc_name, timeline, wavelengths=[params["QUANTUM_WAVELENGTH"], params["QUANTUM_WAVELENGTH"]],
                          frequency=params["SPDC_FREQUENCY"], mean_photon_num=params["MEAN_PHOTON_NUM"], encoding_type=polarizationFock, polarization_fidelity=params["POLARIZATION_FIDELITY"])

        self.add_component(spdc)

        # We receive the emitted photons back here so we can route them to the corresponding Idler or Signal node based on any addional stuff you may want to do.
        # This was originally meant to work with the memory and hence, may be redundant here. 
        spdc.add_receiver(self)
        spdc.add_receiver(self)

    def start(self):
        # states = [[1/np.sqrt(2),1/np.sqrt(2)]] * self.num_emissions
        self.components[self.spdc_name].emit(self.num_emissions)

    def set_source_mpn(self, mpn):
        self.components[self.spdc_name].mean_photon_num = mpn

    def get(self, photon: "Photon", **kwargs):
        # print("sending photons at node.")
        if photon.name == "signal":
            # print("source node signal node name:", self.signal_node_name)
            # print("sending signal photon")
            self.send_qubit(self.signal_node_name, photon)
        elif photon.name == "idler":
            # print("source node idler node name:", self.idler_node_name)
            # print("sending idler photon")
            self.send_qubit(self.idler_node_name, photon)

class PolarizationReceiverNode(Node):
    def __init__(self, name, timeline, params, detectors, port_list):
        # print("receiver node")
        super().__init__(name, timeline)


        # The detectors are now set 
        # if type(src) == str:
        #     src_list = [src+"_det0", src+"_det1"]
        # else:
        #     src_list = src
        #     for i in range(len(src)):
        #         src_list[i] += f"_det{i}"

        # print("receiver node node src_list:", src_list)

        # self.detectors = QSDetectorFockDirect(name = self.name+".detectors", timeline = timeline, src_list = src_list)
        # self.detectors.set_detector(0, efficiency=params["SIGNAL_DET_EFFICIENCY"], dark_count=params["SIGNAL_DET_DARK"], count_rate=int(25e6), time_resolution=params["RESOLUTION"], dead_time=params["SIGNAL_DET_DEAD"])
        # self.detectors.set_detector(1, efficiency=params["IDLER_DET_EFFICIENCY"], dark_count=params["IDLER_DET_DARK"], count_rate=int(25e6), time_resolution=params["RESOLUTION"], dead_time=params["IDLER_DET_DEAD"])
        # 
        self.detectors = detectors
        self.port_list = port_list
        self.detectors.attach(self)

        self.signal_rotator = Rotator("signal_polarizer", timeline)
        self.signal_rotator.add_receiver(self.detectors)

        self.idler_rotator = Rotator("idler_polarizer", timeline)
        self.idler_rotator.add_receiver(self.detectors)
        self.idler_rotator_name = self.idler_rotator.name
        
        self.add_component(self.signal_rotator)
        self.add_component(self.idler_rotator)
        self.add_component(self.detectors)
        self.first_component_name = self.signal_rotator.name
        self.first_proxy_component_name = self.idler_rotator.name
        
        # self.detections = {self.signal_detector:[], self.idler_detector:[]}
        self.temporal_coincidence_window = params["TEMPORAL_COINCIDENCE_WINDOW"]

        self.signal_rotator_angle = 0
        self.idler_rotator_angle = 0

        self.idler_rotation_detection_probs = []
        self.signal_rotation_detection_probs = []

        self.idler_rotation_detection_vars = []
        self.signal_rotation_detection_vars = []

        self.temp_received_photon = None
        

    def receive_qubit(self, src: str, qubit) -> None:
        rotated_photon = self.components[self.first_component_name].get(qubit, meas_basis = "H")

        if self.temp_received_photon == None:
            self.temp_received_photon = rotated_photon
        else:
            self.detectors.get(rotated_photon, port=self.port_list[0], meas_basis = "H")
            self.detectors.get(self.temp_received_photon, port=self.port_list[1], meas_basis = "H")
            self.temp_received_photon = None
            

    def receive_proxy_qubit(self, src: str, qubit) -> None:
        rotated_photon = self.components[self.first_proxy_component_name].get(qubit)

        if self.temp_received_photon == None:
            self.temp_received_photon = rotated_photon
        else:
            self.detectors.get(rotated_photon, port=self.port_list[1], meas_basis = "H")
            self.detectors.get(self.temp_received_photon, port=self.port_list[0], meas_basis = "H")
            self.temp_received_photon = None
        

    def set_det_eff(self, eff):
        self.detectors.detectors[0].efficiency = eff
        self.detectors.detectors[1].efficiency = eff

    def rotateSignal(self, angle):
        self.signal_rotator.rotate(angle)
        
    def rotateIdler(self, angle):
        self.idler_rotator.rotate(angle)

    def collectSignalData(self):
        # print("meas probs:", self.detectors.meas_prob)
        self.signal_rotation_detection_probs.append(deepcopy(self.detectors.meas_prob))
        self.signal_rotation_detection_vars.append(deepcopy(self.detectors.meas_var))

    def reset(self):
        """
        Signifies the end of one run of the entanglement distribution protocol. 
        """
        self.signal_polarizer_angle = 0
        self.idler_polarizer_angle = 0
        
        self.idler_rotation_detection_probs.append(self.signal_rotation_detection_probs)
        self.idler_rotation_detection_vars.append(self.signal_rotation_detection_vars)
        
        self.signal_rotation_detection_probs = []
        self.signal_rotation_detection_vars = []
        


    def trigger(self, detector, info):
        self.detections[detector][-1].append(info["time"])

    def get_data(self):
        # This is the get_data method when you have only 2 detectors. 
        self.coincidences = []
        self.signal_singles = []
        self.idler_singles = []
        self.standard_deviations = []

        print("received probs:", self.idler_rotation_detection_probs)
        print("received vars:", self.idler_rotation_detection_vars)

        # We start self.idler_rotation_detection_probs from 1 because during the first reset, an empty 
        # list is added to self.idler_rotation_detection_probs. So, we ignore that here. 
        # print("vars are:")
        # for i in self.idler_rotation_detection_vars:
        #     print(i)
        for idler_angle_detection_probs in self.idler_rotation_detection_probs:
            coincidence_probs = []
            singles_probs_signal = []
            singles_probs_idler = []
            # Looking at the detection probs for one idler angle. The size of the array is the number of signal angles. 
            for detection_probs in idler_angle_detection_probs:
                coincidence_probs.append(detection_probs["11"])
                singles_probs_signal.append(detection_probs["11"]+detection_probs["10"])
                singles_probs_idler.append(detection_probs["11"]+detection_probs["01"])
                
            self.coincidences.append(coincidence_probs)
            self.signal_singles.append(singles_probs_signal)
            self.idler_singles.append(singles_probs_idler)

        try:
            for idler_angle_detection_var in self.idler_rotation_detection_vars:
                coincidence_std = []
                # Looking at the detection probs for one idler angle. The size of the array is the number of signal angles. 
                for detection_squared_probs in idler_angle_detection_var:
                    coincidence_std.append(np.sqrt(detection_squared_probs["11"] - detection_probs["11"]**2)/np.sqrt(10**9))
                self.standard_deviations.append(coincidence_std)
        except:
            pass

        return self.coincidences, self.signal_singles, self.idler_singles, self.standard_deviations


class BSMNode(Node):
    def __init__(self, name, timeline, params, detectors, port_list):
        # print("receiver node")
        super().__init__(name, timeline)
        
        # if type(src) == str:
        #     self.src_list = [src+"_det0", src+"_det1"]
        # else:
        #     self.src_list = src
        #     for i in range(len(src)):
        #         self.src_list[i] += f"_det{i}"
        
        # print("bsm node src_list:", self.src_list)
        
        # self.detectors = QSDetectorFockDirect(name = self.name+".detectors", timeline = timeline, src_list = self.src_list)

        self.detectors = detectors
        self.port_list = port_list
        # This isn't used but could be used to run trigger commands. 
        self.detectors.attach(self)


        # Add BSM component. 

        # self.beamsplitter = Beamsplitter("beamsplitter", timeline)
        # self.add_component(self.beamsplitter)
        # self.beamsplitter.add_receiver(self.detectors)
        # self.beamsplitter.add_receiver(self.detectors)



        ############### Add beam splitter here. ######################
        # self.signal_rotator = Rotator("signal_polarizer", timeline)
        # self.signal_rotator.add_receiver(self.detectors)

        # self.idler_rotator = Rotator("idler_polarizer", timeline)
        # self.idler_rotator.add_receiver(self.detectors)
        # self.idler_rotator_name = self.idler_rotator.name
        
        # self.add_component(self.signal_rotator)
        # self.add_component(self.idler_rotator)

        self.first_photon_received = False

        # self.first_component_name = self.beamsplitter.name
        # self.first_proxy_component_name = self.beamsplitter.name


        self.add_component(self.detectors)
        # self.first_component_name = self.signal_rotator.name
        
        # self.detections = {self.signal_detector:[], self.idler_detector:[]}
        self.temporal_coincidence_window = params["TEMPORAL_COINCIDENCE_WINDOW"]
        

    # def receive_qubit(self, src: str, qubit) -> None:
    #     # print("receiving qubit at node")
    #     self.components[self.first_component_name].get(qubit, src="signal")

    def receive_qubit(self, src: str, qubit) -> None:
        # print("receiving qubit at node")

        if self.first_photon_received:
            # print("qubit:", qubit)
            # print("BSM received:", self.timeline.quantum_manager.states[qubit.quantum_state].keys, self.timeline.quantum_manager.states[self.first_photon.quantum_state].keys)
            self.components[self.first_component_name].get(photon1 = qubit, photon2 = self.first_photon, ports = self.port_list)
            self.first_photon_received = False
        else:
            self.first_photon_received = True
            self.first_photon = qubit

    def receive_proxy_qubit(self, src: str, qubit) -> None:
        # print("receiving qubit at node")
        # self.components[self.first_proxy_component_name].get(qubit, src=src+"_det1")
        if self.first_photon_received:
            # print("BSM received:", self.timeline.quantum_manager.states[qubit.quantum_state].keys, self.timeline.quantum_manager.states[self.first_photon.quantum_state].keys)
            self.components[self.first_component_name].get(photon1 = self.first_photon, photon2 = qubit, ports = self.port_list)
            self.first_photon_received = False
        else:
            self.first_photon_received = True
            self.first_photon = qubit

    def set_det_eff(self, eff):
        self.detectors.detectors[0].efficiency = eff
        self.detectors.detectors[1].efficiency = eff


    def trigger(self, detector, info):
        self.detections[detector][-1].append(info["time"])

    def get_data(self):
        self.coincidences = []
        self.signal_singles = []
        self.idler_singles = []

        # We start self.idler_rotation_detection_probs from 1 because during the first reset, an empty 
        # list is added to self.idler_rotation_detection_probs. So, we ignore that here. 
        for idler_angle_detection_probs in self.idler_rotation_detection_probs:
            coincidence_probs = []
            singles_probs_signal = []
            singles_probs_idler = []
            # print("idler_angle_detection_probs", idler_angle_detection_probs)
            for detection_probs in idler_angle_detection_probs:
                coincidence_probs.append(detection_probs["11"])
                singles_probs_signal.append(detection_probs["11"]+detection_probs["10"])
                singles_probs_idler.append(detection_probs["11"]+detection_probs["01"])
            self.coincidences.append(coincidence_probs)
            self.signal_singles.append(singles_probs_signal)
            self.idler_singles.append(singles_probs_idler)
        return self.coincidences, self.signal_singles, self.idler_singles


# We have 2 receivers - the signal and idler. The signal is recieved by the 
# actual receiver class itself. However, we want to send the idler to the same place to 
# perform collective measurement. This proxyReceiver hence enables us to do so. Since this is 
# always the idler, the get method has src = "idler" by default. 
class proxyReceiver(Node):
    def __init__(self, name, timeline, receiver:"PolarizationReceiverNode"):
        super().__init__(name, timeline)
        self.add_component(self)
        self.receiver = receiver
        self.first_component_name = self.name

    def receive_qubit(self, src: str, qubit) -> None:
        self.receiver.receive_proxy_qubit(src, qubit)
        # self.receiver.components[self.receiver.idler_rotator_name].get(qubit, src="idler")
        