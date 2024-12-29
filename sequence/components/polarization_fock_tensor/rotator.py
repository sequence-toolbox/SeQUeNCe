
from typing import TYPE_CHECKING, List
from functools import lru_cache

if TYPE_CHECKING:
    from ...kernel.timeline import Timeline

from numpy import trace, pi
# from scipy.sparse import kron, eye
from scipy.linalg import expm
from numpy import kron
# import scipy.sparse as sp
import qutip as qt
import numpy as np
from matplotlib import pyplot as plt

from quimb.tensor import MatrixProductOperator as mpo # type: ignore
from quimb.tensor.tensor_arbgeom import tensor_network_apply_op_vec, tensor_network_apply_op_op # type: ignore

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

    def create_BS_MPO(self, site1, site2, theta, total_sites, N, tag = 'BS'): 

        a = qt.destroy(N).full()
        a_dag = a.T
        I = np.eye(N)
        
        # The V polarization would be transmitted unchanged. So, we only focus on the 
        # H polarized photons. Now, we have 2 modes of H polarized photons which need to be 
        # reflected. So, we create the unitaries for both individually and multiply them (not in this function.)

        hamiltonian_BS = -1j * theta * ( kron(I, a_dag)@kron(a, I) + kron(I, a)@kron(a_dag, I) )
        unitary_BS = expm(hamiltonian_BS)

        BS_MPO = mpo.from_dense(unitary_BS, dims = N, sites = (site1,site2), L=total_sites, tags=tag)
        # BS_MPO = BS_MPO.fill_empty_sites(mode = "full")
        return BS_MPO

    def __init__(self, name: str, timeline: "Timeline"):
        """Constructor for the rotator class.

        Args:
            name (str): name of the rotator instance.
            timeline (Timeline): simulation timeline.
        """

        Entity.__init__(self, name, timeline)  # Splitter is part of the QSDetector, and does not have its own name

        self.rotate(0)
    

    def init(self) -> None:
        """Implementation of Entity interface (see base class)."""

        pass

    @lru_cache(maxsize=100)
    def rotate(self, angle):
        self.theta = angle
        # theta/2 convention assumed arbitrarily. Confirm that this is correct. 
        # hamiltonian = -1j*self.theta/2 * ( self.adag_H @ self.a_V + self.a_H @ self.adag_V)
        # self.U = sp.csr_matrix(expm(hamiltonian))

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
        
        # The main job of this function is to extend the density operator in case we multiple quantum states contributing to the 
        # joint states. This would generally only be used when you have combining states like at BSM apparatuses.  
        prepared_rho, all_keys = self.timeline.quantum_manager._prepare_state([key])

        print("rotatong the rho:", prepared_rho)

        sites = photon.TN_inds
        print("self.name:", self.name)
        rot_mpo = self.create_BS_MPO(site1 = sites[0], site2 = sites[1], theta=self.theta/2, total_sites = prepared_rho.L, N = self.timeline.quantum_manager.N, tag = f"{self.name[:6]}")
        # enforce_1d_like(rot_mpo, site_tags=site_tags, inplace=True)

        # psi_rotated = tensor_network_apply_op_vec(rot_mpo, state_mps, compress=True, contract = True, cutoff = self.timeline.quantum_manager.error_tolerance)
        # prepared_rho.draw()
        # rot_mpo.draw()

        
        # A@B
        rho_rotated = tensor_network_apply_op_op(A = rot_mpo, B = prepared_rho, which_A="lower",which_B="upper", contract = True)
        # B@A.T
        rho_rotated = tensor_network_apply_op_op(A = rot_mpo.H, B = rho_rotated, which_A="lower",which_B="lower", contract = True)
        
        # #### Simply printing the state. ########            
        # print("density matrix output by light source")
        # dense_state = self.timeline.quantum_manager.read_quantum_state(rho_rotated, 2, sparse=True)
        # print("TN light source state:")
        # print(dense_state)
        # plt.figure()
        # plt.imshow(dense_state.todense().real)
        # plt.figure()
        # plt.imshow(dense_state.todense().imag)
        # ########################################

        # rho_rotated.draw()

        # output_state = rotator_op @ prepared_state @ rotator_op.conjugate().transpose()
        # print(type(output_state))
        self.timeline.quantum_manager.set(all_keys, rho_rotated)

        return photon
        # self._receivers[0].get(photon, **kwargs)
