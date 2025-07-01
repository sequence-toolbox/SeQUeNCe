from copy import copy
from typing import Any, TYPE_CHECKING, Callable

from numpy import array, exp

from ..photon import Photon
from ...constants import EPSILON
from ...kernel.entity import Entity
from ...kernel.event import Event
from ...kernel.process import Process
from ...utils import log
from ...utils.encoding import single_atom, single_heralded

if TYPE_CHECKING:
    from ...kernel.timeline import Timeline
    from ...entanglement_management.entanglement_protocol import EntanglementProtocol

from math import inf


def const(t):
    """Constant function thal always returns 1. For AFC memory default spin efficiency."""
    return 1


# define helper functions for analytical BDS decoherence implementation, reference see recurrence protocol paper
def _p_id(x_rate, y_rate, z_rate, t):
    val = (1 + exp(-2 * (x_rate + y_rate) * t) + exp(-2 * (x_rate + z_rate) * t) + exp(-2 * (z_rate + y_rate) * t)) / 4
    return val


def _p_xerr(x_rate, y_rate, z_rate, t):
    val = (1 - exp(-2 * (x_rate + y_rate) * t) - exp(-2 * (x_rate + z_rate) * t) + exp(-2 * (z_rate + y_rate) * t)) / 4
    return val


def _p_yerr(x_rate, y_rate, z_rate, t):
    val = (1 - exp(-2 * (x_rate + y_rate) * t) + exp(-2 * (x_rate + z_rate) * t) - exp(-2 * (z_rate + y_rate) * t)) / 4
    return val


def _p_zerr(x_rate, y_rate, z_rate, t):
    val = (1 + exp(-2 * (x_rate + y_rate) * t) - exp(-2 * (x_rate + z_rate) * t) - exp(-2 * (z_rate + y_rate) * t)) / 4
    return val


