"""Code for Barrett-Kok entanglement Generation protocol

This module defines code to support entanglement generation between single-atom memories on distant nodes.
Also defined is the message type used by this implementation.
Entanglement generation is asymmetric:

* EntanglementGenerationA should be used on the QuantumRouter (with one node set as the primary) and should be started via the "start" method
* EntanglementGeneraitonB should be used on the BSMNode and does not need to be started
"""

from enum import Enum, auto
from typing import List, TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from ..components.memory import Memory
    from ..topology.node import Node

from .entanglement_protocol import EntanglementProtocol
from ..message import Message
from ..kernel.event import Event
from ..kernel.process import Process
from ..utils import log


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

        elif msg_type is GenerationMsgType.NEGOTIATE_ACK:
            self.emit_time = kwargs.get("emit_time")

        elif msg_type is GenerationMsgType.MEAS_RES:
            self.res = kwargs.get("res")
            self.time = kwargs.get("time")
            self.resolution = kwargs.get("resolution")

        else:
            raise Exception("EntanglementGeneration generated invalid message type {}".format(msg_type))


class EntanglementGenerationA(EntanglementProtocol):
    """Entanglement generation protocol for quantum router.

    The EntanglementGenerationA protocol should be instantiated on a quantum router node.
    Instances will communicate with each other (and with the B instance on a BSM node) to generate entanglement.

    Attributes:
        own (QuantumRouter): node that protocol instance is attached to.
        name (str): label for protocol instance.
        middle (str): name of BSM measurement node where emitted photons should be directed.
        other (str): name of distant QuantumRouter node, containing a memory to be entangled with local memory.
        memory (Memory): quantum memory object to attempt entanglement for.
    """

    # todo: use a function to update resource manager

    def __init__(self, own: "Node", name: str, middle: str, other: str, memory: "Memory"):
        """Constructor for entanglement generation a class.

        Args:
            own (Node): node to attach protocol to.
            name (str): name of protocol instance.
            middle (str): name of middle measurement node.
            other (str): name of other node.
            memory (Memory): memory to entangle.
        """

        super().__init__(own, name)
        self.middle = middle
        self.other = other  # other node
        self.other_protocol = None  # other EG protocol on other node

        # memory info
        self.memory = memory
        self.memories = [memory]
        self.remote_memo_id = ""  # memory index used by corresponding protocol on other node

        # network and hardware info
        self.fidelity = memory.raw_fidelity
        self.qc_delay = 0
        self.expected_time = -1

        # memory internal info
        self.ent_round = 0  # keep track of current stage of protocol
        self.bsm_res = [-1, -1]  # keep track of bsm measurements to distinguish Psi+ and Psi-

        self.scheduled_events = []

        # misc
        self.primary = False  # one end node is the "primary" that initiates negotiation
        self.debug = False

    def set_others(self, other: "EntanglementGenerationA") -> None:
        """Method to set other entanglement protocol instance.

        Args:
            other (EntanglementGenerationA): other protocol instance.
        """

        assert self.other_protocol is None
        assert self.fidelity == other.fidelity
        if other.other_protocol is not None:
            assert self == other.other_protocol
        self.other_protocol = other
        self.remote_memo_id = other.memories[0].name
        self.primary = self.own.name > self.other

    def start(self) -> None:
        """Method to start current round of entanglement generation protocol.

        Will update memory and start negotiations with other protocol.

        Side Effects:
            Will call `update_memory` method.
            Will send message through attached node.
        """

        log.logger.info(self.own.name + " protocol start with partner {}, round={}".format(self.other, self.ent_round + 1))

        #if self.debug:
        #    print("EG protocol {} \033[1;36;40mstart\033[0m on node {} with partner {}".format(self.name, self.own.name,
        #                                                                                       self.other))
        #    print("\tround:", self.ent_round + 1)

        # to avoid start after remove protocol
        if self not in self.own.protocols:
            return

        # update memory, and if necessary start negotiations for round
        if self.update_memory() and self.primary:
            # send NEGOTIATE message
            self.qc_delay = self.own.qchannels[self.middle].delay
            message = EntanglementGenerationMessage(GenerationMsgType.NEGOTIATE, self.other_protocol.name, qc_delay=self.qc_delay)
            self.own.send_message(self.other, message)
        
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

        # to avoid start after remove protocol
        if self not in self.own.protocols:
            return

        self.ent_round += 1

        if self.ent_round == 1:
            return True

        elif self.ent_round == 2 and self.bsm_res[0] != -1:
            self.memory.flip_state()

        elif self.ent_round == 3 and self.bsm_res[1] != -1:
            # successful entanglement
            log.logger.info(self.own.name + " successful entanglement of memory {}".format(self.memory))
            self.memory.entangled_memory["node_id"] = self.other
            self.memory.entangled_memory["memo_id"] = self.remote_memo_id
            # TODO: notify of +/- state
            self.memory.fidelity = self.memory.raw_fidelity
            self.own.resource_manager.update(self, self.memory, "ENTANGLED")

        else:
            # entanglement failed
            log.logger.info(self.own.name + " failed entanglement of memory {}".format(self.memory))
            self.own.resource_manager.update(self, self.memory, "RAW")
            return False

        return True

    def emit_event(self) -> None:
        """Method to setup memory and emit photons.

        If the protocol is in round 1, the memory will be first set to the \|+> state.
        Regardless of round, the memory excite method will be invoked.

        Side Effects:
            May change state of attached memory.
            May cause attached memory to emit photon.
        """

        if self.ent_round == 1:
            self.memory.set_plus()
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

        if src not in [self.middle, self.other]:
            return

        msg_type = msg.msg_type

        log.logger.debug(self.own.name + " EG protocol received_message of type {} from node {}, round={}".format(msg.msg_type, src, self.ent_round + 1))

        if msg_type is GenerationMsgType.NEGOTIATE:
            # configure params
            another_delay = msg.qc_delay
            self.qc_delay = self.own.qchannels[self.middle].delay
            cc_delay = int(self.own.cchannels[src].delay)
            total_quantum_delay = max(self.qc_delay, another_delay)

            memory_excite_time = self.memory.next_excite_time
            min_time = max(self.own.timeline.now(), memory_excite_time) + total_quantum_delay - self.qc_delay + cc_delay
            emit_time = self.own.schedule_qubit(self.middle, min_time)# used to send memory
            self.expected_time = emit_time + self.qc_delay

            # schedule emit
            process = Process(self, "emit_event", [])
            event = Event(emit_time, process)
            self.own.timeline.schedule(event)
            self.scheduled_events.append(event)

            # send negotiate_ack
            another_emit_time = emit_time + self.qc_delay - another_delay
            message = EntanglementGenerationMessage(GenerationMsgType.NEGOTIATE_ACK, self.other_protocol.name,
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
            assert emit_time == msg.emit_time, "%d %d %d" % (emit_time, msg.emit_time, self.own.timeline.now())

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
            res = msg.res
            time = msg.time
            resolution = msg.resolution

            log.logger.debug(self.own.name + " received MEAS_RES {} at time {}, expected {}, round={}".format(res, time, self.expected_time, self.ent_round + 1))

            def valid_trigger_time(trigger_time, target_time, resolution):
                upper = target_time + resolution
                lower = 0
                if resolution % 2 == 0:
                    upper = min(upper, target_time + resolution // 2)
                    lower = max(lower, target_time - resolution // 2)
                else:
                    upper = min(upper, target_time + resolution // 2 + 1)
                    lower = max(lower, target_time - resolution // 2 + 1)
                if (upper / resolution) % 1 >= 0.5:
                    upper -= 1
                if (lower / resolution) % 1 < 0.5:
                    lower += 1
                return lower <= trigger_time <= upper

            if valid_trigger_time(time, self.expected_time, resolution):
                # record result if we don't already have one
                i = self.ent_round - 1
                if self.bsm_res[i] == -1:
                    self.bsm_res[i] = res
                else:
                    self.bsm_res[i] = -1

        else:
            raise Exception("Invalid message {} received by EG on node {}".format(msg_type, self.own.name))

        return True

    def is_ready(self) -> bool:
        return self.other_protocol is not None

    def memory_expire(self, memory: "Memory") -> None:
        """Method to receive expired memories."""

        assert memory == self.memory
        self.update_resource_manager(memory, 'RAW')
        for event in self.scheduled_events:
            if event.time >= self.own.timeline.now():
                self.own.timeline.remove_event(event)

    def update_resource_manager(self, memory: "Memory", state: str) -> None:
        """Method to update attached memory to desired state.

        Args:
            memory (Memory): attached memory to update.
            state (str): state memory should be updated to.

        Side Effects:
            May alter the state of `memory`.
        """

        self.own.resource_manager.update(self, memory, state)


class EntanglementGenerationB(EntanglementProtocol):
    """Entanglement generation protocol for BSM node.

    The EntanglementGenerationB protocol should be instantiated on a BSM node.
    Instances will communicate with the A instance on neighboring quantum router nodes to generate entanglement.

    Attributes:
        own (BSMNode): node that protocol instance is attached to.
        name (str): label for protocol instance.
        others (List[str]): list of neighboring quantum router nodes
    """

    def __init__(self, own: "Node", name: str, others: List[str]):
        """Constructor for entanglement generation b protocol.

        Args:
            own (Node): attached node.
            name (str): name of protocol instance.
            others (List[str]): name of protocol instance on end nodes.
        """

        super().__init__(own, name)
        assert len(others) == 2
        self.others = others  # end nodes
        # self.other_protocols = kwargs.get("other_protocols") # other EG protocols (must be same order as others)

    def bsm_update(self, bsm: 'SingleAtomBSM', info: Dict[str, Any]):
        """Method to receive detection events from BSM on node.

        Args:
            bsm (SingleAtomBSM): bsm object calling method.
            info (Dict[str, any]): information passed from bsm.
        """

        assert info['info_type'] == "BSM_res"

        res = info["res"]
        time = info["time"]
        resolution = self.own.bsm.resolution

        for i, node in enumerate(self.others):
            message = EntanglementGenerationMessage(GenerationMsgType.MEAS_RES, None, res=res, time=time,
                                                    resolution=resolution)
            self.own.send_message(node, message)

    def received_message(self, src: str, msg: EntanglementGenerationMessage):
        raise Exception("EntanglementGenerationB protocol '{}' should not receive message".format(self.name))

    def start(self) -> None:
        pass

    def set_others(self, other: "EntanglementProtocol") -> None:
        pass

    def is_ready(self) -> bool:
        return True

    def memory_expire(self) -> None:
        raise Exception("EntanglementGenerationB protocol '{}' should not have memory_expire".format(self.name))
