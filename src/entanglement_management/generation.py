"""Code for entanglement Generation protocol

This module defines code to support entanglement generation between single-atom memories on distant nodes.
Also defined is the message type used by this implementation.
Original implementation is for Barrett-Kok protocol (double heralded).
Additional implementation is for (simplified) single-heralded protocol.

Entanglement generation is asymmetric (for any meet-in-the-middle protocol):
* EntanglementGenerationA should be used on the QuantumRouter (with one node set as the primary) and should be started via the "start" method
* EntanglementGeneraitonB should be used on the BSMNode and does not need to be started
"""

from __future__ import annotations
from enum import Enum, auto
from math import sqrt
from typing import List, TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from ..components.memory import Memory
    from ..topology.node import Node, BSMNode

from .entanglement_protocol import EntanglementProtocol
from ..message import Message
from ..kernel.event import Event
from ..kernel.process import Process
from ..kernel.quantum_manager import BELL_DIAGONAL_STATE_FORMALISM
from ..components.circuit import Circuit
from ..utils import log


# def valid_trigger_time(trigger_time, target_time, resolution):
#     upper = target_time + resolution
#     lower = 0
#     if resolution % 2 == 0:
#         upper = min(upper, target_time + resolution // 2)
#         lower = max(lower, target_time - resolution // 2)
#     else:
#         upper = min(upper, target_time + resolution // 2 + 1)
#         lower = max(lower, target_time - resolution // 2)
#     if (upper / resolution) % 1 >= 0.5:
#         upper -= 1
#     if (lower / resolution) % 1 < 0.5:
#         lower += 1
#     return lower <= trigger_time <= upper


