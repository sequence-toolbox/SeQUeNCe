from typing import TYPE_CHECKING

import numpy

if TYPE_CHECKING:
    from ..kernel.timeline import Timeline
from .photon import Photon
from ..kernel.entity import Entity


class BeamSplitter(Entity):
    def __init__(self, name: str, timeline: "Timeline", **kwargs):
        Entity.__init__(self, name, timeline)  # Splitter is part of the QSDetector, and does not have its own name
        # basis = kwargs.get("basis", [[complex(1), complex(0)], [complex(0), complex(1)]])
        self.fidelity = kwargs.get("fidelity", 1)
        self.receivers = []
        # for BB84
        self.start_time = 0
        self.frequency = 0
        self.basis_list = []  # default value

    def init(self) -> None:
        pass

    def get(self, photon: "Photon") -> None:
        assert photon.encoding_type["name"] == "polarization"

        if numpy.random.random_sample() < self.fidelity:
            index = int((self.timeline.now() - self.start_time) * self.frequency * 1e-12)

            if 0 > index or index >= len(self.basis_list):
                raise Exception("Receive photon but cannot find basis for measurement, index=%d, basis_list length=%d"
                                % (index, len(self.basis_list)))

            res = Photon.measure(self.basis_list[index], photon)
            self.receivers[res].get()

    def set_basis_list(self, basis_list: "List", start_time: int, frequency: int) -> None:
        self.basis_list = basis_list
        self.start_time = start_time
        self.frequency = frequency

    def set_receiver(self, receiver: "Entity", index: int) -> None:
        if index > len(self.receivers):
            raise Exception("index is larger than the lenght of receivers")
        self.receivers.insert(index, receiver)
