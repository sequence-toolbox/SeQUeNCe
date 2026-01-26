from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.network_management.routing_distributed import DistributedRoutingProtocol
from sequence.topology import router_net_topo
import sequence.utils.log as log
from sequence.constants import SECOND


# Two node toplogy, check the FSM states at both routers.
def test_distributed_routing_protocol_1():
    
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
    # modules = ["routing_distributed"]
    # for module in modules:
    #     log.track_module(module)

    tl.init()
    tl.run()

    # at router 0, the FSM for neighbor 1 should be in Full state
    fsm0_1 = routers[0].network_manager.get_routing_protocol().fsm.get(routers[1].name)
    assert fsm0_1.state == "Full"

    # at router 1, the FSM for neighbor 0 should be in Full state
    fsm1_0 = routers[1].network_manager.get_routing_protocol().fsm.get(routers[0].name)
    assert fsm1_0.state == "Full"


# Four node (R0, R1, R2, R3) ring toplogy, check the FSM states at all four nodes.
def test_distributed_routing_protocol_2():
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
    # modules = ["routing_distributed", "node"]
    # for module in modules:
    #     log.track_module(module)

    tl.init()
    tl.run()

    # at router 0, the FSM for neighbor 1 should be in Full state
    fsm0_1 = routers[0].network_manager.get_routing_protocol().fsm.get(routers[1].name)
    assert fsm0_1.state == "Full"
    # at router 0, the FSM for neighbor 3 should be in Full state
    fsm0_3 = routers[0].network_manager.get_routing_protocol().fsm.get(routers[3].name)
    assert fsm0_3.state == "Full"

    # at router 1, the FSM for neighbor 0 should be in Full state
    fsm1_0 = routers[1].network_manager.get_routing_protocol().fsm.get(routers[0].name)
    assert fsm1_0.state == "Full"
    # at router 1, the FSM for neighbor 2 should be in Full state
    fsm1_2 = routers[1].network_manager.get_routing_protocol().fsm.get(routers[2].name)
    assert fsm1_2.state == "Full"

    # at router 2, the FSM for neighbor 1 should be in Full state
    fsm2_1 = routers[2].network_manager.get_routing_protocol().fsm.get(routers[1].name)
    assert fsm2_1.state == "Full"
    # at router 2, the FSM for neighbor 3 should be in Full state
    fsm2_3 = routers[2].network_manager.get_routing_protocol().fsm.get(routers[3].name)
    assert fsm2_3.state == "Full"

    # at router 3, the FSM for neighbor 2 should be in Full state
    fsm3_2 = routers[3].network_manager.get_routing_protocol().fsm.get(routers[2].name)
    assert fsm3_2.state == "Full"
    # at router 3, the FSM for neighbor 0 should be in Full state
    fsm3_0 = routers[3].network_manager.get_routing_protocol().fsm.get(routers[0].name)
    assert fsm3_0.state == "Full"


# Two node (R0, R1) toplogy, R1 is down after 0.5 second, check the FSM states at both nodes.
def test_distributed_routing_protocol_3():
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

    # at router 0, the FSM for neighbor 1 should be in Down state
    fsm0_1 = routers[0].network_manager.get_routing_protocol().fsm.get(routers[1].name)
    assert fsm0_1.state == "Down"

    # at router 1, the FSM for neighbor 0 should be in Down state
    fsm1_0 = routers[1].network_manager.get_routing_protocol().fsm.get(routers[0].name)
    assert fsm1_0.state == "Down"


# Four node (R0, R1, R2, R3) ring toplogy, R1 is down after 0.5 second, check the FSM states at all four nodes.
def test_distributed_routing_protocol_4():
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
    # modules = ["routing_distributed", "node"]
    # for module in modules:
    #     log.track_module(module)

    tl.init()
    process = Process(routers[1], "set_down", [True])
    event = Event(0.5 * SECOND, process)
    tl.schedule(event)

    tl.run()

    # at router 0, the FSM for neighbor 1 should be in Down state
    fsm0_1 = routers[0].network_manager.get_routing_protocol().fsm.get(routers[1].name)
    assert fsm0_1.state == "Down"
    # at router 0, the FSM for neighbor 3 should be in Full state
    fsm0_3 = routers[0].network_manager.get_routing_protocol().fsm.get(routers[3].name)
    assert fsm0_3.state == "Full"

    # at router 1, the FSM for neighbor 0 should be in Down state
    fsm1_0 = routers[1].network_manager.get_routing_protocol().fsm.get(routers[0].name)
    assert fsm1_0.state == "Down"
    # at router 1, the FSM for neighbor 2 should be in Down state
    fsm1_2 = routers[1].network_manager.get_routing_protocol().fsm.get(routers[2].name)
    assert fsm1_2.state == "Down"

    # at router 2, the FSM for neighbor 1 should be in Down state
    fsm2_1 = routers[2].network_manager.get_routing_protocol().fsm.get(routers[1].name)
    assert fsm2_1.state == "Down"
    # at router 2, the FSM for neighbor 3 should be in Full state
    fsm2_3 = routers[2].network_manager.get_routing_protocol().fsm.get(routers[3].name)
    assert fsm2_3.state == "Full"

    # at router 3, the FSM for neighbor 2 should be in Full state
    fsm3_2 = routers[3].network_manager.get_routing_protocol().fsm.get(routers[2].name)
    assert fsm3_2.state == "Full"
    # at router 3, the FSM for neighbor 0 should be in Full state
    fsm3_0 = routers[3].network_manager.get_routing_protocol().fsm.get(routers[0].name)
    assert fsm3_0.state == "Full"



# test_distributed_routing_protocol_1()
# test_distributed_routing_protocol_2()
# test_distributed_routing_protocol_3()
# test_distributed_routing_protocol_4()