"""useful constants"""

from typing import Final

# speed of light in (m / pico second)
SPEED_OF_LIGHT: Final = 2e-4

# |0> and |1>
KET0: Final = (1, 0)
KET1: Final = (0, 1)

# four Bell states
SQRT_HALF: Final = 0.5 ** 0.5
PHI_PLUS:  Final = (SQRT_HALF, 0, 0,  SQRT_HALF)
PHI_MINUS: Final = (SQRT_HALF, 0, 0, -SQRT_HALF)
PSI_PLUS:  Final = (0, SQRT_HALF,  SQRT_HALF, 0)
PSI_MINUS: Final = (0, SQRT_HALF, -SQRT_HALF, 0)

# machine epsilon, i.e., a small number
EPSILON: Final = 1e-8

# convert to picosecond
NANOSECOND:  Final = 10**3
MICROSECOND: Final = 10**6
MILLISECOND: Final = 10**9
SECOND:      Final = 10**12

# Built-In Formalisms
KET_STATE_FORMALISM: Final = "ket_vector"
DENSITY_MATRIX_FORMALISM: Final = "density_matrix"
FOCK_DENSITY_MATRIX_FORMALISM: Final = "fock_density"
BELL_DIAGONAL_STATE_FORMALISM: Final = "bell_diagonal"

# Built-In Generation Protocols
BARRET_KOK: Final = 'barret_kok'
SINGLE_HERALDED: Final = 'single_heralded'



# Topology Config Keys - Topology (parent) Level
ALL_C_CONNECT: Final = "cconnections"    # a connection consist of two opposite direction channels
ALL_C_CHANNEL: Final = "cchannels"
ALL_NODE: Final = "nodes"
ALL_Q_CONNECT: Final = "qconnections"
ALL_Q_CHANNEL: Final = "qchannels"
ALL_TEMPLATES: Final = "templates"

# Topology Config Keys - Shared Properties
ATTENUATION: Final = "attenuation"
CONNECT_NODE_1: Final = "node1"
CONNECT_NODE_2: Final = "node2"
DELAY: Final = "delay"
DISTANCE: Final = "distance"
DST: Final = "destination"
NAME: Final = "name"
SEED: Final = "seed"
SRC: Final = "source"
STOP_TIME: Final = "stop_time"
TRUNC: Final = "truncation"
TYPE: Final = "type"
TEMPLATE: Final = "template"

# Topology Config Keys - quantum simulation constants
GATE_FIDELITY: Final = "gate_fidelity"
MEASUREMENT_FIDELITY: Final = "measurement_fidelity"
FORMALISM: Final = "formalism"  # "ket_vector", "density_matrix", "bell_diagonal", etc

# Topology Config Keys - memory conf
MEMO_ARRAY_SIZE: Final = "memo_size"           # communication memories
DATA_MEMO_ARRAY_SIZE: Final = "data_memo_size" # data memories (DQC)

# Topology Config Keys - QLAN child class
LOCAL_MEMORIES: Final = "local_memories"
CLIENT_NUMBER: Final = "client_number"
MEASUREMENT_BASES: Final = "measurement_bases"
MEM_FIDELITY_ORCH: Final = "memo_fidelity_orch"
MEM_FREQUENCY_ORCH: Final = "memo_frequency_orch"
MEM_EFFICIENCY_ORCH: Final = "memo_efficiency_orch"
MEM_COHERENCE_ORCH: Final = "memo_coherence_orch"
MEM_WAVELENGTH_ORCH: Final = "memo_wavelength_orch"
MEM_FIDELITY_CLIENT: Final = "memo_fidelity_client"
MEM_FREQUENCY_CLIENT: Final = "memo_frequency_client"
MEM_EFFICIENCY_CLIENT: Final = "memo_efficiency_client"
MEM_COHERENCE_CLIENT: Final = "memo_coherence_client"
MEM_WAVELENGTH_CLIENT: Final = "memo_wavelength_client"

#NOTE Config keys for port and process_num removed (unused)

# Node Type Identifiers
BSM_NODE: Final = "BSMNode"
QUANTUM_ROUTER: Final = "QuantumRouter"
DQC_NODE: Final = "DQCNode"
QKD_NODE: Final = "QKDNode"
ORCHESTRATOR: Final = "QlanOrchestratorNode"
CLIENT: Final = "QlanClientNode"
CONTROLLER: Final = "Controller" # Unused for now.

# Connection Type Identifiers
MEET_IN_THE_MID: Final = "meet_in_the_middle"



