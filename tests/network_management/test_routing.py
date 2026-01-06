from sequence.network_management.routing import DistributedRoutingProtocol
from sequence.topology import router_net_topo
import sequence.utils.log as log

def test_distributed_routing_protocol():
    topo = router_net_topo.RouterNetTopo("tests/network_management/ring_topo.json")
    all_nodes = topo.get_nodes()
    routers = all_nodes[router_net_topo.RouterNetTopo.QUANTUM_ROUTER]
    for router in routers:
        routing_protocol = router.network_manager.get_routing_protocol()
        assert isinstance(routing_protocol, DistributedRoutingProtocol)
    
    tl = topo.get_timeline()

    # log_filename = "tests/network_management/test_distributed_routing_protocol.log"
    # log.set_logger(__name__, tl, log_filename)
    # log.set_logger_level('DEBUG')
    # modules = ["routing"]
    # for module in modules:
    #     log.track_module(module)

    tl.init()
    tl.run()



test_distributed_routing_protocol()
