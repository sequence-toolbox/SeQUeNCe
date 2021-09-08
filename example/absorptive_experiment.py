from typing import List, Dict, Any
from pathlib import Path

from json5 import dump
import numpy as np

from sequence.components.bsm import make_bsm
from sequence.components.detector import QSDetectorFockDirect, QSDetectorFockInterference
from sequence.components.light_source import SPDCSource
from sequence.components.memory import AbsorptiveMemory
from sequence.components.photon import Photon
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.kernel.timeline import Timeline
from sequence.topology.node import Node
from sequence.topology.topology import Topology
from sequence.protocol import Protocol
from sequence.utils.encoding import absorptive


# define constants
FREQUENCY = 80e6
ABS_EFFICIENCY = 1.0
MODE_NUM = 100
COHERENCE_TIME = 1
TELECOM_WAVELENGTH = 1000
WAVELENGTH = 500
OVERLAP_ERR = 0

# experiment settings
num_direct_trials = 10
phase_settings = np.linspace(0, 2*np.pi, num=10, endpoint=False)


# for absorptive quantum memory
def efficiency(_: int) -> float:
    return 1.0


# protocol to control photon emission on end node
class EmitProtocol(Protocol):
    def __init__(self, own: "EndNode", name: str, other_node: str, num_qubits: int, source_name: str, memory_name: str):
        """Constructor for Emission protocol.

        Args:
            own (EndNode): node on which the protocol is located.
            name (str): name of the protocol instance.
            other_node (str): name of the other node entangling photons
            num_qubits (int): number of qubits to send in one execution.
            delay_time (int): time to wait before re-starting execution.
            source_name (str): name of the light source on the node.
            memory_name (str): name of the memory on the node.
        """

        super().__init__(own, name)
        self.other_node = other_node
        self.num_qubits = num_qubits
        self.source_name = source_name
        self.memory_name = memory_name

    def start(self):
        self.own.components[self.memory_name]._prepare_AFC()
        
        states = [None] * self.num_qubits  # TODO: rewrite spdc class?
        source = self.own.components[self.source_name]
        source.emit(states)

    def received_message(self, src: str, msg):
        pass


class EndNode(Node):
    """Node for each end of the network.

    This node stores an SPDC photon source and a quantum memory.
    """

    def __init__(self, name: str, timeline: "Timeline", other_node: str, bsm_node: str, measure_node: str):
        super().__init__(name, timeline)

        self.bsm_name = bsm_node
        self.meas_name = measure_node

        # hardware setup
        spdc_name = name + ".spdc_source"
        memo_name = name + ".memory"
        spdc = SPDCSource(spdc_name, timeline, wavelengths=[TELECOM_WAVELENGTH, WAVELENGTH],
                          frequency=FREQUENCY, encoding_type=absorptive, mean_photon_num=0.2)
        memory = AbsorptiveMemory(memo_name, timeline, fidelity=0.85, frequency=FREQUENCY,
                                  absorption_efficiency=ABS_EFFICIENCY, mode_number=MODE_NUM,
                                  coherence_time=COHERENCE_TIME, wavelength=WAVELENGTH, overlap_error=OVERLAP_ERR,
                                  efficiency=efficiency, prepare_time=0, destination=measure_node)
        self.add_component(spdc)
        self.add_component(memory)
        spdc.add_receiver(self)
        spdc.add_receiver(memory)
        memory.add_receiver(self)

        # protocols
        self.emit_protocol = EmitProtocol(self, name + ".emit_protocol", other_node, MODE_NUM, spdc_name, memo_name)

    def get(self, photon: "Photon", **kwargs):
        dst = kwargs.get("dst")
        if dst is None:
            # from spdc source: send to bsm node
            self.send_qubit(self.bsm_name, photon)
        else:
            # from memory: send to destination (measurement) node
            self.send_qubit(dst, photon)


class EntangleNode(Node):
    def __init__(self, name: str, timeline: "Timeline"):
        super().__init__(name, timeline)

        # hardware setup
        bsm_name = name + ".bsm"
        bsm = make_bsm(bsm_name, timeline, "absorptive")
        self.add_component(bsm)
        bsm.attach(self)
        self.set_first_component(bsm_name)

        self.resolution = bsm.resolution
        self.bsm_times = [[], []]

    def bsm_update(self, bsm, info: Dict[str, Any]):
        self.bsm_times[info['res']].append(info['time'])

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
        self.set_first_component(self.direct_detector_name)

        self.bs_detector_name = name + ".bs"
        bs_detector = QSDetectorFockInterference(self.bs_detector_name, tl)
        self.add_component(bs_detector)
        bs_detector.add_receiver(self)

        # time resolution of SPDs
        self.resolution = max([d.time_resolution for d in direct_detector.detectors + bs_detector.detectors])

    def receive_qubit(self, src: str, qubit) -> None:
        self.components[self.first_component_name].get(qubit, src=src)

    def set_phase(self, phase: float):
        self.components[self.bs_detector_name].set_phase(phase)

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
    # open file to store experiment results
    Path("results").mkdir(parents=True, exist_ok=True)
    filename = "results/absorptive.json"
    fh = open(filename, 'w')

    """Run Simulation"""

    tl = Timeline(1e12, 'density_matrix')
    tl.seed(0)

    anl_name = "Argonne"
    hc_name = "Harper Court"
    erc_name = "Eckhardt Research Center"
    erc_2_name = "Eckhardt Research Center 2"

    anl = EndNode(anl_name, tl, hc_name, erc_name, erc_2_name)
    hc = EndNode(hc_name, tl, anl_name, erc_name, erc_2_name)
    erc = EntangleNode(erc_name, tl)
    erc_2 = MeasureNode(erc_2_name, tl, [anl_name, hc_name])

    topo = Topology("Experiment Topo", tl)
    for node in [anl, hc, erc, erc_2]:
        topo.add_node(node)
    topo.add_quantum_channel(anl_name, erc_name, distance=20, attenuation=0)
    topo.add_quantum_channel(hc_name, erc_name, distance=20, attenuation=0)
    topo.add_quantum_channel(anl_name, erc_2_name, distance=20, attenuation=0)
    topo.add_quantum_channel(hc_name, erc_2_name, distance=20, attenuation=0)

    tl.init()

    # calculations for when to start protocol
    delay_anl = topo.nodes[anl_name].qchannels[erc_name].delay
    delay_hc = topo.nodes[hc_name].qchannels[erc_name].delay
    time_anl = max(delay_anl, delay_hc) - delay_anl
    time_hc = max(delay_anl, delay_hc) - delay_hc

    # calculations for when to start recording measurements
    start_time_bsm = time_anl + delay_anl
    mem = anl.get_components_by_type("AbsorptiveMemory")[0]
    total_time = mem.total_time
    start_time_meas = time_anl + total_time + delay_anl

    results_direct_measurement = []
    results_bs_measurement = []

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
        bsm_res = erc.get_valid_bins(start_time_bsm, MODE_NUM, FREQUENCY)
        meas_res = erc_2.get_detector_entries(erc_2.direct_detector_name, start_time_meas, MODE_NUM, FREQUENCY)
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
        bsm_res = erc.get_valid_bins(start_time_bsm, MODE_NUM, FREQUENCY)
        meas_res = erc_2.get_detector_entries(erc_2.bs_detector_name, start_time_meas, MODE_NUM, FREQUENCY)
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