class MemoryArray(Entity):
    """Aggregator for Memory objects.

    Equivalent to an array of single atom memories.
    The MemoryArray can be accessed as a list to get individual memories.

    Attributes:
        name (str): label for memory array instance.
        timeline (Timeline): timeline for simulation.
        memories (list[Memory]): list of all memories.
    """

    def __init__(self, name: str, timeline: "Timeline", num_memories=10,
                 fidelity=0.85, frequency=80e6, efficiency=1, coherence_time=-1, wavelength=500,
                 decoherence_errors: list[float] = None, cutoff_ratio=1):
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
            decoherence_errors (list[int]): pauli decoherence errors. Passed to memory object.
            cutoff_ratio (float): the ratio between cutoff time and memory coherence time (default 1, should be between 0 and 1).
        """

        Entity.__init__(self, name, timeline)
        self.memories = []
        self.memory_name_to_index = {}

        for i in range(num_memories):
            memory_name = self.name + f"[{i}]"
            self.memory_name_to_index[memory_name] = i
            memory = Memory(memory_name, timeline, fidelity, frequency, efficiency, coherence_time, wavelength,
                            decoherence_errors, cutoff_ratio)
            memory.attach(self)
            self.memories.append(memory)
            memory.set_memory_array(self)

    def __getitem__(self, key: int) -> "Memory":
        return self.memories[key]

    def __setitem__(self, key: int, value: "Memory"):
        self.memories[key] = value

    def __len__(self) -> int:
        return len(self.memories)

    def init(self):
        """Implementation of Entity interface (see base class).

        Set the owner of memory as the owner of memory array.
        """

        for memory in self.memories:
            memory.owner = self.owner

    def memory_expire(self, memory: "Memory"):
        """Method to receive expiration events from memories.

        Args:
            memory (Memory): expired memory.
        """

        self.owner.memory_expire(memory)

    def update_memory_params(self, arg_name: str, value: Any) -> None:
        for memory in self.memories:
            memory.__setattr__(arg_name, value)

    def add_receiver(self, receiver: "Entity") -> None:
        """Add receiver to each memory in the memory array to receive photons.

        Args:
            receiver (Entity): receiver of the memory
        """
        for memory in self.memories:
            memory.add_receiver(receiver)

    def get_memory_by_name(self, name: str) -> "Memory":
        """Given the memory's name, get the memory object.

        Args:
            name (str): name of memory
        Return:
            (Memory): the memory object
        """
        index = self.memory_name_to_index.get(name, -1)
        assert index >= 0, "Oops! name={} not exist!"
        return self.memories[index]


class Memory(Entity):
    """Individual single-atom memory.

    This class models a single-atom memory, where the quantum state is stored as the spin of a single ion.
    This class will replace the older implementation once completed.

    Attributes:
        name (str): label for memory instance.
        timeline (Timeline): timeline for simulation.
        fidelity (float):     (current) fidelity of memory.
        raw_fidelity (float): (initial) fidelity of memory.
        frequency (float): maximum frequency at which memory can be excited.
        efficiency (float): probability of emitting a photon when excited.
        coherence_time (float): average usable lifetime of memory (in seconds). Negative value means infinite coherence time.
        wavelength (float): wavelength (in nm) of emitted photons.
        qstate_key (int): key for associated quantum state in timeline's quantum manager.
        memory_array (MemoryArray): memory array aggregating current memory.
        entangled_memory (dict[str, Any]): tracks entanglement state of memory.
        docoherence_errors (list[float]): assumeing the memory (qubit) decoherence channel being Pauli channel,
            Probability distribution of X, Y, Z Pauli errors;
            (default value is -1, meaning not using BDS or further density matrix representation)
            Question: is it general enough? Dephasing/damping channel, multipartite entanglement?
        cutoff_ratio (float): ratio between cutoff time and memory coherence time (default 1, should be between 0 and 1).
        generation_time (float): time when the EPR is first generated (float or int depends on timeing unit)
            (default -1 before generation or not used). Used only for logging
        last_update_time (float): last time when the EPR pair is updated (usually when decoherence channel applied),
            used to determine decoherence channel (default -1 before generation or not used)
        is_in_application (bool): whether the quantum memory is involved in application after successful distribution of EPR pair
    """

    def __init__(self, name: str, timeline: "Timeline", fidelity: float, frequency: float,
                 efficiency: float, coherence_time: float, wavelength: int, decoherence_errors: list[float] = None,
                 cutoff_ratio: float = 1):
        """Constructor for the Memory class.

        Args:
            name (str): name of the memory instance.
            timeline (Timeline): simulation timeline.
            fidelity (float): initial fidelity of memory.
            frequency (float): maximum frequency of excitation for memory.
            efficiency (float): efficiency of memories.
            coherence_time (float): average time (in s) that memory state is valid.
            decoherence_rate (float): rate of decoherence to implement time dependent decoherence.
            wavelength (int): wavelength (in nm) of photons emitted by memories.
            decoherence_errors (list[float]): assuming the memory (qubit) decoherence channel being Pauli channel,
                probability distribution of X, Y, Z Pauli errors
                (default value is None, meaning not using BDS or further density matrix representation)
            cutoff_ratio (float): the ratio between cutoff time and memory coherence time (default 1, should be between 0 and 1).
        """

        super().__init__(name, timeline)
        assert 0 <= fidelity <= 1
        assert 0 <= efficiency <= 1

        self.fidelity = 0
        self.raw_fidelity = fidelity
        self.frequency = frequency
        self.efficiency = efficiency
        self.coherence_time = coherence_time  # coherence time in seconds
        self.decoherence_rate = 1 / self.coherence_time if self.coherence_time > 0 else 0  # rate of decoherence to implement time dependent decoherence
        self.wavelength = wavelength
        self.qstate_key = timeline.quantum_manager.new()
        self.memory_array = None

        self.decoherence_errors = decoherence_errors
        if self.decoherence_errors is not None:
            assert len(self.decoherence_errors) == 3 and abs(sum(self.decoherence_errors) - 1) < EPSILON, \
                "Decoherence errors refer to probabilities for each Pauli error to happen if an error happens, thus should be normalized."
        self.cutoff_ratio = cutoff_ratio
        assert 0 < self.cutoff_ratio <= 1, "Ratio of cutoff time and coherence time should be between 0 and 1"
        self.generation_time = -1
        self.last_update_time = -1
        self.is_in_application = False

        # for photons
        self.encoding = copy(single_atom)
        self.encoding["raw_fidelity"] = self.raw_fidelity

        # for photons in general single-heralded EG protocols
        self.encoding_sh = copy(single_heralded)

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

    def excite(self, dst="", protocol="bk") -> None:
        """Method to excite memory and potentially emit a photon.

        If it is possible to emit a photon, the photon may be marked as null based on the state of the memory.

        Args:
            dst (str): name of destination node for emitted photon (default "").
            protocol (str): Valid values are "bk" (for Barrett-Kok protocol) or "sh" (for single heralded)

        Side Effects:
            May modify quantum state of memory.
            May schedule photon transmission to destination node.
        """

        # if can't excite yet, do nothing
        if self.timeline.now() < self.next_excite_time:
            return

        # create photon
        if protocol == "bk":
            photon = Photon("", self.timeline, wavelength=self.wavelength, location=self.name,
                            encoding_type=self.encoding,
                            quantum_state=self.qstate_key, use_qm=True)
        elif protocol == "sh":
            photon = Photon("", self.timeline, wavelength=self.wavelength, location=self.name,
                            encoding_type=self.encoding_sh,
                            quantum_state=self.qstate_key, use_qm=True)
            # keep track of memory initialization time
            self.generation_time = self.timeline.now()
            self.last_update_time = self.timeline.now()
        else:
            raise ValueError("Invalid protocol type {} specified for meomory.exite()".format(protocol))

        photon.timeline = None  # facilitate cross-process exchange of photons
        photon.is_null = True
        photon.add_loss(1 - self.efficiency)

        if self.frequency > 0:
            period = 1e12 / self.frequency
            self.next_excite_time = self.timeline.now() + period

        # send to receiver
        self._receivers[0].get(photon, dst=dst)
        self.excited_photon = photon

    def expire(self) -> None:
        """Method to handle memory expiration.

        Is scheduled automatically by the `set_plus` memory operation.

        If the quantum memory has been explicitly involved in application after entanglement distribution, do not expire.
            Some simplified applications do not necessarily need to modify the is_in_application attribute.
            Some more complicated applications, such as probe state preparation for distributed quantum sensing,
            may change is_in_application attribute to keep memory from expiring during study.

        Side Effects:
            Will notify upper entities of expiration via the `pop` interface.
            Will modify the quantum state of the memory.
        """

        if self.is_in_application:
            pass

        else:
            if self.excited_photon:
                self.excited_photon.is_null = True

            self.reset()
            # pop expiration message
            self.notify(self)

    def reset(self) -> None:
        """Method to clear quantum memory.

        Will reset quantum state to |0> and will clear entanglement information.

        Side Effects:
            Will modify internal parameters and quantum state.
        """

        self.fidelity = 0
        self.generation_time = -1
        self.last_update_time = -1

        self.timeline.quantum_manager.set([self.qstate_key], [complex(1), complex(0)])
        self.entangled_memory = {'node_id': None, 'memo_id': None}
        if self.expiration_event is not None:
            self.timeline.remove_event(self.expiration_event)
            self.expiration_event = None

    def update_state(self, state: list[complex]) -> None:
        """Method to set the memory state to an arbitrary pure state.

        Args:
            state (list[complex]): array of amplitudes for pure state in Z-basis.

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

    def bds_decohere(self) -> None:
        """Method to decohere stored BDS in quantum memory according to the single-qubit Pauli channels.

        During entanglement distribution (before application phase),
        BDS decoherence can be treated analytically (see entanglement purification paper for explicit formulae).

        Side Effects:
            Will modify BDS diagonal elements and last_update_time.
        """

        if self.decoherence_errors is None:
            # if not considering time-dependent decoherence then do nothing
            pass

        else:
            time = (self.timeline.now() - self.last_update_time) * 1e-12  # duration of memory idling (in s)
            if time > 0 and self.last_update_time > 0:  # time > 0 means time has progressed, self.last_update_time > 0 means the memory has not been reset

                x_rate, y_rate, z_rate = self.decoherence_rate * self.decoherence_errors[0], \
                                         self.decoherence_rate * self.decoherence_errors[1], \
                                         self.decoherence_rate * self.decoherence_errors[2]
                p_I, p_X, p_Y, p_Z = _p_id(x_rate, y_rate, z_rate, time), \
                    _p_xerr(x_rate, y_rate, z_rate, time), \
                    _p_yerr(x_rate, y_rate, z_rate, time), \
                    _p_zerr(x_rate, y_rate, z_rate, time)

                state_now = self.timeline.quantum_manager.states[self.qstate_key].state  # current diagonal elements
                transform_mtx = array([[p_I, p_Z, p_X, p_Y],
                                       [p_Z, p_I, p_Y, p_X],
                                       [p_X, p_Y, p_I, p_Z],
                                       [p_Y, p_X, p_Z, p_I]])  # transform matrix for diagonal elements
                state_new = transform_mtx @ state_now  # new diagonal elements after decoherence transformation

                log.logger.debug(f'{self.name}: before f={state_now[0]:.6f}, after f={state_new[0]:.6f}')

                # update the quantum state stored in quantum manager for self and entangled memory
                keys = self.timeline.quantum_manager.states[self.qstate_key].keys
                self.timeline.quantum_manager.set(keys, state_new)

                # update the last_update_time of self
                # note that the attr of entangled memory should not be updated right now,
                # because decoherence has not been applied there
                self.last_update_time = self.timeline.now()

    def _schedule_expiration(self) -> None:
        if self.expiration_event is not None:
            self.timeline.remove_event(self.expiration_event)

        decay_time = self.timeline.now() + int(self.cutoff_ratio * self.coherence_time * 1e12)
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

    def notify(self, msg: dict[str, Any]):
        for observer in self._observers:
            observer.memory_expire(self)

    def detach(self, observer: 'EntanglementProtocol'):  # observer could be a MemoryArray
        if observer in self._observers:
            self._observers.remove(observer)

    def get_bds_state(self):
        """Method to get state of memory in BDS formalism.

        Will automatically call the `bds_decohere` method.
        """
        self.bds_decohere()
        state_obj = self.timeline.quantum_manager.get(self.qstate_key)
        state = state_obj.state
        return state

    def get_bds_fidelity(self) -> float:
        """Will get the fidelity from the BDS state

        Return:
            (float): the fidelity of the BDS state
        """
        state_obj = self.timeline.quantum_manager.get(self.qstate_key)
        state = state_obj.state
        return state[0]


