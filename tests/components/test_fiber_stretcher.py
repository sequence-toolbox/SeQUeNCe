import numpy as np

from sequence.kernel.timeline import Timeline
from sequence.components.photon import Photon
from sequence.utils.encoding import absorptive
from sequence.components.circuit import Circuit
from sequence.components.fiber_stretcher import FiberStretcher


def test_init():
    tl = Timeline()
    fs = FiberStretcher("fs", tl, np.pi)

    fs_circ = fs._circuit.get_unitary_matrix()
    desired = np.array([[complex(1), complex(0)],
                        [complex(0), complex(-1)]])
    assert np.array_equal(fs_circ, desired)


def test_set_phase():
    tl = Timeline()
    fs = FiberStretcher("fs", tl)
    fs.set_phase(np.pi/2)

    fs_circ = fs._circuit.get_unitary_matrix()
    desired = np.array([[complex(1), complex(0)],
                        [complex(0), complex(0, 1)]])
    assert np.array_equal(fs_circ, desired)


def test_get():
    class DumbReceiver:
        def __init__(self):
            pass

        def get(self, photon, **kwargs):
            pass

    tl = Timeline()
    photon = Photon("", tl, encoding_type=absorptive, use_qm=True)
    fs = FiberStretcher("fs", tl, np.pi)
    receiver = DumbReceiver()
    fs.add_receiver(receiver)

    # set photon to + state
    circuit = Circuit(1)
    circuit.h(0)
    tl.quantum_manager.run_circuit(circuit, [photon.quantum_state])
    # send photon through fiber stretcher
    fs.get(photon)

    photon_state = tl.quantum_manager.get(photon.quantum_state).state
    desired = np.array([complex(np.sqrt(1/2)), complex(-np.sqrt(1/2))])
    assert np.where(np.isclose(photon_state, desired))
