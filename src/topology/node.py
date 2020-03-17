import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..kernel.timeline import Timeline
    from ..protocols.message import Message
    from ..components.optical_channel import QuantumChannel, ClassicalChannel

from ..kernel.entity import Entity
from ..kernel.process import Process
from ..kernel.event import Event
from ..components.memory import MemoryArray
from ..components.bsm import SingleAtomBSM
from ..protocols.entanglement.generation import EntanglementGeneration


class Node(Entity):
    def __init__(self, name: str, timeline: "Timeline", **kwargs):
        Entity.__init__(self, name, timeline)
        self.owner = self
        self.cchannels = {}  # mapping of destination node names to classical channels
        self.qchannels = {}  # mapping of destination node names to quantum channels
        self.protocols = []

    def init(self) -> None:
        for protocol in self.protocols:
            protocol.init()

    def assign_cchannel(self, cchannel: "ClassicalChannel", another: str) -> None:
        self.cchannels[another] = cchannel

    def assign_qchannel(self, qchannel: "QuantumChannel", another: str) -> None:
        self.qchannels[another] = qchannel

    def send_message(self, dst: str, msg: "Message", priority=math.inf) -> None:
        self.cchannels[dst].transmit(msg, self, priority)

    def receive_message(self, src: str, msg: "Message") -> None:
        pass

    def send_qubit(self, dst: str, qubit) -> None:
        self.qchannels[dst].transmit(qubit, self)

    def receive_qubit(self, src: str, qubit) -> None:
        pass


class QuantumRepeater(Node):
    def __init__(self, name: str, timeline: "Timeline", **kwargs) -> None:
        Node.__init__(self, name, timeline, **kwargs)
        self.memory_array = kwargs.get("memory_array", MemoryArray("%s_memory" % name, timeline))
        self.eg = EntanglementGeneration(self)
        self.eg.middles = []
        self.memory_array.upper_protocols.append(self.eg)

    def receive_message(self, src: str, msg: "Message") -> None:
        # signal to protocol that we've received a message
        for protocol in self.protocols:
            if type(protocol) == msg.owner_type:
                if protocol.received_message(src, msg):
                    return

        # if we reach here, we didn't successfully receive the message in any protocol
        print(src, msg)
        raise Exception("Unkown protocol")

    def eg_add_middle(self, middle):
        self.eg.middles.append(middle.name)

    def eg_add_others(self, other):
        self.eg.others.append(other.name)

    def load_events(self):
        self.eg.is_start = True
        process = Process(self.eg, "start", [])
        event = Event(self.timeline.now(), process)
        self.timeline.schedule(event)


class MiddleNode(Node):
    def __init__(self, name: str, timeline: "Timeline", **kwargs) -> None:
        Node.__init__(self, name, timeline, **kwargs)
        self.bsm = SingleAtomBSM("%s_bsm" % name, timeline)
        self.eg = EntanglementGeneration(self)
        self.bsm.upper_protocols.append(self.eg)

    def receive_message(self, src: str, msg: "Message") -> None:
        # signal to protocol that we've received a message
        for protocol in self.protocols:
            if type(protocol) == msg.owner_type:
                if protocol.received_message(src, msg):
                    return

        # if we reach here, we didn't successfully receive the message in any protocol
        print(src, msg)
        raise Exception("Unkown protocol")

    def receive_qubit(self, src: str, qubit):
        self.bsm.get(qubit)

    def eg_add_others(self, other):
        self.eg.others.append(other.name)


# class QuantumRouter(Node):
#     def __init__(self, name, timeline, **kwargs):
#         Node.__init__(self, name, timeline, **kwargs)
#         self.bsm = kwargs.get("bsm", BSM())
#         self.memo_array = kwargs.get("memo_array", MemoryArray())
#         self.control_protocol = [ResourceReservationProtocol(), RoutingProtocol()]
#
#     def receive_message(self, src: str, msg: Message):
#         pass
#
#     def receive_qubit(self, src: str, qubit):
#         pass


