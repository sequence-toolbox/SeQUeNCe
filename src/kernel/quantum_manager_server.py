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
    comm.settimeout(20)
    tick = time()
    if formalism == "KET":
        qm = ParallelQuantumManagerKet({})
    elif formalism == "DENSITY":
        qm = ParallelQuantumManagerDensity({})
    timing_qm_setup.value += time() - tick

    msg = QuantumManagerMessage(QuantumManagerMsgType.CONNECTED, [], [])
    send_msg_with_length(comm, msg)

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


def start_server(ip, port, formalism="KET", log_file="server.log"):
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((ip, port))
    s.listen()
    processes = []
    print("listening at:", ip, port)

    # initialize shared data
    manager = multiprocessing.Manager()
    states = manager.dict()
    locks = manager.dict()

    timing_dict_ops = multiprocessing.Value('d', 0)
    timing_qm_setup = multiprocessing.Value('d', 0)
    timing_comp = manager.dict()
    timing_lock = manager.dict()

    while True:
        c, addr = s.accept()
        msg = recv_msg_with_length(c)

        if msg.type == QuantumManagerMsgType.TERMINATE:
            break
        elif msg.type == QuantumManagerMsgType.CONNECT:
            args = (formalism, c, states, locks, manager,
                    timing_dict_ops, timing_qm_setup, timing_comp, timing_lock)
            process = multiprocessing.Process(target=start_session, args=args)
            processes.append(process)
            process.start()

        _processes = []
        for p in processes:
            if p.is_alive():
                _processes.append(p)
        processes = _processes

    for p in processes:
        p.join()

    # record timing information
    with open(log_file, "w") as fh:
        fh.write("lock timing:\n")
        for msg_type in timing_lock:
            fh.write("\t{}: {}\n".format(msg_type, timing_lock[msg_type]))
        fh.write("\ttotal lock time: {}\n".format(sum(timing_lock.values())))

        fh.write("dictionary operations: {}\n".format(timing_dict_ops.value))
        fh.write("quantum manager setup: {}\n".format(timing_qm_setup.value))

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
