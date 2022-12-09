import pytest
import numpy as np

from sequence.components.bsm import *
from sequence.components.memory import *
from sequence.components.circuit import Circuit
from sequence.kernel.timeline import Timeline
from sequence.kernel.process import Process
from sequence.kernel.event import Event
from sequence.utils.encoding import *


class Parent:
        def __init__(self):
            self.results = []

        def bsm_update(self, src: BSM, msg: Dict[str, Any]):
            entity = msg.get("entity")
            if entity == "BSM":
                res = msg.get("res")
                self.results.append(res)
            else:
                raise Exception("invalid update")


def test_construct_func():
    tl = Timeline()
    detectors2 = [{}] * 2
    detectors4 = [{}] * 4

    # unknown encoding scheme
    with pytest.raises(Exception):
        bsm = make_bsm("bsm", tl, encoding_type="unknown", detectors=detectors4)

    # implemented encoding schemes
    polar_bsm = make_bsm("bsm1", tl, encoding_type="polarization", detectors=detectors4)
    time_bin_bsm = make_bsm("bsm2", tl, encoding_type="time_bin", detectors=detectors2)
    atom_bsm = make_bsm("bsm3", tl, encoding_type="single_atom", detectors=detectors2)

    assert type(polar_bsm) == PolarizationBSM
    assert type(time_bin_bsm) == TimeBinBSM
    assert type(atom_bsm) == SingleAtomBSM


def test_init():
    tl = Timeline()
    detectors = [{"dark_count": 1}] * 2
    bsm = make_bsm("bsm", tl, encoding_type="time_bin", detectors=detectors)
    tl.init()

    assert len(tl.events) == len(detectors) * 2


def test_base_get():
    tl = Timeline()
    photon1 = Photon("", tl, location=1)
    photon2 = Photon("", tl, location=2)
    photon3 = Photon("", tl, location=3)
    photon1_2 = Photon("", tl, location=1)
    detectors = [{}] * 4
    bsm = make_bsm("bsm", tl, encoding_type="polarization", detectors=detectors)

    bsm.get(photon1)
    assert len(bsm.photons) == 1

    # same location
    bsm.get(photon1_2)
    assert len(bsm.photons) == 1

    # different location
    bsm.get(photon2)
    assert len(bsm.photons) == 2

    # later time
    tl.time = 1
    bsm.get(photon3)
    assert len(bsm.photons) == 1


def test_polarization_get():
    tl = Timeline()
    detectors = [{"efficiency": 1}] * 4
    bsm = make_bsm("bsm", tl, encoding_type="polarization", detectors=detectors)
    parent = Parent()
    bsm.attach(parent)

    # get 2 photons in orthogonal states (map to Psi+)
    p1 = Photon("p1", tl, location=1, quantum_state=(complex(1), complex(0)))
    p2 = Photon("p2", tl, location=2, quantum_state=(complex(0), complex(1)))
    bsm.get(p1)
    bsm.get(p2)

    assert len(parent.results) == 1

    # get 2 photons in same state (map to Phi+ / can't measure)
    tl.time = 1e6
    p3 = Photon("p3", tl, location=1, quantum_state=(complex(1), complex(0)))
    p4 = Photon("p4", tl, location=2, quantum_state=(complex(1), complex(0)))
    bsm.get(p3)
    bsm.get(p4)

    assert len(parent.results) == 1


def test_polarization_update():
    tl = Timeline()
    detectors = [{"time_resolution": 1}] * 4
    bsm = make_bsm("bsm", tl, encoding_type="polarization", detectors=detectors)
    parent = Parent()
    bsm.attach(parent)
    detector_list = bsm.detectors

    # test Psi+
    bsm.trigger(detector_list[0], {'time': 0})
    bsm.trigger(detector_list[1], {'time': 0})

    assert len(parent.results) == 1
    assert parent.results[0] == 0

    # test Psi-
    bsm.trigger(detector_list[0], {'time': 1})
    bsm.trigger(detector_list[3], {'time': 1})

    assert len(parent.results) == 2
    assert parent.results[1] == 1

    # test not matching times
    bsm.trigger(detector_list[0], {'time': 2})
    bsm.trigger(detector_list[3], {'time': 3})

    assert len(parent.results) == 2

    # test invalid measurement
    bsm.trigger(detector_list[0], {'time': 4})
    bsm.trigger(detector_list[2], {'time': 4})

    assert len(parent.results) == 2


def test_time_bin_get():
    tl = Timeline()
    detectors = [{"efficiency": 1, "count_rate": 1e9}] * 2
    bsm = make_bsm("bsm", tl, encoding_type="time_bin", detectors=detectors)
    parent = Parent()
    bsm.attach(parent)
    detector_list = bsm.detectors

    # get 2 photons in orthogonal states (map to Psi+)
    p1 = Photon("p1", tl, encoding_type=time_bin, location=1, quantum_state=(complex(1), complex(0)))
    p2 = Photon("p2", tl, encoding_type=time_bin, location=2, quantum_state=(complex(0), complex(1)))
    process = Process(bsm, "get", [p1])
    event = Event(0, process)
    tl.schedule(event)
    process = Process(bsm, "get", [p2])
    event = Event(0, process)
    tl.schedule(event)
    tl.run()

    assert len(parent.results) == 1

    # get 2 photons in same state (map to Phi+ / can't measure)
    p3 = Photon("p3", tl, encoding_type=time_bin, location=1, quantum_state=(complex(1), complex(0)))
    p4 = Photon("p4", tl, encoding_type=time_bin, location=2, quantum_state=(complex(1), complex(0)))
    process = Process(bsm, "get", [p3])
    event = Event(1e6, process)
    tl.schedule(event)
    process = Process(bsm, "get", [p4])
    event = Event(1e6, process)
    tl.schedule(event)
    tl.run()

    assert len(parent.results) == 1


