
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from ...kernel.timeline import Timeline

from numpy import trace, pi
from scipy.sparse import kron, eye
from scipy.sparse.linalg import expm

import numpy as np

from ..photon import Photon
from ...kernel.quantum_utils import povm_0
from ...utils.encoding import polarization
from ...kernel.entity import Entity

class Beamsplitter(Entity):
    """Class modeling a polarization-Fock beamsplitter.

    Simulates operation of a beam splitter using the polarization and fock joint states.
    
    Attributes:
        name (str): label for beamsplitter instance.
        timeline (Timeline): timeline for simulation.
    
    """

    def __init__(self, name: str, timeline: "Timeline"):
        """Constructor for the beamsplitter class.

        Args:
            name (str): name of the beamsplitter instance.
            timeline (Timeline): simulation timeline.
        """

        Entity.__init__(self, name, timeline)  # Splitter is part of the QSDetector, and does not have its own name
        I = eye(self.timeline.quantum_manager.dim)

        a_H = self.timeline.quantum_manager.a_H 
        a_V = self.timeline.quantum_manager.a_V 
        adag_H = self.timeline.quantum_manager.adag_H 
        adag_V = self.timeline.quantum_manager.adag_V 

        # print("BS aH shape:", a_H.shape)
        # print("BS I shape:", I.shape)

        theta = pi/4

        hamiltonian_H = theta * ( kron(I, a_H, 'csr')@kron(adag_H,I,'csr') - kron(a_H, I, 'csr')@kron(I, adag_H, 'csr') )
        U_h = expm(hamiltonian_H)

        hamiltonian_V = theta * ( kron(I, a_V, 'csr')@kron(adag_V,I,'csr') - kron(a_V, I, 'csr')@kron(I, adag_V, 'csr') )
        U_v = expm(hamiltonian_V)

        self.U = U_h @ U_v
    

    def init(self) -> None:
        """Implementation of Entity interface (see base class)."""

        assert len(self._receivers) == 2, f"BeamSplitter should only be attached to 2 outputs. Got {len(self._receivers)} receivers"
 
    def get(self, photon1:Photon, photon2:Photon, **kwargs) -> None:
        """Method to receive a photon for measurement.

        Args:
            photon (Photon): photon to measure (must have polarization encoding)

        Side Effects:
            May call get method of one receiver.
        """

        # assert photon.encoding_type["name"] == "polarization", "Beamsplitter should only be used with polarization."

        key1 = photon1.quantum_state
        all_keys1 = self.timeline.quantum_manager.states[key1].keys
        key2 = photon2.quantum_state
        all_keys2 = self.timeline.quantum_manager.states[key2].keys

        # print("all keys:", all_keys1, all_keys2)

        if not key2 in all_keys1:
            # print("joining states")
            state1 = self.timeline.quantum_manager.states[key1].state
            state2 = self.timeline.quantum_manager.states[key2].state

            # Finding the joint system
            total_state = kron(state1, state2, format = 'csr')

            all_keys1.remove(key1)
            all_keys2.remove(key2)

            all_keys1.extend(all_keys2)
            all_keys1.extend([key1, key2])

            # print("all_keys1:", all_keys1) 
            
            self.timeline.quantum_manager.set(all_keys1, total_state)

        prepared_state, all_keys = self.timeline.quantum_manager._prepare_state([key1])

        # print("joint keys:", all_keys, "operated keys:", key1, key2)

        # print("qm:", type(self.timeline.quantum_manager))

        total_BS_op = self.timeline.quantum_manager._prepare_operator(all_keys, [key1, key2], self.U)

        # print("total_BS_op", total_BS_op.shape)
        # print("prepared_state", prepared_state.shape)
        # print("op dimension:", self.U.shape)


        output_state = total_BS_op @ prepared_state @ total_BS_op.conjugate().transpose()

        self.timeline.quantum_manager.set(all_keys, output_state)
        output_state.data = np.round(output_state.data, 10)
        output_state.eliminate_zeros()

        # print("new_state:", output_state)


        # return photon1, photon2

        # print("beamsplitted state:", output_state)

        self._receivers[0].get(photon1, port = kwargs["ports"][0])
        self._receivers[1].get(photon2, port = kwargs["ports"][1])
