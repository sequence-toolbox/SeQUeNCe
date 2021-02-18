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


def start_session(formalism: str, msg: QuantumManagerMessage,
                  all_keys: List[int], comm: socket, states,
                  least_available, locks, manager, locations,
                  timing_dict_ops=multiprocessing.Value('d', 0),
                  timing_qm_setup=multiprocessing.Value('d', 0),
                  timing_comp={}):
    # TODO: does not need all states and managers;
    # we could copy part of state to the manager and update the global manager
    # after operations

    tick = time()
    local_states = {k: states[k] for k in all_keys}
    timing_dict_ops.value += (time() - tick)

    tick = time()
    if formalism == "KET":
        qm = ParallelQuantumManagerKet(local_states, least_available)
    elif formalism == "DENSITY":
        qm = ParallelQuantumManagerDensity(local_states, least_available)
    timing_qm_setup.value += (time() - tick)

    return_val = None

    if msg.type not in timing_comp:
        timing_comp[msg.type] = 0
    tick = time()

    if msg.type == QuantumManagerMsgType.NEW:
        assert len(msg.args) == 2
        state, location = msg.args
        return_val = qm.new(state)
        locks[return_val] = manager.Lock()
        locations[return_val] = location

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
        del locations[key]

    else:
        raise Exception(
            "Quantum manager session received invalid message type {}".format(
                msg.type))

    timing_comp[msg.type] += (time() - tick)

    # release all locks
    if msg.type != QuantumManagerMsgType.REMOVE:
        tick = time()
        states.update(local_states)
        timing_dict_ops.value += (time() - tick)
        for key in all_keys:
            locks[key].release()

    # send return value
    if return_val is not None:
        data = dumps(return_val)
        comm.sendall(data)

    comm.close()


def start_server(ip, port, formalism="KET"):
    lock_time = {}
    start_time = {}

    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((ip, port))
    s.listen()
    processes = []
    print("connected:", ip, port)

    # initialize shared data
    least_available = multiprocessing.Value('i', 0)
    manager = multiprocessing.Manager()
    states = manager.dict()
    locks = manager.dict()
    locations = manager.dict()

    timing_dict_ops = multiprocessing.Value('d', 0)
    timing_qm_setup = multiprocessing.Value('d', 0)
    timing_comp = manager.dict()
    
    while True:
        c, addr = s.accept()
        raw_msg = c.recv(1024)
        msg = loads(raw_msg)

        # get list of all keys necessary to service request
        all_keys = set()
        for key in msg.keys:
            state = states[key]
            for k in state.keys:
                all_keys.add(k)

        # acquire all necessary locks and record timing
        if msg.type not in lock_time:
            lock_time[msg.type] = 0
        tick = time()
        for key in all_keys:
            locks[key].acquire()
        lock_time[msg.type] += (time() - tick)

        if msg.type == QuantumManagerMsgType.TERMINATE:
            break
        else:
            # generate a new process to handle request
            if msg.type not in start_time:
                start_time[msg.type] = [0, 0]
            tick = time()
            args = (
                formalism, msg, all_keys, c, states, least_available, locks,
                manager, locations,
                timing_dict_ops, timing_qm_setup, timing_comp)
            process = multiprocessing.Process(target=start_session, args=args)
            # processes.append(process)
            process.start()
            start_time[msg.type][0] += 1
            start_time[msg.type][1] += (time() - tick)

    # record timing information
    with open("server.log", "w") as fh:
        fh.write("lock timing:\n")
        for msg_type in lock_time:
            fh.write("\t{}: {}\n".format(msg_type, lock_time[msg_type]))
        fh.write("\ttotal lock time: {}\n".format(sum(lock_time.values())))

        fh.write("process startup timing:\n")
        for msg_type in start_time:
            fh.write("\t{}: {} in {}\n".format(msg_type, start_time[msg_type][0], start_time[msg_type][1]))
        fh.write("\ttotal startup time: {} in {}\n".format(sum(procs for procs, _ in start_time.values()),
                                                           sum(time for _, time in start_time.values())))

        fh.write("dictionary operations: {}\n".format(timing_dict_ops.value))
        fh.write("quantum manager setup: {}\n".format(timing_qm_setup.value))

        fh.write("computation timing:\n")
        for msg_type in timing_comp:
            fh.write("\t{}: {}\n".format(msg_type, timing_comp[msg_type]))
        fh.write("\ttotal computation timing: {}\n".format(sum(timing_comp.values())))

    # for p in processes:
    #     p.terminate()

def kill_server(ip, port):
    s = socket.socket()
    s.connect((ip, port))
    msg = QuantumManagerMessage(QuantumManagerMsgType.TERMINATE, [], [])
    data = dumps(msg)
    s.sendall(data)

