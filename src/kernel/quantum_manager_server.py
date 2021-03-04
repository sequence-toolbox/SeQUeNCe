from enum import Enum, auto
import socket
import argparse
from ipaddress import ip_address
from pickle import loads, dumps
import select
import multiprocessing
from typing import List
from time import time

from .p_quantum_manager import ParallelQuantumManagerKet, \
    ParallelQuantumManagerDensity
from ..utils.communication import send_msg_with_length, recv_msg_with_length
from .quantum_manager import measure_state_with_cache_ket, \
    measure_entangled_state_with_cache_ket, measure_multiple_with_cache_ket


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


def start_session(formalism: str, comm: socket, states, locks, manager,
                  timing_dict_ops=multiprocessing.Value('d', 0),
                  timing_qm_setup=multiprocessing.Value('d', 0),
                  timing_comp={}, timing_lock={}):
    # we could copy part of state to the manager and update the global manager
    # after operations

    while True:
        msg = recv_msg_with_length(comm)
        return_val = None

        if msg.type not in timing_comp:
            timing_comp[msg.type] = 0
        if msg.type not in timing_lock:
            timing_lock[msg.type] = 0

        all_keys = set()
        for key in msg.keys:
            if key in states:
                state = states[key]
                for k in state.keys:
                    all_keys.add(k)
            else:
                all_keys.add(key)

        # acquire all necessary locks and record timing
        tick = time()
        for key in sorted(all_keys):
            if key not in locks:
                locks[key] = manager.Lock()
            locks[key].acquire()
        timing_lock[msg.type] += time() - tick

        tick = time()
        local_states = {}
        for k in all_keys:
            if k in states:
                local_states[k] = states[k]
            else:
                local_states[k] = None

        qm.set_states(local_states)
        timing_qm_setup.value += time() - tick

        tick = time()
        if msg.type == QuantumManagerMsgType.CLOSE:
            comm.close()
            print(measure_state_with_cache_ket.cache_info())
            print(measure_multiple_with_cache_ket.cache_info())
            print(measure_entangled_state_with_cache_ket.cache_info())

            break

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
            all_keys.remove(key)

        else:
            raise Exception(
                "Quantum manager session received invalid message type {}".format(
                    msg.type))
        timing_comp[msg.type] += (time() - tick)

        # release all locks
        if msg.type != QuantumManagerMsgType.REMOVE \
                or msg.type != QuantumManagerMsgType.GET:
            tick = time()
            states.update(local_states)
            timing_dict_ops.value += (time() - tick)

        for key in all_keys:
            locks[key].release()

        # send return value
        if return_val is not None:
            send_msg_with_length(comm, return_val)


def start_server(ip, port, client_num=4, formalism="KET",
                 log_file="server.log"):
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((ip, port))
    s.listen()
    print("listening at:", ip, port)

    timing_comp = {}

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
            msg = recv_msg_with_length(s)
            return_val = None

            tick = time()
            if msg.type == QuantumManagerMsgType.CLOSE:
                s.close()
                sockets.remove(s)
                break

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
                qm.remove(key)

            elif msg.type == QuantumManagerMsgType.TERMINATE:
                for s in sockets:
                    s.close()
                sockets = []
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

    # # record timing information
    with open(log_file, "w") as fh:
        fh.write("computation timing:\n")
        for msg_type in timing_comp:
            fh.write("\t{}: {}\n".format(msg_type, timing_comp[msg_type]))
        fh.write("\ttotal computation timing: {}\n".format(
            sum(timing_comp.values())))


def kill_server(ip, port):
    s = socket.socket()
    s.connect((ip, port))
    msg = QuantumManagerMessage(QuantumManagerMsgType.TERMINATE, [], [])
    send_msg_with_length(s, msg)
