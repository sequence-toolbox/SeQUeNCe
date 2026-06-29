"""Fock quantum channel
"""

import numpy as np
from sequence.components.optical_channel import OpticalChannel
from sequence.kernel.timeline import Timeline
from sequence.topology.node import Node
from sequence.kernel.event import Event
from sequence.kernel.process import Process
import sequence.utils.log as log


class FockQuantumChannel(OpticalChannel):
    """Optical channel for transmission of photons/qubits.

    Attributes:
        name (str): label for channel instance.
        timeline (Timeline): timeline for simulation.
        sender (Node): node at sending end of optical channel.
        receiver (str): name of the node at receiving end of optical channel.
        attenuation (float): attenuation of the fiber (in dB/m).
        distance (int): length of the fiber (in m).

    """
    def __init__(self, name: str, timeline: "Timeline", attenuation: float, distance: int):
        super().__init__(name, timeline, attenuation, distance, polarization_fidelity=1.0, light_speed=3e-4) 
        self.delay = round(self.distance / self.light_speed)
        self.loss = np.exp(self.distance/self.attenuation)


    def set_ends(self, sender: "Node", receiver: str) -> None:
        """Method to set endpoints for the quantum channel.

        This must be performed before transmission.

        Args:
            sender (Node): node sending qubits.
            receiver (str): name of node receiving qubits.
        """

        log.logger.info("Set {}, {} as ends of quantum channel {}".format(sender.name, receiver, self.name))
        self.sender = sender
        self.receiver = receiver
        sender.assign_qchannel(self, receiver)


    def transmit(self, photon) -> None:
        print(f"Quantum Channel receiver: {self.receiver}")

        #if self.loss > 0.01:  # nel caso cambia valore
        future_time = self.timeline.now() + 0.000000001  # Delay opzionale
        # Crea un processo che richiama `receive_qubit` con il fotone e i canali
        process = Process(self.receiver, "receive_qubit", [self.sender.name, photon])
        event = Event(future_time, process)
        self.timeline.schedule(event)
        print("The optical photon reaches the destination")
     