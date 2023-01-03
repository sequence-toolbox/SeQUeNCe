"""The main script for simulating experiment of entanglement generation between two remote AFC absorptive quantum memories.

There are 4 nodes involved: 2 memory nodes, 1 entangling node (for BSM) and 1 measurement node (for measurement of retrieved photonic state).
Each memory node is connected with both entangling node and measurement node, but there is no direct connection between memory nodes.

Each memory node contains an AFC memory instance and an SPDC source instance.
The entangling node contains a QSDetectorFockInterference instance (BSM device with a beamsplitter and two photon detectors behind).
The measurement node contians a QSDetectorFockDirect instance and a QSDetectorFockInterference instance, for measurement of 
    diagonal and off-diagonal elements of the effective 4-d density matrix, respectively.
"""

from typing import List, Callable, TYPE_CHECKING
from pathlib import Path
from copy import copy

if TYPE_CHECKING:
    from sequence.components.photon import Photon

from json import dump
import numpy as np

from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.kernel.timeline import Timeline
from sequence.kernel.quantum_manager import FOCK_DENSITY_MATRIX_FORMALISM
from sequence.components.detector import QSDetectorFockDirect, QSDetectorFockInterference
from sequence.components.light_source import SPDCSource
from sequence.components.memory import AbsorptiveMemory
from sequence.components.optical_channel import QuantumChannel
from sequence.components.photon import Photon
from sequence.topology.node import Node
from sequence.protocol import Protocol
from sequence.kernel.quantum_utils import *  # only for manual calculation and should not be used in simulation


# define simulation constants

# quantum manager
TRUNCATION = 2  # truncation of Fock space (=dimension-1)

# photon sources
TELECOM_WAVELENGTH = 1436  # telecom band wavelength of SPDC source idler photon
WAVELENGTH = 606  # wavelength of AFC memory resonant absorption, of SPDC source signal photon
SPDC_FREQUENCY = 80e6  # frequency of both SPDC sources' photon creation (same as memory frequency and detector count rate)
MEAN_PHOTON_NUM1 = 0.1  # mean photon number of SPDC source on node 1
MEAN_PHOTON_NUM2 = 0.1  # mean photon number of SPDC source on node 2

# detectors
BSM_DET1_EFFICIENCY = 0.6  # efficiency of detector 1 of BSM
BSM_DET2_EFFICIENCY = 0.6  # efficiency of detector 2 of BSM
BSM_DET1_DARK = 150  # Dark count rate (Hz)
BSM_DET2_DARK = 150
MEAS_DET1_EFFICIENCY = 0.6  # efficiency of detector 1 of DM measurement
MEAS_DET2_EFFICIENCY = 0.6  # efficiency of detector 2 of DM measurement
MEAS_DET1_DARK = 150
MEAS_DET2_DARK = 150

# fibers
DIST_ANL_ERC = 20  # distance between ANL and ERC, in km
DIST_HC_ERC = 20  # distance between HC and ERC, in km
ATTENUATION = 0.2  # attenuation rate of optical fibre (in dB/km)
DELAY_CLASSICAL = 5e-3  # delay for classical communication between BSM node and memory nodes (in s)

# memories
MODE_NUM = 100  # number of temporal modes of AFC memory (same for both memories)
MEMO_FREQUENCY1 = SPDC_FREQUENCY  # frequency of memory 1
MEMO_FREQUENCY2 = SPDC_FREQUENCY  # frequency of memory 2
ABS_EFFICIENCY1 = 0.35  # absorption efficiency of AFC memory 1
ABS_EFFICIENCY2 = 0.35  # absorption efficiency of AFC memory 2
PREPARE_TIME1 = 0  # time required for AFC structure preparation of memory 1
PREPARE_TIME2 = 0  # time required for AFC structure preparation of memory 2
COHERENCE_TIME1 = -1  # spin coherence time for AFC memory 1 spinwave storage, -1 means infinite time
COHERENCE_TIME2 = -1  # spin coherence time for AFC memory 2 spinwave storage, -1 means infinite time
AFC_LIFETIME1 = -1  # AFC structure lifetime of memory 1, -1 means infinite time
AFC_LIFETIME2 = -1  # AFC structure lifetime of memory 2, -1 means infinite time
DECAY_RATE1 = 4.3e-8  # retrieval efficiency decay rate for memory 1
DECAY_RATE2 = 4.3e-8  # retrieval efficiency decay rate for memory 2

