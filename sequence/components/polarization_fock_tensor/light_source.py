from typing import List
from functools import lru_cache

from numpy import multiply, sqrt, zeros, outer, kron
from math import factorial
import numpy as np
from numpy.linalg import matrix_power

from scipy import sparse as sp
from scipy.linalg import expm

from matplotlib import pyplot as plt
import qutip as qt

from quimb.tensor import MatrixProductOperator as mpo # type: ignore
from quimb.tensor.tensor_arbgeom import get_coordinate_formatter, tensor_network_apply_op_vec # type: ignore
from quimb.tensor.tensor_1d_compress import tensor_network_1d_compress, enforce_1d_like # type: ignore
from quimb.tensor.tensor_1d import TensorNetwork1DOperator # type: ignore
from quimb.tensor import MatrixProductState as mps # type: ignore


from ..photon import Photon
from ...kernel.entity import Entity
from ...kernel.event import Event
from ...kernel.quantum_utils import sparse_density_partial_trace
from ...kernel.process import Process
from ...utils.encoding import polarizationFock
from ...utils import log
from ..light_source import LightSource

def fill_fn(shape):
    arr = np.zeros(shape)
    idx = tuple([0]*(len(shape)))
    arr[idx] = 1
    return arr


class light_source_module(Entity):
    def __init__(self, name, timeline):
        super().__init__(name, timeline)
        self.spdc_sources = []


    def init(self):
        pass

    def add_SPDCSource(self, name, wavelengths=None, frequency=8e7, mean_photon_num=0.1,
                 encoding_type=polarizationFock, phase_error=0, bandwidth=0, polarization_fidelity = 1):
        self.spdc_sources.append(SPDCSource(name, self.timeline, wavelengths, frequency, mean_photon_num, encoding_type, phase_error, bandwidth, polarization_fidelity))

    def add_receiver(self, receiver: "Entity") -> None:
        for i in self.spdc_sources:
            i.add_receiver(receiver)

    def emit(self, num_emissions, debug = False):
        for i in self.spdc_sources:
            i.emit(num_emissions, debug)



