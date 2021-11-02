from sequence.kernel.timeline import Timeline
from sequence.kernel.process import Process
from sequence.components.detector import Detector


tl = Timeline()
detector = Detector("detector", tl)

process = Process(detector, "get", [None, {"dark_get": False}])
process.run()

assert detector.photon_counter == 1
