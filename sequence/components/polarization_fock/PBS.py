
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

class PBS(Entity):
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


        # Changing this would also require changes to the outputs in the get method. 
        theta_H = np.pi/2
        theta_V = 0

        a_H = self.timeline.quantum_manager.a_H 
        a_V = self.timeline.quantum_manager.a_V 
        adag_H = self.timeline.quantum_manager.adag_H 
        adag_V = self.timeline.quantum_manager.adag_V 

        hamiltonian_H = theta_H * ( kron(I, a_H, 'csr')@kron(adag_H,I,'csr') - kron(a_H, I, 'csr')@kron(I, adag_H, 'csr') )
        U_h = expm(hamiltonian_H)

        hamiltonian_V = theta_V * ( kron(I, a_V, 'csr')@kron(adag_V,I,'csr') - kron(a_V, I, 'csr')@kron(I, adag_V, 'csr') )
        U_v = expm(hamiltonian_V)

        self.U = U_h @ U_v
    

    def init(self) -> None:
        """Implementation of Entity interface (see base class)."""

        assert len(self._receivers) == 2, "BeamSplitter should only be attached to 2 outputs."
 
    def get(self, photon1:Photon, photon2:Photon, **kwargs) -> None:
        """Method to receive a photon for measurement.

        Args:
            photon (Photon): photon to measure (must have polarization encoding)

        Side Effects:
            May call get method of one receiver.
        """

        # assert photon.encoding_type["name"] == "polarization", "Beamsplitter should only be used with polarization."

        key1 = photon1.quantum_state
        key2 = photon2.quantum_state

        prepared_state, all_keys = self.timeline.quantum_manager._prepare_state([key1])
        total_BS_op = self.timeline.quantum_manager._prepare_operator(all_keys, [key1, key2], self.U)

        # print("total_BS_op", total_BS_op.shape)
        # print("prepared_state", prepared_state.shape)

        output_state = total_BS_op @ prepared_state @ total_BS_op.conjugate().transpose()
        self.timeline.quantum_manager.set(all_keys, output_state)
        output_state.data = np.round(output_state.data, 10)
        # return photon1, photon2
        self._receivers[0].get(photon1, src = "V_det")
        self._receivers[0].get(photon2, src = "H_det")
        # self._receivers[1].get(photon2)
