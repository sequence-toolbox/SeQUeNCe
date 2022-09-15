import json
from time import time
import pandas as pd
from mpi4py import MPI
from json import load, dump

from sequence.app.request_app import RequestApp
from psequence.p_router_net_topo import ParallelRouterNetTopo


def main(config_file: str, flow_info_file: str, log_path: str):
    START_TIME = int(1e12)
    DURATION = int(1e12)
    MIN_FIDELITY = 0.9
    MAX_FIDELITY = 0.95

    RAW_FIDELITY = 0.99
    STOP_TIME = 10e12
    SWAP_DEG_RATE = 0.99

    mpi_rank = MPI.COMM_WORLD.Get_rank()
    mpi_size = MPI.COMM_WORLD.Get_size()

    topo = ParallelRouterNetTopo(config_file)
    tl = topo.get_timeline()
    tl.stop_time = STOP_TIME

    # log.set_logger(__name__, tl, "mpi_%d.log" % mpi_rank)
    # log.set_logger_level("DEBUG")
    # log.track_module('generation')
    # log.track_module('bsm')
    fh = open(flow_info_file, 'r')
    flow_info = json.load(fh)
    fh.close()

    flows, flow_memo_size = flow_info["flows"], flow_info["memo_size"]

    routers = topo.get_nodes_by_type(topo.QUANTUM_ROUTER)

    apps = []

    # update routing table
    name_to_router = {}
    for r in routers:
        name_to_router[r.name] = r
    update_forwarding_table = lambda node, dst, next_hop: \
        node.network_manager.protocol_stack[0].update_forwarding_rule(dst,
                                                                      next_hop)
    for path in flows.values():
        for i, n_name in enumerate(path):
            if n_name in name_to_router:
                node = name_to_router[n_name]
                if i < len(path) - 1:
                    update_forwarding_table(node, path[-1], path[i + 1])
                if i > 0:
                    update_forwarding_table(node, path[0], path[i - 1])

    for i, node in enumerate(routers):
        node.memory_array.update_memory_params('raw_fidelity',
                                               RAW_FIDELITY)
        node.network_manager.protocol_stack[1].set_swapping_degradation(
            SWAP_DEG_RATE)

        app = RequestApp(node)
        rng = node.get_generator()
        target_fidelity = rng.uniform(MIN_FIDELITY, MAX_FIDELITY)
        responder = flows[node.name][-1]
        app.start(responder, START_TIME, START_TIME + DURATION,
                  flow_memo_size, target_fidelity)
        apps.append(app)

    tick = time()
    tl.init()
    prepare_time = time() - tick

    tick = time()
    tl.run()
    execution_time = time() - tick

    if mpi_size > 1:
        tl.quantum_manager.disconnect_from_server()

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
        assert app.path == flows[app.node.name], (
            app.node.name, app.reserve_res, app.path, flows[app.node.name])
        assert app.reserve_res, (app.node.name, app.responder, app.reserve_res)
        print(app.node.name, "pass")
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
    df.to_csv(log_path + "/traffic_%d.csv" % mpi_rank)

    # write information of parallelization performance into log_path/perf.json file
    perf_info = {'prepare_time': prepare_time,
                 'execution_time': execution_time,
                 'event_counter': tl.run_counter,
                 'schedule_counter': tl.schedule_counter}

    if mpi_size > 1:
        sync_time = execution_time - tl.computing_time
        parallel_perf_info = {
            'computing_time': tl.computing_time,
            'communication_time': tl.communication_time,
            'sync_time': sync_time,
            'sync_counter': tl.sync_counter,
            'exchange_counter': tl.exchange_counter,
            'io_time': tl.quantum_manager.io_time
        }

        for msg_type in tl.quantum_manager.type_counter:
            parallel_perf_info['%s_counter' % msg_type] = \
                tl.quantum_manager.type_counter[
                    msg_type]

        perf_info.update(parallel_perf_info)

    with open('%s/perf_%d.json' % (log_path, mpi_rank), 'w') as fh:
        dump(perf_info, fh)


if __name__ == "__main__":
    import sys

    config_file_name = sys.argv[1]
    flow_info_file_name = sys.argv[2]
    log_path = sys.argv[3]
    main(config_file_name, flow_info_file_name, log_path)
