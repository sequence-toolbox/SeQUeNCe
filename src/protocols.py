from abc import ABC, abstractmethod

class Protocol(ABC):

    def __init__(self, own, parent_protocols=[], child_protocols=[]):
        self.parent_protocols = parent_protocols
        self.child_protocols = child_protocols
        self.own = own

    @abstractmethod
    def pop(self):
        '''
        information generated in current protocol is poped to all its parents protocols
        '''
        pass

    @abstractmethod
    def push(self):
        '''
        information generated in current protocol is pushed to all its child protocols
        '''
        pass

class EntanglementGeneration(Protocol):

    def __init__(self, own, parent_protocols=[], child_protocols=[]):
        Protocol.__init__(own, parent_protocols, child_protocols)

    def pop(self):
        pass

    def push(self):
        pass

class BBPSSW(Protocol):

    def __init__(self, threshold, own, parent_protocols=[], child_protocols=[]):
        Protocol.__init__(own, parent_protocols, child_protocols)
        self.threshold = threshold
        self.purified_memory = []

    def pop(self, memory_index):
        pass

    def push(self):
        pass

if __name__ == "__main__":
    import topology, timeline
    # create timeline
    tl = timeline.Timeline()

    # create nodes
    alice = topology.Node("alice", tl)
    bob = topology.Node("bob", tl)

    # create classical channel
    cc = topology.ClassicalChannel("cc", tl, distance=1e3, delay=1e5)
    cc.add_end(alice)
    cc.add_end(bob)

    # create memories
    alice_memories, bob_memories = [], []
    for i in range(5):
        memory = topology.Memory("alice memory %d"%i, tl, fidelity=0.6)
        alice_memories.append(memory)
        memory = topology.Memory("bob memory %d"%i, tl, fidelity=0.6)
        bob_memories.append(memory)
    alice_memo_array = topology.MemoryArray("alice memory array", tl, memories=alice_memories)
    bob_memo_array = topology.MemoryArray("bob memory array", tl, memories=bob_memories)
