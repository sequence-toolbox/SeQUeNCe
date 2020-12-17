from sequence.kernel.p_timeline import ParallelTimeline
from sequence.kernel.quantum_manager_server import kill_server
from sequence.topology.node import QuantumRouter, BSMNode
from sequence.components.optical_channel import ClassicalChannel, \
    QuantumChannel
from sequence.app.random_request import RandomRequestApp
import sequence.utils.log as log

from json import dump
import os
import pandas as pd
from time import time


def ring_network(ring_size: int, lookahead: int, stop_time: int, rank: int,
                 mpi_size: int, qm_ip: str, qm_port: int, log_path: str):
    kill = False
    tick = time()
    if not os.path.exists(log_path):
        os.mkdir(log_path)

    CC_DELAY = 1e9
    MEMO_SIZE = 50
    RAW_FIDELITY = 0.99

    tl = ParallelTimeline(lookahead=lookahead, stop_time=stop_time,
                          qm_ip=qm_ip, qm_port=qm_port)
    tl.seed(rank)

    log.set_logger(__name__, tl, "mpi_%d.log" % rank)
    log.set_logger_level("INFO")
    log.track_module('node')
    log.track_module('network_manager')

    routers = []
    bsm_nodes = []
    router_names = []
    group_size = ring_size // mpi_size
    for node_id in range(ring_size):
        node_name = "Node_%d" % node_id
        router_names.append(node_name)
        if node_id // group_size == rank:
            node = QuantumRouter(node_name, tl, MEMO_SIZE)
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
            bsm_nodes.append(node)
        else:
            tl.foreign_entities[node_name] = bsm_id // group_size

    for src in routers + bsm_nodes:
        for dst_index in range(ring_size):
            dst_name = "Node_%d" % dst_index
            if dst_name != src.name:
                cc = ClassicalChannel("cc_%s_%s" % (src.name, dst_name),
                                      tl, 20000, CC_DELAY // 2)
                cc.set_ends(src, dst_name)

            dst_name = "BSM_%d" % dst_index
            if dst_name != src.name:
                cc = ClassicalChannel("cc_%s_%s" % (src.name, dst_name),
                                      tl, 20000, CC_DELAY // 2)
                cc.set_ends(src, dst_name)

    for src in routers:
        bsm_index = int(src.name.replace("Node_", ""))
        bsm_name = "BSM_%d" % bsm_index
        qc = QuantumChannel("qc_%s_%s" % (src.name, bsm_name),
                            tl, 0.0002, lookahead * 2e-4)
        qc.set_ends(src, bsm_name)
        router_name = "Node_%d" % ((bsm_index + 1) % ring_size)
        src.add_bsm_node(bsm_name, router_name)

        bsm_name = "BSM_%d" % ((bsm_index - 1) % ring_size)
        qc = QuantumChannel("qc_%s_%s" % (src.name, bsm_name),
                            tl, 0.0002, lookahead * 2e-4)
        qc.set_ends(src, bsm_name)
        router_name = "Node_%d" % ((bsm_index - 1) % ring_size)
        src.add_bsm_node(bsm_name, router_name)

    if ring_size == 2 and mpi_size == 2:
        if rank == 0:
            routers[0].map_to_middle_node['Node_1'] = 'BSM_0'

    print([router.name for router in routers],
          [bsm_node.name for bsm_node in bsm_nodes])
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

        # for dst in node.network_manager.protocol_stack[0].forwarding_table:
        #     print(node.name, '->', dst, node.network_manager.protocol_stack[0].forwarding_table[dst])
    for node in routers:
        print(node.map_to_middle_node)
    apps = []
    for i, node in enumerate(routers):
        seed = int(node.name.replace("Node_", ""))
        app_node_name = node.name
        others = router_names[:]
        others.remove(app_node_name)
        app = RandomRequestApp(node, others, seed, 1e13, 2e13, 10, 25, 0.8,
                               1.0)
        apps.append(app)
        app.start()

    tl.init()

    prepare_time = time() - tick

    tick = time()
    tl.run()
    execution_time = time() - tick

    tl.quantum_manager.close()

    if kill:
        kill_server(qm_ip, qm_port)

    print(tl.now(), len(tl.events))

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
    wait_times = []
    throughputs = []
    for node in routers:
        initiator = node.name
        reserves = node.app.reserves
        _wait_times = node.app.get_wait_time()
        _throughputs = node.app.get_throughput()
        min_size = min(len(reserves), len(_wait_times), len(_throughputs))
        reserves = reserves[:min_size]
        _wait_times = _wait_times[:min_size]
        _throughputs = _throughputs[:min_size]
        for reservation, path, wait_time, throughput in zip(reserves,
                                                            node.app.paths,
                                                            _wait_times,
                                                            _throughputs):
            responder, s_t, e_t, size, fidelity = reservation
            initiators.append(initiator)
            responders.append(responder)
            start_times.append(s_t)
            end_times.append(e_t)
            memory_sizes.append(size)
            fidelities.append(fidelity)
            paths.append(path)
            wait_times.append(wait_time)
            throughputs.append(throughput)
    traffic_info = {"Initiator": initiators, "Responder": responders,
                    "Start_time": start_times, "End_time": end_times,
                    "Memory_size": memory_sizes, "Fidelity": fidelities,
                    "Path": paths, "Wait_time": wait_times,
                    "Throughput": throughputs}

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
                 'event_counter': tl.event_counter,
                 'schedule_counter': tl.schedule_counter,
                 'exchange_counter': tl.exchange_counter}
    for msg_type in tl.quantum_manager.io_time:
        perf_info['%s_counter' % msg_type] = tl.quantum_manager.type_counter[
            msg_type]
        perf_info['%s_io_time' % msg_type] = tl.quantum_manager.io_time[
            msg_type]

    with open('%s/perf_%d.json' % (log_path, rank), 'w') as fh:
        dump(perf_info, fh)

if __name__ == "__main__":
    from mpi4py import MPI
    from sequence.kernel.quantum_manager_server import valid_port, valid_ip
    import argparse

    rank = MPI.COMM_WORLD.Get_rank()
    size = MPI.COMM_WORLD.Get_size()

    parser = argparse.ArgumentParser(
        description='The example of parallel quantum network')
    parser.add_argument('ip', type=valid_ip, help='listening IP address')
    parser.add_argument('port', type=valid_port, help='listening port number')
    parser.add_argument('ring_size', type=int, help='the size of ring network')
    parser.add_argument('lookahead', type=int,
                        help='the lookahead of parallel simulation (ps); the longer lookahead generate the longer quantum channel')
    parser.add_argument('stop_time', type=int,
                        help='the time of stopping the simulation (sec)')
    parser.add_argument('log_path', type=str,
                        help='the path of log files')

    args = parser.parse_args()

    if rank == 0:
        print('Simulate {}-node ring network {} sec by {} processors'.format(
            args.ring_size, args.stop_time, size))
        print(
            'Connecting to the quanum manager server at {}:{}'.format(args.ip,
                                                                      args.port))
        print('log path: {}'.format(args.log_path))

    ring_network(args.ring_size, args.lookahead, args.stop_time * 1e12, rank,
                 size, args.ip, args.port, args.log_path)
