from __future__ import annotations
from enum import Enum, auto
from math import sqrt
from typing import TYPE_CHECKING, Any

from .generation_message import EntanglementGenerationMessage, GenerationMsgType, valid_trigger_time

if TYPE_CHECKING:
    from ...components.memory import Memory
    from ...topology.node import Node

from ...resource_management.memory_manager import MemoryInfo
from ..entanglement_protocol import EntanglementProtocol
from ...kernel.event import Event
from ...kernel.process import Process
from ...components.circuit import Circuit
from ...utils import log


class EntanglementGenerationBarretKokA(EntanglementProtocol):
    """Entanglement generation protocol for quantum router.

    The EntanglementGenerationA protocol should be instantiated on a quantum router node.
    Instances will communicate with each other (and with the B instance on a BSM node) to generate entanglement.

    Attributes:
        owner (QuantumRouter): node that protocol instance is attached to.
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
        self.middle: str = middle
        self.remote_node_name: str = other
        self.remote_protocol_name: str = ''

        # memory info
        self.memory: Memory = memory
        self.memories: list[Memory] = [memory]
        self.remote_memo_id: str = ""  # memory index used by corresponding protocol on other node

        # network and hardware info
        self.fidelity: float = memory.raw_fidelity
        self.qc_delay: int = 0
        self.expected_time: int = -1   # expected time for middle BSM node to receive the photon

        # memory internal info
        self.ent_round = 0  # keep track of current stage of protocol
        self.bsm_res = [-1, -1]  # keep track of bsm measurements to distinguish Psi+ and Psi-

        self.scheduled_events = []

        # misc
        self.primary: bool = False  # one end node is the "primary" that initiates negotiation
        self.debug: bool = False

        self._qstate_key: int = self.memory.qstate_key

    def set_others(self, protocol: str, node: str, memories: list[str]) -> None:
        """Method to set other entanglement protocol instance.

        Args:
            protocol (str): other protocol name.
            node (str): other node name.
            memories (list[str]): the list of memory names used on other node.
        """
        assert self.remote_protocol_name == ''
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

        # update memory, and if necessary start negotiations for round
        if self.update_memory() and self.primary:
            # send NEGOTIATE message
            self.qc_delay = self.owner.qchannels[self.middle].delay
            frequency = self.memory.frequency
            message = EntanglementGenerationMessage(GenerationMsgType.NEGOTIATE,
                                                    self.remote_protocol_name,
                                                    protocol_type=self,
                                                    qc_delay=self.qc_delay,
                                                    frequency=frequency)
            self.owner.send_message(self.remote_node_name, message)

    def update_memory(self) -> bool | None:
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
        if self not in self.owner.protocols:
            return

        self.ent_round += 1

        if self.ent_round == 1:
            return True

        elif self.ent_round == 2 and self.bsm_res[0] != -1:
            self.owner.timeline.quantum_manager.run_circuit(self._flip_circuit, [self._qstate_key])
            return True

        elif self.ent_round == 3 and self.bsm_res[1] != -1:
            # entanglement succeeded, correction
            if self.primary:
                self.owner.timeline.quantum_manager.run_circuit(self._flip_circuit, [self._qstate_key])
            elif self.bsm_res[0] != self.bsm_res[1]:
                self.owner.timeline.quantum_manager.run_circuit(self._z_circuit, [self._qstate_key])
            self._entanglement_succeed()
            return True

        else:
            # entanglement failed
            self._entanglement_fail()
            return False


    def emit_event(self) -> None:
        """Method to set up memory and emit photons.

        If the protocol is in round 1, the memory will be first set to the |+> state.
        Otherwise, it will apply an x_gate to the memory.
        Regardless of the round, the memory `excite` method will be invoked.

        Side Effects:
            May change state of attached memory.
            May cause attached memory to emit photon.
        """

        if self.ent_round == 1:
            self.memory.update_state(self._plus_state)
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

        log.logger.debug("{} {} received message from node {} of type {}, round={}".format(
                         self.owner.name, self.name, src, msg.msg_type, self.ent_round))

        if msg_type is GenerationMsgType.NEGOTIATE:  # primary -> non-primary
            # configure params
            other_qc_delay = msg.qc_delay
            self.qc_delay = self.owner.qchannels[self.middle].delay
            cc_delay = int(self.owner.cchannels[src].delay)

            # get time for first excite event
            memory_excite_time = self.memory.next_excite_time
            min_time = max(self.owner.timeline.now(), memory_excite_time) + other_qc_delay - self.qc_delay + cc_delay  # cc_delay time for NEGOTIATE_ACK
            emit_time = self.owner.schedule_qubit(self.middle, min_time)  # used to send memory
            self.expected_time = emit_time + self.qc_delay  # expected time for middle BSM node to receive the photon

            # schedule emit
            process = Process(self, "emit_event", [])
            event = Event(emit_time, process)
            self.owner.timeline.schedule(event)
            self.scheduled_events.append(event)

            # send negotiate_ack
            other_emit_time = emit_time + self.qc_delay - other_qc_delay
            message = EntanglementGenerationMessage(GenerationMsgType.NEGOTIATE_ACK,
                                                    self.remote_protocol_name,
                                                    protocol_type=self,
                                                    emit_time=other_emit_time)
            self.owner.send_message(src, message)

            # schedule start if necessary (current is first round, need second round), else schedule update_memory (currently second round)
            # TODO: base future start time on resolution
            future_start_time = self.expected_time + self.owner.cchannels[self.middle].delay + 10  # delay is for sending the BSM_RES to end nodes, 10 is a small gap
            if self.ent_round == 1:
                process = Process(self, "start", [])  # for the second round
            else:
                process = Process(self, "update_memory", [])
            event = Event(future_start_time, process)
            self.owner.timeline.schedule(event)
            self.scheduled_events.append(event)

        elif msg_type is GenerationMsgType.NEGOTIATE_ACK:  # non-primary --> primary
            # configure params
            self.expected_time = msg.emit_time + self.qc_delay  # expected time for middle BSM node to receive the photon

            if msg.emit_time < self.owner.timeline.now():  # emit time calculated by the non-primary node
                msg.emit_time = self.owner.timeline.now()

            # schedule emit
            emit_time = self.owner.schedule_qubit(self.middle, msg.emit_time)
            assert emit_time == msg.emit_time, \
                "Invalid eg emit times {} {} {}".format(emit_time, msg.emit_time, self.owner.timeline.now())

            process = Process(self, "emit_event", [])
            event = Event(msg.emit_time, process)
            self.owner.timeline.schedule(event)
            self.scheduled_events.append(event)

            # schedule start if necessary (current is first round, need second round), else schedule update_memory (currently second round)
            # TODO: base future start time on resolution
            future_start_time = self.expected_time + self.owner.cchannels[self.middle].delay + 10
            if self.ent_round == 1:
                process = Process(self, "start", [])  # for the second round
            else:
                process = Process(self, "update_memory", [])
            event = Event(future_start_time, process)
            self.owner.timeline.schedule(event)
            self.scheduled_events.append(event)

        elif msg_type is GenerationMsgType.MEAS_RES:  # from middle BSM to both non-primary and primary
            detector = msg.detector
            time = msg.time
            resolution = msg.resolution

            log.logger.debug("{} received MEAS_RES={} at time={:,}, expected={:,}, resolution={}, round={}".format(
                             self.owner.name, detector, time, self.expected_time, resolution, self.ent_round))

            if valid_trigger_time(time, self.expected_time, resolution):
                # record result if we don't already have one
                i = self.ent_round - 1
                if self.bsm_res[i] == -1:
                    self.bsm_res[i] = detector  # save the measurement results (detector number)
                else:
                    self.bsm_res[i] = -1  # BSM measured 1, 1 and both didn't lost
            else:
                log.logger.debug('{} BSM trigger time not valid'.format(self.owner.name))

        else:
            raise Exception("Invalid message {} received by EG on node {}".format(msg_type, self.owner.name))

    def is_ready(self) -> bool:
        return self.remote_protocol_name != ''

    def memory_expire(self, memory: "Memory") -> None:
        """Method to receive expired memories."""

        assert memory == self.memory

        self.update_resource_manager(memory, MemoryInfo.RAW)
        for event in self.scheduled_events:
            if event.time >= self.owner.timeline.now():
                self.owner.timeline.remove_event(event)

    def _entanglement_succeed(self):
        log.logger.info(self.owner.name + " successful entanglement of memory {}".format(self.memory))
        self.memory.entangled_memory["node_id"] = self.remote_node_name
        self.memory.entangled_memory["memo_id"] = self.remote_memo_id
        self.memory.fidelity = self.memory.raw_fidelity

        self.update_resource_manager(self.memory, MemoryInfo.ENTANGLED)

    def _entanglement_fail(self):
        for event in self.scheduled_events:
            self.owner.timeline.remove_event(event)
        log.logger.info(self.owner.name + " failed entanglement of memory {}".format(self.memory))

        self.update_resource_manager(self.memory, MemoryInfo.RAW)

