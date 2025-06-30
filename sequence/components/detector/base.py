from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from ...kernel.timeline import Timeline

from ..photon import Photon

from ..circuit import Circuit
from ...kernel.entity import Entity
from ...kernel.event import Event
from ...kernel.process import Process
from ...utils import log

class Detector(Entity):
    """Single photon detector device.

    This class models a single photon detector, for detecting photons.
    Can be attached to many different devices to enable different measurement options.

    Attributes:
        name (str): label for detector instance.
        timeline (Timeline): timeline for simulation.
        efficiency (float): probability to successfully measure an incoming photon.
        dark_count (float): average number of false positive detections per second.
        count_rate (float): maximum detection rate; defines detector cooldown time.
        time_resolution (int): minimum resolving power of photon arrival time (in ps).
        photon_counter (int): counts number of detection events.
    """

    _meas_circuit = Circuit(1)
    _meas_circuit.measure(0)

    def __init__(self, name: str, timeline: "Timeline", efficiency: float = 0.9, dark_count: float = 0, count_rate: float = 25e6, time_resolution: int = 150):
        Entity.__init__(self, name, timeline)  # Detector is part of the QSDetector, and does not have its own name
        self.efficiency = efficiency
        self.dark_count = dark_count  # measured in 1/s
        self.count_rate = count_rate  # measured in Hz
        self.time_resolution = time_resolution  # measured in ps
        self.next_detection_time = -1
        self.photon_counter = 0

    def init(self):
        """Implementation of Entity interface (see base class)."""
        self.next_detection_time = -1
        self.photon_counter = 0
        if self.dark_count > 0:
            self.add_dark_count()

    def get(self, photon=None, **kwargs) -> None:
        """Method to receive a photon for measurement.

        Args:
            photon (Photon): photon to detect (currently unused)

        Side Effects:
            May notify upper entities of a detection event.
        """

        self.photon_counter += 1

        # if get a photon and it has single_atom encoding, measure
        if photon and photon.encoding_type["name"] == "single_atom":
            key = photon.quantum_state
            res = self.timeline.quantum_manager.run_circuit(Detector._meas_circuit, [key], self.get_generator().random())
            # if we measure |0>, return (do not record detection)
            if not res[key]:
                return

        if self.get_generator().random() < self.efficiency:
            self.record_detection()
        else:
            log.logger.debug(f'Photon loss in detector {self.name}')

    def add_dark_count(self) -> None:
        """Method to schedule false positive detection events.

        Events are scheduled as a Poisson process.

        Side Effects:
            May schedule future `get` method calls.
            May schedule future calls to self.
        """

        assert self.dark_count > 0, "Detector().add_dark_count called with 0 dark count rate"
        time_to_next = int(self.get_generator().exponential(
                1 / self.dark_count) * 1e12)  # time to next dark count
        time = time_to_next + self.timeline.now()  # time of next dark count

        process1 = Process(self, "add_dark_count", [])  # schedule photon detection and dark count add in future
        process2 = Process(self, "record_detection", [])
        event1 = Event(time, process1)
        event2 = Event(time, process2)
        self.timeline.schedule(event1)
        self.timeline.schedule(event2)

    def record_detection(self):
        """Method to record a detection event.

        Will calculate if detection succeeds (by checking if we have passed `next_detection_time`)
        and will notify observers with the detection time (rounded to the nearest multiple of detection frequency).
        """

        now = self.timeline.now()

        if now > self.next_detection_time:
            time = round(now / self.time_resolution) * self.time_resolution
            self.notify({'time': time})
            self.next_detection_time = now + (1e12 / self.count_rate)  # period in ps

    def notify(self, info: dict[str, Any]):
        """Custom notify function (calls `trigger` method)."""

        for observer in self._observers:
            observer.trigger(self, info)

class QSDetector(Entity, ABC):
    """Abstract QSDetector parent class.

    Provides a template for objects measuring qubits in different encoding schemes.

    Attributes:
        name (str): label for QSDetector instance.
        timeline (Timeline): timeline for simulation.
        components (list[entity]): list of all aggregated hardware components.
        detectors (list[Detector]): list of attached detectors.
        trigger_times (list[list[int]]): tracks simulation time of detection events for each detector.
    """

    def __init__(self, name: str, timeline: "Timeline"):
        Entity.__init__(self, name, timeline)
        self.components = []
        self.detectors = []
        self.trigger_times = []

    def init(self):
        for component in self.components:
            component.attach(self)
            component.owner = self.owner

    def update_detector_params(self, detector_id: int, arg_name: str, value: Any) -> None:
        self.detectors[detector_id].__setattr__(arg_name, value)

    @abstractmethod
    def get(self, photon: "Photon", **kwargs) -> None:
        """Abstract method for receiving photons for measurement."""

        pass

    def trigger(self, detector: Detector, info: dict[str, Any]) -> None:
        # TODO: rewrite
        detector_index = self.detectors.index(detector)
        self.trigger_times[detector_index].append(info['time'])

    def set_detector(self, idx: int,  efficiency=0.9, dark_count=0, count_rate=int(25e6), time_resolution=150):
        """Method to set the properties of an attached detector.

        Args:
            idx (int): the index of attached detector whose properties are going to be set.
            For other parameters see the `Detector` class. Default values are same as in `Detector` class.
        """
        assert 0 <= idx < len(self.detectors), "`idx` must be a valid index of attached detector."

        detector = self.detectors[idx]
        detector.efficiency = efficiency
        detector.dark_count = dark_count
        detector.count_rate = count_rate
        detector.time_resolution = time_resolution

    def get_photon_times(self):
        return self.trigger_times

    @abstractmethod
    def set_basis_list(self, basis_list: list[int], start_time: int, frequency: float) -> None:
        pass