from ...utils import log
import heapq as hq
from typing import TYPE_CHECKING
import numpy as np
import re
from scapy.all import PcapNgReader, raw
from bitstring import BitArray

if TYPE_CHECKING:
    from ...kernel.timeline import Timeline
    from ...topology.node import Node
    from ...message import Message

from ...components.photon import Photon
from ...kernel.entity import Entity
from ...kernel.event import Event
from ...kernel.process import Process

from ...components.optical_channel import QuantumChannel

from ...constants import SPEED_OF_LIGHT


class QuantumChannel(QuantumChannel):

    def __init__(self, name: str, timeline: "Timeline", attenuation: float, distance: int,
                 polarization_fidelity=1.0, light_speed=SPEED_OF_LIGHT, frequency=8e7, refractive_index = 1.47, density_matrix_tacking = False):
        super().__init__(name, timeline, attenuation, distance, polarization_fidelity, light_speed, frequency)

        self.refractive_index = refractive_index
        self.density_matrix_tacking = density_matrix_tacking

    def transmit(self, photon: "Photon", source: "Node") -> None:
        """Method to transmit photon-encoded qubits.

        Args:
            photon (Photon): photon to be transmitted.
            source (Node): source node sending the qubit.

        Side Effects:
            Receiver node may receive the qubit (via the `receive_qubit` method).
        """

        log.logger.info(
            "{} send qubit with state {} to {} by Channel {}".format(
                self.sender.name, photon.quantum_state, self.receiver,
                self.name))

        assert self.delay >= 0 and self.loss < 1, \
            "QuantumChannel init() function has not been run for {}".format(self.name)
        assert source == self.sender

        self._remove_lowest_time_bin()

        # print("transmitting phootns")

        # transmission logic
        key = photon.quantum_state
        self.timeline.quantum_manager.add_loss(key, self.loss)

        # print("transmitted state:", self.timeline.quantum_manager.states[key].keys)
        

        self.send_photon(photon, source)