def valid_trigger_time(trigger_time, target_time, resolution):
    lower = target_time - (resolution // 2)
    upper = target_time + (resolution // 2)
    return lower <= trigger_time <= upper


class GenerationMsgType(Enum):
    """Defines possible message types for entanglement generation."""

    NEGOTIATE = auto()
    NEGOTIATE_ACK = auto()
    MEAS_RES = auto()


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
            self.frequency = kwargs.get("frequency")

        elif msg_type is GenerationMsgType.NEGOTIATE_ACK:
            self.emit_time = kwargs.get("emit_time")

        elif msg_type is GenerationMsgType.MEAS_RES:
            self.detector = kwargs.get("detector")
            self.time = kwargs.get("time")
            self.resolution = kwargs.get("resolution")

        else:
            raise Exception("EntanglementGeneration generated invalid message"
                            " type {}".format(msg_type))

    def __repr__(self):
        if self.msg_type is GenerationMsgType.NEGOTIATE:
            return "type:{}, qc_delay:{}, frequency:{}".format(self.msg_type,
                                                               self.qc_delay,
                                                               self.frequency)
        elif self.msg_type is GenerationMsgType.NEGOTIATE_ACK:
            return "type:{}, emit_time:{}".format(self.msg_type,
                                                  self.emit_time)

        elif self.msg_type is GenerationMsgType.MEAS_RES:
            return "type:{}, detector:{}, time:{}, resolution={}" \
                   "".format(self.msg_type, self.detector,
                             self.time, self.resolution)

        else:
            raise Exception("EntanglementGeneration generated invalid message"
                            " type {}".format(self.msg_type))


class EntanglementGenerationA(EntanglementProtocol):
    """Entanglement generation protocol for quantum router.

    The EntanglementGenerationA protocol should be instantiated on a quantum router node.
    Instances will communicate with each other (and with the B instance on a BSM node) to generate entanglement.

    We also include the option of single-heralded entanglement generation protocol,
    instead of the default double-heralded Barrett-Kok protocol.
    In current implementation we don't distinguish different Bell states,
    and instead assume that post-measurement feedforward has been done to transform the Bell state in a specific form.

    For thje single-heralded protocol, we use Bell Diagonal States (BDS) to track memory entangled states.
    The intial form of state (ratio of the Pauli errors) is assumed to be determined by the EG protocol itself.
    Note that in reality, this may also depend on memory (e.g. decoherence during the course),
    but this implementation avoids the cases where `raw_epr_errors` in different memories do not match each other.

    Attributes:
        own (QuantumRouter): node that protocol instance is attached to.
        name (str): label for protocol instance.
        middle (str): name of BSM measurement node where emitted photons should be directed.
        remote_node_name (str): name of distant QuantumRouter node, containing a memory to be entangled with local memory.
        memory (Memory): quantum memory object to attempt entanglement for.
        is_sh (bool): if the entanglement generation protocol is single heralded or not
            (default False meaning double-heralded Barrett-Kok protocol)
        raw_fidelity (float): fidelity of successfully generated entangled state at the beginning (default 1).
            here we let entanglement generation protocol record raw fidelity instead of memory,
            this can facilitate definition of distance-dependent raw fidelity
        raw_epr_errors (List[float]): assuming BDS form of raw EPR pair, probability distribution of X, Y, Z Pauli errors;
            default value is -1, meaning not using BDS or further density matrix representation
    """

    _plus_state = [sqrt(1/2), sqrt(1/2)]
    _flip_circuit = Circuit(1)
    _flip_circuit.x(0)
    _z_circuit = Circuit(1)
    _z_circuit.z(0)

    def __init__(self, own: "Node", name: str, middle: str, other: str, memory: "Memory",
                 is_sh: bool = False, raw_fidelity: float = None, raw_epr_errors: List[float] = None):
        """Constructor for entanglement generation A class.

        Args:
            own (Node): node to attach protocol to.
            name (str): name of protocol instance.
            middle (str): name of middle measurement node.
            other (str): name of other node.
            memory (Memory): memory to entangle.
            is_sh (bool): if the entanglement generation protocol is single heralded or not
                (default False, meaning double-heralded Barrett-Kok protocol).
            raw_fidelity (float): fidelity of successfully generated entangled state at the beginning
                (default None, in which case it will assume value from memory object).
            raw_epr_errors (List[float]): assuming BDS form of raw EPR pair, probability distribution of X, Y, Z Pauli errors
                (default value is None, meaning not using BDS or further density matrix representation)
        """

        super().__init__(own, name)
        self.middle: str = middle
        self.remote_node_name: str = other
        self.remote_protocol_name: str = None

        self.is_sh = is_sh
        if is_sh:
            assert self.own.timeline.quantum_manager.formalism == BELL_DIAGONAL_STATE_FORMALISM, \
                "Currently single heralded protocol requires Bell diagonal state formalism."

        if raw_fidelity:
            self.raw_fidelity = raw_fidelity
        else:
            self.raw_fidelity = memory.raw_fidelity
        assert 0.5 <= self.raw_fidelity <= 1, "Raw fidelity of EPR pair must be above 1/2."
        self.raw_epr_errors = raw_epr_errors
        if self.raw_epr_errors:
            assert len(self.raw_epr_errors) == 3, \
                "Raw EPR pair Pauli error list should have three elements in X, Y, Z order."

        # memory info
        self.memory: Memory = memory
        self.memories: List[Memory] = [memory]
        self.remote_memo_id: str = ""  # memory index used by corresponding protocol on other node

        # network and hardware info
        # self.fidelity: float = memory.raw_fidelity
        self.qc_delay: int = 0
        self.expected_time: int = -1

        # memory internal info
        self.ent_round = 0  # keep track of current stage of protocol
        if is_sh:
            self.bsm_res = [0, 0]  # keep track of how many times each detector are triggered, can potentially see number of dark counts if greater than 1
        else:
            self.bsm_res = [-1, -1]  # keep track of bsm measurements to distinguish Psi+ and Psi- for double heralded Barrett-Kok protocol

        self.scheduled_events = []

        # misc
        self.primary: bool = False  # one end node is the "primary" that initiates negotiation
        self.debug: bool = False

        self._qstate_key: int = self.memory.qstate_key

    def set_others(self, protocol: str, node: str, memories: List[str]) -> None:
        """Method to set other entanglement protocol instance.

        Args:
            protocol (str): other protocol name.
            node (str): other node name.
            memories (List[str]): the list of memory names used on other node.
        """
        assert self.remote_protocol_name is None, "Entanglement generation 'set_others' called twice."

        # check if remote protocol matches
        remote_node = self.own.timeline.get_entity_by_name(node)
        try:
            remote_protocol = next(p for p in remote_node.protocols if p.name == protocol)
            assert remote_protocol.is_sh == self.is_sh, \
                "Entanglement generation protocols need to match in heralding schemes."
        except StopIteration:
            # if other protocol hasn't been instantiated yet, just store name
            pass

        self.remote_protocol_name = protocol

        self.remote_memo_id = memories[0]
        self.primary = self.own.name > self.remote_node_name

    def start(self) -> None:
        """Method to start entanglement generation protocol.

        Will start negotiations with other protocol (if primary).

        Side Effects:
            Will send message through attached node.
        """

        log.logger.info(f"{self.own.name} protocol start with partner "
                        f"{self.remote_node_name}")

        # to avoid start after remove protocol
        if self not in self.own.protocols:
            return

        # update memory, and if necessary start negotiations for round
        if self.update_memory() and self.primary:
            # send NEGOTIATE message
            self.qc_delay = self.own.qchannels[self.middle].delay
            frequency = self.memory.frequency
            message = EntanglementGenerationMessage(
                GenerationMsgType.NEGOTIATE, self.remote_protocol_name,
                qc_delay=self.qc_delay, frequency=frequency)
            self.own.send_message(self.remote_node_name, message)

    def update_memory(self):
        """Method to handle necessary memory operations.

        Called on both nodes.
        Will check the state of the memory and protocol.

        Returns:
            bool: if current round was successfull.

        Side Effects:
            May change state of attached memory.
            May update memory state in the attached node's resource manager.
        """

        # to avoid start after protocol removed
        if self not in self.own.protocols:
            return
        
        if self.is_sh:
            # in current implementation of single herald protocol, memory state does not need to change before success
            self.ent_round += 1

            if self.ent_round == 1:
                return True
            
            elif self.ent_round == 2:
                # success when both detectors in BSM are triggered
                if self.bsm_res[0] >= 1 and self.bsm_res[1] >= 1:
                    # successful entanglement
                    # Bell diagonal state assignment to both memories
                    self_key = self._qstate_key
                    tl = self.own.timeline
                    remote_memory = tl.get_entity_by_name(self.remote_memo_id)
                    remote_key = remote_memory.qstate_key
                    keys = [self_key, remote_key]

                    fid = self.raw_fidelity
                    if fid == 1:
                        state = [1., 0., 0., 0.]
                    else:
                        errors = self.raw_epr_errors
                        assert errors is not None, \
                            "Raw EPR pair Pauli error is required for BDS formalism with raw fidelity below 1."
                        infid = 1 - fid
                        x_elem, y_elem, z_elem = [error * infid for error in errors]
                        state = [fid, z_elem, x_elem, y_elem]

                    tl.quantum_manager.set(keys, state)

                    # TODO: if decoherence exists, fidelity recorded in resource manager needs to be changed at future times
                    # TODO: in current implementation, quantum manager has one fixed formalism, 
                    #       and we are using BDS formalism to track the generated and distributed EPR pairs, 
                    #       but in DQS the application will generate and track larger multi-partite state presumably with QuTiP features,
                    #       therefore might be suitable for some separate tracking other than quantum manager

                    self._entanglement_succeed()

                else: 
                    # entanglement failed
                    self._entanglement_fail()
                    return False

            return True

        else:
            self.ent_round += 1

            if self.ent_round == 1:
                return True

            elif self.ent_round == 2 and self.bsm_res[0] != -1:
                self.own.timeline.quantum_manager.run_circuit(
                    EntanglementGenerationA._flip_circuit, [self._qstate_key])

            elif self.ent_round == 3 and self.bsm_res[1] != -1:
                # successful entanglement
                # state correction
                if self.primary:
                    self.own.timeline.quantum_manager.run_circuit(
                        EntanglementGenerationA._flip_circuit, [self._qstate_key])
                elif self.bsm_res[0] != self.bsm_res[1]:
                    self.own.timeline.quantum_manager.run_circuit(
                        EntanglementGenerationA._z_circuit, [self._qstate_key])

                self._entanglement_succeed()

            else:
                # entanglement failed
                self._entanglement_fail()
                return False

            return True

    def emit_event(self) -> None:
        """Method to set up memory and emit photons.

        If the protocol is in round 1, the memory will be first set to the |+> state.
        Otherwise, it will apply an x_gate to the memory.
        Regardless of the round, the memory `excite` method will be invoked.

        Side Effects:
            May change state of attached memory.
            May cause attached memory to emit photon.
        """
        if self.is_sh:
            self.memory.excite(self.middle, "sh")

        else:
            if self.ent_round == 1:
                self.memory.update_state(EntanglementGenerationA._plus_state)
            self.memory.excite(self.middle)

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

        log.logger.debug("{} EG protocol received_message of type {} from node"
                         " {}, round={}".format(self.own.name,
                                                msg.msg_type,
                                                src, self.ent_round))

        if msg_type is GenerationMsgType.NEGOTIATE:
            # configure params
            another_delay = msg.qc_delay
            self.qc_delay = self.own.qchannels[self.middle].delay
            cc_delay = int(self.own.cchannels[src].delay)
            total_quantum_delay = max(self.qc_delay, another_delay)

            # get time for first excite event
            memory_excite_time = self.memory.next_excite_time
            min_time = max(self.own.timeline.now(), memory_excite_time) \
                       + total_quantum_delay - self.qc_delay + cc_delay
            emit_time = self.own.schedule_qubit(self.middle, min_time)  # used to send memory
            self.expected_time = emit_time + self.qc_delay

            # schedule emit
            process = Process(self, "emit_event", [])
            event = Event(emit_time, process)
            self.own.timeline.schedule(event)
            self.scheduled_events.append(event)

            # send negotiate_ack
            another_emit_time = emit_time + self.qc_delay - another_delay
            message = EntanglementGenerationMessage(
                GenerationMsgType.NEGOTIATE_ACK,
                self.remote_protocol_name,
                emit_time=another_emit_time)
            self.own.send_message(src, message)

            # schedule start if necessary, else schedule update_memory
            # TODO: base future start time on resolution
            future_start_time = self.expected_time + self.own.cchannels[self.middle].delay + 10
            if self.ent_round == 1:
                process = Process(self, "start", [])
            else:
                process = Process(self, "update_memory", [])
            event = Event(future_start_time, process)
            self.own.timeline.schedule(event)
            self.scheduled_events.append(event)

        elif msg_type is GenerationMsgType.NEGOTIATE_ACK:
            # configure params
            self.expected_time = msg.emit_time + self.qc_delay

            if msg.emit_time < self.own.timeline.now():
                msg.emit_time = self.own.timeline.now()

            # schedule emit
            emit_time = self.own.schedule_qubit(self.middle, msg.emit_time)
            assert emit_time == msg.emit_time, \
                "Invalid eg emit times %d %d %d" % (emit_time,  msg.emit_time, self.own.timeline.now())

            process = Process(self, "emit_event", [])
            event = Event(msg.emit_time, process)
            self.own.timeline.schedule(event)
            self.scheduled_events.append(event)

            # schedule start if memory_stage is 0, else schedule update_memory
            # TODO: base future start time on resolution
            future_start_time = self.expected_time + self.own.cchannels[self.middle].delay + 10
            if self.ent_round == 1:
                process = Process(self, "start", [])
            else:
                process = Process(self, "update_memory", [])
            event = Event(future_start_time, process)
            self.own.timeline.schedule(event)
            self.scheduled_events.append(event)

        elif msg_type is GenerationMsgType.MEAS_RES:
            detector = msg.detector
            time = msg.time
            resolution = msg.resolution

            log.logger.debug("{} received MEAS_RES {} at time {}, expected {},"
                            " resolution={}, round={}".format(
                self.own.name, detector, time, self.expected_time, resolution, self.ent_round))

            if valid_trigger_time(time, self.expected_time, resolution):
                if self.is_sh == True:
                    self.bsm_res[detector] += 1  # record one trigger of the detector (here `detector` is the index of detector object)

                # record result if we don't already have one
                elif self.is_sh == False:
                    i = self.ent_round - 1
                    if self.bsm_res[i] == -1:
                        self.bsm_res[i] = detector
                    else:
                        self.bsm_res[i] = -1

        else:
            raise Exception("Invalid message {} received by EG on node "
                            "{}".format(msg_type, self.own.name))

    def is_ready(self) -> bool:
        return self.remote_protocol_name is not None

    def memory_expire(self, memory: "Memory") -> None:
        """Method to receive expired memories."""

        assert memory == self.memory

        self.update_resource_manager(memory, 'RAW')
        for event in self.scheduled_events:
            if event.time >= self.own.timeline.now():
                self.own.timeline.remove_event(event)

    def _entanglement_succeed(self):
        log.logger.info(self.own.name + " successful entanglement of memory {}".format(self.memory))
        self.memory.entangled_memory["node_id"] = self.remote_node_name
        self.memory.entangled_memory["memo_id"] = self.remote_memo_id
        self.memory.fidelity = self.raw_fidelity

        self.update_resource_manager(self.memory, 'ENTANGLED')

    def _entanglement_fail(self):
        for event in self.scheduled_events:
            self.own.timeline.remove_event(event)
        log.logger.info(self.own.name + " failed entanglement of memory {}".format(self.memory))
        
        self.update_resource_manager(self.memory, 'RAW')


class EntanglementGenerationB(EntanglementProtocol):
    """Single heralded entanglement generation protocol for BSM node.

    The EntanglementGenerationB protocol should be instantiated on a BSM node.
    Instances will communicate with the A instance on neighboring quantum router nodes to generate entanglement.
    Similar to single heralded protocol A, BSM here does not distinguish the result, but only accounts whether both photons are successfully detected.

    Attributes:
        own (BSMNode): node that protocol instance is attached to.
        name (str): label for protocol instance.
        others (List[str]): list of neighboring quantum router nodes
        is_sh (bool): if the entanglement generation protocol is single heralded or not (default False meaning double-heralded Barrett-Kok protocol).
    """

    def __init__(self, own: "BSMNode", name: str, others: List[str], is_sh: bool=False):
        """Constructor for entanglement generation B protocol.

        Args:
            own (Node): attached node.
            name (str): name of protocol instance.
            others (List[str]): name of protocol instance on end nodes.
            is_sh (bool): if the entanglement generation protocol is single heralded or not (default False meaning double-heralded Barrett-Kok protocol).
        """

        super().__init__(own, name)
        assert len(others) == 2
        self.others = others  # end nodes

        self.is_sh = is_sh

        # TODO: need different way of checking end node protocols match middle
        # remote_protocols = [self.own.timeline.get_entity_by_name(protocol) for protocol in self.others]
        # for remote_protocol in remote_protocols:
        #     assert remote_protocol.is_sh == self.is_sh, \
        #         "Entanglement generation protocols need to match in heralding schemes."

    def bsm_update(self, bsm, info: Dict[str, Any]):
        """Method to receive detection events from BSM on node.

        Args:
            bsm (SingleAtomBSM or SingleHeraldedBSM): bsm object calling method.
            info (Dict[str, any]): information passed from bsm.
        """

        if self.is_sh:
            assert bsm.encoding == "single_heralded", \
                "Single-heralded entanglement generation protocol needs to use SingleHeraldedBSM."
        else:
            assert bsm.encoding == "single_atom", \
                "Barrett-Kok entanglement generation protocol needs to use SingleAtomBSM."

        assert info['info_type'] == "BSM_res"

        res = info["res"]
        time = info["time"]
        resolution = bsm.resolution

        for i, node in enumerate(self.others):
            message = EntanglementGenerationMessage(GenerationMsgType.MEAS_RES,
                                                    None, detector=res, time=time, resolution=resolution)
            self.own.send_message(node, message)

    def received_message(self, src: str, msg: EntanglementGenerationMessage):
        raise Exception("EntanglementGenerationB protocol '{}' should not "
                        "receive message".format(self.name))

    def start(self) -> None:
        pass

    def set_others(self, protocol: str, node: str, memories: List[str]) -> None:
        pass

    def is_ready(self) -> bool:
        return True

    def memory_expire(self, memory: "Memory") -> None:
        raise Exception("Memory expire called for EntanglementGenerationB protocol '{}'".format(self.name))
