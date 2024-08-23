"""Definition of the Process class.

This module defines a process, which is performed when an event is executed.
"""
from typing import Any, List, Dict


class Process:
    """Class of process.

    The process claims the object of process, the function of object, and the arguments for the function.

    Attributes:
        owner (Any): the object of process.
        activation (str): the function name of object.
        activation_args  (List[Any]): the (non-keyword) arguments of object's function.
        activation_kwargs (Dict[Any, Any]): the keyword arguments of object's function.
    """

    def __init__(self, owner: Any, activation_method: str, activation_args: List[Any], activation_kwargs: Dict[Any, Any] = {}):
        self.owner = owner
        self.activation = activation_method
        self.activation_args = activation_args
        self.activation_kwargs = activation_kwargs

    def run(self) -> None:
        """Method to execute process.

        Will run the `activation_method` method of `owner` with 
        `activation_args` passed as args, and 'activation_kwargs' passed as kwargs.
        """

        return getattr(self.owner, self.activation)(*self.activation_args, **self.activation_kwargs)
