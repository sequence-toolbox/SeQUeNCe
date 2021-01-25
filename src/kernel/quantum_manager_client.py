from collections import defaultdict
from socket import socket
from pickle import loads, dumps
from typing import List
from time import time
from mpi4py import MPI

from .quantum_manager import QuantumManagerKet, QuantumManagerDensity
from .quantum_manager_server import generate_arg_parser, QuantumManagerMsgType, QuantumManagerMessage
from ..components.circuit import Circuit


class QuantumManagerClient():
    """Class to pocess interactions with multiprocessing quantum manager server.

    Unless otherwise noted, the operation of all functions are the same as those of the QuantumManagerClass.

    Attributes:
        s (socket): socket for communication with server.
        connected (bool): denotes if client has been properly connected with remote server.
    """

    def __init__(self, formalism: str, ip: str, port: int):
        """Constructor for QuantumManagerClient class.

        Args:
            ip: ip of quantum manager server.
            port: port of quantum manager server.
        """
        self.formalism = formalism
        self.ip = ip
        self.port = port
        self.managed_qubits = set()
        self.io_time = defaultdict(lambda: 0)
        self.type_counter = defaultdict(lambda: 0)

        # local quantum manager
        if formalism == "KET":
            self.qm = QuantumManagerKet()

        elif formalism == "DENSITY":
            self.qm = QuantumManagerDensity()

        else:
            raise Exception(
                "Invalid formalim {} given; should be 'KET' or 'DENSITY'".format(
                    formalism))

    def get_socket_to_server(self) -> "socket":
        s = socket()
        s.connect((self.ip, self.port))
        return s

    def init(self) -> None:
        """Method to configure client connection.

        Must be called before any other methods are used.

        Side Effects:
            Will set the `connected` attribute to True.
        """

        msg = self._send_message(QuantumManagerMsgType.CONNECT, [])
        assert msg.type == QuantumManagerMsgType.CONNECTED, "QuantumManagerClient failed connection."
        self.connected = True

    def new(self, state=(complex(1), complex(0))) -> int:
        """Method to get a new state from server.

        Args:
            state (List): if None, state will be in default state. Otherwise, must match formalism of server.

        Returns:
            int: key for the new state generated.
        """
        # self._check_connection()

        args = [state, MPI.COMM_WORLD.Get_rank()]
        key = self._send_message(QuantumManagerMsgType.NEW, args)
        self.qm.set([key], state)
        self.move_manage_to_client(key)
        return key

    def get(self, key: int) -> any:
        if self._check_local([key]):
            return self.qm.get(key)
        else:
            state = self._send_message(QuantumManagerMsgType.GET, [key])
            return state

    def run_circuit(self, circuit: "Circuit", keys: List[int]) -> any:
        if self._check_local(keys):
            return self.qm.run_circuit(circuit, keys)
        else:
            updated_qubits = []
            visited_qubits = set()
            for key in keys:
                if self.is_managed_by_server(key) or key in visited_qubits:
                    continue
                state = self.qm.get(key)
                for state_key in state.keys:
                    visited_qubits.add(state_key)
                    assert not self.is_managed_by_server(state_key)
                    self.move_manage_to_server(state_key)
                updated_qubits.append(state)

            ret_val = self._send_message(QuantumManagerMsgType.RUN,
                                         [updated_qubits, circuit, keys])
            for measured_q in ret_val:
                self.move_manage_to_client(measured_q)
                if ret_val[measured_q] == 1:
                    self.qm.set_to_one(measured_q)
                else:
                    self.qm.set_to_zero(measured_q)
            return ret_val

    def set(self, keys: List[int], amplitudes: any) -> None:
        if self._check_local(keys):
            self.qm.set(keys, amplitudes)
        else:
            raise NotImplementedError()

        # self._check_connection()
        # self._send_message(QuantumManagerMsgType.SET, [keys, amplitudes])

    def remove(self, key: int) -> None:
        self._check_connection()
        self._send_message(QuantumManagerMsgType.REMOVE, [key])
        self.qm.remove(key)

    def close(self) -> None:
        """Method to close communication with server.

        Side Effects:
            Will set the `connected` attribute to False
        """

        self._check_connection()
        self._send_message(QuantumManagerMsgType.CLOSE, [], expecting_receive=False)
        self.connected = False

    def kill(self) -> None:
        """Method to terminate the connected server.

        Side Effects:
            Will end all processes of remote server.
            Will set the `connected` attribute to False.
        """
        self._check_connection()
        self._send_message(QuantumManagerMsgType.TERMINATE, [],
                           expecting_receive=False)
        self.connected = False

    def is_managed_by_server(self, qubit_key: int) -> bool:
        return not qubit_key in self.managed_qubits

    def move_manage_to_server(self, qubit_key: int):
        self.managed_qubits.remove(qubit_key)

    def move_manage_to_client(self, qubit_key: int):
        self.managed_qubits.add(qubit_key)

    def _check_connection(self):
        assert self.connected, "must run init method before attempting communications"

    def _send_message(self, msg_type, args: List,
                      expecting_receive=True) -> any:
        self.type_counter[msg_type.name] += 1
        tick = time()

        msg = QuantumManagerMessage(msg_type, args)
        data = dumps(msg)
        s = self.get_socket_to_server()
        s.sendall(data)

        if expecting_receive:
            received_data = s.recv(1024)
            s.close()
            received_msg = loads(received_data)
            self.io_time[msg_type.name] += time() - tick
            return received_msg

        self.io_time[msg_type.name] += time() - tick
        s.close()

    def _check_local(self, keys: List[int]):
        return not any([self.is_managed_by_server(key) for key in keys])


if __name__ == '__main__':
    parser = generate_arg_parser()
    args = parser.parse_args()

    client = QuantumManagerClient(args.ip, args.port)
    client.init()

    # send request for new state
    key = client.new()

    # send request to get state
    ket_vec = client.get(key)
    print("|0> state:", ket_vec.state)

    # run Hadamard gate
    circ = Circuit(1)
    circ.h(0)
    client.run_circuit(circ, [key])

    ket_vec = client.get(key)
    print("|+> state:", ket_vec.state)

