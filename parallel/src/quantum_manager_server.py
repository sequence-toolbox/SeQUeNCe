"""This module defines the function to use for the quantum manager server.

This function should be started on a separate process for parallel simulation, \
        using the `mpi_tests/qm_server.py` script or similar.
Additionally defined are utility functions for socket connections and the messages used by the client/server.
"""

from enum import Enum
import socket
import argparse
from ipaddress import ip_address
import select
from typing import List
from time import time
from json import dump
from .communication import send_msg_with_length, recv_msg_with_length
from sequence.components.circuit import Circuit

from .p_quantum_manager import ParallelQuantumManagerKet, ParallelQuantumManagerDensity


def valid_port(port):
    port = int(port)
    if 1 <= port <= 65535:
        return port
    else:
        raise argparse.ArgumentTypeError(
            '%d is not a valid port number' % port)


def valid_ip(ip):
    _ip = ip_address(ip)
    return ip


def generate_arg_parser():
    # TODO: delete?
    parser = argparse.ArgumentParser(description='The server of quantum manager')
    parser.add_argument('ip', type=valid_ip, help='listening IP address')
    parser.add_argument('port', type=valid_port, help='listening port number')
    return parser


class QuantumManagerMsgType(Enum):
    GET = 0
    SET = 1
    RUN = 2
    REMOVE = 3
    TERMINATE = 4
    CLOSE = 5
    CONNECT = 6
    CONNECTED = 7
    SYNC = 8


class QuantumManagerMessage:
    """Message for quantum manager communication.

    Attributes:
        type (Enum): type of message.
        keys (List[int]): list of ALL keys serviced by request.
        args (List[any]): list of other arguments for the request.
    """

    def __init__(self, msg_type: QuantumManagerMsgType, keys: List[int], args: List[any]):
        self.type = msg_type
        self.keys = keys
        self.args = args

    def __repr__(self):
        return str(self.type) + ' ' + str(self.args)

    def serialize(self):
        """Serializes the data stored in the message.

        Returns:
            Dict[str, any]: A dictionary with the following keys:
            - "type": name of the type for the message.
            - "keys": keys for all modified qubits in the quantum state manager, in hex format.
            - "args": JSON-like serialized version of arguments
        """

        hex_keys = [hex(key) for key in self.keys]

        args = {}
        if self.type == QuantumManagerMsgType.SET:
            amplitudes = []
            for cplx_n in self.args[0]:
                if type(cplx_n) == float:
                    amplitudes.append(cplx_n)
                    amplitudes.append(0)
                else:
                    amplitudes.append(cplx_n.real)
                    amplitudes.append(cplx_n.imag)

            args["amplitudes"] = amplitudes

        elif self.type == QuantumManagerMsgType.RUN:
            args["circuit"] = self.args[0].serialize()
            args["keys"] = [hex(key) for key in self.args[1]]
            args["meas_samp"] = -1
            if len(self.args) > 2:
                args["meas_samp"] = self.args[2]

        return {"type": self.type.name, "keys": hex_keys, "args": args}

    def deserialize(self, j_data):
        """Method to reconstruct a message from serialized data.

        Args:
            j_data: serialized QuantumManagerMessage data.
        """

        self.keys = j_data["keys"]

        if j_data["type"] == "GET":
            self.type = QuantumManagerMsgType.GET

        elif j_data["type"] == "SET":
            self.type = QuantumManagerMsgType.SET
            cmplx_n_list = []
            for i in range(0, len(j_data["args"]["amplitudes"]), 2):
                cmplx = complex(j_data["args"]["amplitudes"][i],
                                j_data["args"]["amplitudes"][i + 1])
                cmplx_n_list.append(cmplx)
            self.args = [cmplx_n_list]
        elif j_data["type"] == "RUN":
            self.type = QuantumManagerMsgType.RUN
            # use hex string as key temporarily
            c_raw = j_data["args"]["circuit"]
            circuit = Circuit(1)
            circuit.deserialize(c_raw)
            keys = j_data["args"]["keys"]
            meas_samp = j_data["args"]["meas_samp"]
            self.args = [circuit, keys, meas_samp]

        elif j_data["type"] == "CLOSE":
            self.type = QuantumManagerMsgType.CLOSE
        elif j_data["type"] == "SYNC":
            self.type = QuantumManagerMsgType.SYNC


def start_server(ip: str, port: int, client_num, formalism="KET", log_file="server_log.json"):
    """Main function to run quantum manager server.

    Will run until all clients have disconnected or `TERMINATE` message received.
    Will block processing until all clients connected.

    Args:
        ip (str): ip address server should bind to.
        port (int): port server should bind to.
        client_num (int): number of remote clients that should be connected (one per process).
        formalism (str): formalism to use for quantum manager (default `"KET"` for ket vector).
        log_file (str): output log file to store server information (default `"server_log.json"`).
    """

    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((ip, port))
    s.listen()
    print("listening at:", ip, port)

    timing_comp = {}
    traffic_counter = 0
    msg_counter = 0

    # initialize shared data
    if formalism == "KET":
        qm = ParallelQuantumManagerKet({})
    elif formalism == "DENSITY":
        qm = ParallelQuantumManagerDensity({})

    sockets = []
    for _ in range(client_num):
        c, addr = s.accept()
        sockets.append(c)

    while sockets:
        readable, writeable, exceptional = select.select(sockets, [], [], 1)
        for s in readable:
            msgs = recv_msg_with_length(s)

            traffic_counter += 1
            msg_counter += len(msgs)

            for m_raw in msgs:
                msg = QuantumManagerMessage(None, [], [])
                msg.deserialize(m_raw)
                return_val = None

                tick = time()
                if msg.type == QuantumManagerMsgType.CLOSE:
                    s.close()
                    sockets.remove(s)
                    break

                elif msg.type == QuantumManagerMsgType.GET:
                    assert len(msg.args) == 0
                    state = qm.get(msg.keys[0])
                    return_val = state.serialize()

                elif msg.type == QuantumManagerMsgType.RUN:
                    assert len(msg.args) == 2 or len(msg.args) == 3
                    circuit, keys, meas_samp = msg.args
                    return_val = qm.run_circuit(circuit, keys, meas_samp)
                    if len(return_val) == 0:
                        return_val = None

                elif msg.type == QuantumManagerMsgType.SET:
                    assert len(msg.args) == 1
                    qm.set(msg.keys, msg.args[0])

                elif msg.type == QuantumManagerMsgType.REMOVE:
                    assert len(msg.keys) == 1
                    assert len(msg.args) == 0
                    key = msg.keys[0]
                    qm.remove(key)

                elif msg.type == QuantumManagerMsgType.TERMINATE:
                    for s in sockets:
                        s.close()
                    sockets = []

                elif msg.type == QuantumManagerMsgType.SYNC:
                    return_val = True

                else:
                    raise Exception(
                        "Quantum manager session received invalid message type {}".format(
                            msg.type))

                # send return value
                if return_val is not None:
                    send_msg_with_length(s, return_val)

                if not msg.type in timing_comp:
                    timing_comp[msg.type] = 0
                timing_comp[msg.type] += time() - tick

    # record timing and performance information
    data = {"msg_counter": msg_counter, "traffic_counter": traffic_counter}
    for msg_type in timing_comp:
        data[f"{msg_type.name}_timer"] = timing_comp[msg_type]

    with open(log_file, 'w') as fh:
        dump(data, fh)