# experiment settings
time = int(1e12)
calculate_fidelity_direct = True
calculate_rate_direct = True
num_direct_trials = 200
num_bs_trials_per_phase = 50
phase_settings = np.linspace(0, 2*np.pi, num=20, endpoint=False)


# function to generate standard pure Bell state for fidelity calculation
def build_bell_state(truncation, sign, phase=0, formalism="dm"):
    """Generate standard Bell state which is heralded in ideal BSM.

    For comparison with results from imperfect parameter choices.
    """

    basis0 = np.zeros(truncation+1)
    basis0[0] = 1
    basis1 = np.zeros(truncation+1)
    basis1[1] = 1
    basis10 = np.kron(basis1, basis0)
    basis01 = np.kron(basis0, basis1)
    
    if sign == "plus":
        ket = (basis10 + np.exp(1j*phase)*basis01)/np.sqrt(2)
    elif sign == "minus":
        ket = (basis10 - np.exp(1j*phase)*basis01)/np.sqrt(2)
    else:
        raise ValueError("Invalid Bell state sign type " + sign)

    dm = np.outer(ket, ket.conj())

    if formalism == "dm":
        return dm
    elif formalism == "ket":
        return ket
    else:
        raise ValueError("Invalid quantum state formalism " + formalism)


# retrieval efficiency as function of storage time for absorptive quantum memory, using exponential decay model
def efficiency1(t: int) -> float:
    return np.exp(-t*DECAY_RATE1)


def efficiency2(t: int) -> float:
    return np.exp(-t*DECAY_RATE2)


def add_channel(node1: Node, node2: Node, timeline: Timeline, **kwargs):
    name = "_".join(["qc", node1.name, node2.name])
    qc = QuantumChannel(name, timeline, **kwargs)
    qc.set_ends(node1, node2.name)
    return qc


# protocol to control photon emission on end node
class EmitProtocol(Protocol):
    def __init__(self, own: "EndNode", name: str, other_node: str, photon_pair_num: int,
                 source_name: str, memory_name: str):
        """Constructor for Emission protocol.

        Args:
            own (EndNode): node on which the protocol is located.
            name (str): name of the protocol instance.
            other_node (str): name of the other node to generate entanglement with
            photon_pair_num (int): number of output photon pulses to send in one execution.
            source_name (str): name of the light source on the node.
            memory_name (str): name of the memory on the node.
        """

        super().__init__(own, name)
        self.other_node = other_node
        self.num_output = photon_pair_num
        self.source_name = source_name
        self.memory_name = memory_name

    def start(self):
        if not self.own.components[self.memory_name].is_prepared:
            self.own.components[self.memory_name]._prepare_AFC()
        
        states = [None] * self.num_output  # for Fock encoding only list length matters and list elements do not matter
        source = self.own.components[self.source_name]
        source.emit(states)

    def received_message(self, src: str, msg):
        pass


class EndNode(Node):
    """Node for each end of the network (the memory node).

    This node stores an SPDC photon source and a quantum memory.
    The properties of attached devices are made customizable for each individual node.
    """

    def __init__(self, name: str, timeline: "Timeline", other_node: str, bsm_node: str, measure_node: str,
                 mean_photon_num: float, spdc_frequency: float, memo_frequency: float, abs_effi: float,
                 afc_efficiency: Callable, mode_number: int):
        super().__init__(name, timeline)

        self.bsm_name = bsm_node
        self.meas_name = measure_node

        # hardware setup
        self.spdc_name = name + ".spdc_source"
        self.memo_name = name + ".memory"
        spdc = SPDCSource(self.spdc_name, timeline, wavelengths=[TELECOM_WAVELENGTH, WAVELENGTH],
                          frequency=spdc_frequency, mean_photon_num=mean_photon_num)
        memory = AbsorptiveMemory(self.memo_name, timeline, frequency=memo_frequency,
                                  absorption_efficiency=abs_effi, afc_efficiency=afc_efficiency,
                                  mode_number=mode_number, wavelength=WAVELENGTH, destination=measure_node)
        self.add_component(spdc)
        self.add_component(memory)
        spdc.add_receiver(self)
        spdc.add_receiver(memory)
        memory.add_receiver(self)

        # protocols
        self.emit_protocol = EmitProtocol(self, name + ".emit_protocol", other_node, mode_number, self.spdc_name, self.memo_name)

    def get(self, photon: "Photon", **kwargs):
        dst = kwargs.get("dst")
        if dst is None:
            # from spdc source: send to bsm node
            self.send_qubit(self.bsm_name, photon)
        else:
            # from memory: send to destination (measurement) node
            self.send_qubit(dst, photon)


