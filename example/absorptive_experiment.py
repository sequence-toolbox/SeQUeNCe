from typing import List, Dict, Any

import numpy as np
import matplotlib.pyplot as plt

from sequence.components.bsm import make_bsm
from sequence.components.detector import QSDetector, Detector
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
MODE_NUM = 10000
COHERENCE_TIME = 1
TELECOM_WAVELENGTH = 1000
WAVELENGTH = 500
OVERLAP_ERR = 0
DELAY_TIME = 1e6


# for absorptive quantum memory
def efficiency(_: int) -> float:
    return 1.0


# hardware class to measure photons on measurement node
class CoherenceDetector(QSDetector):
    def __init__(self, name: str, timeline: "Timeline", src_list: List[str]):
        super().__init__(name, timeline)
        self.src_list = src_list
        for i in range(2):
            d = Detector(name + ".detector" + str(i), timeline)
            self.detectors.append(d)
            d.attach(self)

    def init(self):
        pass

    def get(self, photon: "Photon", **kwargs):
        src = kwargs["src"]
        detector_num = self.src_list.index(src)
        res = Photon.measure(None, photon)  # measure (0/1 determines existence of photons in encoding)
        if res:
            self.detectors[detector_num].get()

    def trigger(self, detector: Detector, info: Dict[str, Any]) -> None:
        detector_num = self.detectors.index(detector)
        info['detector_num'] = detector_num
        self.notify(info)

    # does nothing for this class
    def set_basis_list(self, basis_list: List[int], start_time: int, frequency: int) -> None:
        pass


# protocol to control photon emission on end node
class EmitProtocol(Protocol):
    def __init__(self, own: "EndNode", name: str, other_node: str,
                 num_qubits: int, storage_time: int, source_name: str, memory_name: str):
        """Constructor for Emission protocol.

        Args:
            own (EndNode): node on which the protocol is located.
            name (str): name of the protocol instance.
            other_node (str): name of the other node entangling photons
            num_qubits (int): number of qubits to send in one execution.
            storage_time (int): length of time to wait before releasing photons in local memory.
            source_name (str): name of the light source on the node.
            memory_name (str): name of the memory on the node.
        """

        super().__init__(own, name)
        self.other_node = other_node
        self.num_qubits = num_qubits
        self.storage_time = storage_time
        self.source_name = source_name
        self.memory_name = memory_name

    def start(self):
        states = [None] * self.num_qubits  # TODO: rewrite spdc class?
        source = self.own.components[self.source_name]
        source.emit(states)

        future_time = self.own.timeline.now() + self.storage_time
        memory = self.own.components[self.memory_name]
        # retrieve photons and send to coincidence measurement node
        process = Process(memory, "retrieve", [self.own.meas_name])
        event = Event(future_time, process)
        self.own.timeline.schedule(event)

    def received_message(self, src: str, msg):
        pass


