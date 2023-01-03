import numpy as np
from scipy.linalg import fractional_matrix_power
import math

from sequence.kernel.quantum_manager import *
from sequence.components.circuit import Circuit


class DumbCircuit():
    def __init__(self, size, matrix):
        self.size = size
        self.matrix = matrix
        self.measured_qubits = []

    def get_unitary_matrix(self):
        return self.matrix


def test_qmanager_get():
    qm = QuantumManagerKet()
    qm.states[49] = "test_string"
    assert qm.get(49) == "test_string"


def test_qmanager_new():
    NUM_TESTS = 1000

    qm = QuantumManagerKet()
    
    keys = []
    for _ in range(NUM_TESTS):
        keys.append(qm.new())
    assert len(set(keys)) == NUM_TESTS

    test_state = [complex(0), complex(1)]
    key = qm.new(test_state)
    assert np.all(qm.get(key).state == np.array(test_state))


def test_qmanager_set():
    qm = QuantumManagerKet()
    key = qm.new()
    new_state = [complex(0), complex(1)]
    qm.set([key], new_state)
    assert np.all(qm.get(key).state == np.array(new_state))

    key2 = qm.new()
    keys = [key, key2]
    new_state = [complex(1), complex(0), complex(0), complex(0)]
    qm.set(keys, new_state)
    assert np.all(qm.get(key).state == qm.get(key2).state)
    assert np.all(qm.get(key).state == np.array(new_state))


def test_qmanager_remove():
    qm = QuantumManagerKet()
    qm.states[0] = "test_string"
    qm.remove(0)
    assert len(qm.states.keys()) == 0


def test_qmanager_circuit():
    qm = QuantumManagerKet()

    # single state
    key = qm.new()
    circuit = DumbCircuit(1, np.array([[0, 1], [1, 0]]))
    qm.run_circuit(circuit, [key])
    assert np.all(qm.get(key).state == np.array([0, 1]))

    # two states
    key1 = qm.new()
    key2 = qm.new()
    circuit = DumbCircuit(2, np.identity(4))
    qm.run_circuit(circuit, [key1, key2])
    assert np.all(qm.get(key1).state == qm.get(key2).state)
    assert np.all(qm.get(key1).state == np.array([1, 0, 0, 0]))

    # two states, wrong order
    qm.run_circuit(circuit, [key2, key1])
    assert np.all(qm.get(key1).state == qm.get(key2).state)
    assert np.all(qm.get(key1).state == np.array([1, 0, 0, 0]))
    assert qm.get(key1).keys == [key2, key1]

    # single state in multi-qubit system
    key1 = qm.new()
    key2 = qm.new()
    circuit1 = DumbCircuit(2, np.identity(4))
    qm.run_circuit(circuit1, [key1, key2])
    circuit2 = DumbCircuit(1, np.array([[0, 1], [1, 0]]))
    qm.run_circuit(circuit2, [key1])
    assert np.all(qm.get(key1).state == np.array([0, 0, 1, 0]))
    assert (qm.get(key1) is qm.get(key2))

    # extension of circuit
    key1 = qm.new()
    key2 = qm.new()
    qm.set([key1, key2], [0.5 ** 0.5, 0.5 ** 0.5, 0, 0])
    circuit1 = Circuit(1)
    circuit1.x(0)
    qm.run_circuit(circuit1, [key2])
    ket1 = qm.get(key1)
    if ket1.keys[0] > ket1.keys[1]:
        ket1.keys.reverse()
        ket1.state = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]]) @ ket1.state

    key3 = qm.new()
    key4 = qm.new()
    qm.set([key3, key4], [0.5 ** 0.5, 0.5 ** 0.5, 0, 0])
    circuit2 = Circuit(2)
    circuit2.x(1)
    qm.run_circuit(circuit2, [key3, key4])

    ket2 = qm.get(key3)
    if ket2.keys[0] > ket2.keys[1]:
        ket2.keys.reverse()
        ket2.state = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, 1, 0, 0], [0, 0, 0, 1]]) @ ket2.state

    assert np.array_equal(qm.get(key1).state, qm.get(key3).state)