class EntangleNode(Node):
    def __init__(self, name: str, timeline: "Timeline", src_list: List[str]):
        super().__init__(name, timeline)

        # hardware setup
        self.bsm_name = name + ".bsm"
        # assume no relative phase between two input optical paths
        bsm = QSDetectorFockInterference(self.bsm_name, timeline, src_list)
        self.add_component(bsm)
        bsm.attach(self)
        self.set_first_component(self.bsm_name)
        self.resolution = max([d.time_resolution for d in bsm.detectors])

        # detector parameter setup
        bsm.set_detector(0, efficiency=BSM_DET1_EFFICIENCY, count_rate=SPDC_FREQUENCY, dark_count=BSM_DET1_DARK)
        bsm.set_detector(1, efficiency=BSM_DET2_EFFICIENCY, count_rate=SPDC_FREQUENCY, dark_count=BSM_DET1_DARK)

    def receive_qubit(self, src: str, qubit) -> None:
        self.components[self.first_component_name].get(qubit, src=src)

    def get_detector_entries(self, detector_name: str, start_time: int, num_bins: int, frequency: float):
        """Returns detection events for density matrix measurement. Used to determine BSM result.

        Args:
            detector_name (str): name of detector to get measurements from.
            start_time (int): simulation start time of when photons received.
            num_bins (int): number of arrival bins
            frequency (float): frequency of photon arrival (in Hz).

        Returns:
            List[int]: list of length (num_bins) with result for each time bin.
        """

        trigger_times = self.components[detector_name].get_photon_times()
        return_res = [0] * num_bins

        for time in trigger_times[0]:
            closest_bin = int(round((time - start_time) * frequency * 1e-12))
            expected_time = (float(closest_bin) * 1e12 / frequency) + start_time
            if abs(expected_time - time) < self.resolution and 0 <= closest_bin < num_bins:
                return_res[closest_bin] += 1

        for time in trigger_times[1]:
            closest_bin = int(round((time - start_time) * frequency * 1e-12))
            expected_time = (float(closest_bin) * 1e12 / frequency) + start_time
            if abs(expected_time - time) < self.resolution and 0 <= closest_bin < num_bins:
                return_res[closest_bin] += 2

        return return_res


