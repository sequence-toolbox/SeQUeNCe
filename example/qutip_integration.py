import qutip as qtp

def get_memory(mem_info):
    '''Starts the operations on the bell state.
    args: mem_info : : resource_management.memory_manager.MemoryInfo'''
    pass

def bds_to_qobj(bell_st):
    '''Converts bell_st to qutip qobj.
    args: bell_st : : 
    
    Returns: qtp.qobj'''
    pass

def start_decoherence():
    '''Asynch process that modifies stored qobj with decoherence.'''
    pass


if __name__ == "__main__":
    # Get from sequence.
    mem_info=[]
    get_memory(mem_info)

    # Get from sequence.
    bell_st=[] 
    bds_to_qobj(bell_st)

    start_decoherence()
    #Begin gate teleporation.