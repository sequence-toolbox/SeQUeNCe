"""
This module implements the stabilizer-state quantum manager, developed during the project
Realistic Simulation of Quantum Repeater with Encoding and Classical Error Correction.
See arXiv https://arxiv.org/abs/2605.06928 and GitHub repo https://github.com/SagarPatange/Quantum-Repeater-Encoding

The manager stores each quantum state as a stim.TableauSimulator wrapped by StabilizerState. It is intended
for Clifford-circuit workloads where tableau simulation is more compact than dense state-vector or density-matrix
simulation.

Manager keys follow the same shared-state convention as other SeQUeNCe quantum managers: keys that are entangled
reference the same StabilizerState object. When independent stabilizer blocks are used in the same circuit, they
are merged into one tableau block before executing the circuit. Optional noise injection models imperfect gate operation,
idle decoherence, initialization and measurement reporting by sampling Pauli or depolarizing error channels.
"""

import numpy as np
from stim import TableauSimulator, Tableau, Circuit

from .base import QuantumManager
from ..quantum_state import StabilizerState
from ...constants import STABILIZER_FORMALISM, SECOND
from ...utils import log


@QuantumManager.register(STABILIZER_FORMALISM)
class QuantumManagerStabilizer(QuantumManager):
    """Quantum manager for stabilizer-state simulation.

    Attributes:
        base_seed (int | None): Base seed for deterministic child-seed generation.
        noise_rng: NumPy random generator used to sample stochastic noise events.
        one_qubit_gate_fid (float): Single-qubit gate fidelity.
        two_qubit_gate_fid (float): Two-qubit gate fidelity.
        measurement_fid (float): Measurement reporting fidelity.
        initialization_fid (float): Initialization fidelity for newly prepared qubits.
        gate_error_channel (str): Gate-noise channel mode, either depolarize (uniform) or Pauli-weighted.
        idle_error_channel (str): Idle-noise channel mode, either depolarize (uniform) or Pauli-weighted (T1/T2-derived asymmetric channel).
        pauli_1q_weights (tuple[float, ...]): Normalized X/Y/Z weights for one-qubit Pauli errors.
        pauli_2q_weights (tuple[float, ...]): Normalized Stim-order weights for two-qubit Pauli errors.
        last_idle_time_ps_by_key (dict[int, int]): Last idle-time watermark for each state key.
        gate_1q_count (int): Number of sampled one-qubit gates.
        gate_2q_count (int): Number of sampled two-qubit gates.
        gate_1q_error_count (int): Number of inserted one-qubit gate errors.
        gate_2q_error_count (int): Number of inserted two-qubit gate errors.
        measurement_count (int): Number of sampled measurements.
        measurement_error_count (int): Number of inserted measurement reporting errors.
    """

    ONE_QUBIT_GATE_TIME_PS = 20_000
    TWO_QUBIT_GATE_TIME_PS = 250_000
    MEASUREMENT_TIME_PS = 500_000
    RESET_TIME_PS = 1_200_000

    def __init__(self, seed: int | None = None, **kwargs):
        """Initialize a stabilizer manager instance.

        Args:
            seed (int | None): Base seed used for deterministic child-seed generation. If None, seeding is disabled.
            **kwargs: Extra keyword arguments for configuration:
                - one_qubit_gate_fid (float): Single-qubit gate fidelity (default: 1.0).
                - two_qubit_gate_fid (float): Two-qubit gate fidelity (default: 1.0).
                - initialization_fid (float): Initialization fidelity for newly prepared qubits (default: 1.0).
                - measurement_fid (float): Measurement reporting fidelity (default: 1.0).
                - gate_error_channel (str): Gate-noise channel mode, either "depolarize" (uniform) or "pauli" (Pauli-weighted) (default: "pauli").
                - idle_error_channel (str): Idle-noise channel mode, either "depolarize" (uniform) or "pauli" (Pauli-weighted, T1/T2-derived) (default: "pauli").
                - pauli_1q_weights (tuple[float, ...]): Normalized X/Y/Z weights for one-qubit Pauli errors (default: (1.0, 1.0, 1.0)).
                - pauli_2q_weights (tuple[float, ...] | None): Normalized Stim-order weights for two-qubit Pauli errors. If None, defaults are derived from pauli_1q_weights bias.

        Notes:
            The manager uses a counter-based seed derivation strategy for reproducible, human-traceable per-state seeds.
        """
        super().__init__()
        self.base_seed: int | None = seed   # Base seed controls deterministic per-state/per-operation seed derivation.
        self._seed_counter: int = 0         # Monotonic counter used with base_seed to produce unique child seeds.
        self.noise_rng: np.random.Generator = np.random.default_rng(seed)
        self.one_qubit_gate_fid: float = self._validate(kwargs.get("one_qubit_gate_fid", 1.0))
        self.two_qubit_gate_fid: float = self._validate(kwargs.get("two_qubit_gate_fid", 1.0))
        self.measurement_fid: float = self._validate(kwargs.get("measurement_fid", 1.0))
        self.initialization_fid: float = self._validate(kwargs.get("initialization_fid", 1.0))
        self.gate_error_channel: str = kwargs.get("gate_error_channel", "pauli")
        self.idle_error_channel: str = kwargs.get("idle_error_channel", "pauli")
        self.pauli_1q_weights: tuple[float, ...] = self._normalize_pauli_weights(kwargs.get("pauli_1q_weights", (1.0, 1.0, 1.0)), 3, "pauli_1q_weights")
        self.pauli_2q_weights: tuple[float, ...] = self._initialize_pauli_2q_weights(kwargs.get("pauli_2q_weights"))
        self.last_idle_time_ps_by_key: dict[int, int] = {}  # Last active simulation time per key.
        self.gate_1q_count: int = 0
        self.gate_2q_count: int = 0
        self.gate_1q_error_count: int = 0
        self.gate_2q_error_count: int = 0
        self.measurement_count: int = 0
        self.measurement_error_count: int = 0

    @staticmethod
    def _validate(value: float) -> float:
        """Return a probability value after validating it is in [0, 1].
        
        Args:
            value (float): Probability value to validate.

        Returns:
            float: Validated probability value.
        """
        if not 0.0 <= value <= 1.0:
            raise ValueError("Fidelity must be between 0 and 1, inclusive.")
        return value

    def _initialize_pauli_2q_weights(self, raw_pauli_2q_weights: tuple | None = None) -> tuple[float, ...]:
        """Initialize the two-qubit Pauli weights.

        Args:
            raw_pauli_2q_weights: Optional raw PAULI_CHANNEL_2 weights. If None, defaults are derived from the 1q Pauli bias.
        
        Returns:
            tuple[float, ...]: Normalized PAULI_CHANNEL_2 weights in Stim order.
        """
        if raw_pauli_2q_weights is None:
            return self._derive_default_pauli_2q_weights(self.pauli_1q_weights)
        if not isinstance(raw_pauli_2q_weights, tuple):
            raise TypeError("pauli_2q_weights must be a tuple of 15 numeric weights or None")
        return self._normalize_pauli_weights(raw_pauli_2q_weights, 15, "pauli_2q_weights")

    def new(self, state: StabilizerState | Tableau | TableauSimulator | list | None = None) -> int:
        """Create and register a new stabilizer-state key.

        Args:
            state (Optional[Union[StabilizerState, Tableau, TableauSimulator, list]]):
                Optional initializer:
                - None: default seeded single-qubit simulator state.
                - StabilizerState: copied and rebound to the new key.
                - TableauSimulator: copied and rebound to the new key.
                - Tableau / state vector list: converted to simulator state.

        Returns:
            int: Newly allocated state key.

        Raises:
            TypeError: If state is not a supported initializer type.
        """
        key = self._least_available
        self._least_available += 1
        if state is None:
            seed = self._next_seed()
            simulator = TableauSimulator(seed=seed)
            simulator.set_num_qubits(1)
            self._apply_initialization_fidelity(simulator, [0])
            self.states[key] = StabilizerState(state=simulator, keys=[key], seed=seed)
        else:
            self.states[key] = self._initialize_stabilizer_state(state, [key])
        self.last_idle_time_ps_by_key[key] = 0
        return key

    def set(self, keys: list[int], state: StabilizerState | Tableau | TableauSimulator | list):
        """Assign a shared stabilizer state object to one or more keys.

        Args:
            keys (list[int]): State keys that should reference the same state.
            state (StabilizerState | Tableau | TableauSimulator | list): State payload to assign.
        """
        state_obj = self._initialize_stabilizer_state(state, list(keys))
        for key in keys:
            self.states[key] = state_obj

    def run_circuit(self, circuit: Circuit, keys: list[int], inject_gate_error: bool = False) -> dict[int, int]:
        """Execute a Stim circuit on stabilizer states.

        Args:
            circuit: Stim circuit to execute.
            keys (list[int]): Ordered keys mapped to circuit qubit indices.
            inject_gate_error: If True, execute ideal gates and then apply injected gate-noise channels.

        Returns:
            dict[int, int]: Measurement outcomes keyed by measured state keys.
        """
        # 1. Preparation
        if not isinstance(circuit, Circuit):
            raise TypeError(f"circuit must be Circuit from stim, got {type(circuit)}")

        measured_qubits: list[int] = []
        saw_measurement = False
        supported_names = {"H", "X", "Y", "Z", "S", "S_DAG", "CX", "CZ", "SWAP", "M", "MX", "MY"}
        instruction_payloads: list[tuple[str, list[int]]] = []

        for instruction in circuit:
            name = instruction.name
            if name not in supported_names:
                raise ValueError(f"Unsupported stim instruction for stabilizer manager: {name}")

            targets = [int(target.value) for target in instruction.targets_copy()]
            if any(target < 0 or target >= len(keys) for target in targets):
                raise ValueError(f"Stim target out of range for {name}: {targets}")

            if name in {"M", "MX", "MY"}:
                saw_measurement = True
                measured_qubits.extend(targets)
            elif saw_measurement:
                raise ValueError("Stabilizer manager only supports terminal measurements.")
            instruction_payloads.append((name, targets))

        # Prepare validated inputs, merged/shared topology, and key index mapping.
        state_obj, key_to_local = self._prepare_circuit(len(keys), measured_qubits, keys)
        if state_obj is None:
            return {}

        # 2. Execution (with optional noise injection)
        simulator = state_obj.state.copy()
        # Fast path: when gate-noise injection is disabled, batch all non-measurement
        # gates into one Stim circuit and execute it in a single simulator call.
        if not inject_gate_error:
            ideal_circuit = Circuit()
            for name, targets in instruction_payloads:
                if name in {"M", "MX", "MY"}:
                    continue
                for elementary_targets in self._iter_elementary_gate_targets(name, targets):
                    local_targets = [key_to_local[keys[target]] for target in elementary_targets]
                    ideal_circuit.append(name, local_targets)
            if len(ideal_circuit) > 0:
                simulator.do(ideal_circuit)
        else:
            # Slow path: keep per-gate application when noise injection is enabled so
            # each ideal gate can be followed immediately by its noise channel.
            for name, targets in instruction_payloads:
                if name in {"M", "MX", "MY"}:
                    continue

                for elementary_targets in self._iter_elementary_gate_targets(name, targets):
                    circuit_keys = [keys[target] for target in elementary_targets]
                    local_targets = [key_to_local[key] for key in circuit_keys]
                    local_circuit = Circuit()
                    local_circuit.append(name, local_targets)
                    simulator.do(local_circuit)
                    self._apply_gate_error(simulator, name, local_targets)

        # 3. Measurement handling and quantum manager state updates
        if len(measured_qubits) == 0:  # No measurement: commit a fresh shared state object for all keys.
            committed_state = StabilizerState(state=simulator, keys=list(state_obj.keys))
            for key in state_obj.keys:
                self.states[key] = committed_state
            return {}
        else:                          # Measurement: update states according to measurement outcomes and return results.
            # Measure each requested key, report (possibly flipped) bit, and split measured states.
            results: dict[int, int] = {}
            measured_keys: list[int] = []
            for name, targets in instruction_payloads:
                if name not in {"M", "MX", "MY"}:
                    continue

                for target in targets:
                    measured_key = keys[target]
                    local_target = key_to_local[measured_key]
                    self.measurement_count += 1

                    if name == "MX":
                        simulator.h(local_target)
                    elif name == "MY":
                        simulator.s_dag(local_target)
                        simulator.h(local_target)

                    physical_bit = int(simulator.measure(local_target))

                    reported_bit = physical_bit
                    if inject_gate_error and self.measurement_fid < 1.0 and self.noise_rng.random() > self.measurement_fid:
                        reported_bit ^= 1
                        self.measurement_error_count += 1
                    results[measured_key] = reported_bit
                    measured_keys.append(measured_key)

                    collapsed = TableauSimulator(seed=self._next_seed())
                    collapsed.set_num_qubits(1)
                    if physical_bit == 1:
                        collapsed.x(0)
                    self.states[measured_key] = StabilizerState(state=collapsed, keys=[measured_key])

            # Physically drop measured qubits so simulator indices stay compact for remaining keys.
            simulator, remaining_keys = self._drop_keys_from_stabilizer_simulator(simulator, state_obj.keys, measured_keys)

            # Keep unmeasured keys grouped on the shared post-measurement simulator state.
            if remaining_keys:
                remaining_state = StabilizerState(state=simulator, keys=remaining_keys)
                for key in remaining_keys:
                    self.states[key] = remaining_state

            return results

    def _iter_elementary_gate_targets(self, gate_name: str, targets: list[int]) -> list[list[int]]:
        """Split one Stim instruction target list into elementary gate targets.

        Args:
            gate_name: Stim gate name.
            targets: Flat instruction target list in circuit-local indices.

        Returns:
            list[list[int]]: Elementary target groups for one gate application each.
        """
        if gate_name in {"H", "X", "Y", "Z", "S", "S_DAG", "M", "MX", "MY"}:
            return [[target] for target in targets]
        if gate_name in {"CX", "CZ", "SWAP"}:
            if len(targets) % 2 != 0:
                raise ValueError(f"Expected even target count for {gate_name}, got {len(targets)}.")
            return [targets[index:index + 2] for index in range(0, len(targets), 2)]
        raise ValueError(f"Unsupported gate for elementary target split: {gate_name}")

    def get_circuit_duration(self, circuit: Circuit) -> int:
        """Return the estimated execution time of a circuit in picoseconds.

        Args:
            circuit: Stim circuit to estimate.

        Returns:
            int: Estimated circuit duration in picoseconds.
        """
        if not isinstance(circuit, Circuit):
            raise TypeError(f"circuit must be Circuit from stim, got {type(circuit)}")
        duration_ps = 0

        for instruction in circuit:
            name = instruction.name
            targets_raw = instruction.targets_copy()
            if any(not getattr(target, "is_qubit_target", False) for target in targets_raw):
                raise RuntimeError(f"Unsupported non-qubit target in duration estimate: {name}")

            if name in {"H", "X", "Y", "Z", "S", "S_DAG"}:
                duration_ps += self.ONE_QUBIT_GATE_TIME_PS
            elif name in {"CX", "CZ", "SWAP"}:
                duration_ps += self.TWO_QUBIT_GATE_TIME_PS
            elif name in {"M", "MX", "MY"}:
                duration_ps += self.MEASUREMENT_TIME_PS
            else:
                raise RuntimeError(f"Unsupported gate for duration estimate: {name}")

        return int(duration_ps)

    def get_reset_duration(self, num_qubits: int) -> int:
        """Return the estimated reset time in picoseconds.

        Args:
            num_qubits: Number of qubits being reset.

        Returns:
            int: Estimated reset duration in picoseconds.
        """
        if num_qubits < 0:
            raise RuntimeError(f"num_qubits must be >= 0, got {num_qubits}")
        return int(num_qubits * self.RESET_TIME_PS)

    def apply_idling_decoherence(self, keys: list[int], now_ps: int, t1_sec: float, t2_sec: float):
        """Apply time-based idling decoherence to the provided keys.
           The PAULI_CHANNEL_1 applies the standard T1/T2 to Pauli approximation and requires 0 < T2 <= 2*T1

        Args:
            keys: Quantum-manager keys to decohere.
            now_ps: Current simulation time in picoseconds.
            t1_sec: Shared T1 time constant in seconds.
            t2_sec: Shared T2 time constant in seconds.
        """
        if len(keys) == 0:
            return

        if not (0 < t2_sec <= 2 * t1_sec):
            raise ValueError(f"Invalid T1/T2 values: T1={t1_sec}, T2={t2_sec}. Must satisfy 0 < T2 <= 2*T1.")

        state_obj, key_to_local = self._prepare_circuit(len(keys), [], keys)

        for key in keys:
            last_ps = self.last_idle_time_ps_by_key.get(key, now_ps)
            idle_sec = (now_ps - last_ps) / SECOND
            if idle_sec > 0:  # Only proceed if there is a positive idle interval
                px = (1.0 - np.exp(-idle_sec / t1_sec)) / 4.0
                py = px
                pz = (1.0 + np.exp(-idle_sec / t1_sec) - 2.0 * np.exp(-idle_sec / t2_sec)) / 4.0
                local = key_to_local[key]
                noise_circuit = Circuit()
                if self.idle_error_channel == "depolarize":
                    p_idle = float(px + py + pz)
                    noise_circuit.append("PAULI_CHANNEL_1", [local], [p_idle / 3.0, p_idle / 3.0, p_idle / 3.0])
                elif self.idle_error_channel == "pauli":
                    noise_circuit.append("PAULI_CHANNEL_1", [local], [float(px), float(py), float(pz)])
                else:
                    raise ValueError("idle_error_channel must be 'depolarize' or 'pauli'.")
                state_obj.state.do(noise_circuit)

        for key in state_obj.keys:
            self.last_idle_time_ps_by_key[key] = now_ps
    
    def set_to_zero(self, key: int | list[int]):
        """Reset one or more qubits to the |0⟩ computational basis state.

        Args:
            key (int | list[int]): State key or keys of the qubits to reset.
        """
        if isinstance(key, list):
            for single_key in key:
                self.set_to_zero(single_key)
            return

        seed = self._next_seed()
        simulator = TableauSimulator(seed=seed)
        simulator.set_num_qubits(1)
        self._apply_initialization_fidelity(simulator, [0])
        self.states[key] = StabilizerState(state=simulator, keys=[key], seed=seed)
        self.last_idle_time_ps_by_key[key] = 0

    def set_to_one(self, key: int):
        """Reset a single qubit to the |1⟩ computational basis state.

        Args:
            key (int): State key of the qubit to reset.
        """
        seed = self._next_seed()
        sim = TableauSimulator(seed=seed)
        sim.set_num_qubits(1)
        sim.x(0)
        self._apply_initialization_fidelity(sim, [0])
        self.states[key] = StabilizerState(state=sim, keys=[key], seed=seed)
        self.last_idle_time_ps_by_key[key] = 0

    def remove(self, key: int):
        """Remove a key and refresh the debug key layout map.
        
        Args:
            key (int): State key to remove.
        """
        super().remove(key)
        self.last_idle_time_ps_by_key.pop(key, None)

    def reset_error_statistics(self):
        """Clear gate and error counters
        """
        self.gate_1q_count = 0
        self.gate_2q_count = 0
        self.measurement_count = 0
        self.gate_1q_error_count = 0
        self.gate_2q_error_count = 0
        self.measurement_error_count = 0

    def get_error_statistics(self) -> dict[str, int | float]:
        """Return per-run gate accounting statistics.

        Returns:
            dict[str, int | float]: One- and two-qubit gate counts, sampled gate-error counts, and measurement counts.
        """
        return {"gate_1q_count": self.gate_1q_count,
                "gate_2q_count": self.gate_2q_count,
                "measurement_count": self.measurement_count,
                "gate_1q_error_count": self.gate_1q_error_count,
                "gate_2q_error_count": self.gate_2q_error_count,
                "measurement_error_count": self.measurement_error_count}

    def _next_seed(self) -> int | None:
        """Return next seed value or None if unseeded.

        Returns:
            int | None: Next seed value for deterministic operations, or None if seeding is disabled.
        """
        # None means deterministic seeding is disabled for this manager.
        if self.base_seed is None:
            return None
        # Derive a reproducible child seed and advance the counter.
        seed = int(self.base_seed + self._seed_counter)
        self._seed_counter += 1
        return seed

    def _apply_initialization_fidelity(self, simulator: TableauSimulator, targets: list[int]):
        """Apply initialization depolarizing noise to freshly prepared qubits.

        Args:
            simulator: Active simulator to mutate.
            targets: Simulator-local qubit indices that were just initialized.
        """
        p_error = min(1.0, 1.5 * (1.0 - self.initialization_fid))
        if p_error > 0:
            noise_circuit = Circuit()
            for target in targets:
                noise_circuit.append("DEPOLARIZE1", [target], p_error)
            simulator.do(noise_circuit)

    @staticmethod
    def _normalize_pauli_weights(weights: tuple[float, ...], expected_length: int, name: str) -> tuple[float, ...]:
        """Return normalized Pauli weights, falling back to uniform weights when total weight is zero.
        
        Args:
            weights: Tuple of relative Pauli weights.
            expected_length: Expected number of weights (3 for 1q, 15 for 2q).
            name: Name of the weight set for error messages.
        """
        normalized_weights = tuple(float(weight) for weight in weights)
        if len(normalized_weights) != expected_length:
            raise ValueError(f"{name} must have {expected_length} entries.")

        total = float(sum(normalized_weights))
        if total <= 0.0:
            return tuple(1.0 / expected_length for _ in range(expected_length))
        return tuple(weight / total for weight in normalized_weights)

    @staticmethod
    def _derive_default_pauli_2q_weights(pauli_1q_weights: tuple[float, ...], single_only_fraction: float = 0.8) -> tuple[float, ...]:
        """Derive default 2q Pauli weights from the configured 1q Pauli bias.

        Args:
            pauli_1q_weights: Relative 1q Pauli weights in X, Y, Z order.
            single_only_fraction: Fraction of 2q faults assigned to one-sided Pauli terms.

        Returns:
            tuple[float, ...]: Relative PAULI_CHANNEL_2 weights in Stim order.
        """
        total = float(sum(pauli_1q_weights))
        if total <= 0.0:
            x_weight = 1.0 / 3.0
            y_weight = 1.0 / 3.0
            z_weight = 1.0 / 3.0
        else:
            x_weight = float(pauli_1q_weights[0]) / total
            y_weight = float(pauli_1q_weights[1]) / total
            z_weight = float(pauli_1q_weights[2]) / total

        correlated_fraction = 1.0 - float(single_only_fraction)
        single_scale = float(single_only_fraction) / 2.0
        return (single_scale * x_weight,                    # IX
                single_scale * y_weight,                    # IY
                single_scale * z_weight,                    # IZ
                single_scale * x_weight,                    # XI
                correlated_fraction * x_weight * x_weight,  # XX
                correlated_fraction * x_weight * y_weight,  # XY
                correlated_fraction * x_weight * z_weight,  # XZ
                single_scale * y_weight,                    # YI
                correlated_fraction * y_weight * x_weight,  # YX
                correlated_fraction * y_weight * y_weight,  # YY
                correlated_fraction * y_weight * z_weight,  # YZ
                single_scale * z_weight,                    # ZI
                correlated_fraction * z_weight * x_weight,  # ZX
                correlated_fraction * z_weight * y_weight,  # ZY
                correlated_fraction * z_weight * z_weight)  # ZZ
            
    def _sample_pauli_channel_branch(self, channel_name: str, probs: list[float], targets: list[int], source: str) -> str:
        """Sample one realized Pauli-channel branch and log it.

        Args:
            channel_name: Either PAULI_CHANNEL_1 or PAULI_CHANNEL_2.
            probs: Non-identity branch probabilities in Stim order.
            targets: Simulator-local target indices.
            source: Short source tag such as idle or gate:CX.

        Returns:
            str: Sampled Pauli label, e.g. I, Z, IX, or ZZ.
        """
        if channel_name == "PAULI_CHANNEL_1":
            branch_labels = ["I", "X", "Y", "Z"]
            if len(probs) != 3:
                raise ValueError("PAULI_CHANNEL_1 requires 3 probabilities.")
            identity_label = "I"
            identity_prob = max(0.0, 1.0 - sum(probs))
            branch_probs = [identity_prob, probs[0], probs[1], probs[2]]
        elif channel_name == "PAULI_CHANNEL_2":
            branch_labels = [
                "II", "IX", "IY", "IZ",
                "XI", "XX", "XY", "XZ",
                "YI", "YX", "YY", "YZ",
                "ZI", "ZX", "ZY", "ZZ",
            ]
            if len(probs) != 15:
                raise ValueError("PAULI_CHANNEL_2 requires 15 probabilities.")
            identity_label = "II"
            identity_prob = max(0.0, 1.0 - sum(probs))
            branch_probs = [identity_prob] + list(probs)
        else:
            raise ValueError(f"Unsupported channel_name '{channel_name}'.")

        total = float(sum(branch_probs))
        if total <= 0.0:
            sampled_branch = identity_label
        else:
            normalized_probs = [prob / total for prob in branch_probs]
            sampled_index = int(self.noise_rng.choice(len(branch_labels), p=normalized_probs))
            sampled_branch = branch_labels[sampled_index]

        log.logger.info(f"pauli_channel_sample source={source} channel={channel_name} targets={targets} "
                        f"branch={sampled_branch} inserted_error={int(sampled_branch != identity_label)}")
        return sampled_branch

    @staticmethod
    def _apply_sampled_pauli_branch(simulator: TableauSimulator, targets: list[int], sampled_branch: str):
        """Apply a sampled Pauli branch directly to the simulator.

        Args:
            simulator: Active simulator to mutate.
            targets: Simulator-local target indices.
            sampled_branch: Sampled Pauli label such as I, Z, IX, or ZZ.
        """
        if len(sampled_branch) != len(targets):
            raise ValueError("sampled_branch length must match target count.")

        for pauli, target in zip(sampled_branch, targets):
            if pauli == "I":
                continue
            if pauli == "X":
                simulator.x(target)
            elif pauli == "Y":
                simulator.y(target)
            elif pauli == "Z":
                simulator.z(target)
            else:
                raise ValueError(f"Unsupported sampled Pauli '{pauli}'.")

    def _initialize_stabilizer_state(self, initializer: StabilizerState | Tableau | TableauSimulator | list, keys: list[int]) -> StabilizerState:
        """Create a stabilizer state from a supported initializer.

        Args:
            initializer: Stabilizer-compatible initializer.
            keys (list[int]): Keys that should bind to the resulting state.

        Returns:
            StabilizerState: State bound to keys.
        """
        if isinstance(initializer, StabilizerState):
            state = initializer.copy()
            state.keys = list(keys)
            return state

        if isinstance(initializer, TableauSimulator):
            simulator = initializer.copy() if hasattr(initializer, "copy") else initializer
            return StabilizerState(state=simulator, keys=list(keys))

        if isinstance(initializer, Tableau):
            tableau = initializer

        elif isinstance(initializer, list):
            tableau = Tableau.from_state_vector(np.asarray(initializer), endian="little")

        else:
            raise TypeError("Unsupported stabilizer initializer.")

        if len(tableau) != len(keys):
            raise ValueError(f"Initializer tableau has {len(tableau)} qubits but {len(keys)} keys were supplied.")

        # Load the initializer tableau into a fresh simulator bound to these keys.
        simulator = TableauSimulator(seed=self._next_seed())
        simulator.set_inverse_tableau(tableau.inverse())
        return StabilizerState(state=simulator, keys=list(keys))

    def _apply_gate_error(self, simulator: TableauSimulator, gate_name: str, targets: list[int]):
        """Apply sampled gate-error noise after ideal gate application.

        Args:
            simulator (TableauSimulator): Active simulator to mutate.
            gate_name (str): Name of gate that was just applied.
            targets (list[int]): Simulator-local target indices for the gate.

        Notes:
            one_qubit_gate_fid and two_qubit_gate_fid are average gate fidelities. For a Pauli error channel with
            total non-identity error probability p_error on a d-dimensional system, the average fidelity is
            1 - d * p_error / (d + 1). Solving for p_error gives (d + 1) / d * (1 - fidelity). Therefore,
            one-qubit gates use d = 2 and the factor 3 / 2 = 1.5; two-qubit gates use d = 4 and the factor
            5 / 4 = 1.25. The final probability is capped at 1.
        """
        name = gate_name.upper()

        if name in {"H", "X", "Y", "Z", "S", "S_DAG"}:
            self.gate_1q_count += 1
            p_error = min(1.0, 1.5 * (1.0 - self.one_qubit_gate_fid))
            if p_error > 0:
                if self.gate_error_channel == "depolarize":
                    probs = [p_error / 3.0, p_error / 3.0, p_error / 3.0]
                elif self.gate_error_channel == "pauli":
                    probs = [p_error * weight for weight in self.pauli_1q_weights]
                else:
                    raise ValueError("gate_error_channel must be 'depolarize' or 'pauli'.")
                sampled_branch = self._sample_pauli_channel_branch("PAULI_CHANNEL_1", probs, targets, f"gate:{name}")
                if sampled_branch != "I":
                    self.gate_1q_error_count += 1
                self._apply_sampled_pauli_branch(simulator, targets, sampled_branch)

        if name in {"CX", "CZ", "SWAP"}:
            self.gate_2q_count += 1
            p_error = min(1.0, 1.25 * (1.0 - self.two_qubit_gate_fid))
            if p_error > 0:
                if self.gate_error_channel == "depolarize":
                    probs = [p_error / 15.0] * 15
                elif self.gate_error_channel == "pauli":
                    probs = [p_error * weight for weight in self.pauli_2q_weights]
                else:
                    raise ValueError("gate_error_channel must be 'depolarize' or 'pauli'.")
                sampled_branch = self._sample_pauli_channel_branch("PAULI_CHANNEL_2", probs, targets, f"gate:{name}")
                if sampled_branch != "II":
                    self.gate_2q_error_count += 1
                self._apply_sampled_pauli_branch(simulator, targets, sampled_branch)

    def _prepare_circuit(self, num_qubits: int, measured_qubits: list[int], keys: list[int]) -> tuple[StabilizerState | None, dict[int, int]]:
        """Validate run input and prepare shared stabilizer context.

        Args:
            num_qubits (int): Circuit width.
            measured_qubits (list[int]): Measured qubit indices in circuit order.
            keys (list[int]): Ordered keys mapped to circuit qubit indices.

        Returns:
            tuple[StabilizerState | None, dict[int, int]]:
                Shared stabilizer state object and key-to-local index mapping
                (local refers to indices within the shared TableauSimulator, always 0...num_qubits-1).
        """
        if len(keys) != num_qubits:
            raise ValueError(f"circuit width ({num_qubits}) must equal len(keys) ({len(keys)}).")
        if not keys:
            return None, {}
        if len(set(keys)) != len(keys):
            raise ValueError(f"Duplicate keys are not allowed in run_circuit: {keys}")

        missing_keys = [key for key in keys if key not in self.states]
        if missing_keys:
            raise ValueError(f"Unknown key(s) in run_circuit: {missing_keys}")

        if any(i < 0 or i >= num_qubits for i in measured_qubits):
            raise ValueError(f"Measured qubit index out of range: {measured_qubits}")
        if len(set(measured_qubits)) != len(measured_qubits):
            raise ValueError(f"Duplicate measured qubit indices are not allowed: {measured_qubits}")

        # Collect each distinct shared stabilizer block touched by the requested keys.
        unique_states: list[StabilizerState] = []
        seen_state_ids: set[int] = set()
        for key in keys:
            qstate = self.states[key]
            if not isinstance(qstate, StabilizerState):
                raise ValueError(f"Expected StabilizerState for key {key}, got {type(qstate)}")
            if qstate.state.num_qubits != len(qstate.keys):
                raise RuntimeError(f"Tableau/key mismatch for state keys: {qstate.keys}")
            if id(qstate) not in seen_state_ids:
                seen_state_ids.add(id(qstate))
                unique_states.append(qstate)

        if len(unique_states) == 1:
            state_obj = unique_states[0]
        else:
            # Merge independent tableau blocks into one shared simulator state.
            merged_keys: list[int] = []
            merged_tableau = None
            for qstate in unique_states:
                merged_keys.extend(qstate.keys)
                block_tableau = qstate.current_forward_tableau()
                merged_tableau = block_tableau if merged_tableau is None else merged_tableau + block_tableau

            if len(set(merged_keys)) != len(merged_keys):
                raise ValueError(f"Merged state contains duplicate keys: {merged_keys}")
            state_obj = self._initialize_stabilizer_state(merged_tableau, merged_keys)
            for key in merged_keys:
                self.states[key] = state_obj

        # Map manager keys to local qubit indices in the shared tableau block.
        key_to_local = {key: i for i, key in enumerate(state_obj.keys)}
        return state_obj, key_to_local

    @staticmethod
    def _drop_keys_from_stabilizer_simulator(simulator: TableauSimulator, state_keys: list[int], drop_keys: list[int]) -> tuple[TableauSimulator, list[int]]:
        """Drop arbitrary keys by swapping them to tail and truncating qubits.

        Args:
            simulator (TableauSimulator): Simulator to mutate in place.
            state_keys (list[int]): Current key order mapped to simulator qubit indices.
            drop_keys (list[int]): Keys to remove from simulator state.

        Returns:
            tuple[TableauSimulator, list[int]]: Mutated simulator and remaining key order.
        """
        drop_set = set(drop_keys)
        keep_keys = [key for key in state_keys if key not in drop_set]
        tail_keys = [key for key in state_keys if key in drop_set]
        desired_order = keep_keys + tail_keys
        working_keys = list(state_keys)

        # Permute simulator qubits so kept keys come first and dropped keys are at the tail.
        for i, key in enumerate(desired_order):
            j = working_keys.index(key)
            if i != j:
                simulator.swap(i, j)
                working_keys[i], working_keys[j] = working_keys[j], working_keys[i]

        # Truncate tail qubits to physically shrink simulator state.
        if tail_keys:
            simulator.set_num_qubits(len(keep_keys))

        return simulator, keep_keys