class MeasureNode(Node):
    def __init__(self, name: str, timeline: "Timeline", other_nodes: List[str]):
        super().__init__(name, timeline)

        self.direct_detector_name = name + ".direct"
        direct_detector = QSDetectorFockDirect(self.direct_detector_name, timeline, other_nodes)
        self.add_component(direct_detector)
        direct_detector.attach(self)

        self.bs_detector_name = name + ".bs"
        bs_detector = QSDetectorFockInterference(self.bs_detector_name, timeline, other_nodes)
        self.add_component(bs_detector)
        bs_detector.add_receiver(self)

        self.set_first_component(self.direct_detector_name)

        # time resolution of SPDs
        self.resolution = max([d.time_resolution for d in direct_detector.detectors + bs_detector.detectors])

        # detector parameter setup
        direct_detector.set_detector(0, efficiency=MEAS_DET1_EFFICIENCY, count_rate=SPDC_FREQUENCY, dark_count=MEAS_DET1_DARK)
        direct_detector.set_detector(1, efficiency=MEAS_DET2_EFFICIENCY, count_rate=SPDC_FREQUENCY, dark_count=MEAS_DET2_DARK)
        bs_detector.set_detector(0, efficiency=MEAS_DET1_EFFICIENCY, count_rate=SPDC_FREQUENCY, dark_count=MEAS_DET1_DARK)
        bs_detector.set_detector(1, efficiency=MEAS_DET2_EFFICIENCY, count_rate=SPDC_FREQUENCY, dark_count=MEAS_DET2_DARK)

    def receive_qubit(self, src: str, qubit) -> None:
        self.components[self.first_component_name].get(qubit, src=src)

    def set_phase(self, phase: float):
        self.components[self.bs_detector_name].set_phase(phase)

    def get_detector_entries(self, detector_name: str, start_time: int, num_bins: int, frequency: float):
        """Returns detection events for density matrix measurement.

        Args:
            detector_name (str): name of detector to get measurements from.
            start_time (int): simulation start time of when photons received.
            num_bins (int): number of arrival bins
            frequency (float): frequency of photon arrival (in Hz).

        Returns:
            List[int]: list of length (num_bins) with result for each time bin.
        """

        trigger_times = self.components[detector_name].get_photon_times()
        return_res = [0] * num_bins

        for time in trigger_times[0]:
            closest_bin = int(round((time - start_time) * frequency * 1e-12))
            expected_time = (float(closest_bin) * 1e12 / frequency) + start_time
            if abs(expected_time - time) < self.resolution and 0 <= closest_bin < num_bins:
                return_res[closest_bin] += 1

        for time in trigger_times[1]:
            closest_bin = int(round((time - start_time) * frequency * 1e-12))
            expected_time = (float(closest_bin) * 1e12 / frequency) + start_time
            if abs(expected_time - time) < self.resolution and 0 <= closest_bin < num_bins:
                return_res[closest_bin] += 2

        return return_res


