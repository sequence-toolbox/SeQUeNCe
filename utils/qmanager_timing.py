import time
import multiprocessing
import numpy as np

from psequence.quantum_manager_server import generate_arg_parser, start_server
from sequence.kernel.quantum_manager_client import QuantumManagerClient
from sequence.components.circuit import Circuit


def client_function(ip, port):
    client = QuantumManagerClient("KET", ip, port)

    # send request for new state
    key = client.new()

    # send request to get state
    _ = client.get(key)

    # run Hadamard gate
    circ = Circuit(1)
    circ.h(0)
    client.run_circuit(circ, [key])

    # get state again to verify
    _ = client.get(key)


NUM_TRIALS = 10
NUM_CLIENTS = 10

parser = generate_arg_parser()
args = parser.parse_args()

p = multiprocessing.Process(target=start_server, args=(args.ip, args.port))
p.start()

times = []
for _ in range(NUM_TRIALS):
    start = time.time()
    pool = multiprocessing.Pool(NUM_CLIENTS, client_function, [args.ip, args.port])
    pool.close()
    pool.join()
    end = time.time()
    print("\ttime:", end - start)
    times.append(end - start)

p.kill()

print("average time:", np.mean(times))

