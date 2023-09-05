import qutip as qtp

class AppQutipInt:
    def __init__(self) -> None:
        pass

    def start(self):
        pass

    def get_memory(self, mem_info):
        '''Starts the operations on the bell state.
        args: mem_info : : resource_management.memory_manager.MemoryInfo'''
        pass

    def bds_to_qobj(self, bell_st):
        '''Converts bell_st to qutip qobj.
        args: bell_st : : 
        
        Returns: qtp.qobj'''
        pass

    def start_decoherence(self):
        '''Asynch process that modifies stored qobj with decoherence.'''
        pass


if __name__ == "__main__":
    # Start application.
    # Sequence stuff to init.
    app = AppQutipInt()
    app.start()
    # Get from sequence.
    # mem_info=[]
    # app.get_memory(mem_info)

    # # Get from sequence.
    # bell_st=[] 
    # app.bds_to_qobj(bell_st)

    # app.start_decoherence()
    # #Begin gate teleporation.