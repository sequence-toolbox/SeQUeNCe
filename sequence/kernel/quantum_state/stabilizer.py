"""Stabilizer-state quantum formalism.

Use case: efficient simulation of stabilizer states and Clifford operations.
Suitable for simulating second-generation quantum repeaters that require
encoding and error correction.
"""
from stim import TableauSimulator, Tableau

from .base import State


class StabilizerState(State):
    """Stim-backed stabilizer quantum state used by a quantum manager.

    The state is stored internally by a ``stim.TableauSimulator``. Tableau
    accessors are provided for inspection and interoperability with Stim.
    """

    def __init__(self, state: TableauSimulator, keys: list[int], seed: int = None):
        """Create a stabilizer state.

        Args:
            state TableauSimulator: Simulator payload.
                If `None`, a default simulator in |0...0> is created.
            keys (list[int]): Keys associated with this state.
        """
        super().__init__()
        self.keys = list(keys)
        self.seed = seed
        if state is None:
            self.state = TableauSimulator(seed=seed)
        elif isinstance(state, TableauSimulator):
            self.state = state
        else:
            raise TypeError(f"state must be stim.TableauSimulator or None, got {type(state)}")

    @classmethod
    def zero_state(cls, key: int, seed: int = None) -> "StabilizerState":
        """Create a single-qubit stabilizer state initialized to |0>.

        Args:
            key: Quantum-manager key for the qubit.
            seed: Seed used by stim.TableauSimulator.

        Returns:
            StabilizerState: New state bound to `[key]`.
        """
        simulator = TableauSimulator(seed=seed)
        simulator.set_num_qubits(1)
        return cls(state=simulator, keys=[key], seed=seed)

    def copy(self) -> "StabilizerState":
        """Create a copy of this stabilizer state.

        Args:
            None.

        Returns:
            StabilizerState: Copied state with copied keys and simulator.
        """
        if self.state is None:
            simulator = TableauSimulator(seed=self.seed)
        else:
            simulator = self.state.copy(seed=self.seed)
        return StabilizerState(state=simulator, keys=self.keys.copy(), seed=self.seed)
        
    def set_seed(self, seed: int):
        """Set the random seed for this state, affecting future simulator operations."""
        self.seed = seed
        if self.state is not None:
            self.state = self.state.copy(seed=seed)

    def get_seed(self) -> int:
        """Get the current random seed for this state."""
        return self.seed

    def current_inverse_tableau(self) -> Tableau:
        """Return current inverse tableau from simulator state.

        This is mainly for advanced/internal use.
        """
        if self.state is None:
            raise ValueError("StabilizerState is uninitialized (state is None).")
        return self.state.current_inverse_tableau()

    def current_tableau(self) -> Tableau:
        """Return the forward tableau for user-facing state inspection."""
        if self.state is None:
            raise ValueError("StabilizerState is uninitialized (state is None).")
        inverse_tableau = self.state.current_inverse_tableau()
        return inverse_tableau.inverse()

    def __str__(self) -> str:
        """String form defaults to a readable forward-tableau view."""
        return "\n".join(["Keys:", str(self.keys), "Tableau:", str(self.current_tableau()),])

    def serialize(self) -> dict:
        raise NotImplementedError("StabilizerState does not support base complex serialization.")

    def deserialize(self) -> None:
        raise NotImplementedError("StabilizerState cannot be deserialized from base complex format.")
