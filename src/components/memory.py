"""Models for simulation of quantum memories.

This module defines the Memory class to simulate single atom memories as well as the MemoryArray class to aggregate memories.
Memories will attempt to send photons through the `send_qubit` interface of nodes.
Photons should be routed to a BSM device for entanglement generation, or through optical hardware for purification and swapping.
"""

from math import sqrt, inf
from typing import Any, List, TYPE_CHECKING, Dict

from scipy import stats

if TYPE_CHECKING:
    from ..entanglement_management.entanglement_protocol import EntanglementProtocol
    from ..kernel.timeline import Timeline
    from ..topology.node import QuantumRouter

from .photon import Photon
from .circuit import Circuit
from ..kernel.entity import Entity
from ..kernel.event import Event
from ..kernel.process import Process
from ..utils.encoding import single_atom
from ..utils.quantum_state import QuantumState


# array of single atom memories
class MemoryArray(Entity):
    """Aggregator for Memory objects.

    The MemoryArray can be accessed as a list to get individual memories.

    Attributes:
        name (str): label for memory array instance.
        timeline (Timeline): timeline for simulation.
        memories (List[Memory]): list of all memories.
    """

    def __init__(self, name: str, timeline: "Timeline", num_memories=10,
                 fidelity=0.85, frequency=80e6, efficiency=1, coherence_time=-1, wavelength=500):
        """Constructor for the Memory Array class.

        Args:
            name (str): name of the memory array instance.
            timeline (Timeline): simulation timeline.
            num_memories (int): number of memories in the array (default 10).
            fidelity (float): fidelity of memories (default 0.85).
            frequency (float): maximum frequency of excitation for memories (default 80e6).
            efficiency (float): efficiency of memories (default 1).
            coherence_time (float): average time (in s) that memory state is valid (default -1 -> inf).
            wavelength (int): wavelength (in nm) of photons emitted by memories (default 500).
        """

        Entity.__init__(self, name, timeline)
        self.memories = []
        self.owner = None

        for i in range(num_memories):
            memory = Memory(self.name + "[%d]" % i, timeline, fidelity, frequency, efficiency, coherence_time,
                            wavelength)
            memory.attach(self)
            self.memories.append(memory)

    def __getitem__(self, key):
        return self.memories[key]

    def __len__(self):
        return len(self.memories)

    def init(self):
        """Implementation of Entity interface (see base class).

        Set the owner of memory as the owner of memory array.
        """

        for mem in self.memories:
            mem.owner = self.owner
            mem.set_memory_array(self)

    def memory_expire(self, memory: "Memory"):
        """Method to receive expiration events from memories.

        Args:
            memory (Memory): expired memory.
        """

        self.owner.memory_expire(memory)

    def update_memory_params(self, arg_name: str, value: Any) -> None:
        for memory in self.memories:
            memory.__setattr__(arg_name, value)

    def set_node(self, node: "QuantumRouter") -> None:
        self.owner = node