class EndNode(Node):
    """Node for each end of the network.

    This node stores an SPDC photon source and a quantum memory.
    """

    def __init__(self, name: str, timeline: "Timeline", other_node: str, bsm_node: str, measure_node: str,
                 num_qubits: int, storage_time: int):
        super().__init__(name, timeline)

        self.bsm_name = bsm_node
        self.meas_name = measure_node

        # hardware setup
        spdc_name = name + ".spdc_source"
        memo_name = name + ".memory"
        spdc = SPDCSource(spdc_name, timeline, wavelengths=[TELECOM_WAVELENGTH, WAVELENGTH],
                          frequency=FREQUENCY, encoding_type=absorptive)
        memory = AbsorptiveMemory(memo_name, timeline, fidelity=0.85, frequency=FREQUENCY,
                                  absorption_efficiency=ABS_EFFICIENCY, mode_number=MODE_NUM,
                                  coherence_time=COHERENCE_TIME, wavelength=WAVELENGTH, overlap_error=OVERLAP_ERR,
                                  efficiency=efficiency)
        self.add_component(spdc)
        self.add_component(memory)
        spdc.add_receiver(self)
        spdc.add_receiver(memory)
        memory.add_receiver(self)

        # protocols
        self.emit_protocol = EmitProtocol(self, name + ".emit_protocol", other_node,
                                          num_qubits, storage_time, spdc_name, memo_name)

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

        detector_name = name + ".coherence"
        detector = CoherenceDetector(detector_name, timeline, other_nodes)
        self.add_component(detector)
        detector.attach(self)
        self.set_first_component(detector_name)

        self.resolution = max([d.time_resolution for d in detector.detectors])
        self.trigger_times = [[], []]

        self.receive_times = []

    def receive_qubit(self, src: str, qubit) -> None:
        self.receive_times.append(self.timeline.now())
        self.components[self.first_component_name].get(qubit, src=src)

    def update(self, entity, info: Dict[str, Any]) -> None:
        self.trigger_times[info['detector_num']].append(info['time'])

    def get_diagonal_entries(self, start_time: int, num_bins: int, frequency: float):
        """Computes distribution of diagonal matrix entries for density matrix.

        Args:
            start_time (int): simulation start time of when photons received.
            num_bins (int): number of arrival bins
            frequency (float): frequency of photon arrival (in Hz).

        Returns:
            List[int]: list of length (duration * 1e-12 * frequency) with result for each time bin.
        """

        return_res = [0] * num_bins

        for time in self.trigger_times[0]:
            closest_bin = int(round((time - start_time) * frequency * 1e-12))
            expected_time = (float(closest_bin) * 1e12 / frequency) + start_time
            if abs(expected_time - time) < self.resolution and 0 <= closest_bin < num_bins:
                return_res[closest_bin] += 1

        for time in self.trigger_times[1]:
            closest_bin = int(round((time - start_time) * frequency * 1e-12))
            expected_time = (float(closest_bin) * 1e12 / frequency) + start_time
            if abs(expected_time - time) < self.resolution and 0 <= closest_bin < num_bins:
                return_res[closest_bin] += 2

        return return_res


if __name__ == "__main__":
    tl = Timeline(1e12, 'density_matrix')
    tl.seed(0)

    anl_name = "Argonne"
    hc_name = "Harper Court"
    erc_name = "Eckhardt Research Center"
    erc_2_name = "Eckhardt Research Center 2"

    anl = EndNode(anl_name, tl, hc_name, erc_name, erc_2_name, MODE_NUM, DELAY_TIME)
    hc = EndNode(hc_name, tl, anl_name, erc_name, erc_2_name, MODE_NUM, DELAY_TIME)
    erc = EntangleNode(erc_name, tl)
    erc_2 = MeasureNode(erc_2_name, tl, [anl_name, hc_name])

    topo = Topology("Experiment Topo", tl)
    for node in [anl, hc, erc, erc_2]:
        topo.add_node(node)
    topo.add_quantum_channel(anl_name, erc_name, distance=20, attenuation=0.002)
    topo.add_quantum_channel(hc_name, erc_name, distance=20, attenuation=0.002)
    topo.add_quantum_channel(anl_name, erc_2_name, distance=20, attenuation=0.002)
    topo.add_quantum_channel(hc_name, erc_2_name, distance=20, attenuation=0.002)

    tl.init()

    # calculate when to start protocol
    delay_anl = topo.nodes[anl_name].qchannels[erc_name].delay
    delay_hc = topo.nodes[hc_name].qchannels[erc_name].delay

    time_anl = max(delay_anl, delay_hc) - delay_anl
    process = Process(anl.emit_protocol, "start", [])
    event = Event(time_anl, process)
    tl.schedule(event)

    time_hc = max(delay_anl, delay_hc) - delay_hc
    process = Process(hc.emit_protocol, "start", [])
    event = Event(time_hc, process)
    tl.schedule(event)

    tl.run()

    # display metrics
    start_time_bsm = time_anl + delay_anl
    start_time_meas = time_anl + DELAY_TIME + delay_anl

    bsm_res = erc.get_valid_bins(start_time_bsm, MODE_NUM, FREQUENCY)
    meas_res = erc_2.get_diagonal_entries(start_time_meas, MODE_NUM, FREQUENCY)
    meas_res.reverse()  # photons emitted from memory in FILO order

    meas_res_valid = [m for m, b in zip(meas_res, bsm_res) if b == 1]
    counts = [0] * 4
    for i in range(4):
        counts[i] = meas_res_valid.count(i)

    plt.bar(list(range(4)), counts)
    plt.yscale('log')
    plt.show()
