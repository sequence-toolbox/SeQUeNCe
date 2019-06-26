class Process:

    def __init__(self, owner, activation_method, act_params):
        self.__owner = owner
        self.__activation = activation_method
        # replace activation params with list?
        self.__act_params = act_params

    # return activation method with act_params as arguments
    def run(self):
        return getattr(self.__owner, self.__activation)(*self.__act_params)
