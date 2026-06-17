"""Bell diagonal quantum state formalism."""

import numpy as np

from .base import State


class BellDiagonalState(State):
    """Class for representing a 2-qubit EPR pair in the Bell diagonal formalism.

    Has 4 diagonal elements of density matrix in Bell basis.

    Attributes:
        state (np.array): diagonal elements of 2-qubit density matrix in Bell bases. Should be of length 4.
        keys (list[int]): list of keys (subsystems) associated with this state. Should be length 2.
    """

    def __init__(self, diag_elems: list[float], keys: list[int]):
        """Constructor for Bell diagonal state class.

        Args:
            diag_elems (list[float]): 4 diagonal elements of 2-qubit density matrix in Bell bases. 
                Default order: Phi+, Phi-, Psi+, Psi- (i.e. I, Z, X, Y errors).
            keys (list[int]): list of keys to this state in quantum manager. Should be length 2.
        """
        super().__init__()

        diag_elems = np.array(diag_elems, dtype=float)

        if len(diag_elems) != 4:
            raise ValueError("Bell diagonal state must have 4 diagonal elements.")
        if not np.all((0 <= diag_elems) & (diag_elems <= 1)):
            raise ValueError("Bell diagonal elements must be probabilities between 0 and 1.")
        if not np.isclose(np.sum(diag_elems), 1):
            raise ValueError("Bell diagonal elements must sum to 1.")
        if len(keys) != 2:
            raise ValueError("BellDiagonalState is only supported for 2-qubit entangled states.")

        # note: density matrix diagonal elements are guaranteed to be real from Hermiticity
        self.state: np.ndarray = diag_elems
        self.keys = keys
