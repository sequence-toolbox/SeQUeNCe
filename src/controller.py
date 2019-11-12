import math
import numpy
import re

from sequence import encoding
from sequence.process import Process
from sequence.entity import Entity
from sequence.event import Event
from sequence.timeline import Timeline
from sequence import topology

# Protocol
class Controller(Entity):
    def __init__(self, name, timeline, **kwargs):
        super().__init__(name, timeline)

    # entanglement distribution:
    #   send photons from 2 nodes to middle measurement node
    #   middle node sends results to 2 end nodes
    #   end nodes communicate which memories and information on memories
    def entanglement_distribution():
        ## end nodes: schedule "read" operation
        # for memory in node.memories:
        #   memory.read()

        ## middle node: check detector data after certain time, send data to end
        # self.node.get_measurement_result()
        # self.node.send_message()

        ## end node: send data to other end node on memories
        # self.node.send_message()

        pass

    # entanglement purification:
    #   purification operations between 2 end nodes
    def entanglement_purification():
        pass

    # entanglement swap:
    #   within a node
    #   swap entanglement of 2 adjacent memories
    def entanglement_swap():
        pass


