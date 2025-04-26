import numpy as np
from ..kernel.timeline import Timeline


def generate_g_state(num_memories):
    constant = 1 / np.sqrt(2 ** num_memories)
    g_state = np.zeros(2 ** num_memories)
    
    for i in range(2 ** num_memories):
        binary_str = format(i, '0' + str(num_memories) + 'b')
        count_consecutive_ones = sum(1 for j in range(len(binary_str) - 1) if binary_str[j] == '1' and binary_str[j + 1] == '1')

        if count_consecutive_ones % 2 == 1:
            g_state[i] = -constant
        else:
            g_state[i] = constant
            
    return g_state


def entangle_memory(tl: Timeline, memories: list, n: int):

    # 1/sqrt(2)|000> + 0 +...+ 0 + 1/sqrt(2)|111>
    g_state = generate_g_state(n)

    for memo in memories:
        memo.reset()

    qstate_keys = [memo.qstate_key for memo in memories]
    tl.quantum_manager.set(qstate_keys, g_state)


def qlan_entangle_memory(tl: Timeline, local_memories: list, remote_memories: list, n: int):

    # 1/sqrt(2)|000> + 0 +...+ 0 + 1/sqrt(2)|111>
    g_state = generate_g_state(n)

    for memo in local_memories:
        memo.reset()
    for memo in remote_memories:
        memo.reset()

    combined_memories = []
    min_size = min(len(remote_memories), len(local_memories))
    for i in range(min_size):
        combined_memories.append(remote_memories[i])
        combined_memories.append(local_memories[i])

    if len(remote_memories) > len(local_memories):
        combined_memories.extend(remote_memories[min_size:])
    else:
        combined_memories.extend(local_memories[min_size:])

    qstate_keys = [memo.qstate_key for memo in combined_memories]
    tl.quantum_manager.set(qstate_keys, g_state)