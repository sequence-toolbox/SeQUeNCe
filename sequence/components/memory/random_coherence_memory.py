from typing import TYPE_CHECKING

from scipy import stats

from .memory_base import Memory
from ...kernel.event import Event
from ...kernel.process import Process

if TYPE_CHECKING:
    from ...kernel.timeline import Timeline


class MemoryWithRandomCoherenceTime(Memory):
    """Individual single-atom memory.

    This class inherits Memory class and provides possibility to use stochastic model of
    coherence time. This means that loss of entanglement of the memory with a photon occurs
    at random time given by truncated normal distribution with average value set by
    'coherence_time' input parameter and with standard deviation set by 'coherence_time_stdev'
    input parameter. If coherence_time_stdev <= 0.0 is passed, the class behaves exactly as
    original Memory class.

    Attributes:
        name (str): label for memory instance.
        timeline (Timeline): timeline for simulation.
        fidelity (float): (current) fidelity of memory.
        frequency (float): maximum frequency at which memory can be excited.
        efficiency (float): probability of emitting a photon when excited.
        coherence_time (float): average usable lifetime of memory (in seconds).
        coherence_time_stdev (float): standard deviation of coherence time
        wavelength (float): wavelength (in nm) of emitted photons.
        qstate_key (int): key for associated quantum state in timeline's quantum manager.
        entangled_memory (dict[str, Any]): tracks entanglement state of memory.
    """

    def __init__(self, name: str, timeline: "Timeline", fidelity: float, frequency: float,
                 efficiency: float, coherence_time: float, coherence_time_stdev: float, wavelength: int):
        """Constructor for the Memory class.

        Args:
            name (str): name of the memory instance.
            timeline (Timeline): simulation timeline.
            fidelity (float): fidelity of memory.
            frequency (float): maximum frequency of excitation for memory.
            efficiency (float): efficiency of memories.
            coherence_time (float): average time (in s) that memory state is valid
            coherence_time_stdev (float): standard deviation of coherence time
            wavelength (int): wavelength (in nm) of photons emitted by memories.
        """

        super(MemoryWithRandomCoherenceTime, self).__init__(name, timeline, fidelity, frequency,
                                                            efficiency, coherence_time, wavelength)

        # coherence time standard deviation in seconds
        self.coherence_time_stdev = coherence_time_stdev
        self.random_coherence_time = (coherence_time_stdev > 0.0 and
                                      self.coherence_time > 0.0)

    def coherence_time_distribution(self) -> None:
        return stats.truncnorm.rvs(
            -0.95 * self.coherence_time / self.coherence_time_stdev,
            19.0 * self.coherence_time / self.coherence_time_stdev,
            self.coherence_time,
            self.coherence_time_stdev)

    def _schedule_expiration(self) -> None:
        if self.expiration_event is not None:
            self.timeline.remove_event(self.expiration_event)

        coherence_period = (self.coherence_time_distribution()
                            if self.random_coherence_time else
                            self.coherence_time)

        decay_time = self.timeline.now() + int(coherence_period * 1e12)
        process = Process(self, "expire", [])
        event = Event(decay_time, process)
        self.timeline.schedule(event)

        self.expiration_event = event
