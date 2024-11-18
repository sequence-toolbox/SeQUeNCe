from typing import List
from functools import lru_cache

from numpy import multiply, sqrt, zeros, outer
from math import factorial
import numpy as np
from scipy import sparse as sp
from scipy.sparse import kron
from scipy.sparse.linalg import expm
from scipy.linalg import fractional_matrix_power
from matplotlib import pyplot as plt

from ..photon import Photon
from ...kernel.entity import Entity
from ...kernel.event import Event
from ...kernel.quantum_utils import sparse_density_partial_trace
from ...kernel.process import Process
from ...utils.encoding import polarizationFock
from ...utils import log
from ..light_source import LightSource

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
        self.I = sp.eye(self.trunc+1)
        # If the user uses a setting where both the photons have different wavelengths, you take the object 
        # from the user and use it directly. Otherwise, the direct method is to call set_wavelengths which sets 
        # both photons to have 1550nm wavelength. 
        if self.wavelengths is None or len(self.wavelengths) != 2:
            self.set_wavelength()

    def init(self):
        assert len(self._receivers) == 2, "SPDC source must connect to 2 receivers."


    def power(self, matrix, power):
        if power:
            return matrix**power
        return sp.eye(matrix.shape[0])

    # @lru_cache(maxsize=1000)
    # def _generate_tmsv_state(self):
    #     """Method to generate two-mode squeezed vacuum state of two output photonic modes
    #         Problem with this method: When you add up the H and V TMSV components, you are 
    #         creating an incoherent mixture. This is wrong since an entanglement is a coherent 
    #         mixture of these components. So, you'll have to use the PBS unitary to perform the 
    #         combination of H and V components coherently 
    #     Returns:
    #         array: generated state.
    #     """
    #     mean_num = self.mean_photon_num
    #     truncation = self.timeline.quantum_manager.truncation

    #     dim = self.timeline.quantum_manager.dim

    #     vacuum = sp.csr_matrix((dim, 1))
    #     vacuum[0,0] = 1        
        
    #     # create state component amplitudes list
    #     # amp_list = [(mu/(mu + 1))**(n/2) / (sqrt(mu + 1)) for n in range(truncation)]
    #     # amp_list.append((1 - sum([amp ** 2 for amp in amp_list]) )**0.5 )
    #     amp_list = [(sqrt(mean_num / (mean_num + 1)) ** m) / sqrt(mean_num + 1) for m in range(truncation)]
    #     amp_square_list = [amp ** 2 for amp in amp_list]
    #     amp_list.append(sqrt(1 - sum(amp_square_list)))

    #     adag_H = self.timeline.quantum_manager.adag_H
    #     adag_V = self.timeline.quantum_manager.adag_V
        
    #     op_H = 0
    #     op_V = 0
    #     for i in range(truncation+1):
    #         amp = amp_list[i]
    #         # TMSV is a 2 mode state (independent spatial modes). Hence, we take the tensor product of the two mode operators
    #         new_op_H = amp * ( self.power(sp.kron(adag_H, adag_H), i) ) / factorial(i)
    #         new_op_V = amp * ( self.power(sp.kron(adag_V, adag_V), i) ) / factorial(i)
    #         op_H += new_op_H
    #         op_V += new_op_V

    #     # TMSV_density_matrix = op_H @ sp.kron(vacuum, vacuum) @ op_H.conjugate().transpose() + op_V @ sp.kron(vacuum, vacuum) @ op_V.conjugate().transpose()
    #     # print("H state:\n", op_H @ sp.kron(vacuum, vacuum))
    #     # print("V state:\n", op_V @ sp.kron(vacuum, vacuum))
    #     TMSV_state = op_H @ sp.kron(vacuum, vacuum) + op_V @ sp.kron(vacuum, vacuum)
    #     # print("dimensions:", TMSV_state.transpose().shape, TMSV_state.shape)
    #     # print("magnitude :", TMSV_state.transpose() @ TMSV_state)

    #     # TRIAL ONLY!!!!!!!!!!!!!!!!!!
    #     # TMSV_state[40,0] = TMSV_state[20,0]

    #     TMSV_state = np.sqrt(1/(TMSV_state.transpose() @ TMSV_state)[0,0]) * TMSV_state
        
    #     print("TMSV state:\n", TMSV_state)

    #     labels = self.timeline.quantum_manager.generate_labels(2)
    #     # for i,label in enumerate(labels):
    #     #     print(i, label)
    #     # print("labels", labels)

    #     print("TMSV state:\n", [labels[i] for i in list(TMSV_state.nonzero()[0])])

    #     # TMSV_state = op_V @ sp.kron(vacuum, vacuum)
    #     TMSV_density_matrix = TMSV_state @ TMSV_state.conjugate().transpose()
    #     # print("TMSV density matrix:\n", TMSV_density_matrix)
    #     return TMSV_density_matrix
    
    def _find_mat_exp(self, mat):
        ans = sp.eye(mat.shape[0])
        intermediate = 1
        # print("finding matrix exp")
        for i in range(1, 50+1):
            # print("done one iteration")
            intermediate *= mat/i
            # intermediate.data = np.round(intermediate.data, 10)
            # print("num_elements:", len(intermediate.data))
            intermediate.eliminate_zeros()


            ans += intermediate
            # temp.data = intermediate / factorial(i)
        # print("done finding matrix exp")
        return ans


    @lru_cache(maxsize=1000)
    def _generate_tmsv_state(self, dm = True):
        """Method to generate two-mode squeezed vacuum state of two output photonic modes
            Problem with this method: When you add up the H and V TMSV components, you are 
            creating an incoherent mixture. This is wrong since an entanglement is a coherent 
            mixture of these components. So, you'll have to use the PBS unitary to perform the 
            combination of H and V components coherently 
        Returns:
            array: generated state.
        """

        I = sp.eye(self.timeline.quantum_manager.dim)
        a_V = self.timeline.quantum_manager.a_V  
        adag_V = self.timeline.quantum_manager.adag_V 
        a_H = self.timeline.quantum_manager.a_H
        adag_H = self.timeline.quantum_manager.adag_H 
        
        # The H polarization would be transmitted unchanged. So, we only focus on the 
        # V polarized photons. Now, we have 2 modes of V polarized photons which need to be 
        # reflected. So, we create the unitaries for both individually and multiply them. 
        theta_H = np.pi/2

        # print("types:", type(a_V), type(a_V), type(adag_V), type(adag_V), type(I))

        a_H_Signal = kron(a_H, I, "csr")
        adag_H_Signal = kron(adag_H, I, "csr")
        a_H_Idler = kron(I, a_H, "csr")
        adag_H_Idler = kron(I, adag_H, "csr")
        II = kron(I,I, "csr")

        # print("types:", type(a_H_Signal), type(a_H_Idler), type(adag_H_Signal), type(adag_H_Idler), type(II))

        hamiltonian_H_Signal = theta_H * ( kron(II, a_H_Signal, "csr")@kron(adag_H_Signal,II, "csr") - kron(a_H_Signal, II, "csr")@kron(II, adag_H_Signal, "csr") )
        # print("done1")
        hamiltonian_H_Idler = theta_H * ( kron(II, a_H_Idler, "csr")@kron(adag_H_Idler,II, "csr") - kron(a_H_Idler, II, "csr")@kron(II, adag_H_Idler, "csr") )
        # print("done2")

        # print("shape:", hamiltonian_V_Idler.shape, "amount of data:", len(hamiltonian_V_Idler.data))

        U_v_Signal = self._find_mat_exp(hamiltonian_H_Signal)
        U_v_Signal.data = np.round(U_v_Signal.data, 12)
        U_v_Signal.eliminate_zeros()

        U_v_Idler = self._find_mat_exp(hamiltonian_H_Idler)
        U_v_Idler.data = np.round(U_v_Idler.data, 12)
        U_v_Idler.eliminate_zeros()

        # print("done calculating exponentials")

        # diff = approx_exp - U_v_Signal
        # diff.data = np.round(diff.data, 12)
        # diff.eliminate_zeros()
        # print("len of difference:", len(diff.data))



        # U_v_Signal = expm(hamiltonian_V_Signal)
        # print("done3")
        # U_v_Idler = expm(hamiltonian_V_Idler)
        # print("done all")

        
        # print("final shape:", U_v_Idler.shape, "final amount of data:", len(U_v_Idler.data))
        
        BS_U = U_v_Signal @ U_v_Idler

        # Now, we create the 2 TMSV state operators interacting at the Beamsplitter. 

        mean_num = self.mean_photon_num
        # print("mean_num", mean_num)
        truncation = self.timeline.quantum_manager.truncation
        N = self.timeline.quantum_manager.N
        dim = self.timeline.quantum_manager.dim

        vacuum = sp.csr_matrix((dim, 1))
        vacuum[0,0] = 1        

        def generate_amp_list(mean_num):
            amp_list = [(sqrt(mean_num / (mean_num + 1)) ** m) / sqrt(mean_num + 1) for m in range(truncation)]
            amp_square_list = [amp ** 2 for amp in amp_list]
            amp_list.append(sqrt(1 - sum(amp_square_list)))
            return amp_list

        ampH = generate_amp_list(mean_num)
        ampV = generate_amp_list(mean_num)

        op_H = 0
        op_V = 0
        for i in range(truncation+1):
            # TMSV is a 2 mode state (independent spatial modes). Hence, we take the tensor product of the two mode operators
            new_op_H = ampH[i] * ( self.power(sp.kron(adag_H, adag_H), i) ) / factorial(i)
            new_op_V = ampV[i] * ( self.power(sp.kron(adag_V, adag_V), i) ) / factorial(i)
            op_H += new_op_H
            op_V += new_op_V
        
        TMSV_H_state = op_H @ sp.kron(vacuum, vacuum)
        TMSV_V_state = op_V @ sp.kron(vacuum, vacuum)

        total_state = kron(TMSV_H_state, TMSV_V_state)

        entangled_state = BS_U @ total_state

        entangled_state.data = np.round(entangled_state.data, 10)

        state_indices, _ = entangled_state.nonzero()

        # num_photons = 2
        # for n in state_indices:
        #     for i in range(num_photons):
        #         H = (n // (N**(2*i+1))) % N
        #         V = (n // (N**(2*i+0))) % N
        #         # print("n:", n, "H:", H, "V:", V, "i", i, "Val:", entangled_state[n,0])
        #         if H+V > truncation:
        #             # print("deleted:", n)
        #             entangled_state[n,0] = 0        
        

        entangled_state.eliminate_zeros()

        labels = self.timeline.quantum_manager.generate_labels(4)
        # print("TMSV state:\n", [f"{labels[i]}" for i in list(entangled_state.nonzero()[0])])
        # for i in list(entangled_state.nonzero()[0]): print(labels[i], entangled_state[i])
        output = [labels[i] for i in entangled_state.nonzero()[0]]
        # print("Output:", output)

        # print("entangled_state indices:", entangled_state.nonzero()[0])


        if not dm:
            return entangled_state

        entangled_state = 1/np.sqrt((entangled_state.conjugate().transpose() @ entangled_state)[0,0]) * entangled_state

        # print("total_state:", entangled_state)
        # labels = self.timeline.quantum_manager.generate_labels(4)
        # print("TMSV state:\n", [labels[i] for i in list(entangled_state.nonzero()[0])])

        # print("entangled state:", entangled_state)
    
        entangled_state = entangled_state @ entangled_state.conjugate().transpose()


        # Finding the reduced state directly by slicing
        reduced_state = entangled_state[:dim**2, :dim**2]    

        # Finding the reduced state by performing the partial trace
        # tuple_entangled_state = self.timeline.quantum_manager.extract_sparse_data(entangled_state@entangled_state.conjugate().transpose())
        # reduced_state = sparse_density_partial_trace(tuple_entangled_state, (0,), 2, dim**2)
        # print("reduced_state", reduced_state)
        return reduced_state
        

    def emit(self, num_emissions):
        """Method to emit photons.

        Will emit photons for a length of time. We do away with the statelist parameter and assume that the 
        SPDC light source can only generate the TMSV state and no others. 
        The number of photons emitted per period is calculated as a poisson random variable.

        Arguments:
            state_list (List[List[complex]]): list of complex coefficient arrays to send as photon-encoded qubits.
        """
        # log.logger.info("SPDC sourcee {} emitting {} photons".format(self.name, len(state_list)))

        time = self.timeline.now()
 
        for i in range(num_emissions):
            # generate two new photons
            new_photon0 = Photon("signal", self.timeline,
                                    wavelength=self.wavelengths[0],
                                    location=self,
                                    encoding_type=self.encoding_type,
                                    use_qm=True)
            new_photon1 = Photon("idler", self.timeline,
                                    wavelength=self.wavelengths[1],
                                    location=self,
                                    encoding_type=self.encoding_type,
                                    use_qm=True)

            # set shared state to squeezed state
            state = self._generate_tmsv_state()
            keys = [new_photon0.quantum_state, new_photon1.quantum_state]
            # print("entangled keys:", keys)

            # We are using the quantum state manager. 
            self.timeline.quantum_manager.set(keys, state)
            # print("all keys in quantum manager:", self.timeline.quantum_manager.states[new_photon1.quantum_state].keys, self.timeline.quantum_manager.states[new_photon0.quantum_state].keys)
            # print("setting photons succesful")

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
