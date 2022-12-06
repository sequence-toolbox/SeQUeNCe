from math import sqrt
import numpy as np

from sequence.components.detector import *
from sequence.components.photon import Photon
from sequence.kernel.timeline import Timeline
from sequence.kernel.quantum_manager import FOCK_DENSITY_MATRIX_FORMALISM
from sequence.utils.encoding import polarization, time_bin, absorptive, fock

SEED = 0


def clear_qsd_detectors(qsd):
    for d in qsd.detectors:
        d.next_detection_time = -1
        d.photon_counter = 0


def create_detector(efficiency=0.9, dark_count=0, count_rate=25e6, time_resolution=150):
    class Parent:
        def __init__(self, tl):
            self.timeline = tl
            self.log = []

        def trigger(self, detector, msg):
            self.log.append((self.timeline.now(), msg['time'], detector))

    class Owner:
        def __init__(self):
            self.generator = np.random.default_rng(SEED)

        def get_generator(self):
            return self.generator

    tl = Timeline()
    detector = Detector("", tl, efficiency=efficiency, dark_count=dark_count,
                        count_rate=count_rate, time_resolution=time_resolution)
    parent = Parent(tl)
    own = Owner()
    detector.attach(parent)
    detector.owner = own
    return detector, parent, tl


def test_Detector_init():
    detector, parent, tl = create_detector(dark_count=10)
    tl.init()
    assert len(tl.events) == 2


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
    stop_time = 1e14
    detector, parent, tl = create_detector(dark_count=dark_count)
    tl.init()
    tl.stop_time = stop_time
    tl.run()
    assert (len(parent.log) - stop_time / 1e12 * dark_count) / (stop_time / 1e12 * dark_count) < 0.1

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
    detector, parent, tl = create_detector(efficiency=1, count_rate=1e12,
                                           time_resolution=time_resolution)
    times = np.random.randint(0, 1e12, 100, dtype=np.int64)
    times.sort()
    for t in times:
        tl.time = t
        detector.get()
        assert parent.log[-1][1] % time_resolution == 0


def test_Detector_dark_count():
    time = 1e14
    dark_count = 100
    detector, parent, tl = create_detector(dark_count=dark_count)

    tl.init()
    tl.stop_time = time
    tl.run()

    ratio = len(parent.log) / (dark_count * time * 1e-12)
    assert ratio - 1 < 0.1


def test_QSDetectorPolarization_init():
    tl = Timeline()
    qsdetector = QSDetectorPolarization("qsd", tl)
    tl.init()


def test_QSDetectorPolarization_set_basis_list():
    tl = Timeline()
    qsdetector = QSDetectorPolarization("qsd", tl)
    basis_list = []
    start_time = 0
    frequency = 1e6
    qsdetector.set_basis_list(basis_list, start_time, frequency)
    assert qsdetector.splitter.basis_list == basis_list and \
           qsdetector.splitter.start_time == start_time and \
           qsdetector.splitter.frequency == frequency


def test_QSDetectorPolarization_update_splitter_params():
    fidelity = 0.9
    tl = Timeline()
    qsdetector = QSDetectorPolarization("qsd", tl)
    qsdetector.update_splitter_params("fidelity", fidelity)

    assert qsdetector.splitter.fidelity == fidelity


def test_QSDetectorPolarization_update_detector_params():
    tl = Timeline()
    qsdetector = QSDetectorPolarization("qsd", tl)
    qsdetector.update_detector_params(0, "dark_count", 99)
    assert qsdetector.detectors[0].dark_count == 99 and qsdetector.detectors[1].dark_count != 99


def test_QSDetector_update():
    tl = Timeline()
    qsdetector = QSDetectorPolarization("qsd", tl)

    args = [[0, 10], [1, 20], [1, 40]]
    for arg in args:
        qsdetector.trigger(qsdetector.detectors[arg[0]], {'time': arg[1]})
        trigger_times = qsdetector.trigger_times
        assert trigger_times[arg[0]][-1] == arg[1]


def test_QSDetectorPolarization():
    tl = Timeline()
    qsdetector = QSDetectorPolarization("qsd", tl)
    qsdetector.update_detector_params(0, "efficiency", 1)
    qsdetector.update_detector_params(1, "efficiency", 1)
    frequency = 1e5
    start_time = 0
    basis_list = [np.random.randint(2) for _ in range(1000)]
    qsdetector.set_basis_list(basis_list, start_time, frequency)
    tl.init()

    for i in range(1000):
        tl.time = i * 1e12 / frequency
        basis = basis_list[i]
        bit = np.random.randint(2)
        photon = Photon(str(i), tl, quantum_state=polarization["bases"][basis][bit])
        qsdetector.get(photon)

    trigger_times = qsdetector.get_photon_times()
    length = len(trigger_times[0] + trigger_times[1])
    assert length == 1000
    assert qsdetector.get_photon_times() == [[], []]


def test_QSDetectorTimeBin():
    tl = Timeline()
    qsdetector = QSDetectorTimeBin("qsd", tl)
    [qsdetector.update_detector_params(i, "efficiency", 1) for i in range(3)]
    frequency = 1e5
    start_time = 0
    basis_list = [np.random.randint(2) for _ in range(1000)]
    qsdetector.set_basis_list(basis_list, start_time, frequency)
    tl.init()

    for i in range(1000):
        tl.time = i * 1e12 / frequency
        basis = basis_list[i]
        bit = np.random.randint(2)
        photon = Photon(str(i), tl, encoding_type=time_bin,
                        quantum_state=time_bin["bases"][basis][bit])
        qsdetector.get(photon)

    tl.time = 0
    tl.run()

    trigger_times = qsdetector.get_photon_times()
    length = len(trigger_times[0] + trigger_times[1] + trigger_times[2])
    assert abs(length / 1000 - 7 / 8) < 0.1


