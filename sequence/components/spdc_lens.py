"""Model for simulation of an SPDC Lens.

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
    """

    def __init__(self, name, timeline, rate=1):
        """Constructor for the spdc lens class.

        Args:
            name (str): name of the spdc lens instance.
            timeline (Timeline): simulation timeline.
            rate (float): probability of successful down conversion (default 1).
        """

        Entity.__init__(self, name, timeline)
        self.rate = rate

    def init(self):
        """Implementation of Entity interface (see base class)."""

        pass

    def get(self, photon, **kwargs):
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

            photon.combine_state(new_photon)
            photon.set_state((state[0], complex(0), complex(0), state[1]))

            self._receivers[0].get(photon)
            self._receivers[1].get(new_photon)
