class LightSource:
    def __init__(self, name, timeline, *params):
        self.name = name
        self.timeline = timeline
        print("create ls")

    def emit(self, *params):
        print("ls emit")
        pass

