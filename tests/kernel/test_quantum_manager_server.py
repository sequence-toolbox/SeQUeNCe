import multiprocessing
from pickle import loads, dumps
from  unittest.mock import Mock
import numpy as np

from sequence.kernel.quantum_manager import KetState
from sequence.kernel.quantum_manager_server import *


def setup_environment():
    least_available = multiprocessing.Value('i', 0)
    manager = multiprocessing.Manager()
    states = manager.dict()

    return states, least_available


def close():
    msg = QuantumManagerMessage(QuantumManagerMsgType.CLOSE, [])
    data = dumps(msg)
    return data


def test_new():
    # create new message
    msg = QuantumManagerMessage(QuantumManagerMsgType.NEW, [])
    data = dumps(msg)

    # setup environ
    states, least_available = setup_environment()

    # create dummy socket
    s = Mock()
    s.recv.side_effect = [data, close()]

    # run
    start_session(s, states, least_available)

    # get key
    key_data = s.mock_calls[-3][1][0]
    key = loads(key_data)

    assert least_available.value > 0
    assert key == 0


def test_get():
    # create messages
    msg1 = QuantumManagerMessage(QuantumManagerMsgType.NEW, [])
    msg2 = QuantumManagerMessage(QuantumManagerMsgType.GET, [0]) 
    data1 = dumps(msg1)
    data2 = dumps(msg2)

    # setup environ
    states, least_available = setup_environment()

    # create dummy socket
    s = Mock()
    s.recv.side_effect = [data1, data2, close()]

    # run
    start_session(s, states, least_available)

    # get state
    state_data = s.mock_calls[-3][1][0]
    state = loads(state_data)

    assert type(state) is KetState


def test_set():
    desired_state = [complex(0), complex(1)]

    # create messages
    msg1 = QuantumManagerMessage(QuantumManagerMsgType.NEW, [])
    msg2 = QuantumManagerMessage(QuantumManagerMsgType.SET, [[0], desired_state])
    msg3 = QuantumManagerMessage(QuantumManagerMsgType.GET, [0])
    data1 = dumps(msg1)
    data2 = dumps(msg2)
    data3 = dumps(msg3)

    # setup environ
    states, least_available = setup_environment()

    # create dummy socket
    s = Mock()
    s.recv.side_effect = [data1, data2, data3, close()]

    # run
    start_session(s, states, least_available)

    # get state
    state_data = s.mock_calls[-3][1][0]
    state = loads(state_data)

    assert type(state) is KetState
    assert np.array_equal(state.state, np.array(desired_state))


def test_remove():
    # create messages
    msg1 = QuantumManagerMessage(QuantumManagerMsgType.NEW, [])
    msg2 = QuantumManagerMessage(QuantumManagerMsgType.REMOVE, [0])
    data1 = dumps(msg1)
    data2 = dumps(msg2)

    # setup environ
    states, least_available = setup_environment()

    # create dummy socket
    s = Mock()
    s.recv.side_effect = [data1, data2, close()]

    # run
    start_session(s, states, least_available)

    assert not states

