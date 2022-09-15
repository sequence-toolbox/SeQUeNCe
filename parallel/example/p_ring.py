from json import dump
import os
import pandas as pd
from time import time
import numpy as np

from sequence.topology.node import QuantumRouter, BSMNode
from sequence.components.optical_channel import ClassicalChannel, QuantumChannel
from sequence.app.request_app import RequestApp
from psequence.p_timeline import ParallelTimeline
import sequence.utils.log as log


SQRT_HALF = 0.5 ** 0.5
desired_state = [SQRT_HALF, 0, 0, SQRT_HALF]


def complex_array_equal(arr1, arr2, precision=5):
    for c1, c2 in zip(arr1, arr2):
        if abs(c1 - c2) >= 2 ** -precision:
            return False
    return True


class CustomizedApp(RequestApp):
    def __init__(self, node: "QuantumRouter"):
        super(CustomizedApp, self).__init__(node)
        self.desired_state_counter = 0
        self.undesired_state_counter = 0
        self.counter = 0
        self.undesired_state = set()

    def get_memory(self, info: "MemoryInfo") -> None:
        if info.state != "ENTANGLED":
            return

        if info.index in self.memo_to_reserve:
            reservation = self.memo_to_reserve[info.index]
            if info.remote_node == reservation.initiator \
                    and info.fidelity >= reservation.fidelity:
                state = self.node.timeline.quantum_manager.get(
                    info.memory.qstate_key)
                assert len(state.keys) == 2
                self.node.resource_manager.update(None, info.memory, "RAW")
            elif info.remote_node == reservation.responder \
                    and info.fidelity >= reservation.fidelity:
                self.memory_counter += 1
                state = self.node.timeline.quantum_manager.get(
                    info.memory.qstate_key)
                assert len(state.keys) == 2
                self.node.resource_manager.update(None, info.memory, "RAW")


