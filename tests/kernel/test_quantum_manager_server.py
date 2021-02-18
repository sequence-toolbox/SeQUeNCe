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
    locks = manager.dict()
    locations = manager.dict()

    return states, least_available, locks, manager, locations


def new_state():
    return [complex(1), complex(0)]


def test_new():
    # create new message
    msg = QuantumManagerMessage(QuantumManagerMsgType.NEW, [], [new_state(), 0])

    # setup environment
    environment = setup_environment()

    # create dummy socket
    s = Mock()

    all_keys = []
    # run
    start_session("KET", msg, all_keys, s, *environment)

    # get key
    key_data = s.mock_calls[0][1][0]
    key = loads(key_data)

    least_available = environment[1]
    assert least_available.value > 0
    assert key == 0


def test_get():
    # create messages
    msg1 = QuantumManagerMessage(QuantumManagerMsgType.NEW, [], [new_state(), 0])
    msg2 = QuantumManagerMessage(QuantumManagerMsgType.GET, [0], [])

    # setup environ
    environment = setup_environment()

    # create dummy socket
    s = Mock()

    # run
    for msg in [msg1, msg2]:
        locks = environment[2]
        for key in msg.keys:
            locks[key].acquire()
        all_keys = msg.keys
        start_session("KET", msg, all_keys, s, *environment)

    # get state
    state_data = s.mock_calls[2][1][0]
    state = loads(state_data)
    print(type(state_data))

    assert type(state) is KetState


def test_set():
    desired_state = [complex(0), complex(1)]

    # create messages
    msg1 = QuantumManagerMessage(QuantumManagerMsgType.NEW, [],
                                 [new_state(), 0])
    msg2 = QuantumManagerMessage(QuantumManagerMsgType.SET, [0],
                                 [desired_state])
    msg3 = QuantumManagerMessage(QuantumManagerMsgType.GET, [0], [])

    # setup environ
    environment = setup_environment()

    # create dummy socket
    s = Mock()
    # run
    for msg in [msg1, msg2, msg3]:
        locks = environment[2]
        for key in msg.keys:
            locks[key].acquire()
        all_keys = msg.keys
        start_session("KET", msg, all_keys, s, *environment)

    # get state
    print(s.mock_calls)
    state_data = s.mock_calls[3][1][0]
    state = loads(state_data)

    assert type(state) is KetState
    assert np.array_equal(state.state, np.array(desired_state))


def test_remove():
    # create messages
    msg1 = QuantumManagerMessage(QuantumManagerMsgType.NEW, [], [new_state(), 0])
    msg2 = QuantumManagerMessage(QuantumManagerMsgType.REMOVE, [0], [])

    # setup environ
    environment = setup_environment()

    # create dummy socket
    s = Mock()

    # run
    for msg in [msg1, msg2]:
        locks = environment[2]
        for key in msg.keys:
            locks[key].acquire()
        all_keys = msg.keys
        start_session("KET", msg, all_keys, s, *environment)

    states = environment[0]
    assert not states


def test_kill_func():
    from time import sleep

    host = socket.gethostbyname('localhost')
    port = 65432

    p = multiprocessing.Process(target=start_server, args=(host, port))
    p.start()
    sleep(1)
    kill_server(host, port)
    sleep(1)

    is_done = not p.is_alive()
    p.terminate()  # just in case server hasn't terminated
    assert is_done

