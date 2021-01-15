from copy import copy
from enum import Enum, auto
import socket
import argparse
from ipaddress import ip_address
from pickle import loads, dumps
import multiprocessing
import threading

from sequence.kernel.p_quantum_manager import ParallelQuantumManagerKet, ParallelQuantumManagerDensity
from sequence.kernel.quantum_manager import QuantumManager


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
    def __init__(self, type:QuantumManagerMsgType, args:'List[Any]'):
        self.type = type
        self.args = args

    def __repr__(self):
        return str(self.type) + ' ' + str(self.args)


def service_request(comm: socket, qm: QuantumManager, msg: QuantumManagerMessage): 
    return_val = None

    if msg.type == QuantumManagerMsgType.NEW:
        assert len(msg.args) <= 1
        return_val = qm.new(*msg.args)

    elif msg.type == QuantumManagerMsgType.GET:
        assert len(msg.args) == 1
        return_val = qm.get(*msg.args)

    elif msg.type == QuantumManagerMsgType.SET:
        assert len(msg.args) == 2
        qm.set(*msg.args)

    elif msg.type == QuantumManagerMsgType.RUN:
        assert len(msg.args) == 2
        return_val = qm.run_circuit(*msg.args)

    elif msg.type == QuantumManagerMsgType.REMOVE:
        assert len(msg.args) == 1
        qm.remove(*msg.args)

    else:
        raise Exception("Quantum manager session received invalid message type {}".format(msg.type))

    # send return value
    data = dumps(return_val)
    comm.sendall(data)

    comm.close()


def start_server(ip, port, formalism="KET"):
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((ip, port))
    s.listen()
    print("connected:", ip, port)

    # initialize shared data
    least_available = multiprocessing.Value('i', 0)
    manager = multiprocessing.Manager()
    states = manager.dict()
    locks = manager.dict()

    # create quantum manager
    if formalism == "KET":
        qm = ParallelQuantumManagerKet(states, least_available, locks, manager)
    elif formalism == "DENSITY":
        qm = ParallelQuantumManagerDensity(states, least_available, locks, manager)
    else:
        raise Exception("Invalid quantum manager formalism '{}'".format(formalism))

    while True:
        c, addr = s.accept()

        raw_msg = c.recv(1024)
        msg = loads(raw_msg)

        if msg.type == QuantumManagerMsgType.TERMINATE:
            break

        else:
            process = multiprocessing.Process(target=service_request, args=(c, qm, msg))
            process.start()


def kill_server(ip, port):
    s = socket.socket()
    s.connect((ip, port))
    msg = QuantumManagerMessage(QuantumManagerMsgType.TERMINATE, [])
    data = dumps(msg)
    s.sendall(data)

