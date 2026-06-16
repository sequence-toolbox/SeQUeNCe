"""Entanglement generation experiment using the built-in metrics module.

Runs SingleHeralded entanglement generation on a two-node linear topology and
produces plots of success rate versus initial fidelity and success rate over time.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from sequence.app.request_app import RequestApp
from sequence.constants import BELL_DIAGONAL_STATE_FORMALISM, SINGLE_HERALDED
from sequence.entanglement_management.generation import (
    EntanglementGenerationA,
    EntanglementGenerationB,
)
from sequence.kernel.quantum_manager import QuantumManager as qm
from sequence.topology.router_net_topo import RouterNetTopo
from sequence.utils import metrics

EXPERIMENT_DIR = Path(__file__).resolve().parent
CONFIG_FILE = EXPERIMENT_DIR / "two_node.json"


def modify_config(config_file: Path, fidelity: float) -> None:
    """Set initial memory fidelity in the topology template."""
    with config_file.open("r", encoding="utf-8") as file:
        config = json.load(file)

    config["templates"]["perfect_router"]["MemoryArray"]["fidelity"] = fidelity

    with config_file.open("w", encoding="utf-8") as file:
        json.dump(config, file, indent=2)


def collect_trial_metrics(app_start: RequestApp) -> dict:
    """Collect per-trial metrics from the metrics module for the app node."""
    node = app_start.node.name
    return {
        "eg_failures": metrics.get_failures(node),
        "eg_success": metrics.get_successes(node),
        "eg_success_rate": metrics.get_success_rate(node),
        "app_throughput": app_start.get_throughput(),
        "event_records": metrics.storage.get_by_owner(node),
    }


def aggregate_trial_metrics(trial_metrics: list[dict]) -> dict:
    """Aggregate scalar metrics across trials (mirrors eg_symmetric_experiment.py)."""
    scalar_metrics = [key for key in trial_metrics[0] if key != "event_records"]

    aggregated = {}
    for metric in scalar_metrics:
        values = [trial[metric] for trial in trial_metrics]
        aggregated[f"avg_{metric}"] = np.mean(values)
        if len(values) > 0:
            aggregated[f"std_{metric}"] = np.std(values)

    return aggregated


def run_trial(
    config_file: Path,
    prep_time: int,
    collect_time: int,
    qc_freq: float,
    app_node_name: str,
    other_node_name: str,
    num_memories: int,
    fidelity: float,
    trial: int,
) -> dict:
    """Run a single trial and return metrics collected from the metrics module."""
    EntanglementGenerationA.set_global_type(SINGLE_HERALDED)
    EntanglementGenerationB.set_global_type(SINGLE_HERALDED)

    metrics.configure(storage_type="in_memory")
    metrics.enable([metrics.EG_FAILURE, metrics.EG_SUCCESS])

    net_topo = RouterNetTopo(str(config_file))
    qm.set_global_manager_formalism(BELL_DIAGONAL_STATE_FORMALISM)

    tl = net_topo.get_timeline()
    tl.stop_time = prep_time + collect_time

    routers = net_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER)
    bsm_nodes = net_topo.get_nodes_by_type(RouterNetTopo.BSM_NODE)

    base_seed = int(time.time_ns()) % (2**20) + os.getpid()
    for j, node in enumerate(routers + bsm_nodes):
        node.set_seed(base_seed + trial * 1000 + j)

    for qc in net_topo.get_qchannels():
        qc.frequency = qc_freq

    start_node = None
    end_node = None
    for node in routers:
        if node.name == app_node_name:
            start_node = node
        elif node.name == other_node_name:
            end_node = node
    if not start_node or not end_node:
        raise ValueError("Could not find required nodes")

    app_start = RequestApp(start_node)
    RequestApp(end_node)

    tl.init()
    app_start.start(
        other_node_name,
        prep_time,
        prep_time + collect_time,
        num_memories,
        float(fidelity),
    )
    tl.run()

    return collect_trial_metrics(app_start)


def plot_success_rate_vs_fidelity(results: list[dict], output_path: Path) -> None:
    fidelities = [result["initial_fidelity"] for result in results]
    success_rates = [result["avg_eg_success_rate"] for result in results]
    errors = [result["std_eg_success_rate"] for result in results]

    plt.figure(figsize=(8, 6))
    plt.errorbar(fidelities, success_rates, yerr=errors, marker="o", capsize=3)
    plt.xlabel("Initial fidelity")
    plt.ylabel("Entanglement generation success rate")
    plt.title("EG success rate vs initial memory fidelity")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def plot_success_rate_vs_time(event_records: list[dict], output_path: Path) -> None:
    completion_events = [
        record
        for record in event_records
        if record["event_type"] in (metrics.EG_FAILURE, metrics.EG_SUCCESS)
    ]
    completion_events.sort(key=lambda record: record["sim_time"])
    times = [record["sim_time"] * 1e-12 for record in completion_events]
    rates = [record["success_rate"] for record in completion_events]

    plt.figure(figsize=(8, 6))
    plt.plot(times, rates, marker=".", linestyle="-", markersize=4)
    plt.xlabel("Simulation time (s)")
    plt.ylabel("Running EG success rate")
    plt.title("EG success rate vs simulation time")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def main() -> None:
    num_trials = 3
    prep_time = int(1e12)
    collect_time = int(50e12)
    qc_freq = 1e11
    app_node_name = "left"
    other_node_name = "right"
    num_memories = 2
    initial_fidelities = np.round(np.arange(0.6, 1.0, 0.05), 3)
    time_series_fidelity = 0.9

    results = []
    time_series_records: list[dict] = []

    for fidelity in initial_fidelities:
        print(f"Running {num_trials} trial(s) for initial fidelity={fidelity}")
        modify_config(CONFIG_FILE, float(fidelity))

        trial_metrics = [
            run_trial(
                CONFIG_FILE,
                prep_time,
                collect_time,
                qc_freq,
                app_node_name,
                other_node_name,
                num_memories,
                float(fidelity),
                trial,
            )
            for trial in range(num_trials)
        ]

        aggregated_metrics = aggregate_trial_metrics(trial_metrics)

        if fidelity == time_series_fidelity:
            time_series_records = trial_metrics[0]["event_records"]

        result = {
            "initial_fidelity": float(fidelity),
            "num_trials": num_trials,
            **aggregated_metrics,
        }
        results.append(result)

        print(
            f"  avg success rate: {result['avg_eg_success_rate']:.3f} "
            f"(std: {result['std_eg_success_rate']:.3f})"
        )

    df = pd.DataFrame(results)
    df.to_csv(EXPERIMENT_DIR / "output_eg_exp.csv", index=False)

    plot_success_rate_vs_fidelity(
        results, EXPERIMENT_DIR / "success_rate_vs_fidelity.png"
    )
    plot_success_rate_vs_time(
        time_series_records, EXPERIMENT_DIR / "success_rate_vs_time.png"
    )
    print(f"Wrote results to {EXPERIMENT_DIR}")


if __name__ == "__main__":
    main()
