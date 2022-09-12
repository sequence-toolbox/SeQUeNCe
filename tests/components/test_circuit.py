import numpy as np

from sequence.components.circuit import Circuit
from numpy import array, array_equal, identity
from pytest import raises


def test_h():
    circuit = Circuit(1)
    circuit.h(0)
    coefficient = 1 / (2 ** 0.5)
    expect = array([[coefficient, coefficient], [coefficient, -coefficient]])
    assert array_equal(expect, circuit.get_unitary_matrix())


def test_x():
    circuit = Circuit(1)
    circuit.x(0)
    expect = array([[0, 1], [1, 0]])
    assert array_equal(expect, circuit.get_unitary_matrix())


def test_y():
    circuit = Circuit(1)
    circuit.y(0)
    expect = array([[0, complex(0, -1)], [complex(0, 1), 0]])
    assert array_equal(expect, circuit.get_unitary_matrix())


def test_z():
    circuit = Circuit(1)
    circuit.z(0)
    expect = array([[1, 0], [0, -1]])
    assert array_equal(expect, circuit.get_unitary_matrix())


def test_cx():
    circuit = Circuit(2)
    circuit.cx(0, 1)
    expect = array([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1], [0, 0, 1, 0]])
    assert array_equal(expect, circuit.get_unitary_matrix())


def test_ccx():
    circuit = Circuit(3)
    circuit.ccx(0, 1, 2)
    expect = array([[1, 0, 0, 0, 0, 0, 0, 0],
                    [0, 1, 0, 0, 0, 0, 0, 0],
                    [0, 0, 1, 0, 0, 0, 0, 0],
                    [0, 0, 0, 1, 0, 0, 0, 0],
                    [0, 0, 0, 0, 1, 0, 0, 0],
                    [0, 0, 0, 0, 0, 1, 0, 0],
                    [0, 0, 0, 0, 0, 0, 0, 1],
                    [0, 0, 0, 0, 0, 0, 1, 0]])
    assert array_equal(expect, circuit.get_unitary_matrix())


def test_swap():
    circuit = Circuit(2)
    circuit.swap(0, 1)
    expect = array([[1, 0, 0, 0],
                    [0, 0, 1, 0],
                    [0, 1, 0, 0],
                    [0, 0, 0, 1]])
    assert array_equal(expect, circuit.get_unitary_matrix())


def test_t():
    from numpy import e, pi
    circuit = Circuit(1)
    circuit.t(0)
    expect = array([[1, 0], [0, e ** (complex(0, 1) * pi / 4)]])
    assert array_equal(expect, circuit.get_unitary_matrix())


def test_s():
    circuit = Circuit(1)
    circuit.s(0)
    expect = array([[1, 0], [0, complex(0, 1)]])
    assert array_equal(expect, circuit.get_unitary_matrix())


def test_phase():
    circuit = Circuit(1)
    circuit.phase(0, np.pi/2)
    expect = array([[1, 0], [0, complex(0, 1)]])
    assert array_equal(expect, circuit.get_unitary_matrix())


def test_measure():
    qc = Circuit(1)
    assert len(qc.measured_qubits) == 0
    qc.measure(0)
    assert len(qc.measured_qubits) == 1 and 0 in qc.measured_qubits
    with raises(AssertionError):
        qc.h(0)

    qc = Circuit(1)
    qc.h(0)
    qc.get_unitary_matrix()
    assert not qc._cache is None
    qc.x(0)
    assert qc._cache is None
    qc.get_unitary_matrix()
    qc.measure(0)
    assert not qc._cache is None


def test_Circuit():
    qc = Circuit(4)
    expect = identity(16)
    assert array_equal(qc.get_unitary_matrix(), expect)
    assert qc.size == 4 and len(qc.gates) == 0 and len(qc.measured_qubits) == 0
    with raises(AssertionError):
        qc.h(4)
    qc.cx(0, 3)
    qc.cx(1, 2)
    qc.measure(2)
    qc.measure(3)

    expect = array([[1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, ],
                    [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, ],
                    [0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, ],
                    [0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, ],
                    [0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, ],
                    [0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, ],
                    [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, ],
                    [0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, ],
                    [0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, ],
                    [0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, ],
                    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, ],
                    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, ],
                    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, ],
                    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, ],
                    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, ],
                    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, ]])
    assert array_equal(expect, qc.get_unitary_matrix())


def test_serialization():
    CIRCUIT_SIZE = 2
    GATES = [["h", [0], None], ["x", [1], None], ["phase", [0], np.pi]]
    MEASURES = [0]
    circuit = Circuit(2)
    for gate_type, gate_indices, args in GATES:
        if gate_type == "h":
            circuit.h(gate_indices[0])
        elif gate_type == "x":
            circuit.x(gate_indices[0])
        elif gate_type == "phase":
            circuit.phase(gate_indices[0], args)
        else:
            raise NotImplementedError
    for index in MEASURES:
        circuit.measure(index)

    serialized_info = circuit.serialize()
    assert serialized_info["size"] == CIRCUIT_SIZE
    serailized_gates = [{"arg": arg, "indices": gate_indices, "name": gate_type} for
                        gate_type, gate_indices, arg
                        in GATES]
    assert serialized_info["gates"] == serailized_gates
    assert serialized_info["measured_qubits"] == MEASURES

    deserailized_circuit = Circuit(1)
    deserailized_circuit.deserialize(serialized_info)
    assert deserailized_circuit.size == circuit.size
    assert deserailized_circuit.gates == circuit.gates
    assert deserailized_circuit.measured_qubits == circuit.measured_qubits
