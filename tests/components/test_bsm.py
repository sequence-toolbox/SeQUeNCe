import pytest
from sequence.components.bsm import *
from sequence.components.memory import *
from sequence.components.circuit import Circuit
from sequence.kernel.timeline import Timeline
from sequence.utils.encoding import *


class Parent():
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
        bsm = make_bsm("bsm", tl, encoding_type="unknown",
                       detectors=detectors4)

    # implemented encoding schemes
    polar_bsm = make_bsm("bsm1", tl, encoding_type="polarization",
                         detectors=detectors4)
    time_bin_bsm = make_bsm("bsm2", tl, encoding_type="time_bin",
                            detectors=detectors2)
    atom_bsm = make_bsm("bsm3", tl, encoding_type="single_atom",
                        detectors=detectors2)

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
    photon1 = Photon("", location=1)
    photon2 = Photon("", location=2)
    photon3 = Photon("", location=3)
    photon1_2 = Photon("", location=1)
    detectors = [{}] * 2
    bsm = make_bsm("bsm", tl, encoding_type="time_bin", detectors=detectors)

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
    p1 = Photon("p1", location=1, quantum_state=(complex(1), complex(0)))
    p2 = Photon("p2", location=2, quantum_state=(complex(0), complex(1)))
    bsm.get(p1)
    bsm.get(p2)

    assert len(parent.results) == 1

    # get 2 photons in same state (map to Phi+ / can't measure)
    tl.time = 1e6
    p3 = Photon("p3", location=1, quantum_state=(complex(1), complex(0)))
    p4 = Photon("p4", location=2, quantum_state=(complex(1), complex(0)))
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
    p1 = Photon("p1", encoding_type=time_bin, location=1, quantum_state=(complex(1), complex(0)))
    p2 = Photon("p2", encoding_type=time_bin, location=2, quantum_state=(complex(0), complex(1)))
    process = Process(bsm, "get", [p1])
    event = Event(0, process)
    tl.schedule(event)
    process = Process(bsm, "get", [p2])
    event = Event(0, process)
    tl.schedule(event)
    tl.run()

    assert len(parent.results) == 1

    # get 2 photons in same state (map to Phi+ / can't measure)
    p3 = Photon("p3", encoding_type=time_bin, location=1, quantum_state=(complex(1), complex(0)))
    p4 = Photon("p4", encoding_type=time_bin, location=2, quantum_state=(complex(1), complex(0)))
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
            mem1.owner = self
            mem2.owner = self

        def send_qubit(self, dst, photon):
            self.bsm.get(photon)

    tl = Timeline()
    detectors = [{"efficiency": 1}] * 2
    bsm = make_bsm("bsm", tl, encoding_type="single_atom", detectors=detectors)
    parent = Parent()
    bsm.attach(parent)
    mem_1 = Memory("mem_1", tl, fidelity=1, frequency=0, efficiency=1, coherence_time=1, wavelength=500)
    mem_2 = Memory("mem_2", tl, fidelity=1, frequency=0, efficiency=1, coherence_time=1, wavelength=500)

    pw = PhotonSendWrapper(mem_1, mem_2, bsm)

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


