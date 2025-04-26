
from sequence.kernel.timeline import Timeline
from sequence.components.memory import Memory
from sequence.topology.qlan.orchestrator import QlanOrchestratorNode

def test_find_adjacent_nodes():
    tl = Timeline()
    remote_memo_1 = Memory('remote_memo_1', tl, 1, 2000, 1, -1, 500)
    remote_memo_2 = Memory('remote_memo_2', tl, 1, 2000, 1, -1, 500)
    remote_memo_3 = Memory('remote_memo_3', tl, 1, 2000, 1, -1, 500)
        
    Orchestrator = QlanOrchestratorNode("node1", tl, num_local_memories=2, remote_memories=[remote_memo_1, remote_memo_2, remote_memo_3])
        
    Orchestrator.find_adjacent_nodes(tl, Orchestrator.remote_memories)
    assert list(Orchestrator.adjacent_nodes.values()) == [[0,1],[1,2]]


def test_update_bases():
    bases = "XYZ"
    tl = Timeline()
    remote_memo_1 = Memory('remote_memo_1', tl, 1, 2000, 1, -1, 500)
    remote_memo_2 = Memory('remote_memo_2', tl, 1, 2000, 1, -1, 500)
    remote_memo_3 = Memory('remote_memo_3', tl, 1, 2000, 1, -1, 500)
    remote_memo_4 = Memory('remote_memo_4', tl, 1, 2000, 1, -1, 500)
        
    Orchestrator = QlanOrchestratorNode("node1", tl, num_local_memories=3, remote_memories=[remote_memo_1, remote_memo_2, remote_memo_3, remote_memo_4])
        
    assert Orchestrator.bases == 'zzz'
    Orchestrator.update_bases(bases)
    assert Orchestrator.bases == bases


def test_set_app():
    app = "RequestApp"
    tl = Timeline()
    remote_memo_1 = Memory('remote_memo_1', tl, 1, 2000, 1, -1, 500)
    Orchestrator = QlanOrchestratorNode("node1", tl, num_local_memories=0, remote_memories=[remote_memo_1])
    Orchestrator.set_app(app)
    assert Orchestrator.app == app


def test_reset_linear_state():
    target_3 = [0.35355339059327373+0.j,  0.35355339059327373+0.j, 
                0.35355339059327373+0.j, -0.35355339059327373+0.j, 
                0.35355339059327373+0.j,  0.35355339059327373+0.j, 
                -0.35355339059327373+0.j,  0.35355339059327373+0.j]
    tl = Timeline()
    remote_memo_1 = Memory('remote_memo_1', tl, 1, 2000, 1, -1, 500)
    remote_memo_2 = Memory('remote_memo_2', tl, 1, 2000, 1, -1, 500)
    Orchestrator = QlanOrchestratorNode("node1", tl, num_local_memories=1, remote_memories=[remote_memo_1, remote_memo_2])
    Orchestrator.reset_linear_state(tl)
        
    assert target_3 == list(tl.quantum_manager.states[0].state) == list(tl.quantum_manager.states[1].state) == list(tl.quantum_manager.states[2].state)


def test_generate_chain_state():

    target_3 = [0.35355339059327373+0.j,  0.35355339059327373+0.j, 
                0.35355339059327373+0.j, -0.35355339059327373+0.j, 
                0.35355339059327373+0.j,  0.35355339059327373+0.j, 
                -0.35355339059327373+0.j,  0.35355339059327373+0.j]

    tl = Timeline()
    remote_memo_1 = Memory('remote_memo_1', tl, 1, 2000, 1, -1, 500)
    remote_memo_2 = Memory('remote_memo_2', tl, 1, 2000, 1, -1, 500)
    Orchestrator = QlanOrchestratorNode("node1", tl, num_local_memories=1, remote_memories=[remote_memo_1, remote_memo_2])
        
    Orchestrator.resource_manager.generate_chain_state(tl=tl, local_memories=Orchestrator.local_memories, remote_memories=Orchestrator.remote_memories)
        
    assert list(Orchestrator.adjacent_nodes.values()) == [[0,1]]
    assert target_3 == list(tl.quantum_manager.states[0].state) == list(tl.quantum_manager.states[1].state) == list(tl.quantum_manager.states[2].state)
