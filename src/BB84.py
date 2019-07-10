import numpy

from process import Process
from entity import Entity
from event import Event


class BB84(Entity):
    def __init__(self, name, timeline, **kwargs):
        super().__init__(name, timeline)
        self.role = kwargs.get("role", None)
        self.node = None
        self.basis_list = []
        self.bits = []
        self.key = []
        self.parent = None
        self.another = None

    def init(self):
        pass

    def assign_node(self, node_name):
        self.node = self.timeline.entities[node_name]

    def add_parent(self, parent_name):
        self.parent = self.timeline.entities[parent_name]

    def del_parent(self):
        self.parent = None

    def received_message(self):
        if self.node.message == "begin_photon_pulse":  # Bob will start to receive photons
            # generate basis list
            # schedule changes for BeamSplitter Basis
            # clear detector counts
            pass

        elif self.node.message == "end_photon_pulse":  # Bob done receiving photons
            # get photon detection times
            # check if any photons arrived at same time
            # determine indices from detection times
            # record bits
            self.node.send_message("received_qubits")

        elif self.node.message == "received_qubits":  # Alice can send basis
            self.node.send_message("basis_list: {}".format(self.basis_list))

        elif self.node.message == "":  # Bob will compare bases TODO: message?
            # compare own basis with basis message
            # create list of matching indices
            # set key equal to bits with matching bases
            # send to Alice list of matching indices
            pass

        elif self.node.message == "":  # Alice will create own version of key TODO: message?
            # set key equal to bits at received indices
            # check if key long enough
            #   if it is, truncate if necessary and call cascade
            #   otherwise, call generate_key again
            pass

    def receive_qubits(self):
        pass

    def generate_key(self, length):
        bases = [[0, 90], [45, 135]]
        self.basis_list = numpy.random.choice(bases, length)  # list of random bases
        self.bits = numpy.random.choice([0, 1], length)  # list of random bits
        self.node.send_photons(self.basis_list, self.bits, "lightsource")  # send bits to Bob
