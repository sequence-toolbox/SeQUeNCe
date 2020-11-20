from socket import socket
import argparse
from ipaddress import ip_address
from pickle import loads, dumps

from quantum_manager_server import valid_port, valid_ip, generate_arg_parser, QuantumManagerMsgType, QuantumManagerMessage
from sequence.components.circuit import Circuit


if __name__ == '__main__':
    parser = generate_arg_parser()
    args = parser.parse_args()

    # create socket to connect to quantum manager server
    s = socket()
    s.connect((args.ip, args.port))

    # send connect message
    msg = QuantumManagerMessage(QuantumManagerMsgType.CONNECT, [])
    data = dumps(msg)
    s.sendall(data)

    data = s.recv(1024)
    msg = loads(data)
    assert msg.type == QuantumManagerMsgType.CONNECTED

    # send request for new state
    msg = QuantumManagerMessage(QuantumManagerMsgType.NEW, [])
    data = dumps(msg)
    s.sendall(data)

    data = s.recv(1024)
    key = loads(data)

    # send request to get state
    msg = QuantumManagerMessage(QuantumManagerMsgType.GET, [key])
    data = dumps(msg)
    s.sendall(data)

    data = s.recv(1024)
    ket_vec = loads(data)
    print("|0> state:", ket_vec.state)

    # apply hadamard gate
    circ = Circuit(1)
    circ.h(0)
    msg = QuantumManagerMessage(QuantumManagerMsgType.RUN, [circ, [key]])
    data = dumps(msg)
    s.sendall(data)
    _ = s.recv(1024) # wait for circuit to run

    msg = QuantumManagerMessage(QuantumManagerMsgType.GET, [key])
    data = dumps(msg)
    s.sendall(data)

    data = s.recv(1024)
    ket_vec = loads(data)
    print("|+> state:", ket_vec.state)