def test_time_bin_update():
    tl = Timeline()
    detectors = [{}] * 2
    bsm = make_bsm("bsm", tl, encoding_type="time_bin", detectors=detectors)
    parent = Parent()
    bsm.attach(parent)
    detector_list = bsm.detectors

    # test Psi+
    bsm.trigger(detector_list[0], {'time': 0})
    bsm.trigger(detector_list[0], {'time': 0 + time_bin["bin_separation"]})

    assert len(parent.results) == 1
    assert parent.results[0] == 0

    # test Psi-
    bsm.trigger(detector_list[0], {'time': 1e6})
    bsm.trigger(detector_list[1], {'time': 1e6 + time_bin["bin_separation"]})

    assert len(parent.results) == 2
    assert parent.results[1] == 1

    # test invalid time separation
    bsm.trigger(detector_list[0], {'time': 2e6})
    bsm.trigger(detector_list[0], {'time': 2e6})

    assert len(parent.results) == 2

    bsm.trigger(detector_list[0], {'time': 3e6})
    bsm.trigger(detector_list[0], {'time': 4e6})

    assert len(parent.results) == 2


def test_single_atom_get():
    class PhotonSendWrapper():
        def __init__(self, mem1, mem2, bsm):
            self.bsm = bsm
            mem1.add_receiver(self)
            mem2.add_receiver(self)

        def get(self, photon, **kwargs):
            self.bsm.get(photon)

    tl = Timeline()
    detectors = [{"efficiency": 1}] * 2
    bsm = make_bsm("bsm", tl, encoding_type="single_atom", detectors=detectors)
    parent = Parent()
    bsm.attach(parent)
    mem_1 = Memory("mem_1", tl, fidelity=1, frequency=0, efficiency=1, coherence_time=1, wavelength=500)
    mem_2 = Memory("mem_2", tl, fidelity=1, frequency=0, efficiency=1, coherence_time=1, wavelength=500)

    _ = PhotonSendWrapper(mem_1, mem_2, bsm)

    # initially opposite states
    tl.time = 0
    mem_1.update_state([complex(1), complex(0)])
    mem_2.update_state([complex(0), complex(1)])
    mem_1.excite()  # send w/o destination as have direct_receiver set
    mem_2.excite()

    assert len(parent.results) == 1

    # flip state and resend
    tl.time = 1e6
    circ = Circuit(1)
    circ.x(0)
    tl.quantum_manager.run_circuit(circ, [mem_1.qstate_key])
    tl.quantum_manager.run_circuit(circ, [mem_2.qstate_key])
    mem_1.excite()
    mem_2.excite()

    assert len(parent.results) == 2
    # check that we've entangled
    assert len(tl.quantum_manager.get(mem_1.qstate_key).state) == 4
    assert tl.quantum_manager.get(mem_1.qstate_key) is tl.quantum_manager.get(mem_2.qstate_key)


def test_absorptive_get():
    from sequence.components.detector import Detector

    class Measurer:
        def __init__(self, detector):
            self.detector = detector
            self.generator = np.random.default_rng(1)

        def get(self, photon, **kwargs):
            res = Photon.measure(None, photon, self.generator)
            if res:
                self.detector.get()

    class DetectorMonitor:
        def __init__(self, detector: Detector):
            detector.attach(self)
            self.times = []

        def trigger(self, detector, info):
            self.times.append(info["time"])

    class RandomControl:
        def __init__(self, seed):
            self.generator = np.random.default_rng(seed)

        def get_generator(self):
            return self.generator

    NUM_TRIALS = 1000
    PERIOD = 1e6

    tl = Timeline()
    detectors = [{"efficiency": 1}] * 2
    bsm = make_bsm("bsm", tl, encoding_type="absorptive", detectors=detectors)
    random_control = RandomControl(0)
    bsm.owner = random_control
    d0 = Detector("d0", tl, 1)
    d1 = Detector("d1", tl, 1)
    m0 = Measurer(d0)
    m1 = Measurer(d1)
    monitor0 = DetectorMonitor(d0)
    monitor1 = DetectorMonitor(d1)

    tl.init()
    photons0 = [None, None]
    photons1 = [None, None]

    # simulate sending photon pairs
    for i in range(NUM_TRIALS):
        tl.time = i * PERIOD

        # pair 0 (null)
        photons0[0] = Photon("", tl, encoding_type=absorptive, location=0, use_qm=True)
        photons0[1] = Photon("", tl, encoding_type=absorptive, location=0, use_qm=True)
        photons0[0].is_null = True
        photons0[1].is_null = True
        photons0[0].combine_state(photons0[1])
        photons0[0].set_state((complex(1), complex(0), complex(0), complex(0)))

        # pair 1 (not null)
        photons1[0] = Photon("", tl, encoding_type=absorptive, location=1, use_qm=True)
        photons1[1] = Photon("", tl, encoding_type=absorptive, location=1, use_qm=True)
        photons1[0].combine_state(photons1[1])
        photons1[0].set_state((complex(0), complex(0), complex(0), complex(1)))

        # send part of each pair to bsm
        bsm.get(photons0[0])
        bsm.get(photons1[0])

        # detect other part
        m0.get(photons0[1])
        m1.get(photons1[1])

    assert len(set(monitor0.times) & set(monitor1.times)) == 0
    assert len(monitor0.times + monitor1.times) == NUM_TRIALS
    assert abs(len(monitor0.times)/len(monitor1.times) - 1) < 0.1
