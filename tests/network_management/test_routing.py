from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.network_management.routing_distributed import DistributedRoutingProtocol
from sequence.topology import router_net_topo
import sequence.utils.log as log
from sequence.constants import SECOND


def test_distributed_routing_protocol_1():
    '''Two node toplogy, router 1 is down after 0.5 second, check the FSM states at both routers.
    '''
    topo = router_net_topo.RouterNetTopo("tests/network_management/line_topo.json")
    all_nodes = topo.get_nodes()
    routers = all_nodes[router_net_topo.RouterNetTopo.QUANTUM_ROUTER]
    for router in routers:
        routing_protocol = router.network_manager.get_routing_protocol()
        assert isinstance(routing_protocol, DistributedRoutingProtocol)
    
    tl = topo.get_timeline()

    # log_filename = "tests/network_management/test_distributed_routing_protocol.log"
    # log.set_logger(__name__, tl, log_filename)
    # log.set_logger_level('DEBUG')
    # modules = ["routing_distributed", "node"]
    # for module in modules:
    #     log.track_module(module)

    tl.init()
    process = Process(routers[1], "set_down", [True])
    event = Event(0.5 * SECOND, process)
    tl.schedule(event)
    tl.run()

    # the FSM at router 0 for neighbor 1 should be in Down state
    fsm0_1 = routers[0].network_manager.get_routing_protocol().fsm.get(routers[1].name)
    assert fsm0_1.state == "Down"

    # the FSM at router 1 for neighbor 0 should be in Down state
    fsm1_0 = routers[1].network_manager.get_routing_protocol().fsm.get(routers[0].name)
    assert fsm1_0.state == "Down"


# test_distributed_routing_protocol_1()