def test_qmanager_circuit_density():
    qm = QuantumManagerDensity()

    # single state
    key = qm.new()
    circuit = DumbCircuit(1, np.array([[0, 1], [1, 0]]))
    qm.run_circuit(circuit, [key])
    desired_state = np.array([[0, 0],
                              [0, 1]])
    assert np.array_equal(qm.get(key).state, desired_state)

    # two states
    key1 = qm.new()
    key2 = qm.new()
    circuit = DumbCircuit(2, np.identity(4))
    qm.run_circuit(circuit, [key1, key2])
    desired_state = np.array([[1, 0, 0, 0],
                              [0, 0, 0, 0],
                              [0, 0, 0, 0],
                              [0, 0, 0, 0]])
    assert qm.get(key1) is qm.get(key2)
    assert np.array_equal(qm.get(key1).state, desired_state)

    # two states, wrong order
    qm.run_circuit(circuit, [key2, key1])
    assert qm.get(key1) is qm.get(key2)
    assert np.array_equal(qm.get(key1).state, desired_state)
    assert qm.get(key1).keys == [key2, key1]

    # single state in multi-qubit system
    key1 = qm.new()
    key2 = qm.new()
    circuit1 = DumbCircuit(2, np.identity(4))
    qm.run_circuit(circuit1, [key1, key2])
    circuit2 = DumbCircuit(1, np.array([[0, 1], [1, 0]]))
    qm.run_circuit(circuit2, [key1])
    desired_state = np.array([[0, 0, 0, 0],
                              [0, 0, 0, 0],
                              [0, 0, 1, 0],
                              [0, 0, 0, 0]])
    assert np.array_equal(qm.get(key1).state, desired_state)
    assert (qm.get(key1) is qm.get(key2))

    # extension of circuit
    key1 = qm.new()
    key2 = qm.new()

    input_ket = [0.5**0.5, 0.5**0.5, 0, 0]
    input_dense = np.outer(input_ket, input_ket).tolist()

    qm.set([key1, key2], input_dense)
    circuit1 = Circuit(1)
    circuit1.x(0)
    qm.run_circuit(circuit1, [key2])
    density1 = qm.get(key1)
    reversal = np.array([[1, 0, 0, 0],
                         [0, 0, 1, 0],
                         [0, 1, 0, 0],
                         [0, 0, 0, 1]])
    if density1.keys[0] > density1.keys[1]:
        density1.keys.reverse()
        density1.state = reversal @ density1.state @ reversal.T

    key3 = qm.new()
    key4 = qm.new()
    qm.set([key3, key4], input_dense)
    circuit2 = Circuit(2)
    circuit2.x(1)
    qm.run_circuit(circuit2, [key3, key4])

    density2 = qm.get(key3)
    if density2.keys[0] > density2.keys[1]:
        density2.keys.reverse()
        density2.state = reversal @ density2.state @ reversal.T

    assert np.array_equal(density1.state, density2.state)


def test_qmanager__measure():
    NUM_TESTS = 1000

    qm = QuantumManagerKet()

    # single state
    meas_0 = []
    meas_1 = []
    state = [math.sqrt(1/2), math.sqrt(1/2)]
    for _ in range(NUM_TESTS):
        key = qm.new()
        samp = np.random.random()
        res = qm._measure(state, [key], [key], samp)
        if res[key]:
            meas_1.append(key)
        else:
            meas_0.append(key)
    
    assert abs((len(meas_0) / NUM_TESTS) - 0.5) < 0.1
    for key in meas_0:
        assert np.all(qm.get(key).state == np.array([1, 0]))
    for key in meas_1:
        assert np.all(qm.get(key).state == np.array([0, 1]))

    # single state in multi-qubit system
    meas_0 = []
    meas_1 = []
    for _ in range(NUM_TESTS):
        key1 = qm.new(state)
        key2 = qm.new()
        samp = np.random.random()
        # compound
        circuit = Circuit(2)
        circuit.measure(0)
        res = qm.run_circuit(circuit, [key1, key2], samp)
        if res[key1]:
            meas_1.append(key1)
        else:
            meas_0.append(key1)

    assert abs((len(meas_0) / NUM_TESTS) - 0.5) < 0.1
    for key in meas_0:
        assert np.all(qm.get(key).state == np.array([1, 0]))
    for key in meas_1:
        assert np.all(qm.get(key).state == np.array([0, 1]))

    # multiple state
    meas_0 = []
    meas_2 = []
    for _ in range(NUM_TESTS):
        key1 = qm.new(state)
        key2 = qm.new()
        samp = np.random.random()
        # compound
        circuit = Circuit(2)
        circuit.measure(0)
        circuit.measure(1)
        res = qm.run_circuit(circuit, [key1, key2], samp)
        if res[key1]:
            meas_2.append(key1)
        else:
            meas_0.append(key1)
        assert res[key2] == 0

    assert abs((len(meas_0) / NUM_TESTS) - 0.5) < 0.1


