"""Base class for quantum state formalisms."""

from abc import ABC


class State(ABC):
    """Base class for storing quantum states (abstract).

    Attributes:
        state (any): internal representation of the state, may vary by state type.
        keys (list[int]): list of keys pointing to the state, for use with a quantum manager.
    """

    def __init__(self, **kwargs):
        # potential key word arguments for derived classes, e.g. truncation = d-1 for qudit
        super().__init__()
        self.state = None
        self.keys: list = []

    def deserialize(self, json_data) -> None:
        self.keys = json_data["keys"]
        self.state = []
        for i in range(0, len(json_data["state"]), 2):
            complex_val = complex(json_data["state"][i],
                                  json_data["state"][i + 1])
            self.state.append(complex_val)

    def serialize(self) -> dict:
        res: dict[str, list] = {"keys": self.keys}
        state: list = []
        for cplx_n in self.state:
            if type(cplx_n) is float:
                state.append(cplx_n)
                state.append(0)
            elif isinstance(cplx_n, complex):
                state.append(cplx_n.real)
                state.append(cplx_n.imag)
            else:
                raise ValueError("Unknown type of state")

        res["state"] = state
        return res

    def __str__(self):
        return "\n".join(["Keys:", str(self.keys), "State:", str(self.state)])
