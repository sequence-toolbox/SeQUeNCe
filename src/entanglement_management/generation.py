"""Code for Barrett-Kok entanglement Generation protocol

This module defines code to support entanglement generation between single-atom memories on distant nodes.
Also defined is the message type used by this implementation.
Entanglement generation is asymmetric:
    EntanglementGenerationA should be used on the QuantumRouter (with one node set as the primary) and should be started via the "start" method
    EntanglementGeneraitonB should be used on the BSMNode and does not need to be started
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


class GenerationMsgType(Enum):
    NEGOTIATE = auto()
    NEGOTIATE_ACK = auto()
    MEAS_RES = auto()


class EntanglementGenerationMessage(Message):
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
    # todo: use a function to update resource manager
    def __init__(self, own: "Node", name: str, middle: str, other: str, memory: "Memory"):
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
        assert self.other_protocol is None
        assert self.fidelity == other.fidelity
        if other.other_protocol is not None:
            assert self == other.other_protocol
        self.other_protocol = other
        self.remote_memo_id = other.memories[0].name
        self.primary = self.own.name > self.other

    # start: called on initializing node
    #   starts current round of protocol
    #   calls update memory and starts negotiation in anticipation of memory emit
    def start(self) -> None:
        if self.debug:
            print("EG protocol {} \033[1;36;40mstart\033[0m on node {} with partner {}".format(self.name, self.own.name,
                                                                                               self.other))
            print("\tround:", self.ent_round + 1)

        # to avoid start after remove protocol
        if self not in self.own.protocols:
            return

        # update memory, and if necessary start negotiations for round
        if self.update_memory() and self.primary:
            # send NEGOTIATE message
            self.qc_delay = self.own.qchannels[self.middle].delay
            message = EntanglementGenerationMessage(GenerationMsgType.NEGOTIATE, self.other_protocol.name, qc_delay=self.qc_delay)
            self.own.send_message(self.other, message)
        
    # update_memory: called on both nodes
    #   check memory state, performs necessary memory operations
    #   returns True if round successfull, otherwise returns False
    def update_memory(self):
        # to avoid start after remove protocol
        if self not in self.own.protocols:
            return

        self.ent_round += 1

        if self.ent_round == 1:
            return True

        elif self.ent_round == 2 and self.bsm_res[0] != -1:
            self.memory.flip_state()

        elif self.ent_round == 3 and self.bsm_res[1] != -1:
            # entanglement succeeded
            if self.debug:
                print("\tsuccessful entanglement of memory {} on node {}".format(self.memory, self.own.name))
            self.memory.entangled_memory["node_id"] = self.other
            self.memory.entangled_memory["memo_id"] = self.remote_memo_id
            # TODO: notify of +/- state
            self.memory.fidelity = self.memory.raw_fidelity
            self.own.resource_manager.update(self, self.memory, "ENTANGLED")

        else:
            # entanglement failed
            if self.debug:
                print("\tfailed entanglement of memory {} on node {}".format(self.memory, self.own.name))
            self.own.resource_manager.update(self, self.memory, "RAW")
            return False

        return True

    def emit_event(self) -> None:
        if self.ent_round == 1:
            self.memory.set_plus()
        self.memory.excite(self.middle)

    def received_message(self, src: str, msg: EntanglementGenerationMessage) -> None:
        if src not in [self.middle, self.other]:
            return

        if self.debug:
            print("EG protocol {} \033[1;36;40mreceived_message\033[0m on node {}".format(self.name, self.own.name))
            print("\tsource:", src)
            print("\t\033[1;32;40mtype\033[0m:", msg.msg_type)

        msg_type = msg.msg_type

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

            if self.debug:
                print("\ttime:", time)
                print("\texpected:", self.expected_time)
                print("\tresult:", res)

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
        assert memory == self.memory
        self.own.resource_manager.update(self, self.memory, "RAW")
        for event in self.scheduled_events:
            if event.time >= self.own.timeline.now():
                self.own.timeline.remove_event(event)

    # ignore memory expiration events
    def pop(self, **kwargs):
        pass


class EntanglementGenerationB(EntanglementProtocol):
    def __init__(self, own: "Node", name: str, others: List[str]):
        super().__init__(own, name)
        assert len(others) == 2
        self.others = others  # end nodes
        # self.other_protocols = kwargs.get("other_protocols") # other EG protocols (must be same order as others)

    def bsm_update(self, bsm: 'SingleAtomBSM', msg: Dict[str, Any]):
        assert msg['info_type'] == "BSM_res"

        res = msg.get("res")
        time = msg.get("time")
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
