import multiprocessing
from pickle import loads, dumps
from  unittest.mock import Mock
import numpy as np
import time

from sequence.kernel.quantum_manager import KetState
from sequence.kernel.p_quantum_manager import *
from sequence.kernel.quantum_manager_server import *


def setup_environment():
    least_available = multiprocessing.Value('i', 0)
    manager = multiprocessing.Manager()
    states = manager.dict()
    locks = manager.dict()

    return states, least_available, locks, manager


def test_new():
    # create new message
    msg = QuantumManagerMessage(QuantumManagerMsgType.NEW, [])

    # setup environment
    args = setup_environment()

    # create dummy socket
    s = Mock()

    # run
    service_request(s, "KET", *args, msg)

    # get key
    key_data = s.mock_calls[0][1][0]
    key = loads(key_data)

    assert args[1].value > 0
    assert key == 0


def test_get():
    # create messages
    msg1 = QuantumManagerMessage(QuantumManagerMsgType.NEW, [])
    msg2 = QuantumManagerMessage(QuantumManagerMsgType.GET, [0]) 

    # setup environment
    args = setup_environment()

    # create dummy socket
    s = Mock()

    # run
    for msg in [msg1, msg2]:
        service_request(s, "KET", *args, msg)

    # get state
    state_data = s.mock_calls[2][1][0]
    state = loads(state_data)

    assert type(state) is KetState


def test_set():
    desired_state = [complex(0), complex(1)]

    # create messages
    msg1 = QuantumManagerMessage(QuantumManagerMsgType.NEW, [])
    msg2 = QuantumManagerMessage(QuantumManagerMsgType.SET, [[0], desired_state])
    msg3 = QuantumManagerMessage(QuantumManagerMsgType.GET, [0])

    # setup environ
    args = setup_environment()

    # create dummy socket
    s = Mock()

    # run
    for msg in [msg1, msg2, msg3]:
        service_request(s, "KET", *args, msg)

    # get state
    state_data = s.mock_calls[4][1][0]
    state = loads(state_data)

    assert type(state) is KetState
    assert np.array_equal(state.state, np.array(desired_state))


def test_remove():
    # create messages
    msg1 = QuantumManagerMessage(QuantumManagerMsgType.NEW, [])
    msg2 = QuantumManagerMessage(QuantumManagerMsgType.REMOVE, [0])

    # setup environ
    args = setup_environment()

    # create dummy socket
    s = Mock()

    # run
    for msg in [msg1, msg2]:
        service_request(s, "KET", *args, msg)

    assert not args[0]


def test_kill_func():
    host = socket.gethostbyname('localhost')
    port = 65432

    p = multiprocessing.Process(target=start_server, args=(host, port))
    p.start()
    time.sleep(1)
    kill_server(host, port)
    time.sleep(1)

    is_done = not p.is_alive()
    p.terminate()  # just in case server hasn't terminated
    assert is_done

