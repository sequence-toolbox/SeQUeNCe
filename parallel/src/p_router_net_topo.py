from mpi4py import MPI
from sequence.topology.topology import Topology as Topo
from sequence.topology.router_net_topo import RouterNetTopo
from sequence.topology.node import QuantumRouter, BSMNode

from .p_timeline import ParallelTimeline


class ParallelRouterNetTopo(RouterNetTopo):
    def _add_timeline(self, config):
        stop_time = config.get(Topo.STOP_TIME, float('inf'))
        assert MPI.COMM_WORLD.Get_size() == config[self.PROC_NUM]
        lookahead = config[self.LOOKAHEAD]
        ip = config[self.IP]
        port = config[self.PORT]
        self.tl = ParallelTimeline(lookahead, qm_ip=ip, qm_port=port, stop_time=stop_time)

    def _add_nodes(self, config):
        rank = MPI.COMM_WORLD.Get_rank()
        size = MPI.COMM_WORLD.Get_size()

        for node in config[Topo.ALL_NODE]:
            seed, type = node[Topo.SEED], node[Topo.TYPE],
            group, name = node.get(self.GROUP, 0), node[Topo.NAME]
            assert group < size, "Group id is out of scope" \
                                 " ({} >= {}).".format(group, size)
            if group == rank:
                if type == self.BSM_NODE:
                    others = self.bsm_to_router_map[name]
                    node_obj = BSMNode(name, self.tl, others)
                elif type == self.QUANTUM_ROUTER:
                    memo_size = node.get(self.MEMO_ARRAY_SIZE, 0)
                    if memo_size:
                        node_obj = QuantumRouter(name, self.tl, memo_size)
                    else:
                        print("WARN: the size of memory on quantum router {} "
                              "is not set".format(name))
                        node_obj = QuantumRouter(name, self.tl)
                else:
                    raise NotImplementedError("Unknown type of node")

                node_obj.set_seed(seed)
                if type in self.nodes:
                    self.nodes[type].append(node_obj)
                else:
                    self.nodes[type] = [node_obj]
            else:
                self.tl.add_foreign_entity(name, group)
