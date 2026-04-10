import json

import typer
from typing import Annotated
from .graphs import (build_caveman, build_grid, build_star, build_linear, build_mesh, build_ring, build_waxman,
                     build_tree, build_autonomous_system, build_bcube, build_k_n)
from .nx_converter import generate_config

app = typer.Typer()


QcLength = Annotated[float, typer.Argument(help='Distance of the quantum channel (km)')]
QcAttenuation = Annotated[float, typer.Option(help='Attenuation of the link (dB/m)')]
CCDelay = Annotated[float, typer.Option(help='Constant delay of the classical channel (ms)')]
OutputFile = Annotated[str, typer.Option(help='Name of the output file')]
OutputDirectory = Annotated[str, typer.Option(help='Name of the output directory')]
StopTime = Annotated[float, typer.Option(help='Stop time of the simulation (s)')]
Formalism = Annotated[str, typer.Option(help='Formalism of the QuantumManager')]
Template = Annotated[str, typer.Option(help='Path of the template JSON file')]
GateFidelity = Annotated[float, typer.Option(help='Fidelity of the CNOT Gate')]
MeasurementFidelity = Annotated[float, typer.Option(help='Fidelity of the Measurement')]
Seed = Annotated[int|None, typer.Option(help='RNG seed for random graph generation')]

default_template = {
  "perfect_router": {
    "MemoryArray": {
      "frequency": 200000000.0,
      "coherence_time": 2,
      "efficiency": 1,
      "fidelity": 0.9
    }
  },
  "perfect_bsm": {
    "encoding_type": "single_heralded",
    "SingleHeraldedBSM": {
      "detectors": [
        {
          "efficiency": 1,
          "dark_count": 0,
          "time_resolution": 6,
          "count_rate": 100000000000.0
        },
        {
          "efficiency": 1,
          "dark_count": 0,
          "time_resolution": 6,
          "count_rate": 100000000000.0
        }
      ]
    }
  }
}


def get_template(template_path: str) -> dict:
    with open(template_path, 'r') as f:
        data = json.load(f)
    return data

@app.command()
def caveman(
    cliques: Annotated[int, typer.Argument(help="Number of cliques")],
    size: Annotated[int, typer.Argument(help="Size of cliques")],
    qc_length: QcLength,
    qc_attenuation: QcAttenuation = 0.0002,
    cc_delay: CCDelay = 1,
    output: OutputFile = 'output.json',
    directory: OutputDirectory = 'tmp',
    stop_time: StopTime = float("inf"),
    formalism: Formalism = 'bell_diagonal',
    template_path: Template = '',
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1
) -> None:
    template = get_template(template_path) if template_path else default_template
    g = build_caveman(cliques, size)
    generate_config(
        g,
        qc_length=qc_length,
        qc_attn=qc_attenuation,
        cc_delay=cc_delay,
        output_file=output,
        output_directory=directory,
        stop_time=stop_time,
        formalism=formalism,
        node_template=template,
        meas_fid=measurement_fidelity,
        gate_fid=gate_fidelity
    )

@app.command()
def grid(
    size_x: Annotated[int, typer.Argument(help="Number of nodes on the x-axis")],
    size_y: Annotated[int, typer.Argument(help="Number of nodes on the y-axis")],
    qc_length: QcLength,
    qc_attenuation: QcAttenuation = 0.0002,
    cc_delay: CCDelay = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = float("inf"),
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
) -> None:
    template = get_template(template_path) if template_path else default_template
    g = build_grid(size_x, size_y)
    generate_config(
        g,
        qc_length=qc_length,
        qc_attn=qc_attenuation,
        cc_delay=cc_delay,
        output_file=output,
        output_directory=directory,
        stop_time=stop_time,
        formalism=formalism,
        node_template=template,
        meas_fid=measurement_fidelity,
        gate_fid=gate_fidelity,
    )

@app.command()
def star(
    outer_nodes: Annotated[int, typer.Argument(help="Number of nodes connected to the center")],
    qc_length: QcLength,
    qc_attenuation: QcAttenuation = 0.0002,
    cc_delay: CCDelay = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = float("inf"),
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
) -> None:
    template = get_template(template_path) if template_path else default_template
    g = build_star(outer_nodes)
    generate_config(
        g,
        qc_length=qc_length,
        qc_attn=qc_attenuation,
        cc_delay=cc_delay,
        output_file=output,
        output_directory=directory,
        stop_time=stop_time,
        formalism=formalism,
        node_template=template,
        meas_fid=measurement_fidelity,
        gate_fid=gate_fidelity
    )


@app.command()
def linear(
    nodes: Annotated[int, typer.Argument(help="Number of nodes in the chain")],
    qc_length: QcLength,
    qc_attenuation: QcAttenuation = 0.0002,
    cc_delay: CCDelay = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = float("inf"),
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
) -> None:
    template = get_template(template_path) if template_path else default_template
    g = build_linear(nodes)
    generate_config(
        g,
        qc_length=qc_length,
        qc_attn=qc_attenuation,
        cc_delay=cc_delay,
        output_file=output,
        output_directory=directory,
        stop_time=stop_time,
        formalism=formalism,
        node_template=template,
        meas_fid=measurement_fidelity,
        gate_fid=gate_fidelity,
    )


