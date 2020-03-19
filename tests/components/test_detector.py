from numpy import random

from sequence.components.detector import *

random.seed(1)


def create_detector(efficiency=0.9, dark_count=0, count_rate=25e6, time_resolution=150):
    class Parent():
        def __init__(self, tl):
            self.timeline = tl
            self.log = []

        def pop(self, detector, time):
            self.log.append((self.timeline.now(), time, detector))

    tl = Timeline()
    detector = Detector("", tl, efficiency=efficiency, dark_count=dark_count,
                        count_rate=count_rate, time_resolution=time_resolution)
    parent = Parent(tl)
    detector.parents.append(parent)
    return detector, parent, tl


def test_Detector_init():
    detector, parent, tl = create_detector(dark_count=10)
    tl.init()
    assert len(tl.events) > 0


def test_Detector_get():
    # efficiency
    efficiency = 0.5
    detector, parent, tl = create_detector(efficiency=efficiency)
    tl.init()
    for i in range(1000):
        tl.time = i * 1e9
        detector.get()
    assert len(parent.log) / 1000 - efficiency < 0.1

    # dark count
    dark_count = 100
    stop_time = 1e13
    detector, parent, tl = create_detector(dark_count=dark_count)
    tl.init()
    tl.stop_time = stop_time
    tl.run()
    assert len(parent.log) - stop_time / 1e12 * dark_count < 10

    # count rate
    count_rate = 1e11
    interval = 1e12 / count_rate
    detector, parent, tl = create_detector(efficiency=1, count_rate=count_rate)
    arrive_times = [0, 2 * interval, 4 * interval, 4.5 * interval, 5.1 * interval]
    expect_len = [1, 2, 3, 3, 4]
    for time, log_len in zip(arrive_times, expect_len):
        tl.time = time
        detector.get()
        assert len(parent.log) == log_len

    # time_resolution
    time_resolution = 233
    detector, parent, tl = create_detector(efficiency=1, count_rate=1e12, time_resolution=time_resolution)
    times = random.random_integers(0, 1e12, 100)
    times.sort()
    for t in times:
        tl.time = t
        detector.get()
        assert parent.log[-1][1] % time_resolution == 0


def test_QSDetectorPolarization_init():
    assert False


def test_QSDetectorPolarization_get():
    assert False


def test_QSDetectorPolarization_set_basis():
    assert False


def test_QSDetectorPolarization_update_splitter_params():
    assert False


def test_QSDetectorPolarization_update_detector_params():
    assert False


def test_QSDetectorPolarization_pop():
    assert False
