from __future__ import annotations

from typing import TYPE_CHECKING, List, Dict, Any

from .generation_base import EntanglementGenerationA, EntanglementGenerationB, QuantumCircuitMixin
from .generation_message import EntanglementGenerationMessage, GenerationMsgType, valid_trigger_time
from ...components.bsm import SingleHeraldedBSM
from ...constants import BELL_DIAGONAL_STATE_FORMALISM
from ...constants import SINGLE_HERALDED
from ...kernel.event import Event
from ...kernel.process import Process
from ...kernel.quantum_manager import QuantumManager
from ...resource_management.memory_manager import MemoryInfo
from ...utils import log

if TYPE_CHECKING:
    from ...components.memory import Memory
    from ...topology.node import Node, BSMNode




@EntanglementGenerationA.register(SINGLE_HERALDED)
class SingleHeraldedA(EntanglementGenerationA, QuantumCircuitMixin):
    def __init__(self, owner: "Node", name: str, middle: str, other: str, memory: "Memory",
                 raw_fidelity: float = None, raw_epr_errors: List[float] = None):
        super().__init__(owner, name, middle, other, memory)

        self.protocol_type = SINGLE_HERALDED
        assert QuantumManager.get_active_formalism() == BELL_DIAGONAL_STATE_FORMALISM, \
            f"Single Heralded Entanglement generation protocol only supports Bell diagonal state formalism; got {QuantumManager.get_active_formalism()}"

        if raw_fidelity:
            self.raw_fidelity = raw_fidelity
        else:
            self.raw_fidelity = memory.raw_fidelity
        assert 0.5 <= self.raw_fidelity <= 1, "Raw fidelity must be in [0.5, 1]."

        self.raw_epr_errors = raw_epr_errors
        if self.raw_epr_errors is None:
            self.raw_epr_errors = [1 / 3, 1 / 3, 1 / 3]
        if self.raw_epr_errors:
            assert len(self.raw_epr_errors) == 3, \
                "Raw EPR pair pauli error list should have three elements in X, Y, Z order."

        self.bsm_res = [0, 0]

    def update_memory(self) -> bool | None:
        """Method to handle necessary memory operations.

        Called on both nodes.
        Will check the state of the memory and protocol.

        Returns:
            bool: if current round was successful.

        Side Effects:
            May change state of attached memory.
            May update memory state in the attached node's resource manager.
        """

        # Avoid starting if the protocol is removed.
        if self not in self.owner.protocols:
            return

        self.ent_round += 1
        if self.ent_round == 1:
            return True

        elif self.ent_round == 2:
            if self.bsm_res[0] >= 1 and self.bsm_res[1] >= 1:
                quantum_manager = self.owner.timeline.quantum_manager
                self_key = self._qstate_key
                remote_memory: Memory = self.owner.timeline.get_entity_by_name(self.remote_memo_id)

                remote_key = remote_memory.qstate_key
                keys = [self_key, remote_key]

                if self_key not in quantum_manager.states:
                    in_fidelity = 1 - self.raw_fidelity
                    x_elem, y_elem, z_elem = [error * in_fidelity for error in self.raw_epr_errors]
                    state = [self.raw_fidelity, z_elem, x_elem, y_elem]
                    quantum_manager.set(keys, state)
                    self.memory.bds_decohere()
                    remote_memory.bds_decohere()

                self._entanglement_succeed()

        else:
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
        if not self.is_ready():
            log.logger.info(f'{self} is not valid, emit_event() failed.')
            return

        if self.ent_round == 1:
            self.memory.update_state(QuantumCircuitMixin._plus_state)
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
                                                    protocol_type=self.protocol_type,
                                                    emit_time=other_emit_time)
            self.owner.send_message(src, message)

            # schedule start if necessary (current is first round, need second round),
            # else schedule update_memory (currently second round)
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
            self.expected_time = msg.emit_time + self.qc_delay  # expected time for middle BSM node to receive photon

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

            # schedule start if necessary (current is first round, need second round),
            # else schedule update_memory (currently second round)
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

    def _entanglement_succeed(self):
        log.logger.info(f'{self.owner.name} successful entanglement of memory {self.memory}')
        self.memory.entangled_memory['node_id'] = self.remote_node_name
        self.memory.entangled_memory['memo_id'] = self.remote_memo_id
        self.memory.fidelity = self.raw_fidelity

        self.update_resource_manager(self.memory, MemoryInfo.ENTANGLED)


@EntanglementGenerationB.register(SINGLE_HERALDED)
class SingleHeraldedB(EntanglementGenerationB):
    def __init__(self, owner: "BSMNode", name: str, others: List[str]):
        super().__init__(owner, name, others)
        assert len(others) == 2
        self.others = others
        self.protocol_type = SINGLE_HERALDED

    def bsm_update(self, bsm: "SingleHeraldedBSM", info: Dict['str', Any]) -> None:
        """Method to receive detection events from BSM on node.

        Args:
            bsm (SingleAtomBSM or SingleHeraldedBSM): bsm object calling method.
            info (Dict[str, any]): information passed from bsm.
        """
        assert bsm.encoding == SINGLE_HERALDED, \
            "SingleHeraldedB should only be used with SingleHeraldedBSM."

        assert info['info_type'] == 'BSM_res'

        res = info['res']
        time = info['time']
        resolution = bsm.resolution

        for node in self.others:
            message = EntanglementGenerationMessage(GenerationMsgType.MEAS_RES,
                                                    receiver=None,
                                                    protocol_type=self.protocol_type,
                                                    detector=res,
                                                    time=time,
                                                    resolution=resolution)
            self.owner.send_message(node, message)
