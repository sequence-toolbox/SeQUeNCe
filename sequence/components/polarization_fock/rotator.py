
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from ...kernel.timeline import Timeline

from numpy import trace, pi
from scipy.sparse import kron, eye
from scipy.sparse.linalg import expm
import scipy.sparse as sp
from matplotlib import pyplot as plt
from ..photon import Photon
from ...kernel.quantum_utils import povm_0
from ...utils.encoding import polarization
from ...kernel.entity import Entity

class Rotator(Entity):
    """Class modeling a polarization rotator.

    Simulates operation of a beam splitter using the polarization and fock joint states.
    
    Attributes:
        name (str): label for rotator instance.
        timeline (Timeline): timeline for simulation.
    
    """

    def __init__(self, name: str, timeline: "Timeline"):
        """Constructor for the rotator class.

        Args:
            name (str): name of the rotator instance.
            timeline (Timeline): simulation timeline.
        """

        Entity.__init__(self, name, timeline)  # Splitter is part of the QSDetector, and does not have its own name
        I = eye(self.timeline.quantum_manager.N)

        self.a_H = self.timeline.quantum_manager.a_H 
        self.a_V = self.timeline.quantum_manager.a_V 
        self.adag_H = self.timeline.quantum_manager.adag_H 
        self.adag_V = self.timeline.quantum_manager.adag_V 

        self.rotate(0)
    

    def init(self) -> None:
        """Implementation of Entity interface (see base class)."""

        pass
    def rotate(self, angle):
        self.theta = angle
        # theta/2 convention assumed arbitrarily. Confirm that this is correct. 
        hamiltonian = -1j*self.theta/2 * ( self.adag_H @ self.a_V + self.a_H @ self.adag_V)
        self.U = sp.csr_matrix(expm(hamiltonian))

        # print("self.U:", type(self.U))

    def get(self, photon, **kwargs) -> None:
        """Method to receive a photon for measurement.

        Args:
            photon (Photon): photon to measure (must have polarization encoding)

        Side Effects:
            May call get method of one receiver.
        """

        # assert photon.encoding_type["name"] == "polarization", "Beamsplitter should only be used with polarization."
        # print("rotator angle:", self.theta, "at", self.name)

        key = photon.quantum_state
        prepared_state, all_keys = self.timeline.quantum_manager._prepare_state([key])
        rotator_op = self.timeline.quantum_manager._prepare_operator(all_keys, [key], self.U)
        # print("prepard_state:", type(prepared_state), "rotator_op", type(rotator_op))
        output_state = rotator_op @ prepared_state
        
        print("rotated state:")
        print(output_state)
        plt.figure()
        plt.imshow(output_state.todense().real)
        plt.figure()
        plt.imshow(output_state.todense().imag)

        output_state = output_state @ rotator_op.conjugate().transpose()

        # print(type(output_state))
        self.timeline.quantum_manager.set(all_keys, output_state)

        return photon
        # self._receivers[0].get(photon, **kwargs)
