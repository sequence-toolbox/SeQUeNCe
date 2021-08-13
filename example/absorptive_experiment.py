from typing import List

from sequence.components.bsm import make_bsm
from sequence.components.detector import QSDetector, Detector
from sequence.components.light_source import SPDCSource
from sequence.components.memory import AbsorptiveMemory
from sequence.components.photon import Photon
from sequence.kernel.timeline import Timeline
from sequence.topology.node import Node
from sequence.topology.topology import Topology


# define constants
FREQUENCY = 80e6
ABS_EFFICIENCY = 1.0
MODE_NUM = 100
COHERENCE_TIME = 1
TELECOM_WAVELENGTH = 1000
WAVELENGTH = 500
OVERLAP_ERR = 0


# for absorptive quantum memory
def efficiency(_: int) -> float:
    return 1.0


class CoherenceDetector(QSDetector):
    def __init__(self, name: str, timeline: "Timeline", src_list: List[str]):
        super().__init__(name, timeline)
        self.src_list = src_list
        for i in range(2):
            d = Detector(name + ".detector" + str(i), timeline)
            self.detectors.append(d)
            d.attach(self)

    def get(self, photon: "Photon", **kwargs):
        src = kwargs["src"]
        detector_num = self.src_list.index(src)
        res = Photon.measure(None, photon)  # measure (0/1 determines existence of photons in encoding)
        if res:
            self.detectors[detector_num].get()

    # does nothing for this class
    def set_basis_list(self, basis_list: List[int], start_time: int, frequency: int) -> None:
        pass


class EndNode(Node):
    def __init__(self, name: str, timeline: "Timeline"):
        super().__init__(name, timeline)

        # hardware setup
        spdc = SPDCSource(name + ".spdc_source", timeline, wavelengths=[TELECOM_WAVELENGTH, WAVELENGTH])
        memory = AbsorptiveMemory(name + ".memory", timeline, fidelity=0.85, frequency=FREQUENCY,
                                  absorption_efficiency=ABS_EFFICIENCY, mode_number=MODE_NUM,
                                  coherence_time=COHERENCE_TIME, wavelength=WAVELENGTH, overlap_error=OVERLAP_ERR,
                                  efficiency=efficiency)
        self.add_component(spdc)
        self.add_component(memory)
        spdc.add_receiver(self)
        spdc.add_receiver(memory)
        memory.add_receiver(self)

    def get(self, photon: "Photon", **kwargs):
        # TODO: define
        pass


class EntangleNode(Node):
    def __init__(self, name: str, timeline: "Timeline"):
        super().__init__(name, timeline)

        # hardware setup
        bsm_name = name + ".bsm"
        bsm = make_bsm(bsm_name, timeline, "absorptive")
        self.add_component(bsm)
        self.set_first_component(bsm_name)


class MeasureNode(Node):
    def __init__(self, name: str, timeline: "Timeline", other_nodes: List[str]):
        super().__init__(name, timeline)

        detector_name = name + ".coherence"
        detector = CoherenceDetector(detector_name, timeline, other_nodes)
        self.add_component(detector)
        self.set_first_component(detector_name)

    def receive_qubit(self, src: str, qubit) -> None:
        self.components[self.first_component_name].get(qubit, src=src)


if __name__ == "__main__":
    tl = Timeline(1e12, 'density_matrix')

    anl_name = "Argonne"
    hc_name = "Harper Court"
    erc_name = "Eckhardt Research Center"
    erc_2_name = "Eckhardt Research Center 2"

    anl = EndNode(anl_name, tl)
    hc = EndNode(hc_name, tl)
    erc = EntangleNode(erc_name, tl)
    erc_2 = MeasureNode(erc_2_name, tl, [anl_name, hc_name])

    topo = Topology("Experiment Topo", tl)
    for node in [anl, hc, erc, erc_2]:
        topo.add_node(node)
    topo.add_quantum_channel(anl_name, erc_name)
    topo.add_quantum_channel(hc_name, erc_name)
    topo.add_quantum_channel(anl_name, erc_2_name)
    topo.add_quantum_channel(hc_name, erc_2_name)

    tl.init()
    # TODO: add mechanism to start SPDC source/measurement
    tl.run()
