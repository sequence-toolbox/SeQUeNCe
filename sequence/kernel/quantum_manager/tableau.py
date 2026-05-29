

import stim
from stim import TableauSimulator, Tableau
import numpy as np
from typing import Any

from .base import QuantumManager
from ..quantum_state import TableauState
from ...constants import TABLEAU_FORMALISM
from ...components.circuit import Circuit
from ...utils import log


@QuantumManager.register(TABLEAU_FORMALISM)
class QuantumManagerTableau(QuantumManager):
    """Quantum manager scaffold for tableau-state simulation.

    This class follows SeQUeNCe's `QuantumManager` contract so the formalism
    can be swapped with minimal architectural changes.

    Notes:
        Current implementation supports state creation and assignment. Circuit
        execution is intentionally left as a staged TODO.
    """

    ONE_QUBIT_GATE_TIME_PS = 20_000
    TWO_QUBIT_GATE_TIME_PS = 250_000
    MEASUREMENT_TIME_PS = 500_000
    RESET_TIME_PS = 1_200_000

    def __init__(self, truncation: int = 1, seed: int | None = None, **kwargs):
        """Initialize a tableau manager instance.

        Args:
            truncation (int): Hilbert-space truncation placeholder, retained to
                match the parent API and other formalisms.
            seed (int | None): Base seed used for deterministic child-seed
                generation. If `None`, seeding is disabled.
            gate_fid (float): Single-qubit gate fidelity in [0, 1].
            two_qubit_gate_fid (float): Two-qubit gate fidelity in [0, 1].
            measurement_fid (float): Measurement fidelity in [0, 1].
            track_error_statistics (bool): Whether to accumulate per-run gate
                and measurement counters.
            **kwargs: Extra keyword arguments accepted for compatibility.

        Returns:
            None.

        Notes:
            The manager uses a counter-based seed derivation strategy for
            reproducible, human-traceable per-state seeds.
        """
        super().__init__(truncation=truncation)
        # Base seed controls deterministic per-state/per-operation seed derivation.
        self.base_seed = seed
    
        self._seed_counter = 0         # Monotonic counter used with `base_seed` to produce unique child seeds.
        self.branch_rng = np.random.default_rng(seed)
        # Default fidelities are noiseless (1.0) unless explicitly overridden.
        self.gate_fid = float(kwargs.get("gate_fid", kwargs.get("single_qubit_gate_fid", 1.0)))
        self.two_qubit_gate_fid = float(kwargs.get("two_qubit_gate_fid", 1.0))
        self.measurement_fid = float(kwargs.get("measurement_fid", 1.0))
        self.initialization_fid = float(kwargs.get("initialization_fidelity", 1.0))
        self.track_error_statistics = bool(kwargs.get("track_error_statistics", False))
        self.gate_error_channel = str(kwargs.get("gate_error_channel", "pauli")).lower()  # Gate-noise mode: "depolarize" (uniform) or "pauli" (weighted).
        self.idle_error_channel = str(kwargs.get("idle_error_channel", "pauli")).lower()  # Idle-noise mode: "depolarize" (uniform) or "pauli" (T1/T2-derived asymmetric channel).
        self.pauli_1q_weights = tuple(float(w) for w in kwargs.get("pauli_1q_weights", (1.0, 1.0, 1.0)))  # Relative PAULI_CHANNEL_1 weights in X, Y, Z order.
        raw_pauli_2q_weights = kwargs.get("pauli_2q_weights")
        if raw_pauli_2q_weights is None:
            self.pauli_2q_weights = self._derive_default_pauli_2q_weights(self.pauli_1q_weights)  # Default 2q bias inherits the 1q Pauli bias using an 80/20 single-vs-correlated split.
        else:
            self.pauli_2q_weights = tuple(float(w) for w in raw_pauli_2q_weights)
        if len(self.pauli_1q_weights) != 3:
            raise ValueError("pauli_1q_weights must have 3 entries for X, Y, Z.")
        if len(self.pauli_2q_weights) != 15:
            raise ValueError("pauli_2q_weights must have 15 entries in Stim PAULI_CHANNEL_2 order.")
        pauli_1q_total = float(sum(self.pauli_1q_weights))
        if pauli_1q_total <= 0.0:
            self.pauli_1q_weight_fractions = (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0)
        else:
            self.pauli_1q_weight_fractions = tuple(float(weight) / pauli_1q_total for weight in self.pauli_1q_weights)
        pauli_2q_total = float(sum(self.pauli_2q_weights))
        if pauli_2q_total <= 0.0:
            self.pauli_2q_weight_fractions = tuple(1.0 / 15.0 for _ in range(15))
        else:
            self.pauli_2q_weight_fractions = tuple(float(weight) / pauli_2q_total for weight in self.pauli_2q_weights)
        self.last_idle_time_ps_by_key: dict[int, int] = {}  # Last active simulation time per key.
        self.gate_1q_count = 0
        self.gate_2q_count = 0
        self.gate_1q_error_count = 0
        self.gate_2q_error_count = 0
        self.measurement_count = 0
        self.measurement_error_count = 0

    def new(self, state: TableauState | Tableau | TableauSimulator | stim.Circuit | None = None) -> int:
        """Create and register a new tableau-backed state key.

        Args:
            state (Optional[Union[TableauState, Tableau, TableauSimulator, Circuit]]):
                Optional initializer:
                - None: default seeded single-qubit simulator state.
                - TableauState: copied and rebound to the new key.
                - TableauSimulator: copied and rebound to the new key.
                - Tableau / Circuit: converted to simulator state.
                - Also accepts additional formats (e.g., gate-name strings,
                  stabilizer lists, numpy vectors/matrices, and mapping specs).

        Returns:
            int: Newly allocated state key.

        Raises:
            TypeError: If `state` is not a supported initializer type.
        """
        key = self._least_available
        self._least_available += 1
        if state is None:
            seed = self._next_seed()
            simulator = TableauSimulator(seed=seed)
            simulator.set_num_qubits(1)
            self._apply_initialization_fidelity(simulator, [0])
            self.states[key] = TableauState(state=simulator, keys=[key], seed=seed)
        else:
            self.states[key] = self._initialize_tableau_state(state, [key])
        self.last_idle_time_ps_by_key[key] = 0
        return key

    def set(self, keys: list[int], amplitudes: Any) -> None:
        """Assign a shared tableau state object to one or more keys.

        Args:
            keys (list[int]): State keys that should reference the same state.
            amplitudes (Any): State payload to assign.
                - `TableauState`: copied before assignment.
                - Any other object: wrapped in a new `TableauState`.

        Returns:
            None.

        Examples:
            `qm.set([k0], tableau_obj)`
            `qm.set([k0, k1], tableau_state)`

        Notes:
            As in other SeQUeNCe managers, all provided keys are bound to the
            same underlying state object to represent entanglement/grouping.
        """
        super().set(keys, amplitudes)
        state = self._initialize_tableau_state(amplitudes, list(keys))
        for key in keys:
            self.states[key] = state

    def run_circuit(self, circuit: stim.Circuit | Circuit, keys: list[int], meas_samp=None, inject_gate_error: bool = False) -> dict[int, int]:
        """Execute a Stim or SeQUeNCe circuit on tableau-backed states.

        Args:
            circuit: Stim circuit or SeQUeNCe circuit to execute.
            keys (list[int]): Ordered keys mapped to circuit qubit indices.
            meas_samp: Measurement sample value used by run preparation.
            inject_gate_error: If `True`, execute ideal gates and then apply injected gate-noise channels.

        Returns:
            dict[int, int]: Measurement outcomes keyed by measured state keys.
        """
        circuit = self._to_stim_circuit(circuit)

        measured_qubits: list[int] = []
        saw_measurement = False
        supported_names = {"H", "X", "Y", "Z", "S", "S_DAG", "CX", "CZ", "SWAP", "M", "MX", "MY"}
        instruction_payloads: list[tuple[str, list[int]]] = []

        for instruction in circuit:
            name = instruction.name
            if name not in supported_names:
                raise ValueError(f"Unsupported stim instruction for tableau manager: {name}")

            targets = [int(target.value) for target in instruction.targets_copy()]
            if any(target < 0 or target >= len(keys) for target in targets):
                raise ValueError(f"Stim target out of range for {name}: {targets}")

            if name in {"M", "MX", "MY"}:
                saw_measurement = True
                measured_qubits.extend(targets)
            elif saw_measurement:
                raise ValueError("Tableau manager only supports terminal measurements.")
            instruction_payloads.append((name, targets))

        # Prepare validated inputs, merged/shared topology, and key index mapping.
        meas_samp, state_obj, key_to_local = self._prepare_circuit(len(keys), measured_qubits, keys, meas_samp)
        if state_obj is None:
            return {}

        base_simulator = state_obj.state
        simulator = base_simulator.copy() if hasattr(base_simulator, "copy") else base_simulator

        # Fast path: when gate-noise injection is disabled, batch all non-measurement
        # gates into one Stim circuit and execute it in a single simulator call.
        if not inject_gate_error:
            ideal_circuit = stim.Circuit()
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
                    local_circuit = stim.Circuit()
                    local_circuit.append(name, local_targets)
                    simulator.do(local_circuit)
                    self._apply_gate_error(simulator, name, local_targets, circuit_keys)

        # No measurements: commit a fresh shared state object for all keys.
        if len(measured_qubits) == 0:
            committed_state = TableauState(state=simulator, keys=list(state_obj.keys))
            for key in state_obj.keys:
                self.states[key] = committed_state
            return {}

        # Readout-fidelity noise uses the same toggle as gate-noise injection.
        rng = None
        if inject_gate_error and self.measurement_fid < 1.0:
            rng_seed = int(float(meas_samp) * (2 ** 31 - 1))
            rng = np.random.default_rng(rng_seed)

        # Measure each requested key, report (possibly flipped) bit, and split measured states.
        results: dict[int, int] = {}
        measured_keys: list[int] = []
        for name, targets in instruction_payloads:
            if name not in {"M", "MX", "MY"}:
                continue

            for target in targets:
                measured_key = keys[target]
                local_target = key_to_local[measured_key]
                if self.track_error_statistics:
                    self.measurement_count += 1

                if name == "MX":
                    simulator.h(local_target)
                elif name == "MY":
                    simulator.s_dag(local_target)
                    simulator.h(local_target)

                physical_bit = int(simulator.measure(local_target))

                reported_bit = physical_bit
                if inject_gate_error and self.measurement_fid < 1.0 and rng is not None and rng.random() > self.measurement_fid:
                    reported_bit ^= 1
                    if self.track_error_statistics:
                        self.measurement_error_count += 1
                results[measured_key] = reported_bit
                measured_keys.append(measured_key)

                collapsed = TableauSimulator(seed=self._next_seed())
                collapsed.set_num_qubits(1)
                if physical_bit == 1:
                    collapsed.x(0)
                self.states[measured_key] = TableauState(state=collapsed, keys=[measured_key])

        # Physically drop measured qubits so simulator indices stay compact for remaining keys.
        simulator, remaining_keys = self._drop_keys_from_tableau_simulator(simulator, state_obj.keys, measured_keys)

        # Keep unmeasured keys grouped on the shared post-measurement simulator state.
        if remaining_keys:
            remaining_state = TableauState(state=simulator, keys=remaining_keys)
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

    def get_circuit_duration(self, circuit: stim.Circuit | Circuit) -> int:
        """Return the estimated execution time of a circuit in picoseconds.

        Args:
            circuit: Stim circuit or SeQUeNCe circuit to estimate.

        Returns:
            int: Estimated circuit duration in picoseconds.
        """
        circuit = self._to_stim_circuit(circuit)
        duration_ps = 0

        for instruction in circuit:
            name = instruction.name
            targets_raw = instruction.targets_copy()
            if any(not getattr(target, "is_qubit_target", False) for target in targets_raw):
                raise RuntimeError(f"Unsupported non-qubit target in duration estimate: {name}")
            target_count = len(targets_raw)

            if name in {"H", "X", "Y", "Z", "S", "S_DAG"}:
                duration_ps += target_count * self.ONE_QUBIT_GATE_TIME_PS
            elif name in {"CX", "CZ", "SWAP"}:
                duration_ps += (target_count // 2) * self.TWO_QUBIT_GATE_TIME_PS
            elif name in {"M", "MX", "MY"}:
                duration_ps += target_count * self.MEASUREMENT_TIME_PS
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

    def apply_idling_decoherence(self, keys: list[int], now_ps: int, t1_sec: float, t2_sec: float) -> None:
        """Apply time-based idling decoherence to the provided keys.

        Args:
            keys: Quantum-manager keys to decohere.
            now_ps: Current simulation time in picoseconds.
            t1_sec: Shared T1 time constant in seconds.
            t2_sec: Shared T2 time constant in seconds.

        Returns:
            None.
        """
        if t1_sec >= 1e9 and t2_sec >= 1e9:
            for key in keys:
                self.last_idle_time_ps_by_key[key] = now_ps
            return

        _, state_obj, key_to_local = self._prepare_circuit(len(keys), [], keys, 0.5)
        for key in keys:
            last_ps = self.last_idle_time_ps_by_key.get(key, now_ps)
            idle_sec = (now_ps - last_ps) * 1e-12
            # Skip keys with no positive idle interval since the last watermark update.
            if idle_sec <= 0.0:
                continue

            px = py = (1.0 - np.exp(-idle_sec / t1_sec)) / 4.0
            pz = (1.0 + np.exp(-idle_sec / t1_sec) - 2.0 * np.exp(-idle_sec / t2_sec)) / 4.0
            local = key_to_local[key]
            noise_circuit = stim.Circuit()
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
    
    def set_to_zero(self, key: int | list[int]) -> None:
        """Reset one or more qubits to the |0⟩ computational basis state.

        Args:
            key (int | list[int]): State key or keys of the qubits to reset.

        Returns:
            None.
        """
        if isinstance(key, list):
            for single_key in key:
                self.set_to_zero(single_key)
            return

        seed = self._next_seed()
        simulator = TableauSimulator(seed=seed)
        simulator.set_num_qubits(1)
        self._apply_initialization_fidelity(simulator, [0])
        self.states[key] = TableauState(state=simulator, keys=[key], seed=seed)

    def set_to_one(self, key: int) -> None:
        """Reset a single qubit to the |1⟩ computational basis state.

        Args:
            key (int): State key of the qubit to reset.

        Returns:
            None.
        """
        seed = self._next_seed()
        sim = TableauSimulator(seed=seed)
        sim.set_num_qubits(1)
        sim.x(0)
        self._apply_initialization_fidelity(sim, [0])
        self.states[key] = TableauState(state=sim, keys=[key], seed=seed)
        self.last_idle_time_ps_by_key[key] = 0

    def remove(self, key: int) -> None:
        """Remove a key and refresh the debug key layout map."""
        super().remove(key)
        self.last_idle_time_ps_by_key.pop(key, None)

    def reset_error_statistics(self) -> None:
        """Clear accumulated error counters for one logical-pair run.

        Args:
            None.

        Returns:
            None.
        """
        self.gate_1q_count = 0
        self.gate_2q_count = 0
        self.gate_1q_error_count = 0
        self.gate_2q_error_count = 0
        self.measurement_count = 0
        self.measurement_error_count = 0

    def get_error_statistics(self) -> dict[str, int | float]:
        """Return per-run gate accounting statistics.

        Args:
            None.

        Returns:
            dict[str, int | float]: One- and two-qubit gate counts, sampled gate-error counts, and measurement counts.
        """
        return {
            "gate_1q_count": self.gate_1q_count,
            "gate_2q_count": self.gate_2q_count,
            "gate_1q_error_count": self.gate_1q_error_count,
            "gate_2q_error_count": self.gate_2q_error_count,
            "measurement_count": self.measurement_count,
            "measurement_error_count": self.measurement_error_count,
        }

    def _next_seed(self) -> int | None:
        """Return next seed value or None if unseeded."""
        # `None` means deterministic seeding is disabled for this manager.
        if self.base_seed is None:
            return None
        # Derive a reproducible child seed and advance the counter.
        seed = int(self.base_seed + self._seed_counter)
        self._seed_counter += 1
        return seed

    def _apply_initialization_fidelity(self, simulator: TableauSimulator, targets: list[int]) -> None:
        """Apply initialization depolarizing noise to freshly prepared qubits.

        Args:
            simulator: Active simulator to mutate.
            targets: Simulator-local qubit indices that were just initialized.

        Returns:
            None.
        """
        p_error = max(0.0, min(1.0, 1.5 * (1.0 - self.initialization_fid)))
        if p_error <= 0.0:
            return

        noise_circuit = stim.Circuit()
        for target in targets:
            noise_circuit.append("DEPOLARIZE1", [target], p_error)
        simulator.do(noise_circuit)

    def _derive_default_pauli_2q_weights(self, pauli_1q_weights: tuple[float, float, float], single_only_fraction: float = 0.8) -> tuple[float, ...]:
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
        return (
            single_scale * x_weight,                    # IX
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
            correlated_fraction * z_weight * z_weight,  # ZZ
        )

    def _sample_pauli_channel_branch(self, channel_name: str, probs: list[float], targets: list[int], source: str) -> str:
        """Sample one realized Pauli-channel branch and log it.

        Args:
            channel_name: Either ``PAULI_CHANNEL_1`` or ``PAULI_CHANNEL_2``.
            probs: Non-identity branch probabilities in Stim order.
            targets: Simulator-local target indices.
            source: Short source tag such as ``idle`` or ``gate:CX``.

        Returns:
            str: Sampled Pauli label, e.g. ``I``, ``Z``, ``IX``, or ``ZZ``.
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
                "II",
                "IX", "IY", "IZ",
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
            sampled_index = int(self.branch_rng.choice(len(branch_labels), p=normalized_probs))
            sampled_branch = branch_labels[sampled_index]

        log.logger.info(
            f"pauli_channel_sample source={source} channel={channel_name} "
            f"targets={targets} branch={sampled_branch} "
            f"inserted_error={int(sampled_branch != identity_label)}"
        )
        return sampled_branch

    def _apply_sampled_pauli_branch(self, simulator: TableauSimulator, targets: list[int], sampled_branch: str) -> None:
        """Apply a sampled Pauli branch directly to the simulator.

        Args:
            simulator: Active simulator to mutate.
            targets: Simulator-local target indices.
            sampled_branch: Sampled Pauli label such as ``I``, ``Z``, ``IX``, or ``ZZ``.

        Returns:
            None.
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

    def _initialize_tableau_state(self, initializer: TableauState | Tableau | TableauSimulator | np.ndarray | list | tuple, keys: list[int]) -> TableauState:
        """Create a tableau state from a supported initializer.

        Args:
            initializer: Tableau-compatible initializer.
            keys (list[int]): Keys that should bind to the resulting state.

        Returns:
            TableauState: State bound to `keys`.
        """
        if isinstance(initializer, TableauState):
            state = initializer.copy()
            state.keys = list(keys)
            return state

        if isinstance(initializer, TableauSimulator):
            simulator = initializer.copy() if hasattr(initializer, "copy") else initializer
            return TableauState(state=simulator, keys=list(keys))

        if isinstance(initializer, Tableau):
            tableau = initializer
        elif isinstance(initializer, (np.ndarray, list, tuple)):
            tableau = Tableau.from_state_vector(np.asarray(initializer), endian="little")
        else:
            raise TypeError("Unsupported tableau initializer.")

        if len(tableau) != len(keys):
            raise ValueError(f"Initializer tableau has {len(tableau)} qubits but {len(keys)} keys were supplied.")

        # Load the initializer tableau into a fresh simulator bound to these keys.
        simulator = TableauSimulator(seed=self._next_seed())
        simulator.set_inverse_tableau(tableau.inverse())
        return TableauState(state=simulator, keys=list(keys))

    def _apply_gate_error(self, simulator: TableauSimulator, gate_name: str, targets: list[int], circuit_keys: list[int]) -> None:
        """Apply sampled gate-error noise after ideal gate application.

        Args:
            simulator (TableauSimulator): Active simulator to mutate.
            gate_name (str): Name of gate that was just applied.
            targets (list[int]): Simulator-local target indices for the gate.
            circuit_keys (list[int]): Quantum-manager keys targeted by the gate.

        Returns:
            None.
        """
        name = gate_name.upper()

        if name in {"H", "X", "Y", "Z", "S", "S_DAG"}:
            if self.track_error_statistics:
                self.gate_1q_count += 1
            p_error = max(0.0, min(1.0, 1.5 * (1.0 - self.gate_fid)))
            if p_error <= 0.0:
                return
            if self.gate_error_channel == "depolarize":
                probs = [p_error / 3.0, p_error / 3.0, p_error / 3.0]
            elif self.gate_error_channel in {"pauli", "paulierror", "pauli_channel"}:
                probs = [p_error * weight for weight in self.pauli_1q_weight_fractions]
            else:
                raise ValueError("gate_error_channel must be 'depolarize' or 'pauli'.")
            sampled_branch = self._sample_pauli_channel_branch("PAULI_CHANNEL_1", probs, targets, f"gate:{name}")
            if self.track_error_statistics and sampled_branch != "I":
                self.gate_1q_error_count += 1
            self._apply_sampled_pauli_branch(simulator, targets, sampled_branch)
            return

        if name in {"CX", "CZ", "SWAP"}:
            if self.track_error_statistics:
                self.gate_2q_count += 1
            p_error = min(1.0, 1.25 * (1.0 - self.two_qubit_gate_fid))
            if p_error <= 0.0:
                return
            if self.gate_error_channel == "depolarize":
                probs = [p_error / 15.0] * 15
            elif self.gate_error_channel in {"pauli", "paulierror", "pauli_channel"}:
                probs = [p_error * weight for weight in self.pauli_2q_weight_fractions]
            else:
                raise ValueError("gate_error_channel must be 'depolarize' or 'pauli'.")
            sampled_branch = self._sample_pauli_channel_branch("PAULI_CHANNEL_2", probs, targets, f"gate:{name}")
            if self.track_error_statistics and sampled_branch != "II":
                self.gate_2q_error_count += 1
            self._apply_sampled_pauli_branch(simulator, targets, sampled_branch)
            return

    def _to_stim_circuit(self, circuit: stim.Circuit | Circuit) -> stim.Circuit:
        """Normalize supported circuit input into a Stim circuit.

        Args:
            circuit: Stim circuit or SeQUeNCe circuit.

        Returns:
            stim.Circuit: Equivalent Stim circuit.
        """
        if isinstance(circuit, stim.Circuit):
            return circuit

        if not isinstance(circuit, Circuit):
            raise TypeError(f"circuit must be stim.Circuit or SeQUeNCe Circuit, got {type(circuit)}")

        converted = stim.Circuit()
        gate_map = {
            "h": "H",
            "x": "X",
            "y": "Y",
            "z": "Z",
            "s": "S",
            "sdg": "S_DAG",
            "cx": "CX",
            "cz": "CZ",
            "swap": "SWAP",
        }

        for gate_name, indices, arg in circuit.gates:
            if arg is not None:
                raise ValueError(f"Unsupported gate arg for tableau manager: {gate_name}")
            if gate_name not in gate_map:
                raise ValueError(f"Unsupported gate '{gate_name}' for tableau manager.")
            converted.append(gate_map[gate_name], list(indices))

        for qubit in circuit.measured_qubits:
            converted.append("M", [qubit])
        for qubit in circuit.measured_x_qubits:
            converted.append("MX", [qubit])

        return converted

    def _prepare_circuit(self, num_qubits: int, measured_qubits: list[int], keys: list[int], meas_samp=None) -> tuple[float | None, TableauState | None, dict[int, int]]:
        """Validate run input and prepare shared tableau context.

        Args:
            num_qubits (int): Circuit width.
            measured_qubits (list[int]): Measured qubit indices in circuit order.
            keys (list[int]): Ordered keys mapped to circuit qubit indices.
            meas_samp: Optional measurement sample from caller.

        Returns:
            tuple[float | None, TableauState | None, dict[int, int]]:
                Normalized measurement sample, shared tableau state object, and
                key-to-local index mapping.
        """
        if measured_qubits and meas_samp is None:
            meas_samp = 0.5

        if len(keys) != num_qubits:
            raise ValueError(f"circuit width ({num_qubits}) must equal len(keys) ({len(keys)}).")
        if not keys:
            return meas_samp, None, {}
        if len(set(keys)) != len(keys):
            raise ValueError(f"Duplicate keys are not allowed in run_circuit: {keys}")

        missing_keys = [key for key in keys if key not in self.states]
        if missing_keys:
            raise ValueError(f"Unknown key(s) in run_circuit: {missing_keys}")

        if any(i < 0 or i >= num_qubits for i in measured_qubits):
            raise ValueError(f"Measured qubit index out of range: {measured_qubits}")
        if len(set(measured_qubits)) != len(measured_qubits):
            raise ValueError(f"Duplicate measured qubit indices are not allowed: {measured_qubits}")

        # Collect each distinct shared tableau block touched by the requested keys.
        unique_states: list[TableauState] = []
        seen_state_ids: set[int] = set()
        for key in keys:
            qstate = self.states[key]
            if not isinstance(qstate, TableauState):
                raise ValueError(f"Expected TableauState for key {key}, got {type(qstate)}")
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
                block_tableau = qstate.current_tableau()
                merged_tableau = block_tableau if merged_tableau is None else merged_tableau + block_tableau

            if len(set(merged_keys)) != len(merged_keys):
                raise ValueError(f"Merged state contains duplicate keys: {merged_keys}")
            state_obj = self._initialize_tableau_state(merged_tableau, merged_keys)
            for key in merged_keys:
                self.states[key] = state_obj

        # Map manager keys to local qubit indices in the shared tableau block.
        key_to_local = {key: i for i, key in enumerate(state_obj.keys)}
        return meas_samp, state_obj, key_to_local

    def _drop_keys_from_tableau_simulator(self, simulator: TableauSimulator, state_keys: list[int], drop_keys: list[int]) -> tuple[TableauSimulator, list[int]]:
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
