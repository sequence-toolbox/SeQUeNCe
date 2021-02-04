from enum import Enum, auto
import socket
import argparse
from ipaddress import ip_address
from pickle import loads, dumps
import multiprocessing
from typing import List
from time import time

from .p_quantum_manager import ParallelQuantumManagerKet, \
    ParallelQuantumManagerDensity


def valid_port(port):
    port = int(port)
    if 1 <= port <= 65535:
        return port
    else:
        raise argparse.ArgumentTypeError('%d is not a valid port number' % port)


def valid_ip(ip):
    _ip = ip_address(ip)
    return ip


def generate_arg_parser():
    parser = argparse.ArgumentParser(description='The server of quantum manager')
    parser.add_argument('ip', type=valid_ip, help='listening IP address')
    parser.add_argument('port', type=valid_port, help='listening port number')
    return parser


class QuantumManagerMsgType(Enum):
    NEW = 0
    GET = 1
    SET = 2
    RUN = 3
    REMOVE = 4
    TERMINATE = 5


class QuantumManagerMessage():
    """Message for quantum manager communication.

    Attributes:
        type (Enum): type of message.
        keys (List[int]): list of ALL keys serviced by request; used to acquire/set shared locks.
        args (List[any]): list of other arguments for request
    """

    def __init__(self, msg_type: QuantumManagerMsgType, keys: 'List[int]', args: 'List[Any]'):
        self.type = msg_type
        self.keys = keys
        self.args = args

    def __repr__(self):
        return str(self.type) + ' ' + str(self.args)


def start_session(formalism: str, msg: QuantumManagerMessage,
                  all_keys: List[int], comm: socket, states,
                  least_available, locks, manager, locations):
    # TODO: does not need all states and managers;
    # we could copy part of state to the manager and update the global manager
    # after operations

    local_states = {k: states[k] for k in all_keys}

    if formalism == "KET":
        qm = ParallelQuantumManagerKet(local_states, least_available)
    elif formalism == "DENSITY":
        qm = ParallelQuantumManagerDensity(local_states, least_available)

    return_val = None

    if msg.type == QuantumManagerMsgType.NEW:
        assert len(msg.args) == 2
        state, location = msg.args
        return_val = qm.new(state)
        locks[return_val] = manager.Lock()
        locations[return_val] = location

    elif msg.type == QuantumManagerMsgType.GET:
        assert len(msg.args) == 0
        return_val = qm.get(msg.keys[0])

    elif msg.type == QuantumManagerMsgType.RUN:
        assert len(msg.args) == 2
        circuit, keys = msg.args
        return_val = qm.run_circuit(circuit, keys)
        if len(return_val) == 0:
            return_val = None

    elif msg.type == QuantumManagerMsgType.SET:
        assert len(msg.args) == 1
        amplitudes = msg.args[0]
        qm.set(msg.keys, amplitudes)

    elif msg.type == QuantumManagerMsgType.REMOVE:
        assert len(msg.keys) == 1
        assert len(msg.args) == 0
        key = msg.keys[0]
        del states[key]
        del locks[key]
        del locations[key]

    else:
        raise Exception(
            "Quantum manager session received invalid message type {}".format(
                msg.type))

    # release all locks
    if msg.type != QuantumManagerMsgType.REMOVE:
        states.update(local_states)
        for key in all_keys:
            locks[key].release()

    # send return value
    if return_val is not None:
        data = dumps(return_val)
        comm.sendall(data)

    comm.close()


def start_server(ip, port, formalism="KET"):
    lock_time = 0

    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((ip, port))
    s.listen()
    processes = []
    print("connected:", ip, port)

    # initialize shared data
    least_available = multiprocessing.Value('i', 0)
    manager = multiprocessing.Manager()
    states = manager.dict()
    locks = manager.dict()
    locations = manager.dict()

    while True:
        c, addr = s.accept()
        raw_msg = c.recv(1024)
        msg = loads(raw_msg)

        all_keys = set()
        for key in msg.keys:
            state = states[key]
            for k in state.keys:
                all_keys.add(k)

        tick = time()
        for key in all_keys:
            locks[key].acquire()
        lock_time += time() - tick

        if msg.type == QuantumManagerMsgType.TERMINATE:
            break
        else:
            args = (
                formalism, msg, all_keys, c, states, least_available, locks,
                manager, locations)
            process = multiprocessing.Process(target=start_session, args=args)
            # processes.append(process)
            process.start()

    with open("server.log", "w") as fh:
        fh.write("lock_time: {}\n".format(lock_time))

    # for p in processes:
    #     p.terminate()

def kill_server(ip, port):
    s = socket.socket()
    s.connect((ip, port))
    msg = QuantumManagerMessage(QuantumManagerMsgType.TERMINATE, [], [])
    data = dumps(msg)
    s.sendall(data)

