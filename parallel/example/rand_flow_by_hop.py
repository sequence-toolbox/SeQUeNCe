from collections import defaultdict
from time import time
from typing import Dict, List, TYPE_CHECKING
from mpi4py import MPI
from json import load, dump
import pandas as pd

from sequence.kernel.process import Process
from sequence.kernel.event import Event
from sequence.app.random_request import RandomRequestApp
from sequence.app.request_app import RequestApp
from psequence.p_router_net_topo import ParallelRouterNetTopo
import sequence.utils.log as log

if TYPE_CHECKING:
    from sequence.topology.node import QuantumRouter


class ExpRandomReqApp(RandomRequestApp):
    def __init__(self, node: "QuantumRouter", seed: int, min_dur: int,
                 max_dur: int, min_size: int, max_size: int,
                 min_fidelity: float, max_fidelity: float, start_prob: float,
                 scale: float, sleep_time: float,
                 hop_to_others: Dict[int, List[str]]):
        super(ExpRandomReqApp, self).__init__(node, [], seed, min_dur, max_dur,
                                              min_size, max_size, min_fidelity,
                                              max_fidelity)

        self.start_probability = start_prob
        self.scale = scale
        self.sleep_time = sleep_time
        self.hop_to_others = hop_to_others

    def start(self):
        self._update_last_rsvp_metrics()

        if self.rg.random() < self.start_probability:
            hop_num = int(self.rg.exponential(self.scale))
            while len(self.hop_to_others.get(hop_num, [])) == 0:
                hop_num -= 1
            responder = self.rg.choice(self.hop_to_others[hop_num])
            start_time = self.node.timeline.now() + \
                         self.rg.integers(10, 20) * 1e11  # now + 1 sec - 2 sec
            end_time = start_time + self.rg.integers(self.min_dur,
                                                     self.max_dur)
            memory_size = self.rg.integers(self.min_size, self.max_size)
            fidelity = self.rg.uniform(self.min_fidelity, self.max_fidelity)
            RequestApp.start(self, responder, start_time, end_time,
                             memory_size, fidelity)
        else:
            process = Process(self, "start", [])
            event = Event(self.node.timeline.now() + self.sleep_time, process)
            self.node.timeline.schedule(event)


def get_net_qc_graph(config_file: str):
    with open(config_file, 'r') as fh:
        config = load(fh)

    graph = {}
    for node in config[ParallelRouterNetTopo.ALL_NODE]:
        if node[ParallelRouterNetTopo.TYPE] == ParallelRouterNetTopo.QUANTUM_ROUTER:
            graph[node[ParallelRouterNetTopo.NAME]] = []

    bsm_to_router_map = {}
    for qc in config[ParallelRouterNetTopo.ALL_Q_CHANNEL]:
        router, bsm = qc[ParallelRouterNetTopo.SRC], qc[ParallelRouterNetTopo.DST]
        if not bsm in bsm_to_router_map:
            bsm_to_router_map[bsm] = router
        else:
            n1, n2 = bsm_to_router_map[bsm], router
            graph[n1].append(n2)
            graph[n2].append(n1)
    return graph


def get_hop_to_others(graph: Dict, node: str):
    res = {}

    cur_queue = [node]

    hop_num = 0
    visited = defaultdict(lambda: False)
    visited[node] = True

    while cur_queue:
        next_queue = []
        res[hop_num] = []
        for x in cur_queue:
            for next_node in graph[x]:
                if not visited[next_node]:
                    res[hop_num].append(next_node)
                    next_queue.append(next_node)
                    visited[next_node] = True
        hop_num += 1
        cur_queue = next_queue

    return res


def main(config_file: str, log_path: str):
    MIN_DURATION = int(30e9)
    MAX_DURATION = int(31e9)
    MIN_SIZE = 10
    MAX_SIZE = 25
    MIN_FIDELITY = 0.9
    MAX_FIDELITY = 0.95
    START_PROBABILITY = 0.5
    EXP_SCALE = 1
    SLEEP_TIME = 1e12

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

    routers = topo.get_nodes_by_type(topo.QUANTUM_ROUTER)

    graph = get_net_qc_graph(config_file)
    apps = []

    for i, node in enumerate(routers):
        node.memory_array.update_memory_params('raw_fidelity',
                                               RAW_FIDELITY)
        node.network_manager.protocol_stack[1].set_swapping_degradation(
            SWAP_DEG_RATE)

        seed = int(node.name.replace("router_", ""))
        hop_to_others = get_hop_to_others(graph, node.name)
        app = ExpRandomReqApp(node, seed, MIN_DURATION, MAX_DURATION, MIN_SIZE,
                              MAX_SIZE, MIN_FIDELITY, MAX_FIDELITY,
                              START_PROBABILITY, EXP_SCALE, SLEEP_TIME,
                              hop_to_others)
        app.start()
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
        reserves, tps = app.reserves, app.get_all_throughput()
        all_path = app.paths
        if len(tps) != len(reserves):
            assert len(tps) + 1 == len(reserves)
            tps.append(app.get_throughput())
        for reserve, tp, path in zip(reserves, tps, all_path):
            responder, start_t, end_t, memo_size, fidelity = reserve
            initiators.append(app.node.name)
            responders.append(responder)
            start_times.append(start_t)
            end_times.append(end_t)
            memory_sizes.append(memo_size)
            fidelities.append(fidelity)
            paths.append(path)
            throughputs.append(tp)

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
        sync_time = execution_time - tl.computing_time - tl.communication_time1 - tl.communication_time2 - tl.communication_time3
        parallel_perf_info = {
            'computing_time': tl.computing_time,
            'communication_time': tl.communication_time1 + tl.communication_time2 + tl.communication_time3,
            'communication_time1': tl.communication_time1,
            'communication_time2': tl.communication_time2,
            'communication_time3': tl.communication_time3,
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
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('config_file_name', type=str)
    parser.add_argument('log_path', type=str)

    args = parser.parse_args()

    main(args.config_file_name, args.log_path)
