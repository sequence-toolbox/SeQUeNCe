import math
import copy
import numpy

from sequence import encoding
from sequence.process import Process
from sequence.entity import Entity
from sequence.event import Event


# array of atomic ensemble memories
class MemoryArray(Entity):
    def __init__(self, name, timeline, **kwargs):
        Entity.__init__(self, name, timeline)
        self.memory_type = kwargs.get("memory_type", "atom")
        self.max_frequency = kwargs.get("frequency", 1)
        num_memories = kwargs.get("num_memories", 0)
        memory_params = kwargs.get("memory_params", None)
        self.memories = []
        self.frequency = self.max_frequency

        if self.memory_type == "atom":
            for i in range(num_memories):
                memory = AtomMemory(self.name + "[%d]" % i, timeline, **memory_params)
                memory.parents.append(self)
                self.memories.append(memory)

        elif self.memory_type == "ensemble":
            for i in range(num_memories):
                memory = Memory(self.name + "%d" % i, timeline, **memory_params)
                memory.parents.append(self)
                self.memories.append(memory)

        else:
            raise Exception("invalid memory type {}".format(self.memory_type))

    def __getitem__(self, key):
        return self.memories[key]

    def __len__(self):
        return len(self.memories)

    def init(self):
        pass

    def write(self):
        assert self.memory_type == "ensemble"

        time = self.timeline.now()

        period = 1e12 / min(self.frequency, self.max_frequency)

        for mem in self.memories:
            process = Process(mem, "write", [])
            event = Event(time, process)
            self.timeline.schedule(event)
            time += period

    def read(self):
        assert self.memory_type == "ensemble"

        time = self.timeline.now()

        period = 1e12 / min(self.frequency, self.max_frequency)

        for mem in self.memories:
            process = Process(mem, "read", [])
            event = Event(time, process)
            self.timeline.schedule(event)
            time += period

    def pop(self, **kwargs):
        memory = kwargs.get("memory")
        index = self.memories.index(memory)
        # notify node
        self._pop(entity="MemoryArray", index=index)

    def set_direct_receiver(self, indices, direct_receiver):
        for memo_index in indices:
            self.memories[memo_index].direct_receiver = direct_receiver

