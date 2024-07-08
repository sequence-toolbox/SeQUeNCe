import numpy as np

# Basic components
from sequence.kernel.timeline import Timeline
from sequence.topology.node import Node
from sequence.components.memory import Memory

# Log utility
import sequence.utils.log as log
from sequence.utils import log


def generate_g_state(num_memories):
    # Calculate the constant value
    constant = 1 / np.sqrt(2 ** num_memories)
    
    # Initialize the GHZ state vector
    g_state = np.zeros(2 ** num_memories)
    
    # Iterate over all possible binary strings
    for i in range(2 ** num_memories):
        binary_str = format(i, '0' + str(num_memories) + 'b')
        
        # Count occurrences of two consecutive '1's
        count_consecutive_ones = sum(1 for j in range(len(binary_str) - 1) if binary_str[j] == '1' and binary_str[j + 1] == '1')
        
        # Set the value in the GHZ state vector
        if count_consecutive_ones % 2 == 1:
            g_state[i] = -constant
        else:
            g_state[i] = constant
            
    return g_state

def entangle_memory(tl: Timeline, memories: list, n: int):

    # square root of 1/2
    #SQRT_HALF = 0.5 ** 0.5

    # 1/sqrt(2)|000> + 0 +...+ 0 + 1/sqrt(2)|111>
    g_state = generate_g_state(n)

    # Resetting the memories
    for memo in memories:
        memo.reset()

    # Setting the GHZ state
    qstate_keys = [memo.qstate_key for memo in memories]
    tl.quantum_manager.set(qstate_keys, g_state)


def qlan_entangle_memory(tl: Timeline, local_memories: list, remote_memories: list, n: int):

    # 1/sqrt(2)|000> + 0 +...+ 0 + 1/sqrt(2)|111>
    g_state = generate_g_state(n)

    # Resetting the memories
    for memo in local_memories:
        memo.reset()
    for memo in remote_memories:
        memo.reset()

    # DEBUG
    # for i in range(len(remote_memories)):
    #    print(remote_memories[i].qstate_key)

    #for i in range(len(local_memories)):
    #    print(local_memories[i].qstate_key)


    combined_memories = []
    min_size = min(len(remote_memories), len(local_memories))
    for i in range(min_size):
        combined_memories.append(remote_memories[i])
        combined_memories.append(local_memories[i])

    # Add remaining memories from the longer list
    if len(remote_memories) > len(local_memories):
        combined_memories.extend(remote_memories[min_size:])
    else:
        combined_memories.extend(local_memories[min_size:])

    # DEBUG
    # for memo in combined_memories:
    #    print(memo.qstate_key)

    qstate_keys = [memo.qstate_key for memo in combined_memories]
    # print(qstate_keys)
    tl.quantum_manager.set(qstate_keys, g_state)