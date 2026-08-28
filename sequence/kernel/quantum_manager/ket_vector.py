"""This module implements the quantum manager for ket vector states.

Each gate is applied to the state tensor using tensor contraction, without constructing a full-system operator.
This costs O(2^(k+m)), where k is the number of qubits in the combined state and m is the number of qubits
the gate acts on. Since m is usually 1 or 2, it is fixed and small, making the cost O(2^k) and avoiding full
O(4^k) operators and swap matrices.
"""
from __future__ import annotations

import numpy as np

from .base import QuantumManager
from .utils import swap_qubits, validate_circuit_run
from ..quantum_state import KetState, OneDimensionInput
from ..quantum_gates import SUPPORTED_GATES, gate_matrix
from ...constants import KET_VECTOR_FORMALISM

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ...components.circuit import Circuit


def _apply(tensor: np.ndarray, axes: list[int], gate: np.ndarray) -> np.ndarray:
    """Contract an m-qubit ``gate`` into ``tensor`` on ``axes`` (gate-qubit order).

    ``tensor`` is the statevector viewed as an n-axis array of shape (2,)*n -- one
    axis per qubit. This applies ``gate`` to the ``m`` qubits in ``axes`` without
    ever forming the full 2^n x 2^n operator. Cost is O(2^n), vs O(4^n) for the
    matrix path.

    Worked example -- X on qubit 1 of 3 (axes=[1], gate=2x2):
        tensor[b0][b1][b2]                       # the 8 amplitudes as a 2x2x2 grid
        moveaxis(.., [1], [0]) -> [b1][b0][b2]   # bring the target qubit's axis to the front
        reshape(2, -1) -> state_matrix (2, 4)    # rows = target qubit (0/1), columns = other qubits
        gate @ state_matrix                      # apply the gate across other-qubit configurations
        reshape + moveaxis back                  # restore the original axis order
    """
    m = len(axes)
    front = list(range(m))                       # destination axes 0..m-1
    t = np.moveaxis(tensor, axes, front)         # target qubit(s) -> front (a view; no copy)
    shp = t.shape
    # Group target and other axes into rows and columns, apply the gate, then restore the tensor shape.
    t = (gate @ t.reshape(2 ** m, -1)).reshape(shp)
    return np.moveaxis(t, front, axes)           # move the axes back where they were


