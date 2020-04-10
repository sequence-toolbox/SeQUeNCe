from typing import List

from ..message import Message
from ..protocol import Protocol
from ...kernel.event import Event
from ...kernel.process import Process


class EntanglementGenerationMessage(Message):
    def __init__(self, msg_type, receiver, **kwargs):
        super().__init__(msg_type, receiver)
        self.protocol_type = EntanglementGenerationA

        if msg_type == "NEGOTIATE":
            self.qc_delay = kwargs.get("qc_delay")

        elif msg_type == "NEGOTIATE_ACK":
            self.emit_time = kwargs.get("emit_time")

        elif msg_type == "MEAS_RES":
            self.res = kwargs.get("res")
            self.time = kwargs.get("time")
            self.resolution = kwargs.get("resolution")

        else:
            raise Exception("EntanglementGeneration generated invalid message type {}".format(msg_type))


"""
Entanglement generation is asymmetric:
    EntanglementGenerationA should be used on the end nodes (with one node set as the primary) and should be started via the "start" method
    EntanglementGeneraitonB should be used on the middle node and does not need to be started
"""
class EntanglementGenerationA(Protocol):
    def __init__(self, own, name, **kwargs):
        if own is None:
            return

        super().__init__(own, name)
        self.middle = kwargs.get("middle")
        self.other = kwargs.get("other") # other node
        self.other_protocol = kwargs.get("other_protocol") # other EG protocol on other node

        # memory info
        self.memory = kwargs.get("memory", None) # memory operated on
        self.another_index = kwargs.get("another_index", -1) # memory index used by corresponding protocol on other node

        # network and hardware info
        self.fidelity = kwargs.get("fidelity", 0.9)
        self.qc_delay = 0
        self.expected_time = -1

        # memory internal info
        self.ent_round = 0 # keep track of current stage of protocol
        self.bsm_res = [-1, -1] # keep track of bsm measurements to distinguish Psi+ and Psi-
        
        # misc
        self.primary = False # one end node is the "primary" that initiates negotiation
        self.debug = False

    def init(self):
        pass

    # start: called on initializing node
    #   starts current round of protocol
    #   calls update memory and starts negotiation in anticipation of memory emit
    def start(self):
        if self.debug:
            print("EG protocol {} \033[1;36;40mstart\033[0m on node {} with partner {}".format(self.name, self.own.name, self.other))
            print("\tround:", self.ent_round + 1)

        # update memory, and if necessary start negotiations for round
        if self.update_memory() and self.primary:
            # send NEGOTIATE message
            self.qc_delay = self.own.qchannels[self.middle].delay
            message = EntanglementGenerationMessage("NEGOTIATE", self.other_protocol, qc_delay=self.qc_delay)
            self.own.send_message(self.other, message)
        
    # update_memory: called on both nodes
    #   check memory state, performs necessary memory operations
    #   returns True if round successfull, otherwise returns False
    def update_memory(self):
        self.ent_round += 1

        if self.ent_round == 1:
            self.memory.reset()

        elif self.ent_round == 2 and self.bsm_res[0] != -1:
            self.memory.flip_state()

        elif self.ent_round == 3 and self.bsm_res[1] != -1:
            # entanglement succeeded
            if self.debug:
                print("\tsuccessful entanglement of memory {} on node {}".format(self.memory, self.own.name))
            self.memory.entangled_memory["name"] = self.other
            self.memory.entangled_memory["id"] = self.another_index
            self.memory.fidelity = self.fidelity
            # TODO: notify of +/- state
            self.own.resource_manager.update(self.memory, "ENTANGLE")

        else:
            # entanglement failed
            if self.debug:
                print("\tfailed entanglement of memory {} on node {}".format(self.memory, self.own.name))

            self.own.resource_manager.update(self.memory, "EMPTY")
            return False

        return True

    def received_message(self, src: str, msg: EntanglementGenerationMessage):
        if self.debug:
            print("EG protocol {} \033[1;36;40mreceived_message\033[0m on node {}".format(self.name, self.own.name))
            print("\tsource:", src)
            print("\t\033[1;32;40mtype\033[0m:", msg.msg_type)

        msg_type = msg.msg_type

        if msg_type == "NEGOTIATE":
            # configure params
            another_delay = msg.qc_delay
            self.qc_delay = self.own.qchannels[self.middle].delay
            cc_delay = int(self.own.cchannels[src].delay)
            total_quantum_delay = max(self.qc_delay, another_delay)

            min_time = self.own.timeline.now() + total_quantum_delay - self.qc_delay + cc_delay
            emit_time = self.own.schedule_qubit(self.middle, min_time) # used to send memory
            self.expected_time = emit_time + self.qc_delay

            # schedule emit
            process = Process(self.memory, "excite", [self.middle])
            event = Event(emit_time, process)
            self.own.timeline.schedule(event)

            # send negotiate_ack
            another_emit_time = emit_time + self.qc_delay - another_delay
            message = EntanglementGenerationMessage("NEGOTIATE_ACK", self.other_protocol, emit_time=another_emit_time)
            self.own.send_message(src, message)

            # schedule start if necessary, else schedule update_memory
            # TODO: base future start time on resolution
            future_start_time = self.expected_time + self.own.cchannels[self.middle].delay + 1
            if self.ent_round == 1:
                process = Process(self, "start", [])
            else:
                process = Process(self, "update_memory", [])
            event = Event(future_start_time, process)
            self.own.timeline.schedule(event)

        elif msg_type == "NEGOTIATE_ACK":
            # configure params
            self.expected_time = msg.emit_time + self.qc_delay

            if msg.emit_time < self.own.timeline.now():
                msg.emit_time = self.own.timeline.now()

            # schedule emit
            process = Process(self.memory, "excite", [self.middle])
            event = Event(msg.emit_time, process)
            self.own.timeline.schedule(event)

            # schedule start if memory_stage is 0, else schedule update_memory
            # TODO: base future start time on resolution
            future_start_time = self.expected_time + self.own.cchannels[self.middle].delay + 1
            if self.ent_round == 1:
                process = Process(self, "start", [])
            else:
                process = Process(self, "update_memory", [])
            event = Event(future_start_time, process)
            self.own.timeline.schedule(event)

        elif msg_type == "MEAS_RES":
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


class EntanglementGenerationB(Protocol):
    def __init__(self, own, name, **kwargs):
        super().__init__(own, name)
        self.others = kwargs.get("others") # end nodes
        self.other_protocols = kwargs.get("other_protocols") # other EG protocols (must be same order as others)

    def init(self):
        pass

    def pop(self, info_type, **kwargs):
        assert info_type == "BSM_res"

        res = kwargs.get("res")
        time = kwargs.get("time")
        resolution = self.own.bsm.resolution

        for i, node in enumerate(self.others):
            message = EntanglementGenerationMessage("MEAS_RES", None, res=res, time=time, resolution=resolution)
            self.own.send_message(node, message)

    def received_message(self, src: str, msg: EntanglementGenerationMessage):
        raise Exception("EntanglementGenerationB protocol '{}' should not receive message".format(self.name))