def test_qmanager__measure_density():
    NUM_TESTS = 1000

    qm = QuantumManagerDensity()

    # single state
    meas_0 = []
    meas_1 = []
    state_single = [math.sqrt(1/2), math.sqrt(1/2)]
    state = np.outer(state_single, state_single)
    for _ in range(NUM_TESTS):
        key = qm.new()
        samp = np.random.random()
        res = qm._measure(state, [key], [key], samp)
        if res[key]:
            meas_1.append(key)
        else:
            meas_0.append(key)
    
    assert abs((len(meas_0) / NUM_TESTS) - 0.5) < 0.1
    for key in meas_0:
        assert np.all(qm.get(key).state == np.array([[1, 0], [0, 0]]))
    for key in meas_1:
        assert np.all(qm.get(key).state == np.array([[0, 0], [0, 1]]))

    # mixed state
    meas_0 = []
    meas_1 = []
    state = [[0.5, 0], [0, 0.5]]
    for _ in range(NUM_TESTS):
        key = qm.new()
        samp = np.random.random()
        res = qm._measure(state, [key], [key], samp)
        if res[key]:
            meas_1.append(key)
        else:
            meas_0.append(key)
    
    assert abs((len(meas_0) / NUM_TESTS) - 0.5) < 0.1

    # single state in multi-qubit system
    meas_0 = []
    meas_1 = []
    for _ in range(NUM_TESTS):
        key1 = qm.new(state)
        key2 = qm.new()
        samp = np.random.random()
        # compound
        circuit = Circuit(2)
        circuit.measure(0)
        res = qm.run_circuit(circuit, [key1, key2], samp)
        if res[key1]:
            meas_1.append(key1)
        else:
            meas_0.append(key1)

    assert abs((len(meas_0) / NUM_TESTS) - 0.5) < 0.1

    # multiple state
    meas_0 = []
    meas_2 = []
    for _ in range(NUM_TESTS):
        key1 = qm.new(state)
        key2 = qm.new()
        samp = np.random.random()
        # compound
        circuit = Circuit(2)
        circuit.measure(0)
        circuit.measure(1)
        res = qm.run_circuit(circuit, [key1, key2], samp)
        if res[key1]:
            meas_2.append(key1)
        else:
            meas_0.append(key1)
        assert res[key2] == 0

    assert abs((len(meas_0) / NUM_TESTS) - 0.5) < 0.1


def test_qmanager__prepare_state_fock():
    qm = QuantumManagerDensityFock(truncation=2)
    state_0 = [1, 0, 0]
    state_1 = [0, 1, 0]
    combined = np.kron(state_0, state_1)
    desired_state = np.outer(combined, combined.conj())

    # test single state
    key_0 = qm.new()
    key_1 = qm.new()
    qm.set([key_0, key_1], combined)

    new_state, all_keys = qm._prepare_state([key_0, key_1])
    assert np.all(new_state == np.array(desired_state))
    assert np.all(np.array(all_keys) == np.array([key_0, key_1]))

    # test disjoint state
    key_0 = qm.new(state_0)
    key_1 = qm.new(state_1)

    new_state, all_keys = qm._prepare_state([key_0, key_1])
    assert np.all(new_state == np.array(desired_state))
    assert np.all(np.array(all_keys) == np.array([key_0, key_1]))

    # test state that needs swapping
    key_1 = qm.new()
    key_0 = qm.new()
    combined_2 = np.kron(state_1, state_0)
    qm.set([key_1, key_0], combined_2)

    new_state, all_keys = qm._prepare_state([key_0, key_1])
    assert np.all(new_state == np.array(desired_state))
    assert np.all(np.array(all_keys) == np.array([key_0, key_1]))

    # test larger state that needs swapping
    key_0 = qm.new()
    key_1 = qm.new()
    key_2 = qm.new()
    combined_3 = np.kron(np.kron(state_0, state_0), state_1)
    qm.set([key_0, key_1, key_2], combined_3)

    combined_correct = np.kron(np.kron(state_0, state_1), state_0)
    desired_state_alt = np.outer(combined_correct, combined_correct.conj())
    new_state, all_keys = qm._prepare_state([key_0, key_2])
    assert np.all(new_state == np.array(desired_state_alt))
    assert np.all(np.array(all_keys) == np.array([key_0, key_2, key_1]))


def test_qmanager_build_ladder_fock():
    TRUNCATION = 2

    qm = QuantumManagerDensityFock(truncation=TRUNCATION)
    create, destroy = qm.build_ladder()

    # check dims
    assert len(create.shape) == 2
    assert len(destroy.shape) == 2
    assert create.shape[0] == create.shape[1] == TRUNCATION + 1
    assert destroy.shape[0] == destroy.shape[1] == TRUNCATION + 1

    # check properties
    state = [0] * (TRUNCATION + 1)
    state[-1] = 1
    state = array(state)
    state_create = create @ state
    assert all(state_create == 0)

    state = [0] * (TRUNCATION + 1)
    state[0] = 1
    state = array(state)
    state_destroy = destroy @ state
    assert all(state_destroy == 0)

    for i in range(TRUNCATION):
        state = [0] * (TRUNCATION + 1)
        state[i] = 1
        state = array(state)

        state_create = create @ state
        assert state_create[i+1] == sqrt(i+1)
        assert sum(state_create) == sqrt(i+1)

    for i in range(TRUNCATION):
        state = [0] * (TRUNCATION + 1)
        state[i+1] = 1
        state = array(state)

        state_destroy = destroy @ state
        assert state_destroy[i] == sqrt(i+1)
        assert sum(state_destroy) == sqrt(i+1)


