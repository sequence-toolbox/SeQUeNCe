"""Base class for all quantum state formalisms."""

from abc import ABC

OneDimensionInput = list[complex] | tuple[complex, ...]
TwoDimensionInput = list[list[complex]] | tuple[tuple[complex, ...], ...]


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

    def __str__(self):
        return "\n".join(["Keys:", str(self.keys), "State:", str(self.state)])
