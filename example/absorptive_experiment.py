"""The main script for simulating experiment of entanglement generation between two remote AFC absorptive quantum memories.

There are 4 nodes involved: 2 memory nodes, 1 entangling node (for BSM) and 1 measurement node (for measurement of retrieved photonic state).
Each memory node is connected with both entangling node and measurement node, but there is no direct connection between memory nodes.

Each memory node contains an AFC memory instance and an SPDC source instance.
The entangling node contains a QSDetectorFockInterference instance (BSM device with a beamsplitter and two photon detectors behind).
The measurement node contians a QSDetectorFockDirect instance and a QSDetectorFockInterference instance, for measurement of 
    diagonal and off-diagonal elements of the effective 4-d density matrix, respectively.

WIP
"""

from typing import List, Dict, Any, Callable, TYPE_CHECKING
from pathlib import Path

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
from sequence.topology.node import Node
from sequence.protocol import Protocol


# define constants
TRUNCATION = 2  # truncation of Fock space (=dimension-1)
TELECOM_WAVELENGTH = 1436  # telecom band wavelength of SPDC source idler photon
WAVELENGTH = 606  # wavelength of AFC memory resonant absorption, of SPDC source signal photon
MODE_NUM = 100  # number of temporal modes of AFC memory (same for both memories)
SPDC_FREQUENCY = 80e6  # frequency of both SPDC sources' photon creation (same as memory frequency)
DIST_ANL_ERC = 20 # distance between ANL and ERC, in km
DIST_HC_ERC = 20 # distance between HC and ERC, in km
ATTENUATION = 0 # attenuation rate of optical fibre

MEMO_FREQUENCY1 = SPDC_FREQUENCY  # frequency of memory 1
MEMO_FREQUENCY2 = SPDC_FREQUENCY  # frequency of memory 2
ABS_EFFICIENCY1 = 1.0  # absorption efficiency of AFC memory 1
ABS_EFFICIENCY2 = 1.0  # absorption efficiency of AFC memory 2
PREPARE_TIME1 = 0  # time required for AFC structure preparation of memory 1
PREPARE_TIME2 = 0  # time required for AFC structure preparation of memory 2
COHERENCE_TIME1 = -1  # spin coherence time for AFC memory 1 spinwave storage, -1 means infinite time
COHERENCE_TIME2 = -1  # spin coherence time for AFC memory 2 spinwave storage, -1 means infinite time
AFC_LIFETIME1 = -1  # AFC structure lifetime of memory 1, -1 means infinite time
AFC_LIFETIME2 = -1  # AFC structure lifetime of memory 2, -1 means infinite time
MEAN_PHOTON_NUM1 = 0.1  # mean photon number of SPDC source on node 1
MEAN_PHOTON_NUM2 = 0.1  # mean photon number of SPDC source on node 2
DECAY_RATE1 = 0  # retrieval efficiency decay rate for memory 1
DECAY_RATE2 = 0  # retrieval efficiency decay rate for memory 2

