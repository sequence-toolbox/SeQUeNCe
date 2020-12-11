from socket import socket
from pickle import loads, dumps
from typing import List

from .quantum_manager_server import generate_arg_parser, QuantumManagerMsgType, \
    QuantumManagerMessage
from ..components.circuit import Circuit


class QuantumManagerClient():
    """Class to pocess interactions with multiprocessing quantum manager server.

    Unless otherwise noted, the operation of all functions are the same as those of the QuantumManagerClass.

    Attributes:
        s (socket): socket for communication with server.
        connected (bool): denotes if client has been properly connected with remote server.
    """

    def __init__(self, ip, port):
        """Constructor for QuantumManagerClient class.

        Args:
            ip: ip of quantum manager server.
            port: port of quantum manager server.
        """

        self.s = socket()
        self.s.connect((ip, port))
        self.connected = True

    def init(self) -> None:
        """Method to configure client connection.

        Must be called before any other methods are used.

        Side Effects:
            Will set the `connected` attribute to True.
        """

        msg = self._send_message(QuantumManagerMsgType.CONNECT, [])
        assert msg.type == QuantumManagerMsgType.CONNECTED, "QuantumManagerClient failed connection."
        self.connected = True

    def new(self, state=None) -> int:
        """Method to get a new state from server.

        Args:
            state (List): if None, state will be in default state. Otherwise, must match formalism of server.

        Returns:
            int: key for the new state generated.
        """
        self._check_connection()

        if state is None:
            args = []
        else:
            args = [state]

        return self._send_message(QuantumManagerMsgType.NEW, args)

    def get(self, key: int) -> any:
        self._check_connection()
        return self._send_message(QuantumManagerMsgType.GET, [key])

    def run_circuit(self, circuit: "Circuit", keys: List[int]) -> any:
        self._check_connection()
        return self._send_message(QuantumManagerMsgType.RUN, [circuit, keys])

    def set(self, keys: List[int], amplitudes: any) -> None:
        self._check_connection()
        self._send_message(QuantumManagerMsgType.SET, [keys, amplitudes])

    def remove(self, key: int) -> None:
        self._check_connection()
        self._send_message(QuantumManagerMsgType.REMOVE, [key])

    def close(self) -> None:
        """Method to close communication with server.

        Side Effects:
            Will set the `connected` attribute to False
        """

        self._check_connection()
        self._send_message(QuantumManagerMsgType.CLOSE, [])
        self.connected = False

    def kill(self) -> None:
        """Method to terminate the connected server.

        Side Effects:
            Will end all processes of remote server.
            Will set the `connected` attribute to False.
        """
        self._check_connection()
        self._send_message(QuantumManagerMsgType.TERMINATE, [])
        self.connected = False

    def _check_connection(self):
        assert self.connected, "must run init method before attempting communications"

    def _send_message(self, msg_type, args: List) -> any:
        msg = QuantumManagerMessage(msg_type, args)
        data = dumps(msg)
        self.s.sendall(data)

        received_data = self.s.recv(1024)
        received_msg = loads(received_data)
        return received_msg


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

