from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.network_management.routing_distributed import DistributedRoutingProtocol
from sequence.topology import router_net_topo
import sequence.utils.log as log
from sequence.constants import SECOND


# Two node topology, check the FSM states and forwarding tables at both routers
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

    # 1) First check the FSM states at both nodes

    # at router 0, the FSM for neighbor 1 should be in Full state
    fsm0_1 = routers[0].network_manager.get_routing_protocol().fsm.get(routers[1].name)
    assert fsm0_1.state == "Full"
   
    # at router 1, the FSM for neighbor 0 should be in Full state
    fsm1_0 = routers[1].network_manager.get_routing_protocol().fsm.get(routers[0].name)
    assert fsm1_0.state == "Full"

    # 2) Then check the forwarding tables at both nodes

    # at router 0, the next hop to router 1 is router 1
    forwarding_table_0 = routers[0].network_manager.get_forwarding_table()
    assert forwarding_table_0[routers[1].name] == routers[1].name

    # at router 1, the next hop to router 0 is router 0
    forwarding_table_1 = routers[1].network_manager.get_forwarding_table()
    assert forwarding_table_1[routers[0].name] == routers[0].name


# Four node (R0, R1, R2, R3) ring topology, 
# check the FSM states and forwarding tables at all four nodes.
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
    # log.set_logger_level('INFO')
    # modules = ["routing_distributed"]
    # for module in modules:
    #     log.track_module(module)

    tl.init()
    tl.run()

    # 1) First check the FSM states at all four nodes

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

    # 2) Then check the forwarding tables at all four nodes

    forwarding_table_0 = routers[0].network_manager.get_forwarding_table()
    # at router 0, the next hop to router 1 is router 1
    assert forwarding_table_0[routers[1].name] == routers[1].name
    # at router 0, the next hop to router 2 is router 3
    assert forwarding_table_0[routers[2].name] == routers[3].name
    # at router 0, the next hop to router 3 is router 3
    assert forwarding_table_0[routers[3].name] == routers[3].name

    forwarding_table_1 = routers[1].network_manager.get_forwarding_table()
    # at router 1, the next hop to router 0 is router 0
    assert forwarding_table_1[routers[0].name] == routers[0].name
    # at router 1, the next hop to router 2 is router 2
    assert forwarding_table_1[routers[2].name] == routers[2].name
    # at router 1, the next hop to router 3 is router 2
    assert forwarding_table_1[routers[3].name] == routers[2].name

    forwarding_table_2 = routers[2].network_manager.get_forwarding_table()
    # at router 2, the next hop to router 0 is router 3
    assert forwarding_table_2[routers[0].name] == routers[3].name
    # at router 2, the next hop to router 1 is router 1
    assert forwarding_table_2[routers[1].name] == routers[1].name
    # at router 2, the next hop to router 3 is router 3
    assert forwarding_table_2[routers[3].name] == routers[3].name

    # at router 3, the next hop to router 0 is router 0
    forwarding_table_3 = routers[3].network_manager.get_forwarding_table()
    assert forwarding_table_3[routers[0].name] == routers[0].name
    # at router 3, the next hop to router 1 is router 2
    assert forwarding_table_3[routers[1].name] == routers[2].name
    # at router 3, the next hop to router 2 is router 2
    assert forwarding_table_3[routers[2].name] == routers[2].name


# Two node (R0, R1) topology
# R1 is down after 0.5 second, 
# check the FSM states and forwarding tables at both nodes.
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

    # 1) First check the FSM states at both nodes

    # at router 0, the FSM for neighbor 1 should be in Down state
    fsm0_1 = routers[0].network_manager.get_routing_protocol().fsm.get(routers[1].name)
    assert fsm0_1.state == "Down"
    
    # at router 1, the FSM for neighbor 0 should be in Down state
    fsm1_0 = routers[1].network_manager.get_routing_protocol().fsm.get(routers[0].name)
    assert fsm1_0.state == "Down"

    # 2) Then check the forwarding tables at both nodes

    # at router 0, the next hop to router 1 is not in forwarding table
    forwarding_table_0 = routers[0].network_manager.get_forwarding_table()
    assert routers[1].name not in forwarding_table_0

    # at router 1, the next hop to router 0 is not in forwarding table
    forwarding_table_1 = routers[1].network_manager.get_forwarding_table()
    assert routers[0].name not in forwarding_table_1


