import qutip as qtp
import numpy as np
import sequence as sqnc
from sequence.resource_management.memory_manager import MemoryManager 


class AppQutipInt:
    def __init__(self, mem_manager: MemoryManager) -> None:
        '''Args:
            mem_manager (MemoryManager): manages all the memories'''
        self.mem_manager=mem_manager

    def start(self) -> None:
        pass

    def get_memory(self, mem_info):
        '''Starts the operations on the bell state.
        Args: 
            mem_info (resource_management.memory_manager.MemoryInfo): '''
        todo: "Alvin: I'm not sure what method will determine the memory state."
        state="ENTANGLED"
        self.mem_manager.update(mem_info.memory, state)

    def bds_to_qobj(self, bell_st):
        '''Converts bell_st to qutip qobj.
        Args: 
            bell_st (np.ndarray) : 
        Returns: qtp.qobj'''
        return qtp.Qobj(bell_st)
        

    def start_decoherence(self):
        '''Asynch process that modifies stored qobj with decoherence.'''
        pass


if __name__ == "__main__":
    # Start application.
    # Sequence stuff to init.
    mem_manager=[]
    app = AppQutipInt(mem_manager)
    app.start()
    # Get from sequence.
    # mem_info=[]
    # app.get_memory(mem_info)

    # # Get from sequence.
    # bell_st=[] 
    # app.bds_to_qobj(bell_st)

    # app.start_decoherence()
    # #Begin gate teleporation.

    # Tests
    state=np.array([[0,1],[1,0]])
    print(state)
    print(app.bds_to_qobj(state))