"""Models for simulation of fiber stretching.

This module introduces the FiberStretcher class.
The fiber stretcher modifies the phase of incoming photons, but does not add additional delay.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .photon import Photon

from ..kernel.entity import Entity
from .circuit import Circuit


class FiberStretcher(Entity):
    """Class implementing a simple fiber stretcher.

    Attributes:
        name (str): name of the fiber stretcher instance.
        timeline (Timeline): simulation timeline.
        _circuit (Circuit): quantum circuit used to apply a phase shift to incoming photons.
    """

    def __init__(self, name, timeline, phase=0.0):
        """Constructor for Fiber Stretcher class.

        Args:
            name (str): name of the fiber stretcher.
            timeline (Timeline): simulation timeline.
            phase (float): phase to apply to incoming photons (default 0.0).
        """

        super().__init__(name, timeline)
        self._circuit = Circuit(1)
        self._circuit.phase(0, phase)

    def init(self):
        pass

    def set_phase(self, phase: float):
        """Method to change the phase applied to incoming photons.

        Args:
            phase (float): new phase to use.
        """

        self._circuit = Circuit(1)
        self._circuit.phase(0, phase)

    def get(self, photon: "Photon", **kwargs):
        """Method to receive a photon.

        Applies the local phase quantum circuit, then forwards to first receiver.
        This phase is only applied if the photon is using the absorptive encoding scheme.

        Args:
            photon (Photon): photon to transmit.
        """

        if photon.encoding_type['name'] == "absorptive":
            key = photon.quantum_state
            self.timeline.quantum_manager.run_circuit(self._circuit, [key])
        self._receivers[0].get(photon)