def ring_network(ring_size: int, lookahead: int, stop_time: int, rank: int,
                 mpi_size: int, qm_ip: str, qm_port: int, log_path: str):
    tick = time()
    if not os.path.exists(log_path) and rank == 0:
        os.mkdir(log_path)

    # network/hardware params
    CC_DELAY = 1e9
    MEMO_SIZE = 50
    RAW_FIDELITY = 0.9
    ATTENUATION = 0.0002
    SWAP_DEG_RATE = 1

    tl = ParallelTimeline(lookahead=lookahead, stop_time=stop_time, qm_ip=qm_ip, qm_port=qm_port)

    # log.set_logger(__name__, tl, "mpi_%d.log" % rank)
    # log.set_logger_level("DEBUG")
    # log.track_module('generation')
    # log.track_module('bsm')

    routers = []
    bsm_nodes = []
    router_names = []
    group_size = ring_size // mpi_size
    for node_id in range(ring_size):
        node_name = "Node_%d" % node_id
        router_names.append(node_name)
        if node_id // group_size == rank:
            node = QuantumRouter(node_name, tl, MEMO_SIZE)
            node.set_seed(node_id)
            node.memory_array.update_memory_params('raw_fidelity',
                                                   RAW_FIDELITY)
            routers.append(node)
        else:
            tl.foreign_entities[node_name] = node_id // group_size

    for bsm_id in range(ring_size):
        node_name = "BSM_%d" % bsm_id
        if bsm_id // group_size == rank:
            pre_node_name = 'Node_%d' % ((bsm_id - 1) % ring_size)
            post_node_name = 'Node_%d' % bsm_id

            node = BSMNode(node_name, tl, [pre_node_name, post_node_name])
            node.set_seed(ring_size + bsm_id)
            bsm_nodes.append(node)
        else:
            tl.foreign_entities[node_name] = bsm_id // group_size

    for src in routers + bsm_nodes:
        for dst_index in range(ring_size):
            dst_name = "Node_%d" % dst_index
            if dst_name != src.name:
                cc = ClassicalChannel("cc_%s_%s" % (src.name, dst_name),
                                      tl, 20000, CC_DELAY)
                cc.set_ends(src, dst_name)

            dst_name = "BSM_%d" % dst_index
            if dst_name != src.name:
                cc = ClassicalChannel("cc_%s_%s" % (src.name, dst_name),
                                      tl, 20000, CC_DELAY)
                cc.set_ends(src, dst_name)

    for src in routers:
        bsm_index = int(src.name.replace("Node_", ""))
        bsm_name = "BSM_%d" % bsm_index
        qc = QuantumChannel("qc_%s_%s" % (src.name, bsm_name),
                            tl, ATTENUATION, lookahead * 2e-4)
        qc.set_ends(src, bsm_name)
        router_name = "Node_%d" % ((bsm_index - 1) % ring_size)
        src.add_bsm_node(bsm_name, router_name)

        bsm_name = "BSM_%d" % ((bsm_index + 1) % ring_size)
        qc = QuantumChannel("qc_%s_%s" % (src.name, bsm_name),
                            tl, ATTENUATION, lookahead * 2e-4)
        qc.set_ends(src, bsm_name)
        router_name = "Node_%d" % ((bsm_index + 1) % ring_size)
        src.add_bsm_node(bsm_name, router_name)

    if ring_size == 2 and mpi_size == 2:
        if rank == 0:
            routers[0].map_to_middle_node['Node_1'] = 'BSM_0'

    for node in routers:
        node_index = int(node.name.replace("Node_", ""))
        for dst in router_names:
            if node.name != dst:
                dst_index = int(dst.replace("Node_", ""))
                if abs(node_index - dst_index) < ring_size - abs(
                        node_index - dst_index):
                    if dst_index > node_index:
                        bsm_name = "Node_%d" % ((node_index + 1) % ring_size)
                    else:
                        bsm_name = "Node_%d" % ((node_index - 1) % ring_size)
                else:
                    if dst_index > node_index:
                        bsm_name = "Node_%d" % ((node_index - 1) % ring_size)
                    else:
                        bsm_name = "Node_%d" % ((node_index + 1) % ring_size)

                node.network_manager.protocol_stack[0].add_forwarding_rule(dst,
                                                                           bsm_name)

    for node in routers:
        node.network_manager.protocol_stack[1].set_swapping_degradation(
            SWAP_DEG_RATE)

    apps = []
    for node in routers:
        index = int(node.name.replace("Node_", ""))
        app = RequestApp(node)
        if index % 2 == 1:
            apps.append(app)
            responder = "Node_%d" % ((index + 2) % ring_size)
            app.start(responder, 10e12, 11e12, MEMO_SIZE // 2, 0.82)

    tl.init()

    prepare_time = time() - tick

    tick = time()
    tl.run()
    execution_time = time() - tick

    tl.quantum_manager.disconnect_from_server()

    # write network information into log_path/net_info.json file
    if rank == 0:
        net_info = {'topology': 'ring', 'size': ring_size,
                    'lookahead': lookahead,
                    'stop_time': stop_time, 'processor_num': mpi_size,
                    'CC_delay': CC_DELAY, 'QC_delay': lookahead * 2e-4,
                    'memory_array_size': MEMO_SIZE,
                    'initial_fidelity': RAW_FIDELITY}
        with open(log_path + '/net_info.json', 'w') as fh:
            dump(net_info, fh)

    # write reservation information into log_path/traffic_RANK.csv file
    initiators = []
    responders = []
    start_times = []
    end_times = []
    memory_sizes = []
    fidelities = []
    paths = []
    throughputs = []

    for app in apps:
        initiators.append(app.node.name)
        responders.append(app.responder)
        start_times.append(app.start_t)
        end_times.append(app.end_t)
        memory_sizes.append(app.memo_size)
        fidelities.append(app.fidelity)
        paths.append(app.path)
        throughputs.append(app.get_throughput())

    traffic_info = {"Initiator": initiators, "Responder": responders,
                    "Start_time": start_times, "End_time": end_times,
                    "Memory_size": memory_sizes, "Fidelity": fidelities,
                    "Path": paths, "Throughput": throughputs}

    df = pd.DataFrame(traffic_info)
    df.to_csv(log_path + "/traffic_%d.csv" % rank)

    # write information of parallelization performance into log_path/perf.json file
    sync_time = execution_time - tl.computing_time - tl.communication_time
    perf_info = {'prepare_time': prepare_time,
                 'execution_time': execution_time,
                 'computing_time': tl.computing_time,
                 'communication_time': tl.communication_time,
                 'sync_time': sync_time,
                 'sync_counter': tl.sync_counter,
                 'io_time': tl.quantum_manager.io_time,
                 'run_counter': tl.run_counter,
                 'schedule_counter': tl.schedule_counter,
                 'exchange_counter': tl.exchange_counter}
    for msg_type in tl.quantum_manager.type_counter:
        perf_info['%s_counter' % msg_type] = tl.quantum_manager.type_counter[
            msg_type]

    with open('%s/perf_%d.json' % (log_path, rank), 'w') as fh:
        dump(perf_info, fh)


if __name__ == "__main__":
    import argparse
    from mpi4py import MPI
    from sequence.kernel.quantum_manager_server import valid_port, valid_ip

    rank = MPI.COMM_WORLD.Get_rank()
    size = MPI.COMM_WORLD.Get_size()

    parser = argparse.ArgumentParser(description='Example of parallel quantum network')
    parser.add_argument('ip', type=valid_ip, help='quantum server IP address')
    parser.add_argument('port', type=valid_port, help='quantum server port number')
    parser.add_argument('ring_size', type=int, help='the size of ring network')
    parser.add_argument('lookahead', type=int,
                        help='the lookahead of parallel simulation (ps); longer lookahead generates a longer quantum channel')
    parser.add_argument('stop_time', type=int, help='the end time of the simulation (sec)')
    parser.add_argument('log_path', type=str, help='the path for storing log files')

    args = parser.parse_args()

    if rank == 0:
        print('Simulate {}-node ring network {} sec by {} processors'.format(
            args.ring_size, args.stop_time, size))
        print('Connecting to the quantum manager server at {}:{}'.format(
            args.ip, args.port))
        print('log path: {}'.format(args.log_path))

    ring_network(args.ring_size, args.lookahead, args.stop_time * 1e12, rank,
                 size, args.ip, args.port, args.log_path)
