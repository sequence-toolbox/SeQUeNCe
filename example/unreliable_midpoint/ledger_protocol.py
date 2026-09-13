"""A single-heralded end-node protocol that consults the physics ledger.

Registered as ledger_sh. It overrides only the state written on a herald: for a
round the ledger marked unbacked it writes the maximally mixed two-memory state
(all Bell-diagonal elements 1/4), because the two memories were each entangled
with their own emitted photon and those photons were not measured jointly. Any
other round writes the state the library would.
"""
from sequence.entanglement_management.generation.generation_base import (
    EntanglementGenerationA)
from sequence.entanglement_management.generation.single_heralded import (
    SingleHeraldedA)
from .ledger import get_ledger


@EntanglementGenerationA.register("ledger_sh")
class LedgerSingleHeraldedA(SingleHeraldedA):
    """SingleHeraldedA whose herald state is gated on the physics ledger."""

    def _state_on_herald(self):
        ledger = get_ledger(self.owner.timeline)
        if ledger.is_unbacked(self.middle, self.expected_time):
            return [0.25, 0.25, 0.25, 0.25]
        return super()._state_on_herald()
