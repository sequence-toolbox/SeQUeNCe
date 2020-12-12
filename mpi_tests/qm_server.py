from sequence.kernel.quantum_manager_server import generate_arg_parser, \
    QuantumManagerMsgType, start_session
from pickle import dumps, loads
import multiprocessing
from socket import socket

if __name__ == '__main__':
    parser = generate_arg_parser()
    args = parser.parse_args()

    s = socket()
    s.bind((args.ip, args.port))
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
            process = multiprocessing.Process(target=start_session, args=(
            c, states, _least_available))
            processes.append(process)
            process.start()

        else:
            raise Exception(
                'Unknown message type received by quantum manager server')

    for p in processes:
        p.terminate()
