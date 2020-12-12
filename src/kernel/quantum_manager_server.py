from copy import copy
from enum import Enum, auto
import socket
import argparse
from ipaddress import ip_address
from pickle import loads, dumps
import multiprocessing
import threading

from sequence.kernel.p_quantum_manager import ParallelQuantumManagerKet
from sequence.kernel.quantum_manager import QuantumManagerKet


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


class QuantumManagerMsgType():
    NEW = 0
    GET = 1
    SET = 2
    RUN = 3
    REMOVE = 4
    CLOSE = 5
    CONNECT = 6
    TERMINATE = 7
    CONNECTED = 8


class QuantumManagerMessage():
    def __init__(self, type:QuantumManagerMsgType, args:'List[Any]'):
        self.type = type
        self.args = args

    def __repr__(self):
        return str(self.type) + ' ' + str(self.args)


def start_session(comm: socket, states, least_available):
    qm = ParallelQuantumManagerKet(states, least_available)

    # send connected message
    msg = QuantumManagerMessage(QuantumManagerMsgType.CONNECTED, [])
    data = dumps(msg)
    comm.sendall(data)

    while True:
        data = comm.recv(1024)
        msg = loads(data)
        return_val = None

        if msg.type == QuantumManagerMsgType.CLOSE:
            comm.close()
            break

        elif msg.type == QuantumManagerMsgType.NEW:
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


def start_server(ip, port):
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((ip, port))
    s.listen()
    processes = []

    # initialize shared data
    _least_available = multiprocessing.Value('i', 0)
    manager = multiprocessing.Manager()
    states = manager.dict()

    while True:
        c, addr = s.accept()

        raw_msg = c.recv(1024)
        msg = loads(raw_msg)

        if msg.type == QuantumManagerMsgType.TERMINATE:
            break

        elif msg.type == QuantumManagerMsgType.CONNECT:
            process = multiprocessing.Process(target=start_session, args=(c, states, _least_available))
            processes.append(process)
            process.start()

        else:
            raise Exception('Unknown message type received by quantum manager server')

    for p in processes:
        p.terminate()


if __name__ == '__main__':
    parser = generate_arg_parser()
    args = parser.parse_args()

    start_server(args.ip, args.port)

