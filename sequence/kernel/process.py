"""Definition of the Process class.

This module defines a process, which is performed when an event is executed.
"""
from typing import Any, List


class Process:
    """Class of process.

    The process claims the object of process, the function of object, and the arguments for the function.

    Attributes:
        owner (Any): the object of process.
        activation_method (str): the function of object.
        act_params (List[Any]): the arguments of object.
    """

    def __init__(self, owner: Any, activation_method: str, act_params: List[Any], act_kwargs={}):
        self.owner = owner
        self.activation = activation_method
        self.act_params = act_params
        self.act_kwargs = act_kwargs

    def run(self) -> None:
        """Method to execute process.

        Will run the `activation_method` method of `owner` with `act_params` passed as args.
        """

        return getattr(self.owner, self.activation)(*self.act_params, **self.act_kwargs)