@app.command()
def mesh(
    size_x: Annotated[int, typer.Argument(help="Number of nodes on the x-axis")],
    size_y: Annotated[int, typer.Argument(help="Number of nodes on the y-axis")],
    qc_length: QcLength,
    qc_attenuation: QcAttenuation = 0.0002,
    cc_delay: CCDelay = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = float("inf"),
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
) -> None:
    template = get_template(template_path) if template_path else default_template
    g = build_mesh(size_x, size_y)
    generate_config(
        g,
        qc_length=qc_length,
        qc_attn=qc_attenuation,
        cc_delay=cc_delay,
        output_file=output,
        output_directory=directory,
        stop_time=stop_time,
        formalism=formalism,
        node_template=template,
        meas_fid=measurement_fidelity,
        gate_fid=gate_fidelity,
    )


@app.command()
def ring(
    nodes: Annotated[int, typer.Argument(help="Number of nodes in the ring")],
    qc_length: QcLength,
    qc_attenuation: QcAttenuation = 0.0002,
    cc_delay: CCDelay = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = float("inf"),
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
) -> None:
    template = get_template(template_path) if template_path else default_template
    g = build_ring(nodes)
    generate_config(
        g,
        qc_length=qc_length,
        qc_attn=qc_attenuation,
        cc_delay=cc_delay,
        output_file=output,
        output_directory=directory,
        stop_time=stop_time,
        formalism=formalism,
        node_template=template,
        meas_fid=measurement_fidelity,
        gate_fid=gate_fidelity,
    )


@app.command()
def waxman(
    nodes: Annotated[int, typer.Argument(help="Number of nodes in the Waxman graph")],
    qc_length: QcLength,
    qc_attenuation: QcAttenuation = 0.0002,
    cc_delay: CCDelay = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = float("inf"),
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
    seed: Seed = None,
) -> None:
    template = get_template(template_path) if template_path else default_template
    g = build_waxman(nodes, seed=seed)
    generate_config(
        g,
        qc_length=qc_length,
        qc_attn=qc_attenuation,
        cc_delay=cc_delay,
        output_file=output,
        output_directory=directory,
        stop_time=stop_time,
        formalism=formalism,
        node_template=template,
        meas_fid=measurement_fidelity,
        gate_fid=gate_fidelity,
    )


@app.command()
def tree(
    branching_factor: Annotated[
        int, typer.Argument(help="Branching factor of the tree")
    ],
    nodes: Annotated[int, typer.Argument(help="Number of nodes in the tree")],
    qc_length: QcLength,
    qc_attenuation: QcAttenuation = 0.0002,
    cc_delay: CCDelay = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = float("inf"),
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
) -> None:
    template = get_template(template_path) if template_path else default_template
    g = build_tree(branching_factor, nodes)
    generate_config(
        g,
        qc_length=qc_length,
        qc_attn=qc_attenuation,
        cc_delay=cc_delay,
        output_file=output,
        output_directory=directory,
        stop_time=stop_time,
        formalism=formalism,
        node_template=template,
        meas_fid=measurement_fidelity,
        gate_fid=gate_fidelity,
    )


@app.command()
def autonomous_system(
    nodes: Annotated[int, typer.Argument(help="Number of nodes in the AS graph")],
    qc_length: QcLength,
    qc_attenuation: QcAttenuation = 0.0002,
    cc_delay: CCDelay = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = float("inf"),
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
    seed: Seed = None,
) -> None:
    template = get_template(template_path) if template_path else default_template
    g = build_autonomous_system(nodes, seed=seed)
    generate_config(
        g,
        qc_length=qc_length,
        qc_attn=qc_attenuation,
        cc_delay=cc_delay,
        output_file=output,
        output_directory=directory,
        stop_time=stop_time,
        formalism=formalism,
        node_template=template,
        meas_fid=measurement_fidelity,
        gate_fid=gate_fidelity,
    )


@app.command()
def bcube(
    k: Annotated[int, typer.Argument(help="Number of BCube levels (k >= 1)")],
    n: Annotated[int, typer.Argument(help="Number of ports per switch")],
    qc_length: QcLength,
    qc_attenuation: QcAttenuation = 0.0002,
    cc_delay: CCDelay = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = float("inf"),
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
) -> None:
    template = get_template(template_path) if template_path else default_template
    g = build_bcube(k, n)
    generate_config(
        g,
        qc_length=qc_length,
        qc_attn=qc_attenuation,
        cc_delay=cc_delay,
        output_file=output,
        output_directory=directory,
        stop_time=stop_time,
        formalism=formalism,
        node_template=template,
        meas_fid=measurement_fidelity,
        gate_fid=gate_fidelity,
    )


@app.command()
def k_n(
    k: Annotated[int, typer.Argument(help="Number of ports per switch")],
    n: Annotated[int, typer.Argument(help="Number of levels in the fat tree")],
    qc_length: QcLength,
    qc_attenuation: QcAttenuation = 0.0002,
    cc_delay: CCDelay = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = float("inf"),
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
) -> None:
    template = get_template(template_path) if template_path else default_template
    g = build_k_n(k, n)
    generate_config(
        g,
        qc_length=qc_length,
        qc_attn=qc_attenuation,
        cc_delay=cc_delay,
        output_file=output,
        output_directory=directory,
        stop_time=stop_time,
        formalism=formalism,
        node_template=template,
        meas_fid=measurement_fidelity,
        gate_fid=gate_fidelity,
    )