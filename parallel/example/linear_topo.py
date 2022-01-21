import pandas as pd
from time import time
from json import dump, load

from sequence.topology.router_net_topo import RouterNetTopo
from sequence.app.request_app import RequestApp


def main(config_file: str, src: str, dst: str, start_t: int, end_t: int,
         memo_size: int, fidelity: float, log_path: str):
    RAW_FIDELITY = 1
    SWAP_DEG_RATE = 1
    MEMO_FREQ = 2e4
    MEMO_EFF = 0.75
    MEMO_TIME = 1.3
    topo = RouterNetTopo(config_file)
    tl = topo.get_timeline()
    tl.stop_time = end_t + 1
    tl.lookahead = 5e8
    routers = topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER)

    for router in routers:
        router.memory_array.update_memory_params('raw_fidelity', RAW_FIDELITY)
        router.memory_array.update_memory_params('frequency', MEMO_FREQ)
        router.memory_array.update_memory_params('efficiency', MEMO_EFF)
        router.memory_array.update_memory_params('coherence_time', MEMO_TIME)

        router.network_manager.protocol_stack[1].set_swapping_degradation(
            SWAP_DEG_RATE)

    src_app = None
    for r in routers:
        if r.name == src or r.name == dst:
            app = RequestApp(r)
            if r.name == src:
                app.start(dst, start_t, end_t, memo_size, fidelity)
                src_app = app
                print("start request at node", r.name)

    tick = time()
    tl.init()
    prepare_time = time() - tick

    tick = time()
    tl.run()
    execution_time = time() - tick

    tl.quantum_manager.disconnect_from_server()

    if src_app:
        traffic_info = {"Initiator": src, "Responder": dst,
                        "Start_time": start_t, "End_time": end_t,
                        "Memory_size": memo_size, "Fidelity": fidelity,
                        "Path": [src_app.path],
                        "Throughput": src_app.get_throughput()}

        df = pd.DataFrame(traffic_info)
        df.to_csv(log_path + "/linear_traffic.csv")

    # write information of parallelization performance into log_path/perf.json file
    sync_time = execution_time - tl.computing_time - tl.communication_time
    perf_info = {'prepare_time': prepare_time,
                 'execution_time': execution_time,
                 'computing_time': tl.computing_time,
                 'communication_time': tl.communication_time,
                 'io_time': tl.quantum_manager.io_time,
                 'sync_time': sync_time,
                 'sync_counter': tl.sync_counter,
                 'event_counter': tl.run_counter,
                 'schedule_counter': tl.schedule_counter,
                 'exchange_counter': tl.exchange_counter}

    with open('%s/linear_perf_%d.json' % (log_path, tl.id), 'w') as fh:
        dump(perf_info, fh)


if __name__ == "__main__":
    main("linear_32.json", "router_0", "router_31", 100e12, 100.1e12,
         50, 0.9, "log")