class AbsorptiveMemory(Entity):
    """Atomic ensemble absorptive memory.

    This class models an AFC(-spinwave) absorptive memory, where the quantum state is stored as collective excitation of atomic ensemble.
    Rephasing time (predetermined storage time for AFC type) is given by temporal mode number and length of each temporal mode bin.
    This class does not support qubit state manipulation, individual photons should be manipulated instead.

    Before invoking methods like "get" and "retrieve", need to call "prepare" first to prepare the AFC, will take finite simulation time.
    Retrieved photon sequence might be reversed (only for AFC-spinwave), which is physically determined by RF pulses used during spinwave.
    Note that for AFC (not spinwave) type, is_reversed must be False.

    Note that the memory is reusable (available for other rounds of absorption) as long as AFC structure is still usable.
    Once AFC structure expires the memory also expires, and the memory needs to be re-prepared so stored photons cannot be retrieved.
    Spinwave coherence time determines whether a certain cycle of absorption and re-emission will be successful.
    Eg. If on-demand storage time is longer than spinwave coherence time, the information stored in this cycle will be cleared.
        However, if the AFC structure retains usability (in this example AFC_lifetime > coherence_time), the memory itself is not expired.

    Attributes:
        name (str): label for memory instance.
        timeline (Timeline): timeline for simulation.
        fidelity (float): (current) fidelity of memory's entanglement.
        frequency (float): maximum frequency of absorption for memory (total frequency bandwidth of AFC memory) (in Hz).
        absorption_efficiency (float): probability of absorbing a photon when arriving at the memory.
        afc_efficiency (Callable): probability of emitting a photon as a function of AFC re-emission time of optical AFC.
        spin_efficiency (Callable): effeciency of spinwave storage as a function of storage time.
        mode_number (int): number of temporal modes available for storing photons, i.e. number of peaks in Atomic Frequency Comb.
        mode_bin (int):
        afc_lifetime (float): average usable lifetime of AFC structure (in s), 0 means infinite lifetime.
        coherence_time (float): average usable lifetime of spinwave storage (spinwave transition coherence time) (in s), 0 means infinite coherence time.
        wavelength (float): wavelength (in nm) of absorbed and emitted photons.
        total_time (float): AFC re-phasing time (in ps)
        overlap_error (float): error due to photon overlap in one temporal mode, will degrade fidelity.
        prepare_time (float): time to prepare AFC (in ps).
        photon_counter (int): counts number of detection events.
        absorb_start_time (int): start time (in ps) of photon absorption.
        retrieve_start_time (int): start time (in ps) of photon retrieval.
        is_spinwave (Bool): determines if the memory is AFC or AFC-spinwave, default False.
        is_reversed (Bool): determines re-emission sequence, physically determined by RF pulses during spinwave, default False.
        is_prepared (Bool): determines if AFC is successfully prepared.
        memory_array (MemoryArray): memory array aggregating current memory.
        destination (str): name of predetermined re-emission destination node, default None.
        entangled_memory (dict[str, Any]): tracks entanglement state of memory with a memory.
        stored_photons (list[dict]): photons stored in memory temporal modes.
    """

    def __init__(self, name: str, timeline: "Timeline", frequency: float, absorption_efficiency: float,
                 afc_efficiency: Callable, mode_number: int, wavelength: int, prepare_time: int = 0,
                 afc_lifetime: float = -1, coherence_time: float = -1, fidelity: float = 1, overlap_error: float = 0,
                 is_spinwave=False, is_reversed=False, destination=None, spin_efficiency=const):
        """Constructor for the AbsorptiveMemory class.

        Args:
            name (str): name of the memory instance.
            timeline (Timeline): simulation timeline.
            fidelity (float): fidelity of memory.
            frequency (float): maximum frequency of absorption for memory (total frequency bandwidth of AFC memory).
            absorption_efficiency (float): probability of absorbing a photon when arriving at the memory.
            afc_efficiency (Callable): probability of emitting a photon as a function of AFC re-emission time of optical AFC.
            spin_efficiency (Callable): effeciency of spinwave storage as a function of storage time. Default contant unity.
            mode_number (int): number of modes supported for storing photons.
            afc_lifetime (float): average usable lifetime of AFC structure (in s), -1 means infinite lifetime.
            coherence_time (float): average usable lifetime of spinwave storage (spinwave transition coherence time) (in s), -1 means infinite coherence time.
            wavelength (int): wavelength (in nm) of photons emitted by memories.
            overlap_error (float): error due to photon overlap in one temporal mode.
            prepare_time (float): time to prepare AFC (in ps).
            is_spinwave (Bool): determines if the memory is AFC or AFC-spinwave (default False).
            is_reversed (Bool): determines re-emission sequence, physically determined by RF pulses during spinwave (default False).
            destination (str): name of predetermined re-emission destination node (default None).
        """

        super().__init__(name, timeline)
        assert 0 <= fidelity <= 1
        assert 0 <= absorption_efficiency <= 1

        self.fidelity = 0
        self.raw_fidelity = fidelity
        self.frequency = frequency
        self.absorption_efficiency = absorption_efficiency
        self.afc_efficiency = afc_efficiency
        self.spin_efficiency = spin_efficiency
        self.mode_number = mode_number
        self.afc_lifetime = afc_lifetime  # AFC lifetime in seconds
        self.coherence_time = coherence_time  # spinwave coherencetime in seconds
        self.wavelength = wavelength
        self.mode_bin = 1e12 / self.frequency  # time bin for each separate temporal mode in ps
        self.total_time = self.mode_number * self.mode_bin  # AFC rephasing time in ps
        self.overlap_error = overlap_error
        self.prepare_time = prepare_time

        self.photon_counter = 0
        self.absorb_start_time = 0
        self.retrieve_start_time = 0

        self.is_spinwave = is_spinwave
        self.is_reversed = is_reversed
        self.is_prepared = False

        self.memory_array = None
        self.destination = destination

        # keep track of previous BSM result (for entanglement generation)
        # -1 = no result, 0/1 give detector number
        self.previous_bsm = -1

        # keep track of entanglement with memory
        # photon entanglement stored internally within photons
        self.entangled_memory = {'node_id': None, 'memo_id': None}

        # keep track of current memory write (ignore expiration of past states)
        self.expiration_event = None
        self.excited_photons = []

        # initialization of stored_photons dictionary
        self.stored_photons: list[None | dict] = [None] * self.mode_number

    def init(self):
        """Implementation of Entity interface (see base class)."""

        pass

    def set_memory_array(self, memory_array: MemoryArray):
        """Method to set the memory array to which the memory belongs

        Args:
            memory_array (MemoryArray): memory array to which the memory belongs
        """

        self.memory_array = memory_array

    def prepare(self):
        """Method to emulate the effect on timeline by AFC preparation.

        Will schedule a preparation event in the future, after which `is_prepared` is set to true.
        """

        process = Process(self, "_prepare_AFC", [])
        event = Event(self.timeline.now() + self.prepare_time, process)
        self.timeline.schedule(event)

    def _prepare_AFC(self):
        """Method to get AFC prepared, will change is_prepared field.

        Will raise exception if already prepared.
        Should not be called directly, only scheduled by prepare method.
        """

        if self.is_prepared:
            raise Exception("AFC has already been prepared")
        else:
            self.is_prepared = True

            # schedule AFC expiration once it is prepared, if finite AFC lifetime
            if self.afc_lifetime > 0:
                self._schedule_expiration()

    def get(self, photon: "Photon", **kwargs):
        """Method to receive a photon to store in the absorptive memory."""

        # AFC needs to be prepared first
        if not self.is_prepared:
            raise Exception("AFC is not prepared yet.")

        self.photon_counter += 1
        now = self.timeline.now()

        # determine which temporal mode the photon is stored in
        absorb_time = now - self.absorb_start_time
        index = int(absorb_time / self.mode_bin)
        if index < 0 or index >= self.mode_number:
            return

        # require resonant absorption of photons
        # if photon uses Fock representation, inefficiency will be reflected with loss channel
        if photon.encoding_type["name"] == "fock" and photon.wavelength == self.wavelength:
            # invoke loss channel due to absorption inefficiency
            key = photon.quantum_state  # if using Fock representation, the `quantum_state` field is the state key.
            loss = 1 - self.absorption_efficiency  # loss rate due to absorption inefficiency
            # apply loss channel on photonic state and return a new state
            self.timeline.quantum_manager.add_loss(key, loss)

            # store photon information, NOTE the difference between information recorded for different encodings
            # in this case, store more than one photon
            if self.stored_photons[index] is None:
                self.stored_photons[index] = {"photons": [photon], "times": [absorb_time]}
                self.excited_photons.append(photon)
            else:
                self.stored_photons[index]["photons"].append(photon)
                self.stored_photons[index]["times"].append(absorb_time)

        # otherwise, use random counter w/ efficiency
        elif photon.wavelength == self.wavelength and self.get_generator().random() < self.absorption_efficiency:
            # keep one photon per mode since most hardware cannot resolve photon number
            # photon_counter might be larger than mode_number, multi-photon events counted by "number"
            # if "overlap" is True, memory fidelity will be corrected by overlap_error
            if self.stored_photons[index] is None:
                self.stored_photons[index] = {"photon": photon, "time": absorb_time, "number": 1, "overlap": False}
                self.excited_photons.append(photon)
            else:
                self.stored_photons[index]["number"] += 1
                self.stored_photons[index]["overlap"] = True

        # determine absorb_start_time
        if self.photon_counter == 1:
            self.absorb_start_time = now

            # schedule re-emission if memory is not spinwave type
            if not self.is_spinwave:
                process = Process(self, "retrieve", [])
                event = Event(self.absorb_start_time + self.total_time, process)
                self.timeline.schedule(event)
            else:
                # if spinwave type, and if finite spin coherence time, schedule spinwave decoherence induced storage resetting
                if self.coherence_time > 0:
                    self._schedule_storage_reset()

    def retrieve(self, dst=""):
        """Method to re-emit all stored photons in normal/reverse sequence on demand.

        Efficiency is a function of time.
        """

        # AFC needs to be prepared first
        # for simplicity, do not allow memory to re-emit if AFC expires
        if not self.is_prepared:
            raise Exception("AFC is not prepared yet or has expired.")

        # do nothing if there are no photons stored
        if len(self.excited_photons) == 0:
            return

        now = self.timeline.now()
        store_time = now - self.absorb_start_time - self.total_time

        for index in range(self.mode_number):

            if self.stored_photons[index] is not None:
                stored_photons = self.stored_photons[index]

                # check if using Fock representation (will include
                # if photon uses Fock representation, no need for random number judgement
                # inefficiency will be reflected with loss channel
                if "photons" in stored_photons:
                    for photon, absorb_time in zip(stored_photons["photons"], stored_photons["times"]):

                        key = photon.quantum_state
                        # loss rate due to emission inefficiency
                        loss = 1 - self.afc_efficiency(self.total_time) * self.spin_efficiency(store_time)
                        # apply loss channel on photonic state and return a new state
                        self.timeline.quantum_manager.add_loss(key, loss)

                        if self.is_reversed:
                            if not self.is_spinwave:
                                raise Exception("AFC memory can only have normal order of re-emission")
                            emit_time = self.total_time - self.mode_bin - absorb_time  # reversed order of re-emission
                        else:
                            emit_time = absorb_time  # normal order of re-emission

                        if self.destination is not None:
                            dst = self.destination

                        process = Process(self._receivers[0], "get", [photon], {"dst": dst})
                        event = Event(self.timeline.now() + emit_time, process)
                        self.timeline.schedule(event)

                elif self.get_generator().random() < self.afc_efficiency(store_time):
                    photon = stored_photons["photon"]
                    absorb_time = stored_photons["time"]

                    if self.is_reversed:
                        if not self.is_spinwave:
                            raise Exception("AFC memory can only have normal order of re-emission")
                        emit_time = self.total_time - self.mode_bin - absorb_time  # reversed order of re-emission
                    else:
                        emit_time = absorb_time  # normal order of re-emission

                    if self.destination is not None:
                        dst = self.destination

                    process = Process(self._receivers[0], "get", [photon], {"dst": dst})
                    event = Event(self.timeline.now() + emit_time, process)
                    self.timeline.schedule(event)

        # clear entanglement and storage information after re-emission
        # retrieval will re-emit all stored photons and information should no longer be stored
        # clearance unified as storage_reset method
        self.storage_reset()

    def expire(self) -> None:
        """Method to handle memory expiration due to AFC expiration.

        Side Effects:
            Will notify upper entities of expiration via the `pop` interface.
            Will modify information stored by the memory.
        """

        # AFC needs to be prepared first
        if not self.is_prepared:
            raise Exception("AFC is not prepared yet.")

        # if stored photons have not been re-emitted when memory expires
        if self.excited_photons:
            for i in range(len(self.excited_photons)):
                self.excited_photons[i].is_null = True

        self.reset()
        # pop expiration message
        self.notify(self)

    def reset(self) -> None:
        """Method to clear quantum memory.

        Will reset memory state to no photon stored and will clear entanglement information.
        Will reset AFC to unprepared state.

        Side Effects:
            Will modify internal parameters and photon storage information.
        """

        self.storage_reset()
        self.is_prepared = False

        if self.expiration_event is not None:
            self.timeline.remove_event(self.expiration_event)
            self.expiration_event = None

    def storage_reset(self) -> None:
        """Method to clear information stored in one cycle of photon storage."""

        self.fidelity = 0
        self.entangled_memory = {'node_id': None, 'memo_id': None}
        self.photon_counter = 0
        self.absorb_start_time = 0
        # no photon should be retrieved after storage reset
        # re-emitted photons' is_null attribute should not be modified when memory expires
        self.excited_photons = []
        self.stored_photons = [None] * self.mode_number

    def _schedule_expiration(self) -> None:
        """Schedule the expiration of memory according to AFC lifetime."""

        if self.expiration_event is not None:
            self.timeline.remove_event(self.expiration_event)

        decay_time = self.timeline.now() + int(self.afc_lifetime * 1e12)
        process = Process(self, "expire", [])
        event = Event(decay_time, process)
        self.timeline.schedule(event)

        self.expiration_event = event

    def _schedule_storage_reset(self) -> None:
        """Schedule the resetting of a cycle of photon storage in spinwave.

        Only invoked when the memory type is AFC-spinwave.
        Storage resetting time is determined by AFC rephasing time and spinwave coherence time.
        """

        reset_time = self.timeline.now() + int(self.total_time + self.coherence_time * 1e12)
        process = Process(self, "storage_reset", [])
        event = Event(reset_time, process)
        self.timeline.schedule(event)

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
        """Method to get the simulation time when the memory is expired"""

        return self.expiration_event.time if self.expiration_event else inf

    def notify(self, msg: dict[str, Any]):
        for observer in self._observers:
            observer.memory_expire(self)

    def detach(self, observer: 'EntanglementProtocol'):
        if observer in self._observers:
            self._observers.remove(observer)
