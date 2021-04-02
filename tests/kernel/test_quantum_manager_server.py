import socket
import multiprocessing
import os
from time import sleep
from pickle import loads, dumps
from  unittest.mock import Mock
import numpy as np

from sequence.kernel.quantum_manager import KetState
from sequence.kernel.quantum_manager_server import *
from sequence.kernel.quantum_manager_client import QuantumManagerClient


def get_open_port():
    s = socket.socket()
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_set_get():
    state1 = [complex(1), complex(0)]
    state2 = [complex(1), complex(0), complex(0), complex(0)]

    # setup server/client
    port = get_open_port()
    p = multiprocessing.Process(target=start_server, args=('127.0.0.1', port, 1))
    p.start()
    sleep(1)

    client = QuantumManagerClient("KET", '127.0.0.1', port)

    # single state
    client.set([0], state1)
    assert not client.qm.states
    return_state1 = client.get(0)

    # set and read entangled state
    client.set([0, 1], state2)
    assert not client.qm.states
    return_state2 = client.get(0)

    p.terminate()

    assert type(return_state1) is KetState
    assert type(return_state2) is KetState
    assert np.array_equal(return_state1.state, np.array(state1))
    assert np.array_equal(return_state2.state, np.array(state2))


def test_close_func():
    port = get_open_port()
    p = multiprocessing.Process(target=start_server, args=('127.0.0.1', port, 1))
    p.start()
    sleep(1)

    client = QuantumManagerClient("KET", '127.0.0.1', port)
    client.disconnect_from_server()
    sleep(1)

    is_done = not p.is_alive()
    p.terminate()  # just in case server hasn't terminated
    try:
        os.remove('server_log.json')
    except:
        pass
    assert is_done

