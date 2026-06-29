"""Stabilizer-state quantum formalism.

This module utilizes stim.TableauSimulator as the dynamic stabilizer-state simulator.

Space complexity: O(n^2) for n qubits. More precisely, the space complexity is 4n(n+1), which consists of
                  2n(n+1) for the stabilizer generators and 2n(n+1) for the destabilizer generators.

Use case: Suitable for simulating protocols that require quantum encoding and error correction.
"""

from stim import TableauSimulator, Tableau, PauliString
from .base import State


class StabilizerState(State):
    """Stim-backed stabilizer quantum state used by a quantum manager.

    The state is stored internally by a ``stim.TableauSimulator``. Tableau
    accessors are provided for inspection and interoperability with Stim.

    Attributes:
        state (TableauSimulator): the internal stabilizer state simulator.
        keys (list[int]): list of keys (subsystems) associated with this state.
        seed (int | None): random seed used by the simulator
    """

    def __init__(self, state: TableauSimulator | None, keys: list[int], seed: int | None = None):
        """Create a stabilizer state.

        Args:
            state (TableauSimulator | None): Simulator payload. If `None`, a default simulator in |0...0> is created.
            keys (list[int]): Keys associated with this state.
            seed (int | None): Seed used by stim.TableauSimulator.
        """
        super().__init__()
        self.keys = keys
        self.seed = seed
        if state is None:
            self.state = TableauSimulator(seed=seed)
        elif isinstance(state, TableauSimulator):
            self.state = state
        else:
            raise TypeError(f"state must be stim.TableauSimulator or None, got {type(state)}")

    @classmethod
    def zero_state(cls, key: int, seed: int | None = None) -> "StabilizerState":
        """Create a single-qubit stabilizer state initialized to |0>.

        Args:
            key (int): Quantum-manager key for the qubit.
            seed (int | None): Seed used by stim.TableauSimulator.

        Returns:
            StabilizerState: New state bound to `[key]`.
        """
        simulator = TableauSimulator(seed=seed)
        simulator.set_num_qubits(1)
        return cls(state=simulator, keys=[key], seed=seed)

    def copy(self) -> "StabilizerState":
        """Create a copy of this stabilizer state.

        Returns:
            StabilizerState: Copied state with copied keys and simulator.
        """
        assert isinstance(self.state, TableauSimulator), "state must be a stim.TableauSimulator to copy"
        simulator = self.state.copy(seed=self.seed)
        return StabilizerState(state=simulator, keys=self.keys.copy(), seed=self.seed)
        
    def set_seed(self, seed: int):
        """Set the random seed for this state, affecting future simulator operations.
        
        Args:
            seed (int): new random seed to set.
        """
        self.seed = seed
        if self.state is not None:
            self.state = self.state.copy(seed=self.seed)

    def get_seed(self) -> int | None:
        """Get the current random seed for this state.
        
        Returns:
            int | None: Current random seed.
        """
        return self.seed

    def current_inverse_tableau(self) -> Tableau:
        """Return current inverse tableau from simulator state.

        Returns:
            Tableau: current inverse tableau.
        """
        return self.state.current_inverse_tableau()

    def current_forward_tableau(self) -> Tableau:
        """Return the forward tableau for user-facing state inspection, which describes the Clifford transformation

        Returns:
            Tableau: current forward tableau.
        """
        inverse_tableau = self.state.current_inverse_tableau()
        return inverse_tableau.inverse()

    def canonical_stabilizers(self) -> list[PauliString]:
        """Return the simulator's canonical stabilizer generators, which describes the quantum state in a normalized stabilizer-generator form.
        
        Distinction against forward tableau: many different Clifford circuits can produce the same stabilizer state. 
            Their forward tableaus may differ, but their canonical stabilizers can be the same because the final state is the same.

        Returns:
            list[PauliString]: canonical stabilizer generators.
        """
        return self.state.canonical_stabilizers()

    def __str__(self) -> str:
        """The string representation of a stabilizer state includes its keys and canonical stabilizers.
        
        Returns:
            str: string representation of the state.
        """
        return "\n".join(["Keys:", str(self.keys), "Canonical stabilizers:", str(self.canonical_stabilizers())])

    def __repr__(self) -> str:
        """The repr representation of a stabilizer state includes its keys, 
        canonical stabilizers, inverse tableau, and forward tableau.
        
        Returns:
            str: repr representation of the state.
        """
        canonical_stabilizer = str(self)
        inverse_tableau = self.current_inverse_tableau()
        forward_tableau = self.current_forward_tableau()
        return f"{canonical_stabilizer}\nInverse tableau:\n{inverse_tableau}\nForward tableau:\n{forward_tableau}"
