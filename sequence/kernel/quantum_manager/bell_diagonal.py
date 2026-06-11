"""
This module implements the quantum manager for Bell diagonal states.
"""

from ..quantum_state import BellDiagonalState
from ...constants import BELL_DIAGONAL_STATE_FORMALISM
from .base import QuantumManager


@QuantumManager.register(BELL_DIAGONAL_STATE_FORMALISM)
class QuantumManagerBellDiagonal(QuantumManager):
    """Class to track and manage quantum states with the bell diagonal formalism.

    To be aligned with analytical formulae, we have assumed that successfully generated EPR pair is in Phi+ form.
    And note that the 4 BDS elements are in I, Z, X, Y order.

    * BDS is only used for entanglement distribution (generation, swapping, purification), assuming underlying errors being purely Pauli.
    * All manipulation results can be tracked analytically, without explicit quantum gates / channels / measurements.
    """

    def __init__(self, **kwargs):
        super().__init__()

    def new(self, state=None) -> int:
        """Generates new quantum state key for quantum manager.

        NOTE: since this generates only one state, there will be no corresponding entangled state stored.
        The Bell diagonal state formalism assumes entangled states;
        thus, attempting to call `get` will return an exception until entangled.
        The purpose of this function is thus mainly to avoid state key collisions.

        Args:
            state (Any): to conform to type definition (does nothing).

        Returns:
            int: quantum state key corresponding to state.
        """
        key = self._least_available
        self._least_available += 1
        return key

    def get(self, key: int):
        if key not in self.states:
            raise Exception("Attempt to get Bell diagonal state before entanglement.")

        return super().get(key)

    def set(self, keys: list[int], diag_elems: list[float]) -> None:
        super().set(keys, diag_elems)
        # assert len(keys) == 2, "Bell diagonal states must have 2 keys."
        if len(keys) != 2:
            # raise Warning("bell diagonal quantum manager received invalid set request")  # optional
            for key in keys:
                if key in self.states:
                    self.states.pop(key)
            return
        new_state = BellDiagonalState(diag_elems, keys)
        for key in keys:
            self.states[key] = new_state

    def set_to_noiseless(self, keys: list[int]):
        self.set(keys, [float(1), float(0), float(0), float(0)])