@QuantumManager.register(KET_VECTOR_FORMALISM)
class QuantumManagerKet(QuantumManager):
    """Class to track and manage quantum states with the ket vector formalism."""

    def __init__(self):
        super().__init__()

    def new(self, state: OneDimensionInput = (complex(1), complex(0))) -> int:
        """Method to create a new ket state.

        Args:
            state (OneDimensionInput): 1D state-vector amplitudes.

        Returns:
            int: the key of the new state.
        """
        key = self._least_available
        self._least_available += 1
        self.states[key] = KetState(state, [key])
        return key

    def run_circuit(self, circuit: Circuit, keys: list[int], meas_samp: float = None) -> dict[int, int]:
        """Apply a circuit to the qubits named by `keys`.

        Each gate is applied by tensor contraction. This costs O(2^(k+m)) = O(2^k) ,
        where k is the number of qubits in the combined state and m is the number of qubits the gate acts on (1 or 2).

        Args:
            circuit (Circuit): quantum circuit to apply.
            keys (list[int]): keys of the qubits to apply the circuit to, 
                              in circuit-qubit order; may span several separate KetStates.
            meas_samp (float): random sample in [0, 1) used for measurement; 
                               required when the circuit measures any qubit.

        Returns:
            dict[int, int]: mapping of each measured key to its outcome, or an
                            empty dict when the circuit performs no measurement.
        """
        unsupported = [g[0] for g in circuit.gates if g[0] not in SUPPORTED_GATES]
        if unsupported:
            raise NotImplementedError(f"QuantumManagerKet.run_circuit received unsupported gate(s): {unsupported}")
        validate_circuit_run(circuit, keys, meas_samp)

        # Combine distinct KetStates and record their qubit order. Deduplicate by object identity if needed.
        old_states, all_keys, seen = [], [], set()
        for key in keys:
            qstate = self.states[key]
            if id(qstate) not in seen:             # skip states already pulled in
                seen.add(id(qstate))
                old_states.append(qstate.state)
                all_keys += qstate.keys
        state = np.array([1], dtype=complex)
        for s in old_states:
            state = np.kron(state, s)

        # Apply each gate by contraction
        k = len(all_keys)
        tensor = state.reshape((2,) * k)           # flat 2^k vector -> k-axis grid
        key_to_axis = {key: i for i, key in enumerate(all_keys)}
        for name, indices, arg in circuit.gates:
            # Map circuit key positions to tensor axes in gate-qubit order.
            axes = [key_to_axis[keys[i]] for i in indices]
            tensor = _apply(tensor, axes, gate_matrix(name, arg))
        new_state = tensor.reshape(-1)             # back to a flat 2^k vector

        if len(circuit.measured_qubits) == 0:
            # No measurement: create a new KetState
            new_ket = KetState(new_state, all_keys)
            for key in all_keys:
                self.states[key] = new_ket
            return {}
        else:
            # Measurement: collapse the state and return the outcomes
            meas_keys = [keys[i] for i in circuit.measured_qubits]
            return self._measure(new_state, meas_keys, all_keys, meas_samp)

    def set(self, keys: list[int], amplitudes: OneDimensionInput) -> None:
        """Set the quantum state for the given keys.

        Args:
            keys (list[int]): list of keys of the quantum state.
            amplitudes (OneDimensionInput): amplitudes to set the state to.
        """
        new_state = KetState(amplitudes, keys)
        for key in keys:
            self.states[key] = new_state

    def get_ascending_keys(self, key: int) -> KetState:
        """Method to get quantum state stored at an index.
           Reorders qubits (in-place) in ascending order of keys before returning.

        Args:
            key (int): key for quantum state.

        Returns:
            KetState: quantum state at supplied key.
        """
        state = super().get(key)
        self.reorder_qubits_ascending_keys(state)
        return state

    def reorder_qubits_ascending_keys(self, state: KetState) -> None:
        """Update the quantum state (in-place) to match the ascending order of keys.
           Meanwhile, the reordered state is also set in the quantum manager.
        
        Args:
            state (KetState): The quantum state to reorder.
        """
        target_all_keys = sorted(state.keys)
        if state.keys != target_all_keys:
            _, swap_matrix = swap_qubits(state.keys, target_all_keys)
            reordered_state = swap_matrix @ state.state
            state.state = reordered_state
            self.set(target_all_keys, reordered_state.tolist())

    def set_to_zero(self, key: int) -> None:
        """Set the qubit at the given key to the |0> state.

        Args:
            key (int): key of the qubit to set to |0>.
        """
        self.set([key], [complex(1), complex(0)])

    def set_to_one(self, key: int) -> None:
        """Set the qubit at the given key to the |1> state.

        Args:
            key (int): key of the qubit to set to |1>.
        """
        self.set([key], [complex(0), complex(1)])

    def _measure(self, state: np.ndarray, keys: list[int], all_keys: list[int], meas_samp: float) -> dict[int, int]:
        """Measure `keys` and collapse their shared state.

        The measured axes are flattened into 2^m outcomes, where m is the number of measured qubits and
        `keys[0]` is the most-significant bit. Computing branch probabilities costs O(2^k) for k total qubits,
        avoiding O(4^k) projectors. Measured keys become basis states, while remaining qubits receive the
        normalized sampled branch.

        Args:
            state (np.ndarray): flat amplitudes ordered by `all_keys`.
            keys (list[int]): keys to measure in outcome bit order.
            all_keys (list[int]): qubit order of `state`.
            meas_samp (float): random sample in [0, 1) selecting the outcome.

        Returns:
            dict[int, int]: mapping of each measured key to its outcome (0 or 1).
        """
        m = len(keys)
        k = len(all_keys)
        arr = np.asarray(state, dtype=complex).reshape((2,) * k)

        # Group measured axes into rows in `keys` order; `keys[0]` is the most-significant outcome bit.
        meas_axes = [all_keys.index(key) for key in keys]
        t = np.moveaxis(arr, meas_axes, range(m)).reshape(2 ** m, -1)

        # Compute Born probabilities and sample from their cumulative distribution.
        probs = np.sum(t.conjugate() * t, axis=1).real
        cumulative_probs = np.cumsum(probs)
        cumulative_probs[-1] = 1.0  # Prevent round-off from excluding the final outcome.
        result = int(np.searchsorted(cumulative_probs, meas_samp, side="right"))
        outcome = bin(result)[2:].zfill(m)  # Convert to an m-bit binary string.
        bits = [int(bit) for bit in outcome]

        # Reassign each measured key to its basis state
        basis = (np.array([1, 0], dtype=complex), np.array([0, 1], dtype=complex))
        for key, bit in zip(keys, bits):
            self.states[key] = KetState(basis[bit], [key])
        # Reassign remaining qubits (if any) to the renormalized post-measurement branch.
        rem_keys = [key for key in all_keys if key not in keys]
        if rem_keys:
            new_state = (t[result] / np.sqrt(probs[result])).reshape(-1)
            new_obj = KetState(new_state, rem_keys)
            for rem in rem_keys:
                self.states[rem] = new_obj
        return dict(zip(keys, bits))
