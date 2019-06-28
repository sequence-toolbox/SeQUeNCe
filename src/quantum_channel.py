class QChannel:
    def __init__(self, name, timeline, *params):
        self.name = name
        self.timeline = timeline
        print("create qc")

    def set_sender(self, *params):
        print("set qc sender")

    def set_receiver(self, *params):
        print("set qc receiver")