class SPDCSource(LightSource):
    """Model for a laser light source for entangled photons (via SPDC).

    The SPDCLightSource component acts as a simple low intensity laser with an SPDC lens.
    It provides entangled photon clusters at a set frequency.

    Attributes:
        name (str): label for beamsplitter instance
        timeline (Timeline): timeline for simulation
        frequency (float): frequency (in Hz) of photon creation.
        wavelengths (List[float]): wavelengths (in nm) of emitted entangled photons.
            If a list is given, it should contain two elements (corresponding to two modes).
        linewidth (float): st. dev. in photon wavelength (in nm) (currently unused).
        mean_photon_num (float): mean number of photons emitted each period.
        encoding_type (Dict): encoding scheme of emitted photons (as defined in the encoding module).
        phase_error (float): phase error applied to qubits.
    """

    def __init__(self, name, timeline, wavelengths=None, frequency=8e7, mean_photon_num=0.1,
                 encoding_type=polarizationFock, phase_error=0, bandwidth=0, polarization_fidelity = 1):
        super().__init__(name, timeline, frequency, 0, bandwidth, mean_photon_num, encoding_type, phase_error)
        self.wavelengths = wavelengths
        self.polarization_fidelity = polarization_fidelity
        self.trunc = self.timeline.quantum_manager.truncation
        # self.I = sp.eye(self.trunc+1)
        # If the user uses a setting where both the photons have different wavelengths, you take the object 
        # from the user and use it directly. Otherwise, the direct method is to call set_wavelengths which sets 
        # both photons to have 1550nm wavelength. 
        if self.wavelengths is None or len(self.wavelengths) != 2:
            self.set_wavelength()

    def init(self):
        assert len(self._receivers) == 2, "SPDC source must connect to 2 receivers."


    # def power(self, matrix, power):
    #     if power:
    #         return matrix**power
    #     return sp.eye(matrix.shape[0])

    
    # def _find_mat_exp(self, mat):
    #     ans = sp.eye(mat.shape[0])
    #     intermediate = 1
    #     # print("finding matrix exp")
    #     for i in range(1, 50+1):
    #         # print("done one iteration")
    #         intermediate *= mat/i
    #         # intermediate.data = np.round(intermediate.data, 10)
    #         # print("num_elements:", len(intermediate.data))
    #         intermediate.eliminate_zeros()


        #     ans += intermediate
        #     # temp.data = intermediate / factorial(i)
        # # print("done finding matrix exp")
        # return ans


    def create_TMSV_OP_Dense(self, N, mean_photon_num):

        a = qt.destroy(N).full()
        a_dag = a.T
        truncation = (N-1)      

        # print()

        def generate_amp_list(mean_photon_num):
            amp_list = [(sqrt(mean_photon_num / (mean_photon_num + 1)) ** m) / sqrt(mean_photon_num + 1) for m in range(truncation)]
            amp_square_list = [amp ** 2 for amp in amp_list]
            amp_list.append(sqrt(1 - sum(amp_square_list)))
            return amp_list

        amp = generate_amp_list(mean_photon_num)

        op = np.complex128(0)
        for i in range(truncation+1):
            # TMSV is a 2 mode state (independent spatial modes). Hence, we take the tensor product of the two mode operators
            new_op = amp[i] * ( matrix_power(kron(a_dag, a_dag), i) ) / factorial(i)
            op += new_op

        return op


    def create_MPO(self, site1, site2, total_sites, op, N, tag):
        MPO = mpo.from_dense(op, dims = N, sites = (site1,site2), L=total_sites, tags=tag)
        return MPO
    

    def create_BS_MPO(self, site1, site2, theta, total_sites, N, tag = 'BS'): 

        a = qt.destroy(N).full()
        a_dag = a.T
        I = np.eye(N)
        
        # The V polarization would be transmitted unchanged. So, we only focus on the 
        # H polarized photons. Now, we have 2 modes of H polarized photons which need to be 
        # reflected. So, we create the unitaries for both individually and multiply them (not in this function.)

        hamiltonian_BS = -theta * ( kron(I, a_dag)@kron(a, I) - kron(I, a)@kron(a_dag, I) )
        unitary_BS = expm(hamiltonian_BS)

        BS_MPO = mpo.from_dense(unitary_BS, dims = N, sites = (site1,site2), L=total_sites, tags=tag)
        # BS_MPO = BS_MPO.fill_empty_sites(mode = "full")
        return BS_MPO
    

    def polarization_entangled_MPS(self, vacuum, N, mean_photon_num, num_modes, error_tolerance, compress = True, contract = True):

        psi = vacuum.copy()
        psi.add_tag("L0")
        site_tags = psi.site_tags

        # Creating TMSV ops:
        TMSV_op_dense = self.create_TMSV_OP_Dense(N, mean_photon_num)

        TMSV_MPO_H = self.create_MPO(site1 = 0, site2 = 2, total_sites = num_modes, op = TMSV_op_dense, N = N, tag = r"$TMSV_H$")
        enforce_1d_like(TMSV_MPO_H, site_tags=site_tags, inplace=True)
        TMSV_MPO_H.add_tag("L1")

        TMSV_MPO_V = self.create_MPO(site1 = 5, site2 = 7, total_sites = num_modes, op = TMSV_op_dense, N = N, tag = r"$TMSV_V$")
        enforce_1d_like(TMSV_MPO_V, site_tags=site_tags, inplace=True)
        TMSV_MPO_V.add_tag("L1")

        # Creating PBS ops:
        U_PBS_H_Signal = self.create_BS_MPO(site1 = 2, site2 = 6, theta=np.pi/2, total_sites = num_modes, N = N, tag = r"$PBS_S$")
        enforce_1d_like(U_PBS_H_Signal, site_tags=site_tags, inplace=True)
        U_PBS_H_Signal.add_tag("L1")

        U_PBS_H_Idler = self.create_BS_MPO(site1 = 0, site2 = 4, theta=np.pi/2, total_sites = num_modes, N = N, tag = r"$PBS_I$")
        enforce_1d_like(U_PBS_H_Idler, site_tags=site_tags, inplace=True)
        U_PBS_H_Signal.add_tag("L1")

        # Create entangled state:
        psi = tensor_network_apply_op_vec(TMSV_MPO_H, psi, compress=compress, contract = contract, cutoff = error_tolerance)
        psi = tensor_network_apply_op_vec(TMSV_MPO_V, psi, compress=compress, contract = contract, cutoff = error_tolerance)
        psi = tensor_network_apply_op_vec(U_PBS_H_Idler, psi, compress=compress, contract = contract, cutoff = error_tolerance)
        psi = tensor_network_apply_op_vec(U_PBS_H_Signal, psi, compress=compress, contract = contract, cutoff = error_tolerance)

        for _ in range(4):
            psi.measure(0, remove = True, renorm = True, inplace = True)

        # Not used for TN implermentation. Used for validating impelmentation with dense version
        TMSV_state = psi.to_dense()
        TMSV_state = np.reshape(TMSV_state.data, (-1, 1), order = 'C')
        TMSV_state = sp.csr_matrix(TMSV_state)
        TMSV_state.data = np.round(TMSV_state.data, 10)
        TMSV_state.eliminate_zeros()

        return psi, TMSV_state

    def create_vacuum_state(self, num_modes, N, bond_dim = 2, tags = "In"):
        return mps.from_fill_fn(
                    fill_fn,
                    L=num_modes,
                    bond_dim=bond_dim,
                    phys_dim=N,
                    cyclic=False,
                    tags=tags
                )

    def emit(self, num_emissions, debug = False):
        """Method to emit photons.

        Will emit photons for a length of time. We do away with the statelist parameter and assume that the 
        SPDC light source can only generate the TMSV state and no others. 
        The number of photons emitted per period is calculated as a poisson random variable.

        Arguments:
            state_list (List[List[complex]]): list of complex coefficient arrays to send as photon-encoded qubits.
        """

        time = self.timeline.now()
 
        for i in range(num_emissions):
            # generate two new photons
            new_photon0 = Photon(self.name+"signal", self.timeline,
                                    wavelength=self.wavelengths[0],
                                    location=self,
                                    encoding_type=self.encoding_type,
                                    use_qm=True)
            new_photon1 = Photon(self.name+"_idler", self.timeline,
                                    wavelength=self.wavelengths[1],
                                    location=self,
                                    encoding_type=self.encoding_type,
                                    use_qm=True)

            # set shared state to squeezed state
            num_modes = 8
            vacuum = self.create_vacuum_state(num_modes=num_modes, N=self.timeline.quantum_manager.N)
            


            state, dense_state = self.polarization_entangled_MPS(vacuum, self.timeline.quantum_manager.N, self.mean_photon_num, num_modes, self.timeline.quantum_manager.error_tolerance)
            
            # print(dense_state)
            state_H = state.H
            state_H.retag_({'In': 'Out'})
            state_H.site_ind_id = 'b{}'
            rho = (state_H | state)
            for i in range(rho.L):
                rho ^= f"I{i}"   
            rho = TensorNetwork1DOperator(rho)
            rho._upper_ind_id = state.site_ind_id
            rho._lower_ind_id = state_H.site_ind_id
            rho = rho.fuse_multibonds()


            #### Simply printing the state. ########            
            # print("density matrix output by light source")
            # dense_state = self.timeline.quantum_manager.read_quantum_state(rho, 2, sparse=True)
            # print("TN light source state:")
            # print(dense_state)
            # plt.figure()
            # plt.imshow(dense_state.todense().real)
            # plt.figure()
            # plt.imshow(dense_state.todense().imag)
            ########################################


            keys = [new_photon0.quantum_state, new_photon1.quantum_state]
            # print("entangled keys:", keys)

            # We are using the quantum state manager. 
            self.timeline.quantum_manager.set(keys, rho)

            # print("LS type:", type(self.timeline.quantum_manager.states[new_photon0.quantum_state].state))

            new_photon0.TN_inds = [0,1]
            new_photon1.TN_inds = [2,3]
            # print("all keys in quantum manager:", self.timeline.quantum_manager.states[new_photon1.quantum_state].keys, self.timeline.quantum_manager.states[new_photon0.quantum_state].keys)
            # print("setting photons succesful")

            if debug:
                return new_photon0, new_photon1

            self.send_photons(time, [new_photon0, new_photon1])
            self.photon_counter += 1
            time += 1e12 / self.frequency

    def send_photons(self, time, photons: List["Photon"]):
        log.logger.debug("SPDC source {} sending photons to {} at time {}".format(self.name, self._receivers, time))
        # print("sending photons at light source")
        assert len(photons) == 2
        for dst, photon in zip(self._receivers, photons):
            process = Process(dst, "get", [photon])
            event = Event(int(round(time)), process)
            self.timeline.schedule(event)
        

    def set_wavelength(self, wavelength1=1550, wavelength2=1550):
        """Method to set the wavelengths of photons emitted in two output modes."""
        self.wavelengths = [wavelength1, wavelength2]