# Four node (R0, R1, R2, R3) ring topology
# R2 is down after 0.5 second,
# check the FSM states & Forwarding table at all four nodes.
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
    # log.set_logger_level('INFO')
    # modules = ["routing_distributed"]
    # for module in modules:
    #     log.track_module(module)

    tl.init()
    process = Process(routers[2], "set_down", [True])
    event = Event(0.5 * SECOND, process)
    tl.schedule(event)

    tl.run()

    # 1) First check the FSM states at all four nodes

    # at router 0, the FSM for neighbor 1 should be in Full state
    fsm0_1 = routers[0].network_manager.get_routing_protocol().fsm.get(routers[1].name)
    assert fsm0_1.state == "Full"
    # at router 0, the FSM for neighbor 3 should be in Full state
    fsm0_3 = routers[0].network_manager.get_routing_protocol().fsm.get(routers[3].name)
    assert fsm0_3.state == "Full"

    # at router 1, the FSM for neighbor 0 should be in Full state
    fsm1_0 = routers[1].network_manager.get_routing_protocol().fsm.get(routers[0].name)
    assert fsm1_0.state == "Full"
    # at router 1, the FSM for neighbor 2 should be in Down state
    fsm1_2 = routers[1].network_manager.get_routing_protocol().fsm.get(routers[2].name)
    assert fsm1_2.state == "Down"

    # at router 2, the FSM for neighbor 1 should be in Down state
    fsm2_1 = routers[2].network_manager.get_routing_protocol().fsm.get(routers[1].name)
    assert fsm2_1.state == "Down"
    # at router 2, the FSM for neighbor 3 should be in Down state
    fsm2_3 = routers[2].network_manager.get_routing_protocol().fsm.get(routers[3].name)
    assert fsm2_3.state == "Down"

    # at router 3, the FSM for neighbor 2 should be in Down state
    fsm3_2 = routers[3].network_manager.get_routing_protocol().fsm.get(routers[2].name)
    assert fsm3_2.state == "Down"
    # at router 3, the FSM for neighbor 0 should be in Full state
    fsm3_0 = routers[3].network_manager.get_routing_protocol().fsm.get(routers[0].name)
    assert fsm3_0.state == "Full"

    # 2) Then check the forwarding tables at all four nodes
    forwarding_table_0 = routers[0].network_manager.get_forwarding_table()
    # at router 0, the next hop to router 1 is router 1
    assert forwarding_table_0[routers[1].name] == routers[1].name
    # at router 0, the next hop to router 2 is not in forwarding table
    assert routers[2].name not in forwarding_table_0
    # at router 0, the next hop to router 3 is router 3
    assert forwarding_table_0[routers[3].name] == routers[3].name

    forwarding_table_1 = routers[1].network_manager.get_forwarding_table()
    # at router 1, the next hop to router 0 is router 0
    assert forwarding_table_1[routers[0].name] == routers[0].name
    # at router 1, the next hop to router 2 is not in forwarding table
    assert routers[2].name not in forwarding_table_1
    # at router 1, the next hop to router 3 is router 0
    assert forwarding_table_1[routers[3].name] == routers[0].name

    forwarding_table_2 = routers[2].network_manager.get_forwarding_table()
    # at router 2, the next hop to router 0 is not in forwarding table
    assert routers[0].name not in forwarding_table_2
    # at router 2, the next hop to router 1 is not in forwarding table
    assert routers[1].name not in forwarding_table_2
    # at router 2, the next hop to router 3 is not in forwarding table
    assert routers[3].name not in forwarding_table_2

    forwarding_table_3 = routers[3].network_manager.get_forwarding_table()
    # at router 3, the next hop to router 0 is router 0
    assert forwarding_table_3[routers[0].name] == routers[0].name
    # at router 3, the next hop to router 1 is router 0
    assert forwarding_table_3[routers[1].name] == routers[0].name
    # at router 3, the next hop to router 2 is not in forwarding table
    assert routers[2].name not in forwarding_table_3


# Two node (R0, R1) topology, LSA refresh is turned off
# Corner case: the MAX_AGE is very small (0.002 second),
# check the FSM states and forwarding tables at both nodes.
def test_distributed_routing_protocol_5():

    topo = router_net_topo.RouterNetTopo("tests/network_management/line_topo.json")
    all_nodes = topo.get_nodes()
    routers = all_nodes[router_net_topo.RouterNetTopo.QUANTUM_ROUTER]
    DistributedRoutingProtocol.MAX_AGE = int(0.002 * SECOND)
    for router in routers:
        routing_protocol = router.network_manager.get_routing_protocol()
        routing_protocol.refresh_enabled = False
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

    # 1) First check the FSM states at both nodes

    # at router 0, the FSM for neighbor 1 should be in Loading state
    fsm0_1 = routers[0].network_manager.get_routing_protocol().fsm.get(routers[1].name)
    assert fsm0_1.state == "Loading"
    
    # at router 1, the FSM for neighbor 0 should be in Loading state
    fsm1_0 = routers[1].network_manager.get_routing_protocol().fsm.get(routers[0].name)
    assert fsm1_0.state == "Loading"

    # 2) Then check the forwarding tables at both nodes

    # at router 0, the next hop to router 1 is not in forwarding table
    forwarding_table_0 = routers[0].network_manager.get_forwarding_table()
    assert routers[1].name not in forwarding_table_0

    # at router 1, the next hop to router 0 is not in forwarding table
    forwarding_table_1 = routers[1].network_manager.get_forwarding_table()
    assert routers[0].name not in forwarding_table_1


