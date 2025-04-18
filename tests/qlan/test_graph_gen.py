
from matplotlib.pylab import randint
from sequence.qlan.graph_gen import generate_g_state, entangle_memory, qlan_entangle_memory
from sequence.components.circuit import Circuit
from sequence.kernel.timeline import Timeline
from sequence.components.memory import Memory


def check_minus_and_numeric_values(g1, g2):
    m1 = 0
    m2 = 0
    for i in range(len(g1)):
        if g1[i].real < 0:
            m1 += 1
        assert round(abs(g1[i].real), 2) == round(abs(g2[i].real), 2)
    for i in range(len(g2)):
        if g2[i].real < 0:
            m2 += 1
        assert round(abs(g1[i].real), 2) == round(abs(g2[i].real), 2)
        print("G1: ",g1[i]," G2: ",g2[i])
    assert m1 == m2


def test_generate_g_state():
        
    tl = Timeline()

    for num_memories in range(1,10):
        dummy_memories = []       
        g_state = generate_g_state(num_memories)
        g_state = [complex(x) for x in g_state]
        assert len(g_state) == 2 ** num_memories
        
        qc = Circuit(num_memories)
        for i in range(num_memories):
            dumy_memo = Memory(f'dummy_memo_{num_memories}_{i}', tl, 1, 2000, 1, -1, 500)
            dummy_memories.append(dumy_memo.qstate_key)
            qc.h(i)

        for i in range(num_memories - 1):
            qc.cz(i, (i + 1))

        tl.quantum_manager.run_circuit(circuit=qc, keys=dummy_memories)
        expected_result = list(tl.quantum_manager.states[max(dummy_memories)].state)

        assert (len(expected_result) == len(g_state))
        check_minus_and_numeric_values(g_state, expected_result)


def test_qlan_entangle_memory():
    
    tl = Timeline()
    local_memo_1 = Memory('local_memo_1', tl, 1, 2000, 1, -1, 500)
    local_memo_2 = Memory('local_memo_2', tl, 1, 2000, 1, -1, 500)
    remote_memo_1 = Memory('remote_memo_1', tl, 1, 2000, 1, -1, 500)
    remote_memo_2 = Memory('remote_memo_2', tl, 1, 2000, 1, -1, 500)
		
    local_memories = [local_memo_1, local_memo_2]
    remote_memories = [remote_memo_1, remote_memo_2]
    n = 4

    qlan_entangle_memory(tl, local_memories, remote_memories, n)
    
    for memo in local_memories + remote_memories:
        assert memo.qstate_key in tl.quantum_manager.states
    
    combined_memories = []
    combined_memories = [remote_memories[0], local_memories[0], remote_memories[1], local_memories[1]]

    keys = [memo.qstate_key for memo in combined_memories]

    for i in range(0, len(keys)-1,2):
        assert keys[i] > keys[i+1]

    g_state = tl.quantum_manager.states[0].state
    qstate_keys = [memo.qstate_key for memo in combined_memories]

    qc = Circuit(n)
    for i in range(n):
        qc.h(i)
    for i in range(n - 1):
        qc.cz(i, (i + 1))
    
    tl.quantum_manager.run_circuit(circuit=qc, keys=qstate_keys)
    expected_result = list(tl.quantum_manager.states[min(qstate_keys)].state)

    assert (len(expected_result) == len(g_state))
    check_minus_and_numeric_values(g_state, expected_result)