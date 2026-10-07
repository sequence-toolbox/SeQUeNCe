"""Utilities shared by quantum-manager implementations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from numpy.typing import NDArray
from qutip_qip.circuit import QubitCircuit
from qutip_qip.operations import Gate, gate_sequence_product

if TYPE_CHECKING:
    from ...components.circuit import Circuit


def validate_circuit_run(circuit: Circuit, keys: list[int], meas_samp=None) -> None:
    """Validate common circuit inputs. Used by QuantumManagerKet and QuantumManagerDensity.

    Args:
        circuit (Circuit): quantum circuit to apply.
        keys (list[int]): list of keys for quantum states to apply circuit to.
        meas_samp (float): random sample used for measurement.
    """
    if len(keys) != circuit.size:
        raise ValueError("Mismatch between circuit size and supplied qubits.")
    if circuit.measured_qubits and meas_samp is None:
        raise ValueError("Must specify random sample when measuring qubits.")


def swap_qubits(all_keys: list[int], keys: list[int]) -> tuple[list[int], NDArray]:
    """Swap qubits in the circuit. Used by QuantumManagerKet and QuantumManagerDensity.

    Args:
        all_keys (list[int]): The list of all qubit keys.
        keys (list[int]): The list of qubit keys to swap.

    Returns:
        tuple: updated list of all keys and the swap matrix.
    """
    swap_circuit = QubitCircuit(N=len(all_keys))
    for i, key in enumerate(keys):
        j = all_keys.index(key)
        if j != i:
            gate = Gate("SWAP", targets=[i, j])
            swap_circuit.add_gate(gate)
            all_keys[i], all_keys[j] = all_keys[j], all_keys[i]
    swap_mat = gate_sequence_product(swap_circuit.propagators()).full()
    return all_keys, swap_mat
