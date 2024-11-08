from functools import lru_cache

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, List
from numpy import eye, kron, exp, sqrt
from scipy.linalg import fractional_matrix_power
from math import factorial
import numpy as np
# import cupy as cp
# from numba import jit
import sys
import numpy.ma as ma
from scipy.linalg import sqrtm
import scipy.sparse as sp
np.set_printoptions(threshold = sys.maxsize)
np.set_printoptions(suppress=True)
np.set_printoptions(linewidth=np.inf)

from quimb.tensor import MatrixProductOperator as mpo  # type: ignore
from numpy.linalg import matrix_power
import qutip as qt

if TYPE_CHECKING:
    from ...kernel.timeline import Timeline

from ..photon import Photon
from ..beam_splitter import BeamSplitter
from ..switch import Switch
from ..interferometer import Interferometer
from ..circuit import Circuit
from ...kernel.event import Event
from ...kernel.entity import Entity
from ...kernel.process import Process
from ..detector import QSDetectorFockDirect, QSDetector, Detector



class QSDetectorFockDirect(QSDetector):

    # TODO: Override the set_detector method to include the detector dead times.

    def power(self, matrix, power):
        if power:
            return matrix**power
        return sp.eye(matrix.shape[0])

    def __init__(self, name: str, timeline: "Timeline", port_list : List[str]):
        super().__init__(name, timeline)
        # self.meas_outcomes = [0]*len(src_list)
        self.not_first_detection = -1
        self.meas_prob = {}
        self.meas_index = 0
        self.port_list = port_list

        # init method of original QSDetectorFockDirect
        self.detectors = []
        self.components = self.detectors

        self.povms = [None] * 4
        self.keys = []
        self.TN_inds = []

    def init(self):
        # self._generate_povms()
        super().init()
        self.trigger_times = [[]]*len(self.detectors)
        self.arrival_times = [[]]*len(self.detectors)
        self.num_possible_outcomes = 2**len(self.detectors)
        # Correct this to change the 4 below to the number of detectors
        format_string = f"{{0:0{len(self.detectors)}b}}"
        self.meas_outcomes = [format_string.format(i) for i in range(self.num_possible_outcomes)]
        self.meas_var = {}
        self.temp_photons = []

        # print("meas outcome:", self.meas_outcomes)

    # Not using anymore. This is useful when you have just one pair of detectors. Present implementation
    # is meant to work with any number of inputs. 
    # def _generate_povms(self):
    #     """Method to generate POVM operators corresponding to photon detector having 0 and 1 click
    #     Will be used to generated outcome probability distribution.
    #     """

    #     # assume using Fock quantum manager
    #     truncation = self.timeline.quantum_manager.truncation

    #     create = self.timeline.quantum_manager.adag_H
    #     destroy = self.timeline.quantum_manager.a_H

    #     # print("create type", type(create))

    #     create0 = create * sqrt(self.detectors[0].efficiency)
    #     destroy0 = destroy * sqrt(self.detectors[0].efficiency)
    #     series_elem_list = [((-1)**i) * create0.power(i+1) @ destroy0.power(i+1) / factorial(i+1) for i in range(truncation)] # (-1)^i * a_dag^(i+1) @ a^(i+1) / (i+1)! = (-1)^(i+2) * a_dag^(i+1) @ a^(i+1) / (i+1)! since goes from 0->n
        
    #     # print("type in list:", type(series_elem_list[0]))

    #     # These are the 1 and 0 POVMs for the 0th subsystem (the photons arriving at the 0th detector).
    #     povm0_1 = sp.csr_matrix(sum(series_elem_list))
    #     povm0_1.eliminate_zeros()
    #     povm0_0 = sp.csr_matrix(sp.eye(povm0_1.shape[0]) - povm0_1)


    #     create1 = create * sqrt(self.detectors[1].efficiency)
    #     destroy1 = destroy * sqrt(self.detectors[1].efficiency)
    #     series_elem_list = [((-1)**i) * create1.power(i+1) @ destroy1.power(i+1) / factorial(i+1) for i in range(truncation)]
        
    #     # These are the 1 and 0 POVMs for the 1st subsystem.
    #     povm1_1 = sp.csr_matrix(sum(series_elem_list))
    #     povm1_1.eliminate_zeros()
    #     # The original code substracted povm0_1 rather than povm1_1 which I believe would be wrong. 
    #     povm1_0 = sp.csr_matrix(sp.eye(povm1_1.shape[0]) - povm1_1)

    #     # print("povm type at detector:", type(povm0_0))
    #     self.povms = [povm0_0, povm0_1, povm1_0, povm1_1]
    #     self.sqrt_povms = [sp.csr_matrix(sqrtm(povm.A)) for povm in self.povms]
    #     # print("all povms are:")
    #     # for i in self.povms:
    #     #     # print(i)
    #     #     print(i.shape)
    #     #     print("those were the povms")
    #     self.povms = tuple([self.timeline.quantum_manager.extract_sparse_data(povm) for povm in self.povms])
    #     self.sqrt_povms = tuple([self.timeline.quantum_manager.extract_sparse_data(povm) for povm in self.sqrt_povms])
        
    # @lru_cache(maxsize=1000)
    # def _generate_povm_pair(self, idx):
    #     """Method to generate POVM operators corresponding to photon detector having 0 and 1 click
    #     Will be used to generated outcome probability distribution.
    #     """

    #     # assume using Fock quantum manager
    #     truncation = self.timeline.quantum_manager.truncation

    #     create = self.timeline.quantum_manager.adag_H
    #     destroy = self.timeline.quantum_manager.a_H

    #     create = create * sqrt(self.detectors[idx].efficiency)
    #     destroy = destroy * sqrt(self.detectors[idx].efficiency)
    #     series_elem_list = [((-1)**i) * self.power(create, (i+1)) @ self.power(destroy, (i+1)) / factorial(i+1) for i in range(truncation)] # (-1)^i * a_dag^(i+1) @ a^(i+1) / (i+1)! = (-1)^(i+2) * a_dag^(i+1) @ a^(i+1) / (i+1)! since goes from 0->n

    #     povm_1 = sp.csr_matrix(sum(series_elem_list))
    #     povm_1.eliminate_zeros()
    #     povm_0 = sp.csr_matrix(sp.eye(povm_1.shape[0]) - povm_1)

    #     povms = [povm_0, povm_1]
    #     sqrt_povms = [sp.csr_matrix(sqrtm(povm.toarray())) for povm in povms]

    #     povms = tuple([self.timeline.quantum_manager.extract_sparse_data(povm) for povm in povms])
    #     sqrt_povms = tuple([self.timeline.quantum_manager.extract_sparse_data(povm) for povm in sqrt_povms])
        
    #     return povms, sqrt_povms


    # @lru_cache(maxsize=1000)
    # def _generate_joint_povm_pair(self, asTuple = True):
    #     """Method to generate POVM operators corresponding to photon detector having 0 and 1 click
    #     Will be used to generated outcome probability distribution.
    #     """

    #     # assume using Fock quantum manager
    #     truncation = self.timeline.quantum_manager.truncation

    #     create = self.timeline.quantum_manager.adag_H
    #     destroy = self.timeline.quantum_manager.a_H

    #     # Assuming both the detectors are identical and hence, using the efficiency of the 0th detector alone. 
    #     create = create * sqrt(self.detectors[0].efficiency)
    #     destroy = destroy * sqrt(self.detectors[0].efficiency)
    #     series_elem_list = [((-1)**i) * self.power(create, (i+1)) @ self.power(destroy, (i+1)) / factorial(i+1) for i in range(truncation)] # (-1)^i * a_dag^(i+1) @ a^(i+1) / (i+1)! = (-1)^(i+2) * a_dag^(i+1) @ a^(i+1) / (i+1)! since goes from 0->n

    #     povm_1 = sp.csr_matrix(sum(series_elem_list))
    #     povm_1.eliminate_zeros()
    #     povm_0 = sp.csr_matrix(sp.eye(povm_1.shape[0]) - povm_1)

    #     povm_00 = sp.kron(povm_0, povm_0)
    #     povm_11 = sp.kron(povm_1, povm_1)

    #     # Compiling
    #     # povms = [povm_00, povm_11]
    #     # sqrt_povms = [sp.csr_matrix(sqrtm(povm.A)) for povm in povms]
    #     povm_squares = [povm_00@povm_00, povm_11@povm_11, povm_11]
    #     if not asTuple:
    #         return povm_squares
    #     # Creating tuples
    #     # povms = tuple([self.timeline.quantum_manager.extract_sparse_data(povm) for povm in povms])
    #     # sqrt_povms = tuple([self.timeline.quantum_manager.extract_sparse_data(povm) for povm in sqrt_povms])
    #     povm_squares = tuple([self.timeline.quantum_manager.extract_sparse_data(povm) for povm in povm_squares])
        
    #     return povm_squares



    def create_POVM_OP_Dense(self, efficiency, outcome, N):
        a = qt.destroy(N).full()
        a_dag = a.T
        create0 = a_dag * sqrt(efficiency)
        destroy0 = a * sqrt(efficiency)
        series_elem_list = [((-1)**i) * matrix_power(create0, (i+1)) @ matrix_power(destroy0, (i+1)) / factorial(i+1) for i in range(N-1)] # (-1)^i * a_dag^(i+1) @ a^(i+1) / (i+1)! = (-1)^(i+2) * a_dag^(i+1) @ a^(i+1) / (i+1)! since goes from 0->n
        # print(series_elem_list[0])
        dense_op = sum(series_elem_list)

        if outcome == 0:
            dense_op = np.eye(dense_op.shape[0]) - dense_op
        # print(dense_op)
        return dense_op

    def generate_POVM_MPO(self, sites, outcome, total_sites, efficiency, N, tag = "POVM"):
        dense_op = self.create_POVM_OP_Dense(efficiency, outcome, N)

        POVM_MPOs = []
        for i in sites:
            POVM_MPOs.append(mpo.from_dense(dense_op, dims = N, sites = (i,), L=total_sites, tags=tag))

        return POVM_MPOs    


    def set_detector(self, idx: int,  efficiency=0.9, dark_count=0, count_rate=int(25e6), time_resolution=150, dead_time = 7000):
        """Method to set the properties of an attached detector.

        Args:
            idx (int): the index of attached detector whose properties are going to be set.
            For other parameters see the `Detector` class. Default values are same as in `Detector` class.
        """
        # assert 0 <= idx < len(self.detectors), "`idx` must be a valid index of attached detector."
        detector = Detector("detector" + str(idx), self.timeline)
        detector.efficiency = efficiency
        detector.dark_count = dark_count
        detector.count_rate = count_rate
        detector.time_resolution = time_resolution
        detector.dead_time = dead_time

        self.detectors.append(detector)


    def get_joint(self, photon):
        # keys = [photon.quantum_state for photon in photons]

        key = photon.quantum_state

        povm_squares = self._generate_joint_povm_pair()
        
        # The probs are the probabilities of geatting the outputs correspondin to the POVMs that were passed to the measure func. 
        # It is the responsibility of the get_joint function to remember which index corresponds to what POVM and eventually what output.
        # Of course in this case however, the operator we are dealing with is the square of the POVM, so the "probability" doesn't really
        # mean much and is only used for calculating the variance in the probability of the actual proabbility. 
        probs = self.timeline.quantum_manager.measure([key], povms=povm_squares, sqrt_povms=None, meas_samp=None, outcome = None, measure_all = True)

        self.meas_var["00"] = probs[0]
        self.meas_var["11"] = probs[1]


    def get(self, photon: "Photon", **kwargs):

        port = kwargs["port"]            
        # Only change in this method:
        # assert photon.encoding_type["name"] == "fock", "Photon must be in Fock representation."
        input_port = self.port_list.index(port)  # determine at which input the Photon arrives, an index

        # record arrival time
        arrival_time = self.timeline.now()
        self.arrival_times[input_port].append(arrival_time)

        # If you have more than 2 detectors, simply change the logic for setting first_detection.
        # Everything else should work out. 
        # print("not_first_detection:", self.not_first_detection+1)
        
        self.not_first_detection = (self.not_first_detection+1)%len(self.detectors)

        self.keys.append(photon.quantum_state)  # the photon's key pointing to the quantum state in quantum manager
        
        if kwargs["meas_basis"] == "H":
            self.TN_inds.append(photon.TN_inds[0])
        elif kwargs["meas_basis"] == "V":
            self.TN_inds.append(photon.TN_inds[1])
        else:
            self.TN_inds.append(photon.TN_inds[0])
            self.TN_inds.append(photon.TN_inds[1])

        # print("receiver received photon:", self.timeline.quantum_manager.states[photon.quantum_state].keys, key)

        # samp = self.get_generator().random()  # random measurement sample
        samp = None # The random sample is generally used when  we are working in the Monte Carlo 
                    # mode of opaeration. This is not the case here though. Hence, None. 

        if self.not_first_detection == len(self.detectors) - 1:
            # Right now, we assume that all the detectors have the same efficiency. This can be changed 
            # by passing all detector efficiencies to the measure function, but we are still stuck with 
            # corresponding the quantum manager keys with MPS tensors.
            prob, mps = self.timeline.quantum_manager.measure(self.keys, self.TN_inds, outcomes = self.meas_outcomes[self.meas_index], efficiencies = [self.detectors[i].efficiency for i in range(len(self.detectors))])
            self.meas_index = (self.meas_index+1)%self.num_possible_outcomes
            self.meas_prob[self.meas_outcomes[self.meas_index]] = prob

            self.keys = []
            self.TN_inds = []



    def set_basis_list(self, basis_list: List[int], start_time: int, frequency: int) -> None:
        pass