class Memory(Entity):
    """Individual single-atom memory.

    This class models a single-atom memory, where the quantum state is stored as the spin of a single ion.
    This class will replace the older implementation once completed.

    Attributes:
        name (str): label for memory instance.
        timeline (Timeline): timeline for simulation.
        fidelity (float): (current) fidelity of memory.
        frequency (float): maximum frequency at which memory can be excited.
        efficiency (float): probability of emitting a photon when excited.
        coherence_time (float): average usable lifetime of memory (in seconds).
        wavelength (float): wavelength (in nm) of emitted photons.
        qstate (QuantumState): quantum state of memory.
        entangled_memory (Dict[str, Any]): tracks entanglement state of memory.
    """

    _meas_circuit = Circuit(1)
    _meas_circuit.measure(0)

    def __init__(self, name: str, timeline: "Timeline", fidelity: float, frequency: float,
                 efficiency: float, coherence_time: int, wavelength: int):
        """Constructor for the Memory class.

        Args:
            name (str): name of the memory instance.
            timeline (Timeline): simulation timeline.
            fidelity (float): fidelity of memory.
            frequency (float): maximum frequency of excitation for memory.
            efficiency (float): efficiency of memories.
            coherence_time (float): average time (in s) that memory state is valid.
            wavelength (int): wavelength (in nm) of photons emitted by memories.
            qstate_key (int): key for associated quantum state in timeline's quantum manager.
        """

        super().__init__(name, timeline)
        assert 0 <= fidelity <= 1
        assert 0 <= efficiency <= 1

        self.fidelity = 0
        self.raw_fidelity = fidelity
        self.frequency = frequency
        self.efficiency = efficiency
        self.coherence_time = coherence_time  # coherence time in seconds
        self.wavelength = wavelength
        self.qstate_key = timeline.quantum_manager.new()

        self.memory_array = None

        # keep track of previous BSM result (for entanglement generation)
        # -1 = no result, 0/1 give detector number
        self.previous_bsm = -1

        # keep track of entanglement
        self.entangled_memory = {'node_id': None, 'memo_id': None}

        # keep track of current memory write (ignore expiration of past states)
        self.expiration_event = None
        self.excited_photon = None

        self.next_excite_time = 0

    def init(self):
        pass

    def set_memory_array(self, memory_array: MemoryArray):
        self.memory_array = memory_array

    def excite(self, dst="") -> None:
        """Method to excite memory and potentially emit a photon.

        If it is possible to emit a photon, the photon may be marked as null based on the state of the memory.

        Args:
            dst (str): name of destination node for emitted photon (default "").

        Side Effects:
            May modify quantum state of memory.
            May schedule photon transmission to destination node.
        """

        # if can't excite yet, do nothing
        if self.timeline.now() < self.next_excite_time:
            return

        # measure quantum state
        res = self.timeline.quantum_manager.run_circuit(Memory._meas_circuit,
                                                        [self.qstate_key],
                                                        self.get_generator().random())
        state = res[self.qstate_key]

        # create photon and check if null
        photon = Photon("", wavelength=self.wavelength, location=self,
                        encoding_type=single_atom)
        photon.memory = self
        photon.qstate_key = self.qstate_key
        if state == 0:
            photon.is_null = True

        if self.frequency > 0:
            period = 1e12 / self.frequency
            self.next_excite_time = self.timeline.now() + period

        # send to node
        if (state == 0) or (self.get_generator().random() < self.efficiency):
            self.owner.send_qubit(dst, photon)
            self.excited_photon = photon

    def expire(self) -> None:
        """Method to handle memory expiration.

        Is scheduled automatically by the `set_plus` memory operation.

        Side Effects:
            Will notify upper entities of expiration via the `pop` interface.
            Will modify the quantum state of the memory.
        """

        if self.excited_photon:
            self.excited_photon.is_null = True

        self.reset()
        # pop expiration message
        self.notify(self)

    def reset(self) -> None:
        """Method to clear quantum memory.

        Will reset quantum state to \|0> and will clear entanglement information.

        Side Effects:
            Will modify internal parameters and quantum state.
        """

        self.fidelity = 0

        self.timeline.quantum_manager.set([self.qstate_key], [complex(1), complex(0)])
        self.entangled_memory = {'node_id': None, 'memo_id': None}
        if self.expiration_event is not None:
            self.timeline.remove_event(self.expiration_event)
            self.expiration_event = None

    def update_state(self, state: List[complex]) -> None:
        """Method to set the memory state to an arbitrary pure state.

        Args:
            state (List[complex]): array of amplitudes for pure state in Z-basis.

        Side Effects:
            Will modify internal quantum state and parameters.
            May schedule expiration event.
        """

        self.timeline.quantum_manager.set([self.qstate_key], state)
        self.previous_bsm = -1
        self.entangled_memory = {'node_id': None, 'memo_id': None}

        # schedule expiration
        if self.coherence_time > 0:
            self._schedule_expiration()

    def _schedule_expiration(self) -> None:
        if self.expiration_event is not None:
            self.timeline.remove_event(self.expiration_event)

        decay_time = self.timeline.now() + int(self.coherence_time * 1e12)
        process = Process(self, "expire", [])
        event = Event(decay_time, process)
        self.timeline.schedule(event)

        self.expiration_event = event

    def update_expire_time(self, time: int):
        """Method to change time of expiration.

        Should not normally be called by protocols.

        Args:
            time (int): new expiration time.
        """

        time = max(time, self.timeline.now())
        if self.expiration_event is None:
            if time >= self.timeline.now():
                process = Process(self, "expire", [])
                event = Event(time, process)
                self.timeline.schedule(event)
        else:
            self.timeline.update_event_time(self.expiration_event, time)

    def get_expire_time(self) -> int:
        return self.expiration_event.time if self.expiration_event else inf

    def notify(self, msg: Dict[str, Any]):
        for observer in self._observers:
            observer.memory_expire(self)

    def detach(self, observer: 'EntanglementProtocol'):
        if observer in self._observers:
            self._observers.remove(observer)

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
        qstate (QuantumState): quantum state of memory.
        entangled_memory (Dict[str, Any]): tracks entanglement state of memory.
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
            qstate_key (int): key for associated quantum state in timeline's quantum manager.
        """

        super(MemoryWithRandomCoherenceTime, self).__init__(name, timeline, fidelity, frequency, 
                         efficiency, coherence_time, wavelength)
        
        # coherence time standard deviation in seconds
        self.coherence_time_stdev = coherence_time_stdev
        self.random_coherence_time = ( coherence_time_stdev > 0.0 and
                                      self.coherence_time > 0.0 )
        
    def coherence_time_distribution(self) -> None:
        return stats.truncnorm.rvs(
            -0.95 * self.coherence_time / self.coherence_time_stdev,
            19.0 * self.coherence_time / self.coherence_time_stdev,
            self.coherence_time,
            self.coherence_time_stdev )        

    def _schedule_expiration(self) -> None:
        if self.expiration_event is not None:
            self.timeline.remove_event(self.expiration_event)
            
        coherence_period = ( self.coherence_time_distribution() 
                            if self.random_coherence_time else 
                            self.coherence_time )

        decay_time = self.timeline.now() + int(coherence_period * 1e12)
        process = Process(self, "expire", [])
        event = Event(decay_time, process)
        self.timeline.schedule(event)

        self.expiration_event = event