def test_QSDetectorFockDirect():
    NUM_TRIALS = 1000
    COUNT_RATE = 80e6
    period = (1e12 / COUNT_RATE) + 1
    src_list = ["a", "b"]

    tl = Timeline(formalism=FOCK_DENSITY_MATRIX_FORMALISM)

    qsd = QSDetectorFockDirect("qsd", tl, src_list)
    [qsd.update_detector_params(i, "efficiency", 1) for i in range(2)]
    [qsd.update_detector_params(i, "count_rate", COUNT_RATE) for i in range(2)]

    tl.init()

    for _ in range(1000):
        photon = Photon("", tl, encoding_type=fock, use_qm=True)
        photon.set_state((0, 1))
        qsd.get(photon, src=src_list[0])
        tl.time += period

    times = qsd.get_photon_times()
    assert len(times[0]) == NUM_TRIALS

    tl.time = 0
    for _ in range(1000):
        photon = Photon("", tl, encoding_type=fock, use_qm=True)
        photon.set_state((0, 1))
        qsd.get(photon, src=src_list[1])
        tl.time += period

    times = qsd.get_photon_times()
    assert len(times[1]) == NUM_TRIALS


def test_QSDetectorFockInterference():
    class RandomControl:
        def __init__(self, seed):
            self.generator = np.random.default_rng(seed)

        def get_generator(self):
            return self.generator

    NUM_TRIALS = 1000
    COUNT_RATE = 80e6
    period = (1e12 / COUNT_RATE) + 1
    psi_minus = [complex(0), complex(sqrt(1 / 2)), -complex(sqrt(1 / 2)), complex(0)]
    src_list = ["a", "b"]

    tl = Timeline(formalism=FOCK_DENSITY_MATRIX_FORMALISM)

    qsd = QSDetectorFockInterference("qsd", tl, src_list)
    random_control = RandomControl(0)
    qsd.owner = random_control
    [qsd.update_detector_params(i, "efficiency", 1) for i in range(2)]
    [qsd.update_detector_params(i, "count_rate", COUNT_RATE) for i in range(2)]

    tl.init()

    # # measure unentangled
    # for _ in range(NUM_TRIALS):
    #     p0 = Photon("", tl, encoding_type=fock, use_qm=True)
    #     qsd.get(p0, src=src_list[0])
    #     tl.time += period
    #
    # times = qsd.get_photon_times()
    # assert abs(len(times[0]) / len(times[1])) - 1 < 0.1

    # measure unentangled, two incident real photons
    tl.time = 0
    clear_qsd_detectors(qsd)
    for _ in range(NUM_TRIALS):
        p0 = Photon("", tl, encoding_type=fock, use_qm=True)
        p1 = Photon("", tl, encoding_type=fock, use_qm=True)
        p0.set_state((complex(0), complex(1)))
        p1.set_state((complex(0), complex(1)))
        qsd.get(p0, src=src_list[0])
        qsd.get(p1, src=src_list[1])
        tl.time += period

    times = qsd.get_photon_times()
    assert abs(len(times[0]) / len(times[1])) - 1 < 0.1

    # measure entangled, no phase
    tl.time = 0
    clear_qsd_detectors(qsd)
    for _ in range(NUM_TRIALS):
        p0 = Photon("", tl, encoding_type=fock, use_qm=True)
        p1 = Photon("", tl, encoding_type=fock, use_qm=True)
        key0 = p0.quantum_state
        key1 = p1.quantum_state
        tl.quantum_manager.set([key0, key1], psi_minus)
        qsd.get(p0, src=src_list[0])
        qsd.get(p1, src=src_list[1])
        tl.time += period

    times = qsd.get_photon_times()
    assert len(times[1]) == NUM_TRIALS

    # measure entangled, pi/2 phase
    tl.time = 0
    clear_qsd_detectors(qsd)
    qsd.set_phase(np.pi/2)
    for _ in range(NUM_TRIALS):
        p0 = Photon("", tl, encoding_type=fock, use_qm=True)
        p1 = Photon("", tl, encoding_type=fock, use_qm=True)
        key0 = p0.quantum_state
        key1 = p1.quantum_state
        tl.quantum_manager.set([key0, key1], psi_minus)
        qsd.get(p0, src=src_list[0])
        qsd.get(p1, src=src_list[1])
        tl.time += period

    times = qsd.get_photon_times()
    assert abs(len(times[0]) / len(times[1]) - 1) < 0.1

    # measure entangled, pi phase
    tl.time = 0
    clear_qsd_detectors(qsd)
    qsd.set_phase(np.pi)
    for _ in range(NUM_TRIALS):
        p0 = Photon("", tl, encoding_type=fock, use_qm=True)
        p1 = Photon("", tl, encoding_type=fock, use_qm=True)
        key0 = p0.quantum_state
        key1 = p1.quantum_state
        tl.quantum_manager.set([key0, key1], psi_minus)
        qsd.get(p0, src=src_list[0])
        qsd.get(p1, src=src_list[1])
        tl.time += period

    times = qsd.get_photon_times()
    assert len(times[0]) == NUM_TRIALS
