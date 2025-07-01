from copy import copy
from typing import Any, TYPE_CHECKING

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

from .memory_array import MemoryArray

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


# define helper functions for analytical BDS decoherence implementation, reference see recurrence protocol paper
def _p_id(x_rate, y_rate, z_rate, t):
    val = (1 + exp(-2*(x_rate+y_rate)*t) + exp(-2*(x_rate+z_rate)*t) + exp(-2*(z_rate+y_rate)*t)) / 4
    return val


def _p_xerr(x_rate, y_rate, z_rate, t):
    val = (1 - exp(-2*(x_rate+y_rate)*t) - exp(-2*(x_rate+z_rate)*t) + exp(-2*(z_rate+y_rate)*t)) / 4
    return val


def _p_yerr(x_rate, y_rate, z_rate, t):
    val = (1 - exp(-2*(x_rate+y_rate)*t) + exp(-2*(x_rate+z_rate)*t) - exp(-2*(z_rate+y_rate)*t)) / 4
    return val


def _p_zerr(x_rate, y_rate, z_rate, t):
    val = (1 + exp(-2*(x_rate+y_rate)*t) - exp(-2*(x_rate+z_rate)*t) - exp(-2*(z_rate+y_rate)*t)) / 4
    return val