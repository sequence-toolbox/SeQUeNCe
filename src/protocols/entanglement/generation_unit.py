# UNIT TEST FILE FOR ENTANGLEMENT GENERATION

from generation import EntanglementGeneration
from purification import BBPSSW
from ...kernel.timeline import Timeline
from ...components import *
from ...utils.encoding import single_atom

def three_node_test():
    tl = Timeline()
    
