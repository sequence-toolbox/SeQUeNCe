from enum import Enum, auto
from socket import socket
import argparse
from ipaddress import ip_address
from pickle import loads, dumps
import multiprocessing


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


class QuantumManagerMessage():
    def __init__(self, type:QuantumManagerMsgType, args:'List[Any]'):
        self.type = type
        self.args = args

    def __repr__(self):
        return str(self.type) + ' ' + str(self.args)


def start_session(comm:socket):
    while 1:
        data = comm.recv(1024)
        msg = loads(data)

        if msg.type == QuantumManagerMsgType.CLOSE:
            comm.close()
            break

        print(msg.type, msg.args)
        # todo: logic of quantum manager



if __name__ == '__main__':
    parser = generate_arg_parser()
    args = parser.parse_args()

    s = socket()
    s.bind((args.ip, args.port))
    s.listen()
    processes = []
    while 1:
        c, addr = s.accept()

        raw_msg = c.recv(1024)
        msg = loads(raw_msg)
        print(msg.type, QuantumManagerMsgType.CONNECT, type(msg.type), type(QuantumManagerMsgType.CONNECT), msg.type is QuantumManagerMsgType.CONNECT )
        if msg.type == QuantumManagerMsgType.TERMINATE:
            break
        elif msg.type == QuantumManagerMsgType.CONNECT:
            process = multiprocessing.Process(target=start_session, args=(c,))
            processes.append(process)
            process.start()
        else:
            raise Exception('Unknown message type received by quantum manager server')

    for p in processes:
        p.terminate()