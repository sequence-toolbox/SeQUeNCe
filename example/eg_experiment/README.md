# Entanglement Generation Metrics Experiment

This quick experiment demonstrates the built-in `metrics` module by running 
a SingleHeralded entanglement generation experiment on a two-node linear 
topology and plotting:

- **Success rate vs initial fidelity** (`success_rate_vs_fidelity.png`)
- **Running success rate vs simulation time** (`success_rate_vs_time.png`)

## Generate Topology

Generate the network config:

A `two_node.json` configuration is already provided in the directory, but
this command is what is used to generate it.

```bash
generate-topology linear 2 \
  --memory-size 64 \
  --formalism bell_diagonal \
  --output two_node.json \
  --directory example/eg_experiment
```

## Run Experiment

```bash
uv run python example/eg_experiment/eg_experiment.py
```

Results are written to this directory:

- `output_eg_exp.csv` — aggregated trial metrics per initial fidelity
- `success_rate_vs_fidelity.png`
- `success_rate_vs_time.png`

The experiment structure follows
[eg_symmetric_experiment.py](https://github.com/sequence-toolbox/entanglement_purification_experiment/blob/6c49f649bdacfeebefcd85c91e9902151d775368/eg_symmetric_experiment.py),
but uses `sequence.utils.metrics` instead of monkey-patching `QuantumRouter`.
