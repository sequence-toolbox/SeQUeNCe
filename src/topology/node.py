from time import monotonic_ns
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..kernel.timeline import Timeline
    from ..protocols.message import Message
    from ..components.optical_channel import QuantumChannel, ClassicalChannel

from ..kernel.entity import Entity
from ..components.memory import MemoryArray
from ..components.bsm import SingleAtomBSM
from ..components.light_source import LightSource
from ..components.detector import QSDetectorPolarization, QSDetectorTimeBin
from ..protocols.qkd.BB84 import BB84
from ..protocols.management.manager import ResourceManager
from ..utils.encoding import *


class Node(Entity):
    def __init__(self, name: str, timeline: "Timeline"):
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
        if priority == math.inf:
            priority = monotonic_ns()
        self.cchannels[dst].transmit(msg, self, priority)

    def receive_message(self, src: str, msg: "Message") -> None:
        # signal to protocol that we've received a message
        if msg.receiver is not None:
            for protocol in self.protocols:
                if protocol.name == msg.receiver and protocol.received_message(src, msg):
                    return
        else:
            matching = [p for p in self.protocols if type(p) == msg.protocol_type]
            for p in matching:
                p.received_message(src, msg)

    def schedule_qubit(self, dst: str, min_time: int) -> int:
        return self.qchannels[dst].schedule_transmit(min_time)

    def send_qubit(self, dst: str, qubit) -> None:
        self.qchannels[dst].transmit(qubit, self)

    def receive_qubit(self, src: str, qubit) -> None:
        pass


class MiddleNode(Node):
    def __init__(self, name: str, timeline: "Timeline", other_nodes: [str], **kwargs) -> None:
        from ..protocols.entanglement.generation import EntanglementGenerationB
        Node.__init__(self, name, timeline, **kwargs)
        self.bsm = SingleAtomBSM("%s_bsm" % name, timeline)
        self.eg = EntanglementGenerationB(self, "{}_eg".format(name), other_nodes)
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


class QuantumRouter(Node):
    def __init__(self, name, tl, memo_size=50):
        Node.__init__(self, name, tl)
        self.memory_array = MemoryArray(name + ".MemoryArray", tl, num_memories=memo_size)
        self.memory_array.owner = self
        self.resource_manager = ResourceManager(self)

    def receive_message(self, src: str, msg: "Message") -> None:
        if msg.receiver == "resource_manager":
            self.resource_manager.received_message(src, msg)
        else:
            if msg.receiver is None:
                matching = [p for p in self.protocols if type(p) == msg.protocol_type]
                for p in matching:
                    p.received_message(src, msg)
            else:
                for protocol in self.protocols:
                    if protocol.name == msg.receiver:
                        protocol.received_message(src, msg)
                        break


class QKDNode(Node):
    """
    Protocol stack of QKDNode follows "BBN QKD Protocol Suite" introduced in the DARPA quantum network.
    (https://arxiv.org/pdf/quant-ph/0412029.pdf) page 24
    The protocol stack is :

    |      Authentication     |  <= No implementation
    |  Privacy Amplification  |  <= No implementation
    |    Entropy Estimation   |  <= No implementation
    |     Error Correction    |  <= implemented by cascade
    |         Sifting         |  <= implemented by BB84
    """

    def __init__(self, name: str, timeline: "timeline", encoding=polarization):
        Node.__init__(self, name, timeline)
        self.encoding = encoding
        self.lightsource = LightSource(name + ".lightsource", timeline, encoding_type=encoding)
        self.lightsource.owner = self

        if encoding["name"] == "polarization":
            self.qsdetector = QSDetectorPolarization(name + ".qsdetector", timeline)
        elif encoding["name"] == "time_bin":
            self.qsdetector = QSDetectorTimeBin(name + ".qsdetector", timeline)
        else:
            raise Exception("invalid encoding {} given for QKD node {}".format(encoding["name"], name))
        self.qsdetector.owner = self

        # Create BB84 protocol
        self.sifting_protocol = BB84(self, name + ".BB84")
        self.protocols.append(self.sifting_protocol)
        self.qsdetector.protocols.append(self.sifting_protocol)

    def init(self) -> None:
        Node.init(self)
        assert self.sifting_protocol.role != -1

    def update_lightsource_params(self, arg_name: str, value: Any) -> None:
        self.lightsource.__setattr__(arg_name, value)

    def get_bits(self, light_time, start_time, frequency):
        # compute received bits based on encoding scheme
        encoding = self.encoding["name"]
        bits = [-1] * int(round(light_time * frequency))  # -1 used for invalid bits

        if encoding == "polarization":
            detection_times = self.qsdetector.get_photon_times()

            # determine indices from detection times and record bits
            for time in detection_times[0]:  # detection times for |0> detector
                index = round((time - start_time) * frequency * 1e-12)
                if 0 <= index < len(bits):
                    bits[index] = 0

            for time in detection_times[1]:  # detection times for |1> detector
                index = round((time - start_time) * frequency * 1e-12)
                if 0 <= index < len(bits):
                    if bits[index] == 0:
                        bits[index] = -1
                    else:
                        bits[index] = 1

        elif encoding == "time_bin":
            detection_times = self.qsdetector.get_photon_times()
            bin_separation = self.encoding["bin_separation"]
        
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

        else:
            raise Exception("QKD node {} has illegal encoding type {}".format(self.name, encoding))

        return bits

    def set_bases(self, basis_list, start_time, frequency, component):
        encoding_type = component.encoding_type
        basis_start_time = start_time - 1e12 / (2 * frequency)

        if encoding_type["name"] == "polarization":
            splitter = component.splitter
            splitter.start_time = basis_start_time
            splitter.frequency = frequency

            splitter_basis_list = []
            for b in basis_list:
                splitter_basis_list.append(encoding_type["bases"][b])
            splitter.basis_list = splitter_basis_list

        elif encoding_type["name"] == "time_bin":
            switch = component.switch
            switch.start_time = basis_start_time
            switch.frequency = frequency
            switch.state_list = basis_list

        else:
            raise Exception("Invalid encoding type for node " + self.name)

    def receive_message(self, src: str, msg: "Message") -> None:
        # signal to protocol that we've received a message
        for protocol in self.protocols:
            if type(protocol) == msg.owner_type:
                protocol.received_message(src, msg)
                return

        # if we reach here, we didn't successfully receive the message in any protocol
        print(src, msg)
        raise Exception("Unkown protocol")

    def receive_qubit(self, src: str, qubit) -> None:
        self.qsdetector.get(qubit)
