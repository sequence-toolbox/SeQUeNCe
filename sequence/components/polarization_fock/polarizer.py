from typing import List
from ...kernel.entity import Entity
from ...kernel.quantum_state import State 
from ...components.photon import Photon
from ...components.polarizer import Polarizer
import numpy as np


class Polarizer(Polarizer):
    
    # def __init__(self, name, timeline, num_qubits = 1, angles = {0:0}):
        

    #     Entity.__init__(self, name, timeline)
    #     self.num_qubits = num_qubits
    #     self.rx = lambda theta:np.array([ [np.cos(theta/2), np.sin(theta/2)], [-np.sin(theta/2), np.cos(theta/2)] ])
    #     self.identity = np.eye(2)
    #     self.ket_0 = np.array([1,0])[np.newaxis].T
    #     self.rotate(angles)


    # def init(self):
    #     """Implementation of Entity interface (see base class)."""

    #     pass

    def rotate(self, new_angles_dict):
        """
        Rotate the polarizers by angles specified in dictionary new_angles_dict. 
        The contents of the dict are: {qubit_index : polarizer angle} 
        """
        self.projector = 1
        for i in new_angles_dict.keys():
            self.projector = self.rx(new_angles_dict[i]) @ self.ket_0


    def get(self, photon, **kwargs):
        print("polarizer.")
        key = photon.quantum_state

        prepared_state, all_keys = self.timeline.quantum_manager._prepare_state([key])
        total_projector = self.timeline.quantum_manager._prepare_operator(all_keys, [key], self.projector)

        output_state = total_projector @ prepared_state @ total_projector.conjugate().transpose()
        self.timeline.quantum_manager.set(all_keys, output_state)
        self._receivers[0].get(photon, kwargs)
