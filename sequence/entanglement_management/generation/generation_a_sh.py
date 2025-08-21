from __future__ import annotations

from math import sqrt
from typing import TYPE_CHECKING, List

from .generation_message import EntanglementGenerationMessage, GenerationMsgType, valid_trigger_time
from ...resource_management.memory_manager import MemoryInfo

if TYPE_CHECKING:
    from ...components.memory import Memory
from ...kernel.quantum_manager import BELL_DIAGONAL_STATE_FORMALISM
from ..entanglement_protocol import EntanglementProtocol
from ...kernel.event import Event
from ...kernel.process import Process
from ...components.circuit import Circuit
from ...utils import log


class EntanglementGenerationSingleHeraldedA(EntanglementProtocol):
    _plus_state = [sqrt(1 / 2), sqrt(1 / 2)]
    _flip_circuit = Circuit(1)
    _flip_circuit.x(0)
    _z_circuit = Circuit(1)
    _z_circuit.z(0)

    def __init__(self, owner: "Node", name: str, middle: str, other: str, memory: "Memory",
                 raw_fidelity: float = None, raw_epr_errors: List[float] = None):
        super().__init__(owner, name)

        assert self.owner.timeline.quantum_manager.formalism == BELL_DIAGONAL_STATE_FORMALISM, \
            "Single Heralded Entanglement generation protocol only supports Bell diagonal state formalism."

        self.middle: str = middle
        self.remote_node_name: str = other
        self.remote_protocol_name: str = ''

        if raw_fidelity:
            self.raw_fidelity: float = raw_fidelity
        else:
            self.raw_fidelity: float = memory.raw_fidelity

        assert 0.5 <= self.raw_fidelity <= 1, "Raw fidelity must be in [0.5, 1]."

        self.raw_epr_errors = raw_epr_errors
        if self.raw_epr_errors is None:
            self.raw_epr_errors = [1 / 3, 1 / 3, 1 / 3]
        if self.raw_epr_errors:
            assert len(self.raw_epr_errors) == 3, \
                "Raw EPR pair pauli error list should have three elements in X, Y, Z order."

        # Memory Info
        self.memory: Memory = memory
        self.memories: List[Memory] = [memory]
        self.remote_memo_id: str = ''

        # Network and Hardware Info
        self.qc_delay: int = 0
        self.expected_time: int = -1

        # Memory Internal Info
        self.ent_round = 0
        self.bsm_res = [0, 0]

        self.scheduled_events = []

        # Misc.
        self.primary: bool = False
        self.debug: bool = False
        self._qstate_key: int = self.memory.qstate_key

    def set_others(self, protocol: str, node: str, memories: List[str]):
        """Method to set other entanglement protocol instance.

        Args:
            protocol (str): other protocol name.
            node (str): other node name.
            memories (List[str]): the list of memory names used on other node.
        """
        assert self.remote_protocol_name != '', \
            "Remote protocol name is already set, cannot set again."

        remote_node = self.owner.timeline.get_entity_by_name(node)
        """try:
            remote_protocol = next(p for p in remote_node.protocols if p.name == protocol)

        except StopIteration:
            pass"""
        self.remote_protocol_name = protocol
        self.remote_memo_id = memories[0]

    def update_memory(self) -> bool:
        """Method to handle necessary memory operations.

        Called on both nodes.
        Will check the state of the memory and protocol.

        Returns:
            bool: if current round was successfull.

        Side Effects:
            May change state of attached memory.
            May update memory state in the attached node's resource manager.
        """
        self.ent_round += 1
        if self.ent_round == 1:
            return True

        elif self.ent_round == 2:
            if self.bsm_res[0] >= 1 and self.bsm_res[1] >= 1:
                self_key = self._qstate_key
                tl = self.owner.timeline
                remote_memory = tl.get_entity_by_name(self.remote_memo_id)
                remote_key = remote_memory.qstate_key
                keys = [self.key, remote_key]

                fidelity = self.raw_fidelity
                if fidelity == 1:
                    state = [1., 0., 0., 0.]

                else:
                    assert self.raw_fidelity is not None, \
                        "Raw EPR pair Pauli error is required for BDS formalism with raw fidelity below 1."
                    inverse_fidelity = 1 - fidelity
                    x_element, y_element, z_element = [error * inverse_fidelity for error in self.raw_epr_errors]
                    state = [fidelity, x_element, y_element, z_element]

                tl.quantum_manager.set(keys, state)
                self._entanglement_succeed()

        else:
            self._entanglement_fail()
            return False

        return True

    def start(self) -> None:
        """Method to start entanglement generation protocol.

        Will start negotiations with other protocol (if primary).

        Side Effects:
            Will send message through attached node.
        """
        log.logger.info(f'{self.owner.name} protocol start with partner {self.remote_node_name}')

        if self not in self.owner.protocols:
            return

        if self.update_memory() and self.primary:
            self.qc_delay = self.owner.qchannels[self.middle].delay
            frequency = self.memory.frequency
            message = EntanglementGenerationMessage(GenerationMsgType.NEGOTIATE,
                                                    self.remote_protocol_name,
                                                    protocol_type=self,
                                                    qc_delay=self.qc_delay,
                                                    frequency=frequency)
            self.owner.send_message(self.remote_node_name, message)

    def emit_event(self) -> None:
        self.memory.excite(self.middle, protocol='sh')

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
            min_time = max(self.owner.timeline.now(),
                           memory_excite_time) + other_qc_delay - self.qc_delay + cc_delay  # cc_delay time for NEGOTIATE_ACK
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
            future_start_time = self.expected_time + self.owner.cchannels[
                self.middle].delay + 10  # delay is for sending the BSM_RES to end nodes, 10 is a small gap
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
                self.bsm_res[detector] += 1
            else:
                log.logger.debug('{} BSM trigger time not valid'.format(self.owner.name))

        else:
            raise Exception("Invalid message {} received by EG on node {}".format(msg_type, self.owner.name))

    def is_ready(self) -> bool:
        return self.remote_protocol_name != ''

    def memory_expire(self, memory: "Memory") -> None:
        assert memory == self.memory, "Memory to expire does not match the protocol's memory."
        self.update_resource_manager(memory, MemoryInfo.RAW)
        for event in self.scheduled_events:
            if event.time >= self.owner.timeline.now():
                self.owner.timeline.remove_event(event)

    def _entanglement_succeed(self):
        log.logger.info(f'{self.owner.name} successful entanglement of memory {self.memory}')
        self.memory.entangled_memory['node_id'] = self.remote_node_name
        self.memory.entangled_memory['memo_id'] = self.remote_memo_id
        self.memory.fidelity = self.raw_fidelity

        self.update_resource_manager(self.memory, MemoryInfo.ENTANGLED)

    def _entanglement_fail(self):
        for event in self.scheduled_events:
            self.owner.timeline.remove_event(event)
        log.logger.info(f'{self.owner.name} failed entanglement of memory {self.memory}')

        self.update_resource_manager(self.memory, MemoryInfo.RAW)
