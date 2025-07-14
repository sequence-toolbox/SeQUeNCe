from trajectree.fock_optics.light_sources import light_source
from trajectree.fock_optics.noise_models import single_mode_bosonic_noise_channels
from trajectree.fock_optics.utils import extend_MPS, create_vacuum_state
from trajectree.fock_optics.measurement import bell_state_measurement
from trajectree.trajectory import quantum_channel

from sequence.kernel.timeline import Timeline
from sequence.kernel.event import Event
from sequence.kernel.entity import Entity
from scipy import sparse as sp


class end_node():

    def __init__(self, name, timeline, params):
        self.params = params
        self.name = name
        self.timeline = timeline

    def emit_SPDCSource(self):

        vacuum = create_vacuum_state(num_modes=8, N=self.params["N"])

        # Entangled state from EPS

        print("vacuum:", vacuum, "N:", self.params["N"], "mean_photon_num:", self.params["mean_photon_num"], "num_modes:", 8, "error_tolerance:", self.params["error_tolerance"])

        psi, TMSV_state = light_source(vacuum, self.params["N"], self.params["mean_photon_num"], 8, self.params["error_tolerance"], compress=True, contract=True)

        if not self.timeline.initial_state == None:
            self.timeline.initial_state = extend_MPS(psi)
        else:
            self.timeline.initial_state = psi

    # def _direct_fidelity_calculation(self, )

    
class QuantumChannel():
    def __init__(self, name, timeline, params):
        self.name = name
        self.timeline = timeline
        self.params = params

    def transmit(self, mode_pair):
        damping_kraus_ops = single_mode_bosonic_noise_channels(noise_parameter = self.params["channel_loss"], N = self.params["N"])
        two_mode_kraus_ops = [sp.kron(op, op) for op in damping_kraus_ops]
        self.timeline.quantum_channel_list.append(quantum_channel(N = self.params["N"], num_modes = self.timeline.initial_state.L, formalism = "kraus", kraus_ops_tuple = (mode_pair, two_mode_kraus_ops)))

class BSM_node():
    def __init__(self, name, timeline, params):
        self.name = name
        self.timeline = timeline
        self.params = params

    def perform_BSM(self, modes):
        BSM_MPOs = bell_state_measurement(None, self.params['N'], self.timeline.initial_state.site_tags, self.timeline.initial_state.L, self.params['det_eff'], self.params['error_tolerance'], pnr = self.params['pnr'], return_MPOs = True, compress=True, contract=True)

if __name__ == "__main__":

    params = {
        "truncation": 4,
        "N": 5,
        "channel_loss": 0.1,
        "mean_photon_num": 0.5,
        "error_tolerance": 1e-7,
        "det_eff": 0.9,
        "pnr": False
    }

    timeline = Timeline(stop_time=100, truncation = 4)
    timeline.quantum_channel_list = []
    timeline.initial_state = None
    timeline.N = params["N"]

    alice = end_node("Alice", timeline, params)
    bob = end_node("Bob", timeline, params)
    channel = QuantumChannel("Quantum Channel", timeline, params)
    bsm = BSM_node("BSM", timeline, params)

    # Entanglement generation sits here. 
    # This msut be scheduled in the timeline. Doing it here manually for simplicity.
    alice.emit_SPDCSource()
    bob.emit_SPDCSource()

    # Transmitting a pair of modes (polarization modes) from both the end nodes to the BSM.  
    channel.transmit(mode_pair=(2,3))
    channel.transmit(mode_pair=(6,7))

    # After transmission, the channels simply send a message to the BSM node to run the BSM operation. 
    bsm.perform_BSM(modes=((2,6),(3,7)))






