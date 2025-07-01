"""Models for simulating bell state measurement.

This module defines an abstract class for a 'BSM'


This module defines a template bell state measurement (BSM) class,
as well as implementations for polarization, time bin, and memories encoding schemes.
Also defined is a function to automatically construct a BSM of a specified type.
"""

from math import sqrt
from typing import TYPE_CHECKING, Any

from ..detector.base import Detector
from ...kernel.entity import Entity

if TYPE_CHECKING:
    from ...kernel.timeline import Timeline

from abc import abstractmethod

class BSM(Entity):
    """Parent class for bell state measurement devices.

    Attributes:
        name (str): label for BSM instance.
        timeline (Timeline): timeline for simulation.
        phase_error (float): phase error applied to measurement.
        detectors (list[Detector]): list of attached photon detection devices.
        resolution (int): maximum time resolution achievable with attached detectors.
    """

    _phi_plus = [complex(sqrt(1 / 2)), complex(0), complex(0), complex(sqrt(1 / 2))]
    _phi_minus = [complex(sqrt(1 / 2)), complex(0), complex(0), -complex(sqrt(1 / 2))]
    _psi_plus = [complex(0), complex(sqrt(1 / 2)), complex(sqrt(1 / 2)), complex(0)]
    _psi_minus = [complex(0), complex(sqrt(1 / 2)), -complex(sqrt(1 / 2)), complex(0)]

    # Get all children
    _subclasses = []
    @classmethod
    def get_children(cls):
        return list(cls._subclasses)
    def __init_subclass__(cls):
        BSM._subclasses.append(cls)

    def __init__(self, name: str, timeline: "Timeline", phase_error: float = 0, detectors=None):
        """Constructor for base BSM object.

        Args:
            name (str): name of the beamsplitter instance.
            timeline (Timeline): simulation timeline.
            phase_error (float): Phase error applied to polarization photons (default 0).
            detectors (list[dict[str, Any]]): list of parameters for attached detectors,
                in dictionary format (default None).
        """

        super().__init__(name, timeline)
        self.encoding = "None"
        self.phase_error = phase_error
        self.photons = []
        self.photon_arrival_time = -1
        self.resolution = None

        self.detectors = []
        if detectors is not None:
            for i, d in enumerate(detectors):
                if d is not None:
                    detector = Detector("{}_{}".format(self.name, i), timeline, **d)
                    detector.attach(self)
                    detector.owner = self
                else:
                    detector = None
                self.detectors.append(detector)

        # define bell basis vectors
        self.bell_basis = ((complex(sqrt(1 / 2)), complex(0), complex(0), complex(sqrt(1 / 2))),
                           (complex(sqrt(1 / 2)), complex(0), complex(0), -complex(sqrt(1 / 2))),
                           (complex(0), complex(sqrt(1 / 2)), complex(sqrt(1 / 2)), complex(0)),
                           (complex(0), complex(sqrt(1 / 2)), -complex(sqrt(1 / 2)), complex(0)))

    def init(self):
        """Implementation of Entity interface (see base class)."""

        # get resolution
        self.resolution = max(d.time_resolution for d in self.detectors)

        self.photons = []
        self.photon_arrival_time = -1

    @abstractmethod
    def get(self, photon, **kwargs):
        """Method to receive a photon for measurement (abstract).

        Arguments:
            photon (Photon): photon to measure.
        """

        assert photon.encoding_type["name"] == self.encoding, \
            "BSM expecting photon with encoding '{}' received photon with encoding '{}'".format(
                self.encoding, photon.encoding_type["name"])

        # check if photon arrived later than current photon
        if self.photon_arrival_time < self.timeline.now():
            # clear photons
            self.photons = [photon]
            # set arrival time
            self.photon_arrival_time = self.timeline.now()

        # check if we have a photon from a new location
        if not any([reference.location == photon.location for reference in self.photons]):
            self.photons.append(photon)

    @abstractmethod
    def trigger(self, detector: Detector, info: dict[str, Any]):
        """Method to receive photon detection events from attached detectors (abstract).

        Arguments:
            detector (Detector): the source of the detection message.
            info (dict[str, Any]): the message from the source detector.
        """

        pass

    def notify(self, info: dict[str, Any]):
        for observer in self._observers:
            observer.bsm_update(self, info)

    def update_detectors_params(self, arg_name: str, value: Any) -> None:
        """Updates parameters of attached detectors."""
        for detector in self.detectors:
            detector.__setattr__(arg_name, value)