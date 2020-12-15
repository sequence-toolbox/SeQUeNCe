from sequence.kernel.p_timeline import ParallelTimeline
from sequence.kernel.quantum_manager_server import kill_server
from sequence.topology.node import QuantumRouter, BSMNode
from sequence.components.optical_channel import ClassicalChannel, \
    QuantumChannel
from sequence.app.random_request import RandomRequestApp
import sequence.utils.log as log


def generate_network(ring_size: int, lookahead: int, stop_time: int, rank: int,
                     mpi_size: int, qm_ip: str, qm_port: int, kill=True):
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
            node = QuantumRouter(node_name, tl)
            routers.append(node)
        else:
            tl.foreign_entities[node_name] = node_id // group_size

    for bsm_id in range(ring_size):
        node_name = "BSM_%d" % bsm_id
        if bsm_id // group_size == rank:
            node = QuantumRouter(node_name, tl)
            bsm_nodes.append(node)
        else:
            tl.foreign_entities[node_name] = bsm_id // group_size

    for src in routers + bsm_nodes:
        for dst_index in range(ring_size):
            dst_name = "Node_%d" % dst_index
            if dst_name != src.name:
                cc = ClassicalChannel("cc_%s_%s" %
                                      (src.name, dst_name), tl, 20000, 1e9)
                cc.set_ends(src, dst_name)

            dst_name = "BSM_%d" % dst_index
            if dst_name != src.name:
                cc = ClassicalChannel("cc_%s_%s" %
                                      (src.name, dst_name), tl, 20000, 1e9)
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

    apps = []
    for i, node in enumerate(routers):
        app_node_name = node.name
        others = router_names[:]
        others.remove(app_node_name)
        app = RandomRequestApp(node, others, i, 1e13, 2e13, 10, 25, 0.8, 1.0)
        apps.append(app)
        app.start()

    tl.init()
    tl.run()

    if kill:
        kill_server(qm_pi, qm_port)

    print(tl.now(), len(tl.events))


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
                        help='the lookahead of parallel simulation; the longer lookahead generate the longer quantum channel')
    parser.add_argument('stop_time', type=int,
                        help='the time of stopping the simulation')

    args = parser.parse_args()

    generate_network(args.ring_size, args.lookahead, args.stop_time, rank,
                     size, args.ip, args.port)