# Two node (R0, R1) topology, LSA refresh is turned off
# the MAX_AGE is 50 seconds, while the simulation time is 100 seconds,
# check the FSM states and forwarding tables at both nodes.
def test_distributed_routing_protocol_6():

    topo = router_net_topo.RouterNetTopo("tests/network_management/line_topo.json")
    all_nodes = topo.get_nodes()
    routers = all_nodes[router_net_topo.RouterNetTopo.QUANTUM_ROUTER]
    DistributedRoutingProtocol.MAX_AGE = int(50 * SECOND)
    for router in routers:
        routing_protocol = router.network_manager.get_routing_protocol()
        routing_protocol.refresh_enabled = False
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

    # 1) First check the FSM states at both nodes

    # at router 0, the FSM for neighbor 1 should be in Full state
    fsm0_1 = routers[0].network_manager.get_routing_protocol().fsm.get(routers[1].name)
    assert fsm0_1.state == "Full"
    
    # at router 1, the FSM for neighbor 0 should be in Full state
    fsm1_0 = routers[1].network_manager.get_routing_protocol().fsm.get(routers[0].name)
    assert fsm1_0.state == "Full"

    # 2) Then check the forwarding tables at both nodes

    # at router 0, the next hop to router 1 is not in forwarding table
    forwarding_table_0 = routers[0].network_manager.get_forwarding_table()
    assert routers[1].name not in forwarding_table_0

    # at router 1, the next hop to router 0 is not in forwarding table
    forwarding_table_1 = routers[1].network_manager.get_forwarding_table()
    assert routers[0].name not in forwarding_table_1


# Two node (R0, R1) topology, LSA refresh is turned on
# the MAX_AGE is 50 seconds, while the simulation time is 100 seconds,
# check the FSM states, forwarding tables, and LSDB seq_number at both nodes.
def test_distributed_routing_protocol_7():

    DistributedRoutingProtocol.MAX_AGE = int(50 * SECOND)
    topo = router_net_topo.RouterNetTopo("tests/network_management/line_topo.json")
    all_nodes = topo.get_nodes()
    routers = all_nodes[router_net_topo.RouterNetTopo.QUANTUM_ROUTER]
    for router in routers:
        routing_protocol = router.network_manager.get_routing_protocol()
        routing_protocol.refresh_enabled = True
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

    # 1) First check the FSM states at both nodes

    # at router 0, the FSM for neighbor 1 should be in Full state
    fsm0_1 = routers[0].network_manager.get_routing_protocol().fsm.get(routers[1].name)
    assert fsm0_1.state == "Full"
    
    # at router 1, the FSM for neighbor 0 should be in Full state
    fsm1_0 = routers[1].network_manager.get_routing_protocol().fsm.get(routers[0].name)
    assert fsm1_0.state == "Full"

    # 2) Then check the forwarding tables at both nodes

    # at router 0, the next hop to router 1 is router_1
    forwarding_table_0 = routers[0].network_manager.get_forwarding_table()
    assert forwarding_table_0[routers[1].name] == routers[1].name

    # at router 1, the next hop to router 0 is router_0
    forwarding_table_1 = routers[1].network_manager.get_forwarding_table()
    assert forwarding_table_1[routers[0].name] == routers[0].name

    # 3) Last, check the LSDB seq_number at both nodes

    # at router 0, the LSDB seq_number should be 4 (started at 0, incremented at 0s, 25s, 50s, 75s)
    lsdb_seq_number_0 = routers[0].network_manager.get_routing_protocol().seq_number
    assert lsdb_seq_number_0 == 4

    # at router 1, the LSDB seq_number should be 4 (started at 0, incremented at 0s, 25s, 50s, 75s)
    lsdb_seq_number_1 = routers[1].network_manager.get_routing_protocol().seq_number
    assert lsdb_seq_number_1 == 4


# test_distributed_routing_protocol_1()
# test_distributed_routing_protocol_2()
# test_distributed_routing_protocol_3()
# test_distributed_routing_protocol_4()
# test_distributed_routing_protocol_5()
# test_distributed_routing_protocol_6()
# test_distributed_routing_protocol_7()
