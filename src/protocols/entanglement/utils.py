from ..protocol import Protocol


class EndProtocol(Protocol):
    '''
    This protocol is used to measure the number of success entanglement distribution
    '''
    def __init__(self, own):
        Protocol.__init__(self, own)
        self.dist_counter = 0

    def init(self):
        pass

    def pop(self, **kwargs):
        if "info_type" in kwargs:
            return
        
        self.dist_counter += 1
        memory_index = kwargs.get("memory_index")
        another_node = kwargs.get("another_node")
        print("EndProtocol received memory index {} on node {} entangled with {}".format(memory_index, self.own.name, another_node))
        print("\tcurrent time:", self.own.timeline.now()/1e12)
        self._push(index=memory_index)

    def push(self, **kwargs):
        pass

    def received_message(self, src, msg):
        return

