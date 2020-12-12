from sequence.kernel.quantum_manager_server import generate_arg_parser, start_server
from pickle import dumps, loads
import multiprocessing
from socket import socket

if __name__ == '__main__':
    parser = generate_arg_parser()
    args = parser.parse_args()

    start_server(args.ip, args.port)