# class QSdetectorPolarization(Entity):
#     def __init__(self, name: str, timeline: "Timeline", params:"Dict"):
#         super.__init__(name, timeline)

#         self.PBS = PBS("PBS", timeline)

#         self.detectors = QSDetectorFockDirect(name = self.name+".detectors", timeline = timeline, src_list = ["V_det", "H_det"])
#         self.detectors.set_detector(0, efficiency=params["SIGNAL_DET_EFFICIENCY"], dark_count=params["SIGNAL_DET_DARK"], count_rate=int(25e6), time_resolution=params["RESOLUTION"], dead_time=params["SIGNAL_DET_DEAD"])
#         self.detectors.set_detector(1, efficiency=params["IDLER_DET_EFFICIENCY"], dark_count=params["IDLER_DET_DARK"], count_rate=int(25e6), time_resolution=params["RESOLUTION"], dead_time=params["IDLER_DET_DEAD"])
#         self.detectors.attach(self)

#         self.PBS.add_receiver(self.detectors)

#         self.first_detection = True

#         self.photons = []

#     def get(self, photon, **kwargs):
#         src = kwargs["src"]
#         input_port = self.src_list.index(src)  # determine at which input the Photon arrives, an index

#         # record arrival time
#         arrival_time = self.timeline.now()
#         self.arrival_times[input_port].append(arrival_time)
#         self.photons[input_port] = photon

#         if not self.first_detection:
#             self.PBS.get(self.photons[0], self.photons[1])
#             self.photons = []

#     def update(self, detector, info):
#         # This is how the detector communicates with the protocol. 
#         pass