# experiment settings
num_direct_trials = 10
phase_settings = np.linspace(0, 2*np.pi, num=10, endpoint=False)


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
                 retrieval_efficiency: Callable):
        super().__init__(name, timeline)

        self.bsm_name = bsm_node
        self.meas_name = measure_node

        # hardware setup
        self.spdc_name = name + ".spdc_source"
        self.memo_name = name + ".memory"
        spdc = SPDCSource(self.spdc_name, timeline, wavelengths=[TELECOM_WAVELENGTH, WAVELENGTH],
                          frequency=spdc_frequency, mean_photon_num=mean_photon_num)
        memory = AbsorptiveMemory(self.memo_name, timeline, frequency=memo_frequency,
                                  absorption_efficiency=abs_effi, efficiency=retrieval_efficiency,
                                  mode_number=MODE_NUM, wavelength=WAVELENGTH, destination=measure_node)
        self.add_component(spdc)
        self.add_component(memory)
        spdc.add_receiver(self)
        spdc.add_receiver(memory)
        memory.add_receiver(self)

        # protocols
        self.emit_protocol = EmitProtocol(self, name + ".emit_protocol", other_node, MODE_NUM, self.spdc_name, self.memo_name)

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
        bsm_name = name + ".bsm"
        # assume no relative phase between two input optical paths
        bsm = QSDetectorFockInterference(bsm_name, timeline, src_list)
        self.add_component(bsm)
        bsm.attach(self)
        self.set_first_component(bsm_name)

        self.resolution = max([d.time_resolution for d in bsm.detectors])
        self.bsm_times = [[], []]

    def receive_qubit(self, src: str, qubit) -> None:
        self.components[self.first_component_name].get(qubit, src=src)

    # TODO: record BSM result (which SPD clicks) to determine the standard Bell state's relative sign for fidelity calculation
    def get_valid_bins(self, start_time: int, num_bins: int, frequency: float):
        """Computes time bins containing a BSM measurement.

        Args:
            start_time (int): simulation start time of when photons received.
            num_bins (int): number of arrival bins
            frequency (float): frequency of photon arrival (in Hz).

        Returns:
            List[int]: list of length num_bins containing 0/1.
                List element is 0 for an unsuccessful measurement and 1 for successful.
        """

        return_bins = [0] * num_bins

        for time in self.bsm_times[0] + self.bsm_times[1]:
            closest_bin = int(round((time - start_time) * frequency * 1e-12))
            expected_time = (float(closest_bin) * 1e12 / frequency) + start_time
            if abs(expected_time - time) < self.resolution and 0 <= closest_bin < num_bins:
                return_bins[closest_bin] = not return_bins[closest_bin]

        return return_bins


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

    def receive_qubit(self, src: str, qubit) -> None:
        self.components[self.first_component_name].get(qubit, src=src)

    def set_phase(self, phase: float):
        self.components[self.bs_detector_name].set_phase(phase)

    # TODO: check
    def get_detector_entries(self, detector_name: str, start_time: int, num_bins: int, frequency: float):
        """Computes distribution of detection events for density matrix.

        Args:
            detector_name (str): name of detector to get measurements from.
            start_time (int): simulation start time of when photons received.
            num_bins (int): number of arrival bins
            frequency (float): frequency of photon arrival (in Hz).

        Returns:
            List[int]: list of length (duration * 1e-12 * frequency) with result for each time bin.
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
    # TODO: WIP
    # open file to store experiment results
    Path("results").mkdir(parents=True, exist_ok=True)
    filename = "results/absorptive.json"
    fh = open(filename, 'w')

    """Setup Simulation"""

    tl = Timeline(1e12, formalism=FOCK_DENSITY_MATRIX_FORMALISM, truncation=TRUNCATION)

    anl_name = "Argonne"
    hc_name = "Harper Court"
    erc_name = "Eckhardt Research Center BSM"
    erc_2_name = "Eckhardt Research Center Measurement"
    seeds = [1, 2, 3, 4]
    src_list = [anl_name, hc_name]  # the list of sources, note the order

    anl = EndNode(anl_name, tl, hc_name, erc_name, erc_2_name, mean_photon_num=MEAN_PHOTON_NUM1,
                  spdc_frequency=SPDC_FREQUENCY, memo_frequency=MEMO_FREQUENCY1, abs_effi=ABS_EFFICIENCY1,
                  retrieval_efficiency=efficiency1)
    hc = EndNode(hc_name, tl, anl_name, erc_name, erc_2_name, mean_photon_num=MEAN_PHOTON_NUM2,
                 spdc_frequency=SPDC_FREQUENCY, memo_frequency=MEMO_FREQUENCY2, abs_effi=ABS_EFFICIENCY2,
                 retrieval_efficiency=efficiency2)
    erc = EntangleNode(erc_name, tl, src_list)
    erc_2 = MeasureNode(erc_2_name, tl, src_list)

    for seed, node in zip(seeds, [anl, hc, erc, erc_2]):
        node.set_seed(seed)

    qc1 = add_channel(anl, erc, tl, distance=DIST_ANL_ERC, attenuation=ATTENUATION)
    qc2 = add_channel(hc, erc, tl, distance=DIST_HC_ERC, attenuation=ATTENUATION)
    qc3 = add_channel(anl, erc_2, tl, distance=DIST_ANL_ERC, attenuation=ATTENUATION)
    qc4 = add_channel(hc, erc_2, tl, distance=DIST_HC_ERC, attenuation=ATTENUATION)

    # calculations for when to start protocol
    # requirement: photons must arrive at beamsplitter to realize interference
    delay_anl = anl.qchannels[erc_name].delay
    delay_hc = hc.qchannels[erc_name].delay
    time_anl = max(delay_anl, delay_hc) - delay_anl
    time_hc = max(delay_anl, delay_hc) - delay_hc

    # calculations for fibre length modification for retrieved photon measurement
    # requirement: photons must arrive at beamsplitter to realize interference
    dalay_anl_reemit = anl.components[anl.memo_name].total_time
    delay_hc_reemit = hc.components[hc.memo_name].total_time
    delay_anl_meas = anl.qchannels[erc_2_name].delay
    delay_hc_meas = hc.qchannels[erc_2_name].delay
    delay_anl_meas_tot = time_anl + dalay_anl_reemit + delay_anl_meas
    delay_hc_meas_tot = time_hc + delay_hc_reemit + delay_hc_meas
    time_anl_meas = max(delay_anl_meas_tot, delay_hc_meas_tot) - delay_anl_meas_tot
    time_hc_meas = max(delay_anl_meas_tot, delay_hc_meas_tot) - delay_hc_meas_tot
    dist_anl_meas = qc3.light_speed * time_hc_meas + DIST_ANL_ERC
    dist_hc_meas = qc4.light_speed * time_anl_meas + DIST_HC_ERC

    qc3.set_distance(dist_anl_meas)
    qc4.set_distance(dist_hc_meas)

    # calculations for when to start recording measurements
    # TODO: check
    start_time_bsm = time_anl + delay_anl
    mem = anl.get_components_by_type("AbsorptiveMemory")[0]
    total_time = mem.total_time
    start_time_meas = time_anl + total_time + delay_anl

    tl.init()

    results_direct_measurement = []
    results_bs_measurement = []

    """Run Simulation"""

    for i in range(num_direct_trials):
        # start protocol for emitting
        process = Process(anl.emit_protocol, "start", [])
        event = Event(time_anl, process)
        tl.schedule(event)
        process = Process(hc.emit_protocol, "start", [])
        event = Event(time_hc, process)
        tl.schedule(event)

        tl.run()
        print("finished direct measurement trial {} out of {}".format(i+1, num_direct_trials))

        # collect data
        bsm_res = erc.get_valid_bins(start_time_bsm, MODE_NUM, SPDC_FREQUENCY)
        meas_res = erc_2.get_detector_entries(erc_2.direct_detector_name, start_time_meas, MODE_NUM, SPDC_FREQUENCY)
        num_bsm_res = sum(bsm_res)
        meas_res_valid = [m for m, b in zip(meas_res, bsm_res) if b]
        probs = [0.0] * 4
        for j in range(4):
            probs[j] = meas_res_valid.count(j) / num_bsm_res
        results_direct_measurement.append(probs)

        # reset timeline
        tl.time = 0
        tl.init()

    # change to other measurement
    erc_2.set_first_component(erc_2.bs_detector_name)
    for i, phase in enumerate(phase_settings):
        erc_2.set_phase(phase)

        # start protocol for emitting
        process = Process(anl.emit_protocol, "start", [])
        event = Event(time_anl, process)
        tl.schedule(event)
        process = Process(hc.emit_protocol, "start", [])
        event = Event(time_hc, process)
        tl.schedule(event)

        tl.run()
        print("finished interference measurement trial {} out of {}".format(i+1, len(phase_settings)))

        # collect data
        bsm_res = erc.get_valid_bins(start_time_bsm, MODE_NUM, SPDC_FREQUENCY)
        meas_res = erc_2.get_detector_entries(erc_2.bs_detector_name, start_time_meas, MODE_NUM, SPDC_FREQUENCY)
        meas_res_valid = [m for m, b in zip(meas_res, bsm_res) if b]
        num_detector_0 = meas_res.count(1) + meas_res_valid.count(3)
        num_detector_1 = meas_res.count(2) + meas_res_valid.count(3)
        freqs = [num_detector_0/(total_time * 1e-12), num_detector_1/(total_time * 1e-12)]
        results_bs_measurement.append(freqs)

        # reset timeline
        tl.time = 0
        tl.init()

    """Store results"""

    info = {"direct results": results_direct_measurement, "bs results": results_bs_measurement}
    dump(info, fh)

    # plt.bar(list(range(4)), counts)
    # plt.yscale('log')
    # plt.show()
