"""This module defines the QuantumManagerClient class.

This client provides the same interface as the QuantumManager class for manipulating qubits.
Qubits only managed by the local process are stored within a QuantumManager class instance.
Qubits managed or accessed between processes are stored on a remote quantum manager server.
"""
from collections import defaultdict
from socket import socket
from typing import List
from time import time
from uuid import uuid4
from sequence.kernel.quantum_manager import QuantumManagerKet, QuantumManagerDensity, KetState, \
    KET_STATE_FORMALISM, DENSITY_MATRIX_FORMALISM
from sequence.components.circuit import Circuit
from .communication import send_msg_with_length, recv_msg_with_length

from .quantum_manager_server import QuantumManagerMsgType, \
    QuantumManagerMessage


class QuantumManagerClient:
    """Class to process interactions with remote quantum manager server.

    Unless otherwise noted, the operation of all functions are the same as those of the QuantumManagerClass.

    Attributes:
        formalism (str): formalism to use for quantum manager (must match server).
        ip (str): ip address of quantum manager server.
        port (int): port of quantum manager server.
        socket (socket): socket for communication with server.
        managed_qubits (set): keys for all qubits managed locally by client.
        message_buffer (List): list of messages to send to quantum manager server.
    """

    def __init__(self, formalism: str, ip: str, port: int):
        """Constructor for QuantumManagerClient class.

        Args:
            formalism (str): formalism to use for quantum manager.
            ip (str): ip of quantum manager server.
            port (int): port of quantum manager server.
        """
        self.formalism = formalism
        self.ip = ip
        self.port = port
        self.socket = socket()
        self.managed_qubits = set()
        self.io_time = 0
        self.type_counter = defaultdict(lambda: 0)
        self.client_call_counter = 0
        self.message_buffer = []

        self.socket.connect((self.ip, self.port))
        self.socket.settimeout(20)

        # local quantum manager
        if formalism == KET_STATE_FORMALISM:
            self.qm = QuantumManagerKet()
        elif formalism == DENSITY_MATRIX_FORMALISM:
            self.qm = QuantumManagerDensity()
        else:
            raise Exception("Invalid formalism {} given".format(formalism))

    def get_socket_to_server(self) -> "socket":
        return self.socket

    def disconnect_from_server(self):
        """Closes socket connection with quantum manager server.

        Uses a message of type `QuantumManagerServer.CLOSE`.

        Side Effects:
            closes socket attribute connection.
        """

        self._send_message(QuantumManagerMsgType.CLOSE, [], [],
                           expecting_receive=False)
        self.flush_message_buffer()

    def new(self, state=(complex(1), complex(0))) -> int:
        """Method to get a new state from server.

        Args:
            state (List): if None, state will be in default state. Otherwise, must match formalism of server.

        Returns:
            int: key for the new state generated.
        """
        self.client_call_counter += 1
        key = uuid4().int
        # below code cannot be removed because of the assertion in the
        # move_manage_to_client function
        self.qm.set([key], state)
        self.move_manage_to_client([key], state)
        return key

    def get(self, key: int) -> any:
        self.client_call_counter += 1
        if self._check_local([key]):
            return self.qm.get(key)
        else:
            state_raw = self._send_message(QuantumManagerMsgType.GET, [key],
                                           [])
            state = KetState([0, 1], [0])
            state.deserialize(state_raw)
            return state

    def run_circuit(self, circuit: "Circuit", keys: List[int], meas_samp=None) -> any:
        self.client_call_counter += 1
        if self._check_local(keys):
            return self.qm.run_circuit(circuit, keys, meas_samp)
        else:
            visited_qubits = set()
            for key in keys:
                if key in visited_qubits:
                    continue
                if self.is_managed_by_server(key):
                    visited_qubits.add(key)
                else:
                    state = self.qm.get(key)
                    for state_key in state.keys:
                        visited_qubits.add(state_key)
                        assert not self.is_managed_by_server(state_key)
                    self.move_manage_to_server(state.keys[0])
            # todo: move qubit to client if all keys of entangled qubits belong
            #       to the client
            if len(circuit.measured_qubits) == 0:
                self._send_message(QuantumManagerMsgType.RUN,
                                   list(visited_qubits),
                                   [circuit, keys], False)
                return {}

            ret_val_raw = self._send_message(QuantumManagerMsgType.RUN,
                                             list(visited_qubits),
                                             [circuit, keys, meas_samp])

            ret_val = {}
            for key in ret_val_raw:
                ret_val[int(key, 16)] = ret_val_raw[key]

            for measured_q in ret_val:
                if not measured_q in self.qm.states:
                    continue
                if ret_val[measured_q] == 1:
                    self.move_manage_to_client([measured_q], [0, 1])
                else:
                    self.move_manage_to_client([measured_q], [1, 0])
            return ret_val

    def set(self, keys: List[int], amplitudes: any) -> None:
        self.client_call_counter += 1
        if self._check_local(keys):
            self.qm.set(keys, amplitudes)
        elif all(key in self.qm.states for key in keys):
            self.move_manage_to_client(keys, amplitudes)
        else:
            for key in keys:
                self.move_manage_to_server(key, sync_state=False)
            self._send_message(QuantumManagerMsgType.SET, keys, [amplitudes],
                               False)

    def remove(self, key: int) -> None:
        self.client_call_counter += 1
        self._send_message(QuantumManagerMsgType.REMOVE, [key], [])
        self.qm.remove(key)

    def kill(self) -> None:
        """Method to terminate the connected server.

        Uses a message of type `QuantumManagerMsgType.TERMINATE`.

        Side Effects:
            Will end all processes on the remote server.
        """
        self.client_call_counter += 1
        self._send_message(QuantumManagerMsgType.TERMINATE, [], [],
                           expecting_receive=False)

    def is_managed_by_server(self, qubit_key: int) -> bool:
        return qubit_key not in self.managed_qubits

    def move_manage_to_server(self, qubit_key: int, sync_state=True):
        """Move management of a qubit from the local quantum manager to quantum manager server.

        Args:
            qubit_key (int): qubit key to move.
            sync_state (bool): indicates if server state should be set to match local (default `True`).
        """

        if self.is_managed_by_server(qubit_key):
            return
        if qubit_key in self.qm.states:
            state = self.qm.get(qubit_key)
            for key in state.keys:
                self.managed_qubits.remove(key)
            if sync_state:
                self._send_message(QuantumManagerMsgType.SET, state.keys,
                                   [state.state], False)

    def move_manage_to_client(self, qubit_keys: List[int], amplitude: any):
        assert all(qubit_key in self.qm.states for qubit_key in qubit_keys)
        for key in qubit_keys:
            self.managed_qubits.add(key)
        self.qm.set(qubit_keys, amplitude)

    def _send_message(self, msg_type, keys: List, args: List,
                      expecting_receive=True) -> any:
        """Sends a message to the remote quantum manager server.

        Args:
            msg_type (QuantumManagerMsgType): type of message to send.
            keys (List[int]): list of all keys affected by message process.
            args (List[any]): any other arguments used for the message.
            expecting_receive (bool): indicates if client should block until response received (default `True`).

        Returns:
            any: result of process on quantum manager server (if `expecting_receive` is `True`).
        """

        self.type_counter[msg_type.name] += 1

        msg = QuantumManagerMessage(msg_type, keys, args)
        self.message_buffer.append(msg)

        if expecting_receive:
            self.flush_message_buffer()
            tick = time()
            received_msg = recv_msg_with_length(self.socket)
            self.io_time += time() - tick
            return received_msg

    def flush_message_buffer(self):
        if len(self.message_buffer) > 0:
            tick = time()
            msgs = [msg.serialize() for msg in self.message_buffer]
            send_msg_with_length(self.socket, msgs)
            self.io_time += time() - tick
            self.message_buffer = []

    def flush_before_sync(self):
        if len(self.message_buffer) > 0:
            self._send_message(QuantumManagerMsgType.SYNC, [], [])

    def _check_local(self, keys: List[int]):
        return not any([self.is_managed_by_server(key) for key in keys])
