"""Model for simulation of a SPDC Lens.

This module defines the SPDCLens class for creation of entangled photons.
"""

from copy import deepcopy

from ..kernel.entity import Entity


class SPDCLens(Entity):
    """Lens to create entangled photons (via SPDC).

    Attributes:
        name (str): label for SPDCLens instance.
        timeline (Timeline): timeline for simulation.
        rate (float): probability of successful down conversion.
        direct_receiver (Entity): entity to receive entangled photons.
    """

    def __init__(self, name, timeline, rate=1, direct_receiver=None):
        """Constructor for the spdc lens class.

        Args:
            name (str): name of the spdc lens instance.
            timeline (Timeline): simulation timeline.
            rate (float): probability of successfull down conversion (default 1).
            direct_receiver (Entity): entity to receive down-converted photons (default None).
        """

        Entity.__init__(self, name, timeline)
        self.rate = rate
        self.direct_receiver = direct_receiver

    def init(self):
        """Implementation of Entity interface (see base class)."""

        pass

    def get(self, photon):
        """Method to receive a photon for transmission.

        Based on rate probability, may split photon into two entangled photons.

        Args:
            photon (Photon): photon to down-convert.

        Side Effects:
            May create two entangledd photons and send them to the direct_receiver.
        """

        if self.get_generator().random() < self.rate:
            state = photon.quantum_state
            photon.wavelength /= 2
            new_photon = deepcopy(photon)

            photon.entangle(new_photon)
            photon.set_state((state[0], complex(0), complex(0), state[1]))

            self.direct_receiver.get(photon)
            self.direct_receiver.get(new_photon)

    def assign_receiver(self, receiver):
        self.direct_receiver = receiver
