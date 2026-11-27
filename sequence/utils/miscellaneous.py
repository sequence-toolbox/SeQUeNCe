"""
Miscellaneous utility functions for the SeQUeNCe framework.
"""

import sequence as sq

def set_type_and_formalism(generation_type: str, formalism: str) -> None:
    """Configure the global generation type and quantum state formalism.

    Args:
        generation_type (str): Entanglement generation type
        formalism (str): Quantum state formalism for purification, swapping, and the quantum manager.
    """
    for protocol in (sq.EntanglementGenerationA, sq.EntanglementGenerationB):
        protocol.set_global_type(generation_type)

    for protocol in (sq.PurificationProtocol, sq.EntanglementSwappingA, sq.EntanglementSwappingB):
        protocol.set_formalism(formalism)

    sq.QuantumManager.set_global_manager_formalism(formalism)
