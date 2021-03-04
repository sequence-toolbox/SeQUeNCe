from sequence.kernel.quantum_manager_server import start_server, valid_ip, \
    valid_port
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