class QKDNode(Node):
    def __init__(self, name: str, timeline: "timeline"):
        Node.__init__(self, name, timeline)
        self.lightsource = None
        self.qsdetector = None

    def set_lightsource(self, lightsource):
        self.lightsource = lightsource
        self.lightsource.owner = self

    def set_qsdetector(self, qsdetector):
        self.qsdetector = qsdetector
        self.qsdetector.owner = self

    def send_qubits(self, basis_list, bit_list, source_name):
        encoding_type = self.components[source_name].encoding_type
        state_list = []
        for i, bit in enumerate(bit_list):
            state = (encoding_type["bases"][basis_list[i]])[bit]
            state_list.append(state)

        self.components[source_name].emit(state_list)

    def send_photons(self, state, num, source_name):
        state_list = [state] * num
        self.components[source_name].emit(state_list)

    def get_bits(self, light_time, start_time, frequency, detector_name):
        encoding_type = self.components[detector_name].encoding_type
        bits = [-1] * int(round(light_time * frequency))  # -1 used for invalid bits

        if encoding_type["name"] == "polarization":
            detection_times = self.components[detector_name].get_photon_times()

            # determine indices from detection times and record bits
            for time in detection_times[0]:  # detection times for |0> detector
                index = int(round((time - start_time) * frequency * 1e-12))
                if 0 <= index < len(bits):
                    bits[index] = 0

            for time in detection_times[1]:  # detection times for |1> detector
                index = int(round((time - start_time) * frequency * 1e-12))
                if 0 <= index < len(bits):
                    if bits[index] == 0:
                        bits[index] = -1
                    else:
                        bits[index] = 1

            return bits

        elif encoding_type["name"] == "time_bin":
            detection_times = self.components[detector_name].get_photon_times()
            bin_separation = encoding_type["bin_separation"]

            # single detector (for early, late basis) times
            for time in detection_times[0]:
                index = int(round((time - start_time) * frequency * 1e-12))
                if 0 <= index < len(bits):
                    if abs(((index * 1e12 / frequency) + start_time) - time) < bin_separation / 2:
                        bits[index] = 0
                    elif abs(((index * 1e12 / frequency) + start_time) - (time - bin_separation)) < bin_separation / 2:
                        bits[index] = 1

            # interferometer detector 0 times
            for time in detection_times[1]:
                time -= bin_separation
                index = int(round((time - start_time) * frequency * 1e-12))
                # check if index is in range and is in correct time bin
                if 0 <= index < len(bits) and \
                        abs(((index * 1e12 / frequency) + start_time) - time) < bin_separation / 2:
                    if bits[index] == -1:
                        bits[index] = 0
                    else:
                        bits[index] = -1

            # interferometer detector 1 times
            for time in detection_times[2]:
                time -= bin_separation
                index = int(round((time - start_time) * frequency * 1e-12))
                # check if index is in range and is in correct time bin
                if 0 <= index < len(bits) and \
                        abs(((index * 1e12 / frequency) + start_time) - time) < bin_separation / 2:
                    if bits[index] == -1:
                        bits[index] = 1
                    else:
                        bits[index] = -1

            return bits

        else:
            raise Exception("Invalid encoding type for node " + self.name)

    def set_bases(self, basis_list, start_time, frequency, detector_name):
        encoding_type = self.components[detector_name].encoding_type
        basis_start_time = start_time - 1e12 / (2 * frequency)

        if encoding_type["name"] == "polarization":
            splitter = self.components[detector_name].splitter
            splitter.start_time = basis_start_time
            splitter.frequency = frequency

            splitter_basis_list = []
            for b in basis_list:
                splitter_basis_list.append(encoding_type["bases"][b])
            splitter.basis_list = splitter_basis_list

        elif encoding_type["name"] == "time_bin":
            switch = self.components[detector_name].switch
            switch.start_time = basis_start_time
            switch.frequency = frequency
            switch.state_list = basis_list

        else:
            raise Exception("Invalid encoding type for node " + self.name)