if __name__ == "__main__":

    """Setup Simulation"""

    """ For generating effective fidelity 2-d plot
    dim = 100 
    
    mean_num1_list = np.linspace(0.02, 0.1, num=dim, endpoint=True)
    mean_num2_list = np.linspace(0.02, 0.1, num=dim, endpoint=True)

    fidelity_mat = np.zeros((dim,dim))
    idx1 = -1
    idx2 = -1
    for mean_num1 in mean_num1_list:
        idx1 += 1

        for mean_num2 in mean_num2_list:
            idx2 += 1
            
            tl = Timeline(time, formalism=FOCK_DENSITY_MATRIX_FORMALISM, truncation=TRUNCATION)

            anl_name = "Argonne"
            hc_name = "Harper Court"
            erc_name = "Eckhardt Research Center BSM"
            erc_2_name = "Eckhardt Research Center Measurement"
            seeds = [1, 2, 3, 4]
            src_list = [anl_name, hc_name]  # the list of sources, note the order
        
            anl = EndNode(anl_name, tl, hc_name, erc_name, erc_2_name, mean_photon_num=mean_num1,
                          spdc_frequency=SPDC_FREQUENCY, memo_frequency=MEMO_FREQUENCY1, abs_effi=ABS_EFFICIENCY1,
                          afc_efficiency=efficiency1, mode_number=MODE_NUM)
            hc = EndNode(hc_name, tl, anl_name, erc_name, erc_2_name, mean_photon_num=mean_num2,
                         spdc_frequency=SPDC_FREQUENCY, memo_frequency=MEMO_FREQUENCY2, abs_effi=ABS_EFFICIENCY2,
                         afc_efficiency=efficiency2, mode_number=MODE_NUM)
            erc = EntangleNode(erc_name, tl, src_list)
            erc_2 = MeasureNode(erc_2_name, tl, src_list)
        
            for seed, node in zip(seeds, [anl, hc, erc, erc_2]):
                node.set_seed(seed)
        
            # extend fiber lengths to be equivalent
            fiber_length = max(DIST_ANL_ERC, DIST_HC_ERC)
        
            qc1 = add_channel(anl, erc, tl, distance=fiber_length, attenuation=ATTENUATION, frequency=10e7)
            qc2 = add_channel(hc, erc, tl, distance=fiber_length, attenuation=ATTENUATION, frequency=10e7)
            qc3 = add_channel(anl, erc_2, tl, distance=fiber_length, attenuation=ATTENUATION, frequency=10e7)
            qc4 = add_channel(hc, erc_2, tl, distance=fiber_length, attenuation=ATTENUATION, frequency=10e7)
        
            tl.init()
        
            # Pre-simulation explicit calculation of entanglement fidelity upon successful BSM
        
            # use non-transmitted Photon as interface with existing methods in SeQUeNCe
            spdc_anl = anl.components[anl.spdc_name]
            spdc_hc = hc.components[hc.spdc_name]
            memo_anl = anl.components[anl.memo_name]
            memo_hc = hc.components[hc.memo_name]
            channel_anl = anl.qchannels[erc_name]
            channel_hc = hc.qchannels[erc_name]
            bsm = erc.components[erc.bsm_name]
        
            # photon0: idler, photon1: signal
            photon0_anl = Photon("", spdc_anl.timeline, wavelength=spdc_anl.wavelengths[0], location=spdc_anl, encoding_type=spdc_anl.encoding_type, use_qm=True)
            photon1_anl = Photon("", spdc_anl.timeline, wavelength=spdc_anl.wavelengths[1], location=spdc_anl, encoding_type=spdc_anl.encoding_type, use_qm=True)
            # set shared state to squeezed state
            state_spdc_anl = spdc_anl._generate_tmsv_state()
            keys = [photon0_anl.quantum_state, photon1_anl.quantum_state]
            tl.quantum_manager.set(keys, state_spdc_anl)
        
            photon0_hc = Photon("", spdc_hc.timeline, wavelength=spdc_hc.wavelengths[0], location=spdc_hc, encoding_type=spdc_hc.encoding_type, use_qm=True)
            photon1_hc = Photon("", spdc_hc.timeline, wavelength=spdc_hc.wavelengths[1], location=spdc_hc, encoding_type=spdc_hc.encoding_type, use_qm=True)
            # set shared state to squeezed state
            state_spdc_hc = spdc_hc._generate_tmsv_state()
            keys = [photon0_hc.quantum_state, photon1_hc.quantum_state]
            tl.quantum_manager.set(keys, state_spdc_hc)
        
            # photon loss upon absorption by memories
            key_anl_memo = photon1_anl.quantum_state
            loss_anl_memo = 1 - memo_anl.absorption_efficiency
            tl.quantum_manager.add_loss(key_anl_memo, loss_anl_memo)
            key_hc_memo = photon1_hc.quantum_state
            loss_hc_memo = 1 - memo_hc.absorption_efficiency
            tl.quantum_manager.add_loss(key_hc_memo, loss_hc_memo)
    
            # transmission loss through optical fibres (overwrites previous variables)
            key_anl_pho = photon0_anl.quantum_state
            loss_anl_pho = channel_anl.loss
            tl.quantum_manager.add_loss(key_anl_pho, loss_anl_pho)
            key_hc_pho = photon0_hc.quantum_state
            loss_hc_pho = channel_anl.loss
            tl.quantum_manager.add_loss(key_hc_pho, loss_hc_pho)
        
            # QSDetector measurement and remaining state after partial trace
            povms = bsm.povms
            povm_tuple = tuple([tuple(map(tuple, povm)) for povm in povms])
            keys = [photon0_anl.quantum_state, photon0_hc.quantum_state]
            new_state, all_keys = tl.quantum_manager._prepare_state(keys)
            indices = tuple([all_keys.index(key) for key in keys])
            state_tuple = tuple(map(tuple, new_state))
            states, probs = measure_multiple_with_cache_fock_density(state_tuple, indices, len(all_keys), povm_tuple, tl.quantum_manager.truncation)
            state_plus, state_minus = states[1], states[2]
                    
            # assign remaining state (minus as example)
            if len(keys) < len(all_keys):
                indices = tuple([all_keys.index(key) for key in keys])
                new_state_tuple = tuple(map(tuple, state_plus))
                remaining_state = density_partial_trace(new_state_tuple, indices, len(all_keys), tl.quantum_manager.truncation)
                
            # effective Bell state generated 
            def effective_state(state):
                state[0][0] = 0
                state = state/np.trace(state)
                
                return state
            
            remaining_state_eff = effective_state(remaining_state)
            
            # calculate the fidelity with reference Bell state
            bell_plus = build_bell_state(tl.quantum_manager.truncation, "plus")
            bell_minus = build_bell_state(tl.quantum_manager.truncation, "minus")
            fidelity = np.trace(remaining_state_eff.dot(bell_minus)).real
            
            fidelity_mat[idx1][idx2] = fidelity
                
        idx2 = -1
            
    # plot the 2-d matrix
    
    num1, num2 = np.meshgrid(mean_num1_list, mean_num2_list)
    
    fig = plt.figure(figsize=(8,6))
    im = plt.imshow(fidelity_mat, cmap=plt.cm.RdBu, extent=(0.02, 0.1, 0.1, 0.02))
    plt.colorbar(im)  
    plt.title("Effective Fidelity with Mean Photon Number")
    plt.xlabel("mean photon number of source 1 $\mu_1$")
    plt.ylabel("mean photon number of source 2 $\mu_2$")
    plt.show()
    """

    tl = Timeline(time, formalism=FOCK_DENSITY_MATRIX_FORMALISM, truncation=TRUNCATION)

    anl_name = "Argonne"
    hc_name = "Harper Court"
    erc_name = "Eckhardt Research Center BSM"
    erc_2_name = "Eckhardt Research Center Measurement"
    seeds = [1, 2, 3, 4]
    src_list = [anl_name, hc_name]  # the list of sources, note the order

    anl = EndNode(anl_name, tl, hc_name, erc_name, erc_2_name, mean_photon_num=MEAN_PHOTON_NUM1,
                  spdc_frequency=SPDC_FREQUENCY, memo_frequency=MEMO_FREQUENCY1, abs_effi=ABS_EFFICIENCY1,
                  afc_efficiency=efficiency1, mode_number=MODE_NUM)
    hc = EndNode(hc_name, tl, anl_name, erc_name, erc_2_name, mean_photon_num=MEAN_PHOTON_NUM2,
                 spdc_frequency=SPDC_FREQUENCY, memo_frequency=MEMO_FREQUENCY2, abs_effi=ABS_EFFICIENCY2,
                 afc_efficiency=efficiency2, mode_number=MODE_NUM)
    erc = EntangleNode(erc_name, tl, src_list)
    erc_2 = MeasureNode(erc_2_name, tl, src_list)

    for seed, node in zip(seeds, [anl, hc, erc, erc_2]):
        node.set_seed(seed)

    # extend fiber lengths to be equivalent
    fiber_length = max(DIST_ANL_ERC, DIST_HC_ERC)

    qc1 = add_channel(anl, erc, tl, distance=fiber_length, attenuation=ATTENUATION)
    qc2 = add_channel(hc, erc, tl, distance=fiber_length, attenuation=ATTENUATION)
    qc3 = add_channel(anl, erc_2, tl, distance=fiber_length, attenuation=ATTENUATION)
    qc4 = add_channel(hc, erc_2, tl, distance=fiber_length, attenuation=ATTENUATION)

    tl.init()

    # calculate start time for protocol
    # since fiber lengths equal, both start at 0
    start_time_anl = start_time_hc = 0

    # calculations for when to start recording measurements
    delay_anl = anl.qchannels[erc_2_name].delay
    delay_hc = hc.qchannels[erc_2_name].delay
    assert delay_anl == delay_hc
    start_time_bsm = start_time_anl + delay_anl
    mem = anl.components[anl.memo_name]
    total_time = mem.total_time
    start_time_meas = start_time_anl + total_time + delay_anl

    results_direct_measurement = []
    results_bs_measurement = [[] for _ in phase_settings]

    """Pre-simulation explicit calculation of effective entanglement fidelity upon successful BSM"""

    if calculate_fidelity_direct:
        # use non-transmitted Photon as interface with existing methods in SeQUeNCe
        spdc_anl = anl.components[anl.spdc_name]
        spdc_hc = hc.components[hc.spdc_name]
        memo_anl = anl.components[anl.memo_name]
        memo_hc = hc.components[hc.memo_name]
        channel_anl = anl.qchannels[erc_name]
        channel_hc = hc.qchannels[erc_name]
        bsm = erc.components[erc.bsm_name]

        # photon0: idler, photon1: signal
        photon0_anl = Photon("", tl, wavelength=spdc_anl.wavelengths[0], location=spdc_anl,
                             encoding_type=spdc_anl.encoding_type, use_qm=True)
        photon1_anl = Photon("", tl, wavelength=spdc_anl.wavelengths[1], location=spdc_anl,
                             encoding_type=spdc_anl.encoding_type, use_qm=True)
        # set shared state to squeezed state
        state_spdc_anl = spdc_anl._generate_tmsv_state()
        keys = [photon0_anl.quantum_state, photon1_anl.quantum_state]
        tl.quantum_manager.set(keys, state_spdc_anl)

        photon0_hc = Photon("", tl, wavelength=spdc_hc.wavelengths[0], location=spdc_hc,
                            encoding_type=spdc_hc.encoding_type, use_qm=True)
        photon1_hc = Photon("", tl, wavelength=spdc_hc.wavelengths[1], location=spdc_hc,
                            encoding_type=spdc_hc.encoding_type, use_qm=True)
        # set shared state to squeezed state
        state_spdc_hc = spdc_hc._generate_tmsv_state()
        keys = [photon0_hc.quantum_state, photon1_hc.quantum_state]
        tl.quantum_manager.set(keys, state_spdc_hc)

        # photon loss upon absorption by memories
        key_anl = photon1_anl.quantum_state
        loss_anl = 1 - memo_anl.absorption_efficiency
        tl.quantum_manager.add_loss(key_anl, loss_anl)
        key_hc = photon1_hc.quantum_state
        loss_hc = 1 - memo_hc.absorption_efficiency
        tl.quantum_manager.add_loss(key_hc, loss_hc)

        # transmission loss through optical fibres
        key_anl = photon0_anl.quantum_state
        loss_anl = channel_anl.loss
        tl.quantum_manager.add_loss(key_anl, loss_anl)
        key_hc = photon0_hc.quantum_state
        loss_hc = channel_anl.loss
        tl.quantum_manager.add_loss(key_hc, loss_hc)

        # QSDetector measurement
        povms = bsm.povms
        povm_tuple = tuple([tuple(map(tuple, povm)) for povm in povms])
        keys = [photon0_anl.quantum_state, photon0_hc.quantum_state]
        new_state, all_keys = tl.quantum_manager._prepare_state(keys)
        indices = tuple([all_keys.index(key) for key in keys])
        state_tuple = tuple(map(tuple, new_state))
        states, probs = measure_multiple_with_cache_fock_density(state_tuple, indices, len(all_keys), povm_tuple,
                                                                 tl.quantum_manager.truncation)
        state_plus, state_minus = states[1], states[2]
    
        # calculate remaining state
        indices = tuple([all_keys.index(key) for key in keys])
        new_state_tuple = tuple(map(tuple, state_plus))
        remaining_state = density_partial_trace(new_state_tuple, indices, len(all_keys),
                                                tl.quantum_manager.truncation)
        remaining_keys = [key for key in all_keys if key not in keys]
            
        # effective Bell state generated 
        def effective_state(state):
            state_copy = copy(state)
            state_copy[0][0] = 0
            state_copy = state_copy/np.trace(state_copy)
            
            return state_copy
        
        remaining_state_eff = effective_state(remaining_state)
        
        # calculate the fidelity with reference Bell state
        bell_plus = build_bell_state(tl.quantum_manager.truncation, "plus")
        bell_minus = build_bell_state(tl.quantum_manager.truncation, "minus")
        fidelity = np.trace(remaining_state_eff.dot(bell_minus)).real

        print("Directly calculated effective fidelity:", fidelity)

        """Pre-simulation explicit calculation of entanglement generation rate based on calculation above"""

        if calculate_rate_direct:
            duration_photon = MODE_NUM / SPDC_FREQUENCY  # duration of emitted photon train from SPDC source
            delay_fiber_anl = anl.qchannels[erc_name].delay
            delay_fiber_hc = hc.qchannels[erc_name].delay
            assert delay_fiber_anl == delay_fiber_hc
            delay_fiber = delay_fiber_anl  # time for photon to travel from SPDC source to BSM device
            delay_classical = DELAY_CLASSICAL  # delay for classical communication between BSM node and memory nodes

            # total duration from first photon emitted to last photon's detection result communicated back
            duration_tot = duration_photon + delay_fiber + delay_classical

            prob_herald = probs[1] + probs[2]  # calculate heralding probability
            num_generated_avg = MODE_NUM * prob_herald  # average number of entangled pairs generated in one emission cycle

            rate = num_generated_avg / duration_tot

            print("Directly calculated entanglement generation:", rate)

    """Run Simulation"""

    for i in range(num_direct_trials):
        # start protocol for emitting
        process = Process(anl.emit_protocol, "start", [])
        event = Event(start_time_anl, process)
        tl.schedule(event)
        process = Process(hc.emit_protocol, "start", [])
        event = Event(start_time_hc, process)
        tl.schedule(event)

        tl.run()
        print("finished direct measurement trial {} out of {}".format(i+1, num_direct_trials))

        # collect data

        # BSM results determine relative sign of reference Bell state and herald successful entanglement
        bsm_res = erc.get_detector_entries(erc.bsm_name, start_time_bsm, MODE_NUM, SPDC_FREQUENCY)
        bsm_success_indices = [i for i, res in enumerate(bsm_res) if res == 1 or res == 2]
        meas_res = erc_2.get_detector_entries(erc_2.direct_detector_name, start_time_meas, MODE_NUM, SPDC_FREQUENCY)

        num_bsm_res = len(bsm_success_indices)
        meas_res_valid = [meas_res[i] for i in bsm_success_indices]
        counts_diag = [0] * 4
        for j in range(4):
            counts_diag[j] = meas_res_valid.count(j)
        res_diag = {"counts": counts_diag, "total_count": num_bsm_res}
        results_direct_measurement.append(res_diag)

        # reset timeline
        tl.time = 0
        tl.init()

    # change to other measurement
    erc_2.set_first_component(erc_2.bs_detector_name)
    for i, phase in enumerate(phase_settings):
        erc_2.set_phase(phase)

        for j in range(num_bs_trials_per_phase):
            # start protocol for emitting
            process = Process(anl.emit_protocol, "start", [])
            event = Event(start_time_anl, process)
            tl.schedule(event)
            process = Process(hc.emit_protocol, "start", [])
            event = Event(start_time_hc, process)
            tl.schedule(event)

            tl.run()
            print("finished interference measurement trial {} out of {} for phase {} out ouf {}".format(
                j+1, num_bs_trials_per_phase, i+1, len(phase_settings)))

            # collect data

            # relative sign should influence interference pattern
            bsm_res = erc.get_detector_entries(erc.bsm_name, start_time_bsm, MODE_NUM, SPDC_FREQUENCY)
            bsm_success_indices_1 = [i for i, res in enumerate(bsm_res) if res == 1]
            bsm_success_indices_2 = [i for i, res in enumerate(bsm_res) if res == 2]
            meas_res = erc_2.get_detector_entries(erc_2.bs_detector_name, start_time_meas, MODE_NUM, SPDC_FREQUENCY)
            res_interference = {}

            # detector 1
            num_bsm_res = len(bsm_success_indices_1)
            meas_res_valid = [meas_res[i] for i in bsm_success_indices_1]
            num_detector_0 = meas_res_valid.count(1) + meas_res_valid.count(3)
            num_detector_1 = meas_res_valid.count(2) + meas_res_valid.count(3)
            counts_interfere = [num_detector_0, num_detector_1]
            res_interference["counts1"] = counts_interfere
            res_interference["total_count1"] = num_bsm_res

            # detector 2
            num_bsm_res = len(bsm_success_indices_2)
            meas_res_valid = [meas_res[i] for i in bsm_success_indices_2]
            num_detector_0 = meas_res_valid.count(1) + meas_res_valid.count(3)
            num_detector_1 = meas_res_valid.count(2) + meas_res_valid.count(3)
            counts_interfere = [num_detector_0, num_detector_1]
            res_interference["counts2"] = counts_interfere
            res_interference["total_count2"] = num_bsm_res

            results_bs_measurement[i].append(res_interference)

            # reset timeline
            tl.time = 0
            tl.init()

    """Store results"""

    # open file to store experiment results
    Path("results").mkdir(parents=True, exist_ok=True)
    filename = "results/absorptive.json"
    fh = open(filename, 'w')
    info = {"num_direct_trials": num_direct_trials, "num_bs_trials": num_bs_trials_per_phase,
            "num_phase": len(phase_settings),
            "direct results": results_direct_measurement, "bs results": results_bs_measurement}
    dump(info, fh)
