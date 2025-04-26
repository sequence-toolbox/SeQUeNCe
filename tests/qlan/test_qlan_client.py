from sequence.kernel.timeline import Timeline
from sequence.topology.qlan.client import QlanClientNode
from sequence.topology.qlan.orchestrator import QlanOrchestratorNode


def test_update_orchestrator_valid():
        
    tl = Timeline()
    client1 = QlanClientNode(name='test_client1', tl=tl, num_local_memories=1)
    client2 = QlanClientNode(name='test_client2', tl=tl, num_local_memories=1)
    
    client1_memo = client1.get_components_by_type("Memory")[0]
    client2_memo = client2.get_components_by_type("Memory")[0]

    orchestrator = QlanOrchestratorNode("node1", tl, num_local_memories=1, remote_memories=[client1_memo, client2_memo])

    client1.update_orchestrator(orchestrator.local_memory_names)
    client2.update_orchestrator(orchestrator.local_memory_names)

    assert client1.resource_manager.remote_memories == client1.remote_memories == client2.resource_manager.remote_memories == client2.remote_memories


def test_update_orchestrator_invalid():
    tl = Timeline()
    client1 = QlanClientNode(name='test_client1', tl=tl, num_local_memories=1)
    
    dumb_memo = []  # or some invalid state

    try:
        client1.update_orchestrator(dumb_memo)
    except ValueError:
        assert True, "ValueError is raised as expected"
