import math

from ..components.optical_channel import *
from ..protocols.message import Message


class Node(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.owner = self
        self.components = {}
        self.cchannels = {}  # mapping of destination node names to classical channels
        self.qchannels = {}  # mapping of destination node names to quantum channels
        self.protocols = []

    def init(self):
        for protocol in self.protocols:
            protocol.init()

    def assign_component(self, component: Entity, label: str):
        component.parents.append(self)
        self.components[label] = component

    def assign_cchannel(self, cchannel: ClassicalChannel, another: str):
        self.cchannels[another] = cchannel

    def assign_qchannel(self, qchannel: QuantumChannel, another: str):
        self.qchannels[another] = qchannel

    def send_message(self, dst: str, msg: Message, priority=math.inf):
        self.cchannels[dst].transmit(msg, self, priority)

    def receive_message(self, src: str, msg: Message):
        # signal to protocol that we've received a message
        for protocol in self.protocols:
            if type(protocol) == msg.owner_type:
                if protocol.received_message(src, msg):
                    return

        # if we reach here, we didn't successfully receive the message in any protocol
        print(src, msg)
        raise Exception("Unkown protocol")

    def send_qubit(self, dst: str, qubit):
        pass

    def receive_qubit(self, src: str, qubit):
        pass


class _Node(Entity):
    def __init__(self, name, timeline, **kwargs):
        assert (' ' not in name)
        Entity.__init__(self, name, timeline)
        self.components = kwargs.get("components", {})
        self.cchannels = {}  # mapping of destination node names to classical channels
        self.qchannels = {}  # mapping of destination node names to quantum channels
        self.protocols = []

    def init(self):
        for protocol in self.protocols:
            protocol.init()

    def assign_component(self, component: Entity, label: str):
        component.parents.append(self)
        self.components[label] = component

    def assign_cchannel(self, cchannel: ClassicalChannel):
        # Must have used ClassicalChannel.addend prior to using this method
        another = ""
        for end in cchannel.ends:
            if end.name != self.name:
                another = end.name
        if another in self.cchannels:
            print("warn: overwrite classical channel from %s to %s" % (self.name, another))
        self.cchannels[another] = cchannel

    def assign_qchannel(self, qchannel: QuantumChannel):
        components = self.components.values()
        is_sender = qchannel.sender in components
        is_receiver = qchannel.receiver in components
        assert is_sender ^ is_receiver, "node must be explicitly 1 end of quantum channel"

        if is_sender:
            device = qchannel.receiver
        else:
            device = qchannel.sender

        # find parent node
        parent = device.parents[0]
        while not isinstance(parent, Node):
            parent = parent.parents[0]
            if parent is None:
                Exception("could not find parent of component {} in '{}'.assign_qchannel".format(device.name, self.name))

        self.qchannels[parent.name] = qchannel

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

    def get_source_count(self):
        source = self.components['lightsource']
        return source.photon_counter

    def _pop(self, **kwargs):
        for protocol in self.protocols:
            protocol.pop(**kwargs)

    def pop(self, **kwargs):
        entity = kwargs.get("entity")
        # TODO: figure out how to get encoding_type
        # encoding_type = self.components[entity].encoding_type

        if entity == "QSDetector":
            raise Exception("unimplemented method for handling QSDetector result in node '{}'".format(self.name))

            # calculate bit and then pop to protocols
            detector_index = kwargs.get("detector_num")
            bit = -1

            if encoding_type.name == "polarization":
                bit = detector_index
                # TODO: pop to protocol

            elif encoding_type.name == "time_bin":
                bin_separation = encoding_type.bin_separation
                # TODO: need early and late arrival time to calculate bit value

        elif entity == "BSM":
            self._pop(info_type="BSM_res", **kwargs)

        elif entity == "MemoryArray":
            self._pop(info_type="expired_memory", index=kwargs.get("index"))

    def send_message(self, dst: str, msg: Message, priority=math.inf):
        self.cchannels[dst].transmit(msg, self, priority)

    def receive_message(self, src: str, msg: Message):
        # signal to protocol that we've received a message
        for protocol in self.protocols:
            if type(protocol) == msg.owner_type:
                if protocol.received_message(src, msg):
                    return

        # if we reach here, we didn't successfully receive the message in any protocol
        print(src, msg)
        raise Exception("Unkown protocol")
