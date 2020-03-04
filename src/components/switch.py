from .detector import Detector
from .photon import Photon
from ..kernel.entity import Entity
from ..kernel.event import Event
from ..kernel.process import Process


class Switch(Entity):
    def __init__(self, timeline, **kwargs):
        Entity.__init__(self, "", timeline)
        self.receivers = []
        self.start_time = 0
        self.frequency = 0
        self.state_list = [kwargs.get("state", 0)]

    def init(self):
        pass

    def add_receiver(self, entity):
        self.receivers.append(entity)

    def set_state(self, state):
        self.state_list = [state]

    def get(self, photon):
        index = int((self.timeline.now() - self.start_time) * self.frequency * 1e-12)
        if index < 0 or index >= len(self.state_list):
            index = 0

        receiver = self.receivers[self.state_list[index]]

        # check if receiver is detector, if we're using time bin, and if the photon is "late" to schedule measurement
        if isinstance(receiver, Detector):
            if photon.encoding_type["name"] == "time_bin" and Photon.measure(photon.encoding_type["bases"][0], photon):
                time = self.timeline.now() + photon.encoding_type["bin_separation"]
                process = Process(receiver, "get", [])
                event = Event(time, process)
                self.timeline.schedule(event)
            else:
                receiver.get()
        else:
            receiver.get(photon)