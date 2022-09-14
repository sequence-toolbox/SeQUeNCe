"""This script provides a method for starting the Quantum Manager Server (Python Version).

This script assumes the ket vector formalism for the quantum manager.
To change the formalism, add an argument to the `start_server` function (see the kernel/quantum_manager_server.py module).

Arguments:
    ip (str): ip address to listen on.
    port (int): port to listen on.
    client_num (int): number of quantum manager clients linked to the server.
"""

from psequence.quantum_manager_server import start_server, valid_ip, valid_port
import argparse

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='The server of quantum manager')
    parser.add_argument('ip', type=valid_ip, help='listening IP address')
    parser.add_argument('port', type=valid_port, help='listening port number')
    parser.add_argument('client_num', type=int,
                        help='The number of connected clients')
    args = parser.parse_args()

    start_server(args.ip, args.port, args.client_num)