def test_qmanager_apply_operator_fock():
    TRUNCATION = 2

    qm = QuantumManagerDensityFock(truncation=2)
    create, destroy = qm.build_ladder()
    excited = np.zeros((TRUNCATION + 1, TRUNCATION + 1))
    excited[1, 1] = 1

    # single state
    key = qm.new()
    qm.apply_operator(create, [key])
    new_state = qm.get(key)
    assert np.all(new_state.state == excited)

    # compound state
    key1 = qm.new()
    key2 = qm.new()
    oper = np.eye((TRUNCATION + 1) ** 2)
    qm.apply_operator(oper, [key1, key2])
    qm.apply_operator(create, [key1])
    new_state = qm.get(key1)

    desired2 = np.zeros((TRUNCATION + 1, TRUNCATION + 1))
    desired2[0, 0] = 1
    desired = np.kron(excited, desired2)
    assert np.all(new_state.state == desired)

    # comound operator
    key1 = qm.new()
    key2 = qm.new()
    oper = np.kron(create, create)
    qm.apply_operator(oper, [key1, key2])
    new_state = qm.get(key1)

    desired = np.kron(excited, excited)
    assert np.all(new_state.state == desired)


def test_qmanager_measure_fock():
    NUM_TESTS = 1000
    TRUNCATION = 2

    qm = QuantumManagerDensityFock(truncation=2)
    create, destroy = qm.build_ladder()
    series_elem_list = [((-1) ** i) * fractional_matrix_power(create, i + 1).dot(
        fractional_matrix_power(destroy, i + 1)) / math.factorial(i + 1) for i in range(TRUNCATION)]
    povm1 = sum(series_elem_list)
    povm0 = eye(TRUNCATION + 1) - povm1

    # single state
    meas_0 = []
    meas_1 = []
    state_single = [math.sqrt(1 / 2), math.sqrt(1 / 2), 0]
    state = np.outer(state_single, state_single)
    for _ in range(NUM_TESTS):
        key = qm.new(state)
        samp = np.random.random()
        res = qm.measure([key], [povm0, povm1], samp)
        if res:
            meas_1.append(key)
        else:
            meas_0.append(key)

    assert abs((len(meas_0) / NUM_TESTS) - 0.5) < 0.1
    for key in meas_0:
        assert qm.states[key] is None
    for key in meas_1:
        assert qm.states[key] is None

    # single state in multi-qubit system
    meas_0 = []
    meas_1 = []
    for _ in range(NUM_TESTS):
        key1 = qm.new(state)
        key2 = qm.new()
        samp = np.random.random()
        # compound
        oper = np.identity((TRUNCATION + 1) ** 2)
        qm.apply_operator(oper, [key1, key2])
        res = qm.measure([key1], [povm0, povm1], samp)
        if res:
            meas_1.append(key2)
        else:
            meas_0.append(key2)

    assert abs((len(meas_0) / NUM_TESTS) - 0.5) < 0.1

    desired = [0] * (TRUNCATION + 1)
    desired[0] = 1
    desired_density = np.outer(desired, desired)
    for key in meas_0:
        assert np.all(qm.get(key).state == desired_density)
    for key in meas_1:
        assert np.all(qm.get(key).state == desired_density)

    # multiple state
    povm00 = np.kron(povm0, povm0)
    povm01 = np.kron(povm0, povm1)
    povm10 = np.kron(povm1, povm0)
    povm11 = np.kron(povm1, povm1)
    meas_0 = []
    meas_2 = []
    for _ in range(NUM_TESTS):
        key1 = qm.new(state)
        key2 = qm.new()
        samp = np.random.random()
        # compound
        oper = np.identity((TRUNCATION + 1) ** 2)
        qm.apply_operator(oper, [key1, key2])
        res = qm.measure([key1, key2], [povm00, povm01, povm10, povm11], samp)
        if res == 2:
            meas_2.append(key1)
        elif res == 0:
            meas_0.append(key1)
        else:
            raise Exception()

    assert abs((len(meas_0) / NUM_TESTS) - 0.5) < 0.1
