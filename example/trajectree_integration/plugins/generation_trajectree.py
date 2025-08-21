"""Code for Barrett-Kok entanglement Generation protocol

This module defines code to support entanglement generation between single-atom memories on distant nodes.
Also defined is the message type used by this implementation.
Entanglement generation is asymmetric:

* EntanglementGenerationA should be used on the QuantumRouter (with one node set as the primary) and should be started via the "start" method
* EntanglementGeneraitonB should be used on the BSMNode and does not need to be started
"""

from __future__ import annotations
from enum import Enum, auto
from math import sqrt
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sequence.components.memory import Memory
    from sequence.components.bsm import SingleAtomBSM
    from sequence.topology.node import Node, BSMNode

from sequence.resource_management.memory_manager import MemoryInfo
from sequence.entanglement_management.entanglement_protocol import EntanglementProtocol
from sequence.message import Message
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.components.circuit import Circuit
from sequence.utils import log

from functools import lru_cache

import numpy as np
from trajectree.sequence.swap import perform_swapping_simulation # type: ignore

from sequence.config import CONFIG

log.logger.debug("Using Trajectree backend for entanglement generation")

def valid_trigger_time(trigger_time: int, target_time: int, resolution: int) -> bool:
    """return True if the trigger time is valid, else return False."""
    lower = target_time - (resolution // 2)
    upper = target_time + (resolution // 2)
    return lower <= trigger_time <= upper


class GenerationMsgType(Enum):
    """Defines possible message types for entanglement generation."""

    NEGOTIATE = auto()
    NEGOTIATE_ACK = auto()
    ENTANGLEMENT_SUCCESS = auto()


class EntanglementGenerationMessage(Message):
    """Message used by entanglement generation protocols.

    This message contains all information passed between generation protocol instances.
    Messages of different types contain different information.

    Attributes:
        msg_type (GenerationMsgType): defines the message type.
        receiver (str): name of destination protocol instance.
        qc_delay (int): quantum channel delay to BSM node (if `msg_type == NEGOTIATE`).
        frequency (float): frequency with which local memory can be excited (if `msg_type == NEGOTIATE`).
        emit_time (int): time to emit photon for measurement (if `msg_type == NEGOTIATE_ACK`).
        res (int): detector number at BSM node (if `msg_type == MEAS_RES`).
        time (int): detection time at BSM node (if `msg_type == MEAS_RES`).
        resolution (int): time resolution of BSM detectors (if `msg_type == MEAS_RES`).
    """

    def __init__(self, msg_type: GenerationMsgType, receiver: str, **kwargs):
        super().__init__(msg_type, receiver)
        self.protocol_type = EntanglementGenerationA

        if msg_type is GenerationMsgType.NEGOTIATE:
            self.qc_delay = kwargs.get("qc_delay")
            self.cc_delay = kwargs.get("cc_delay")
            self.frequency = kwargs.get("frequency")

        elif msg_type is GenerationMsgType.NEGOTIATE_ACK:
            self.attempt_time = kwargs.get("attempt_time")
            self.start_time = kwargs.get("start_time")
        elif msg_type is GenerationMsgType.ENTANGLEMENT_SUCCESS:
            self.fidelity = kwargs.get("fidelity")
        else:
            raise Exception("EntanglementGeneration generated invalid message type {}".format(msg_type))

    def __repr__(self):
        if self.msg_type is GenerationMsgType.NEGOTIATE:
            return "type:{}, qc_delay:{}, frequency:{}".format(self.msg_type, self.qc_delay, self.frequency)
        elif self.msg_type is GenerationMsgType.NEGOTIATE_ACK:
            return "type:{}".format(self.msg_type)
        elif self.msg_type is GenerationMsgType.ENTANGLEMENT_SUCCESS:
            return "type:{}".format(self.msg_type)
        else:
            raise Exception("EntanglementGeneration generated invalid message type {}".format(self.msg_type))


class EntanglementGenerationA(EntanglementProtocol):
    """Entanglement generation protocol for quantum router.

    The EntanglementGenerationA protocol should be instantiated on a quantum router node.
    Instances will communicate with each other (and with the B instance on a BSM node) to generate entanglement.

    Attributes:
        own (QuantumRouter): node that protocol instance is attached to.
        name (str): label for protocol instance.
        middle (str): name of BSM measurement node where emitted photons should be directed.
        remote_node_name (str): name of distant QuantumRouter node, containing a memory to be entangled with local memory.
        memory (Memory): quantum memory object to attempt entanglement for.
    """

    _plus_state = [sqrt(1/2), sqrt(1/2)]
    _flip_circuit = Circuit(1)
    _flip_circuit.x(0)
    _z_circuit = Circuit(1)
    _z_circuit.z(0)

    def __init__(self, owner: "Node", name: str, middle: str, other: str, memory: "Memory"):
        """Constructor for entanglement generation A class.

        Args:
            owner (Node): node to attach protocol to.
            name (str): name of protocol instance.
            middle (str): name of middle measurement node.
            other (str): name of other node.
            memory (Memory): memory to entangle.
        """

        super().__init__(owner, name)
        self.remote_node_name: str = other
        self.remote_protocol_name: str = None
        self.middle = middle

        # memory info
        self.memory: Memory = memory
        self.memories: list[Memory] = [memory]
        self.remote_memo_id: str = ""  # memory index used by corresponding protocol on other node

        # network and hardware info
        self.fidelity: float = memory.raw_fidelity
        self.qc_delay: int = 0
        self.expected_time: int = -1   # expected time for middle BSM node to receive the photon

        self.scheduled_events = []

        # misc
        self.primary: bool = False  # one end node is the "primary" that initiates negotiation
        self.debug: bool = False

        self._qstate_key: int = self.memory.qstate_key

    def is_ready(self) -> bool:
        return self.remote_protocol_name is not None
    
    def memory_expire(self, memory: "Memory") -> None:
        print("memory expire was called, see where it was used.")


    def set_others(self, protocol: str, node: str, memories: list[str]) -> None:
        """Method to set other entanglement protocol instance.

        Args:
            protocol (str): other protocol name.
            node (str): other node name.
            memories (list[str]): the list of memory names used on other node.
        """
        assert self.remote_protocol_name is None
        self.remote_protocol_name = protocol
        self.remote_memo_id = memories[0]
        self.primary = self.owner.name > self.remote_node_name

    def start(self) -> None:
        """Method to start "one round" in the entanglement generation protocol (there are two rounds in Barrett-Kok).

        Will start negotiations with other protocol (if primary).

        Side Effects:
            Will send message through attached node.
        """

        log.logger.info(f"{self.name} protocol start with partner {self.remote_protocol_name}")

        # to avoid start after remove protocol
        if self not in self.owner.protocols:
            return

        # Notice that these correspond to the delays to the BSM. 
        self.qc_delay = self.owner.qchannels[self.middle].delay
        self.cc_delay = self.owner.cchannels[self.middle].delay

        # update memory, and if necessary start negotiations for round
        if self.primary:
            self.memory_frequency = self.memory.frequency
            message = EntanglementGenerationMessage(GenerationMsgType.NEGOTIATE, self.remote_protocol_name,
                                                    qc_delay=self.qc_delay, cc_delay=self.cc_delay, frequency=self.memory_frequency)
            self.owner.send_message(self.remote_node_name, message)

    def received_message(self, src: str, msg: EntanglementGenerationMessage) -> None:
        """Method to receive messages.

        This method receives messages from other entanglement generation protocols.
        Depending on the message, different actions may be taken by the protocol.

        Args:
            src (str): name of the source node sending the message.
            msg (EntanglementGenerationMessage): message received.

        Side Effects:
            May schedule various internal and hardware events.
        """

        if src not in [self.middle, self.remote_node_name]:
            return

        msg_type = msg.msg_type

        log.logger.debug("{} {} received message from node {} of type {}".format(
                         self.owner.name, self.name, src, msg.msg_type))

        if msg_type is GenerationMsgType.NEGOTIATE:  # primary -> non-primary
            # configure params
            # Note again, that all of these corresponf to the delays to the BSM node.
            other_qc_delay = msg.qc_delay
            other_cc_delay = msg.cc_delay
            total_quantum_delay = max(self.qc_delay, other_qc_delay)
            total_classical_delay = max(self.cc_delay, other_cc_delay)

            end_node_cc_delay = self.owner.cchannels[self.remote_node_name].delay

            # get time for first excite event
            memory_excite_time = self.memory.next_excite_time
            start_time = max(self.owner.timeline.now(), memory_excite_time) + total_quantum_delay - self.qc_delay + end_node_cc_delay  # end_node_cc_delay time for NEGOTIATE_ACK
            attempt_time = total_quantum_delay + total_classical_delay # expected time for middle BSM node to receive the photon

            message = EntanglementGenerationMessage(GenerationMsgType.NEGOTIATE_ACK, self.remote_protocol_name, start_time=start_time, attempt_time=attempt_time)
            self.owner.send_message(src, message)

        elif msg_type is GenerationMsgType.NEGOTIATE_ACK:  # non-primary --> primary
            log.logger.debug("calling trajectree ent generation")
            success_probability, fidelity = self.entanglement_generation_trajectree()

            num_attempts = np.random.geometric(success_probability)  # time to first occurence in a Bernoulli process is a geometric distribution. 
            # while not np.random.random() < success_probability:
            #     num_attempts += 1
            log.logger.debug("success_probability", success_probability, "num_attempts", num_attempts)

            success_time = msg.start_time + (msg.attempt_time + 1e12/self.memory_frequency) * num_attempts

            message = EntanglementGenerationMessage(GenerationMsgType.ENTANGLEMENT_SUCCESS, self.remote_protocol_name, fidelity=fidelity)
            process = Process(self.owner, "send_message", [src, message])
            event = Event(success_time - self.owner.cchannels[self.remote_node_name].delay, process)
            self.owner.timeline.schedule(event)

            process = Process(self, "_entanglement_succeed", [fidelity])
            event = Event(success_time, process)
            self.owner.timeline.schedule(event)


        elif msg_type is GenerationMsgType.ENTANGLEMENT_SUCCESS:
            self._entanglement_succeed(msg.fidelity)


    @lru_cache(maxsize=5)
    def entanglement_generation_trajectree(self):
        # Set simulation params
        log.logger.debug("checking for cached entanglement")

        if self.owner.cached_entanglement.get(self.remote_node_name, None) == None:

            log.logger.debug("cached entanglement not found, running simulation")

            N = CONFIG["truncation"]+1
            error_tolerance = CONFIG["error_tolerance"]

            params = {
                "PA_det_loss": CONFIG["templates"]["perfect_bsm"]["TrajectreeBSM"]["detectors"][0]["efficiency"],
                "BSM_det_loss_1": 1e-3+1-CONFIG["templates"]["perfect_bsm"]["TrajectreeBSM"]["detectors"][0]["efficiency"], #  0.045,
                "BSM_det_loss_2": 1e-3+1-CONFIG["templates"]["perfect_bsm"]["TrajectreeBSM"]["detectors"][0]["efficiency"], # 0.135,
                "BSM_dark_counts_1": 1+1e-3,
                "BSM_dark_counts_2": 1+1e-3,
                "channel_loss": 1 - 10 ** (CONFIG["qconnections"][0]["distance"] * CONFIG["qconnections"][0]["attenuation"] / -10),
                "chi": CONFIG["templates"]["perfect_router"]["mean_photon_num"], # Here we are assuming that all the nodes in the network have the same mean photon number.
                "BSM_meas": {0:(2,3), 1:(6,7)},

                "if_analyze_entanglement": False,
                "calc_fidelity": True,
            }

            num_modes = 8

            num_simulations = CONFIG["num_simulations"]

            cache_sizes = [2]

            fidelities, probabilities, t_eval = perform_swapping_simulation(N, num_modes, num_simulations, params, error_tolerance)
            
            self.owner.cached_entanglement[self.remote_node_name] = (np.mean(probabilities), np.mean(fidelities))
        else:
            log.logger.debug("cached entanglement found:", self.owner.cached_entanglement[self.remote_node_name])

        return self.owner.cached_entanglement[self.remote_node_name] 


    def _entanglement_succeed(self, fidelity):
        log.logger.debug("succeeding entanglement gen at", self.owner.name, "at time:", self.owner.timeline.now())
        log.logger.info(self.owner.name + " successful entanglement of memory {}".format(self.memory))
        self.memory.entangled_memory["node_id"] = self.remote_node_name
        self.memory.entangled_memory["memo_id"] = self.remote_memo_id
        self.memory.fidelity = fidelity

        self.update_resource_manager(self.memory, MemoryInfo.ENTANGLED)


class EntanglementGenerationB(EntanglementProtocol):
    # Dummy class to make it compatible with imports. 
    

    def __init__(self, owner: "BSMNode", name: str, others: list[str]):
        """Constructor for entanglement generation B protocol.

        Args:
            own (Node): attached node.
            name (str): name of protocol instance.
            others (list[str]): name of protocol instance on end nodes.
        """

        super().__init__(owner, name)
        assert len(others) == 2
        self.others = others  # end nodes


    def start(self) -> None:
        """Method to start entanglement protocol process (abstract)."""

        pass

    def is_ready(self) -> bool:
        """Method to check if protocol is ready to start (abstract).

        Returns:
            bool: if protocol is ready or not.
        """

        pass

    def memory_expire(self, memory: "Memory") -> None:
        """Method to receive a memory expiration event (abstract)."""

        pass

    def received_message(self, src: str, msg: EntanglementGenerationMessage):
        pass

    def set_others(self, protocol: str, node: str, memories: list[str]) -> None:
        pass