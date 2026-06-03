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

        # check formatting
        assert all([elem <= 1.001 and elem >= 0 for elem in diag_elems]), (
            "Illegal value with elem > 1 or elem < 0 in density matrix diagonal elements")
        assert abs(sum([elem for elem in diag_elems]) - 1) < 1e-5, (
            "Density matrix diagonal elements do not sum to 1")
        assert len(keys) == 2, "BellDiagonalState density matrix are only supported for 2-qubit entangled states."

        # note: density matrix diagonal elements are guaranteed to be real from Hermiticity
        self.state: list[float] = np.array(diag_elems, dtype=float)
        self.keys = keys
