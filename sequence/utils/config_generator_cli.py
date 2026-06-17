"""
Command-line tool for generating network configurations using various graph topologies.

This module provides multiple commands to generate different types of graphs based on user inputs.
The generated configurations can then be used in simulation frameworks with specific parameters,
including quantum channel distance, link attenuation, classical channel delay, and measurement fidelity.

It is possible to create a topology using a custom graph by passing a GML file.

Classes:
    app: The main Typer application for CLI commands.

Commands:
    caveman: Generate a caveman graph topology.
    grid: Generate a grid graph topology.
    star: Generate a star graph topology.
    linear: Generate a linear graph topology.
    mesh: Generate a mesh graph topology.
    ring: Generate a ring graph topology.
    waxman: Generate a Waxman graph topology.
    tree: Generate a Full r-ary tree graph topology.
    autonomous-system: Generate an autonomous-system topology of size n
    bcube: Generate the BCube topology.
    k-n: Generate k-ary n-tree graph topology.

Example:
    generate-topology <topology> <parameters>; Generate <topology> with parameters <parameters>
    generate-topology --help; Display possible topologies.
    generate-topology <topology> --help; Display parameters for a topology type.
    generate-topology custom <gml_path.gml>; Create a custom topology from a GML file.
"""
import json
import yaml
from typing import Annotated

import networkx as nx
import typer

from .graphs import (
    build_autonomous_system,
    build_bcube,
    build_caveman,
    build_grid,
    build_k_n,
    build_linear,
    build_mesh,
    build_ring,
    build_star,
    build_tree,
    build_waxman,
)
from .nx_converter import generate_config

app = typer.Typer()

QCLength = Annotated[float, typer.Option(help='Length of the quantum channel (km)')]
QCAttenuation = Annotated[float, typer.Option(help='Attenuation of the quantum channel (dB/m)')]
CCDelay = Annotated[float, typer.Option(help="Constant delay of the classical channel (ms)")]
MemorySize = Annotated[int, typer.Option(help="Number of quantum memories per node")]
OutputFile = Annotated[str, typer.Option(help="Name of the output file")]
OutputDirectory = Annotated[str, typer.Option(help="Name of the output directory")]
StopTime = Annotated[float | None, typer.Option(help="Stop time of the simulation (s)")]
Formalism = Annotated[str, typer.Option(help="Formalism of the QuantumManager")]
Template = Annotated[str, typer.Option(help="Path of the template JSON or YAML file")]
GateFidelity = Annotated[float, typer.Option(help="Fidelity of the CNOT Gate")]
MeasurementFidelity = Annotated[float, typer.Option(help="Fidelity of the Measurement")]
Seed = Annotated[int | None, typer.Option(help="RNG seed for random graph generation")]
GMLPath = Annotated[str, typer.Argument(help="Path of the .gml file.")]


def get_template(template_path: str) -> dict:
    with open(template_path, "r") as f:
        if template_path.lower().endswith((".yaml", ".yml")):
            data = yaml.safe_load(f)
        elif template_path.lower().endswith(".json"):
            data = json.load(f)
        else:
            raise ValueError("Incompatible file type for template. Required: JSON or YAML")
    return data


@app.command()
def caveman(
    cliques: Annotated[int, typer.Argument(help="Number of cliques")],
    size: Annotated[int, typer.Argument(help="Size of cliques")],
    length: QCLength = 10,
    attenuation: QCAttenuation = 0.0002,
    cc_delay: CCDelay = 1,
    memory_size: MemorySize = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = None,
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
) -> None:
    template = get_template(template_path) if template_path else None
    g = build_caveman(cliques, size, length=length, attenuation=attenuation)
    generate_config(
        g,
        cc_delay=cc_delay,
        memory_size=memory_size,
        output_file=output,
        output_directory=directory,
        stop_time=stop_time,
        formalism=formalism,
        node_template=template,
        meas_fid=measurement_fidelity,
        gate_fid=gate_fidelity,
    )


@app.command()
def grid(
    size_x: Annotated[int, typer.Argument(help="Number of nodes on the x-axis")],
    size_y: Annotated[int, typer.Argument(help="Number of nodes on the y-axis")],
    length: QCLength = 10,
    attenuation: QCAttenuation = 0.0002,
    cc_delay: CCDelay = 1,
    memory_size: MemorySize = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = None,
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
) -> None:
    template = get_template(template_path) if template_path else None
    g = build_grid(size_x, size_y, length=length, attenuation=attenuation)
    generate_config(
        g,
        cc_delay=cc_delay,
        memory_size=memory_size,
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
    outer_nodes: Annotated[
        int, typer.Argument(help="Number of nodes connected to the center")
    ],
    length: QCLength = 10,
    attenuation: QCAttenuation = 0.0002,
    cc_delay: CCDelay = 1,
    memory_size: MemorySize = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = None,
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
) -> None:
    template = get_template(template_path) if template_path else None
    g = build_star(outer_nodes, length=length, attenuation=attenuation)
    generate_config(
        g,
        cc_delay=cc_delay,
        memory_size=memory_size,
        output_file=output,
        output_directory=directory,
        stop_time=stop_time,
        formalism=formalism,
        node_template=template,
        meas_fid=measurement_fidelity,
        gate_fid=gate_fidelity,
    )


@app.command()
def linear(
    nodes: Annotated[int, typer.Argument(help="Number of nodes in the chain")],
    length: QCLength = 10,
    attenuation: QCAttenuation = 0.0002,
    cc_delay: CCDelay = 1,
    memory_size: MemorySize = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = None,
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
) -> None:
    template = get_template(template_path) if template_path else None
    g = build_linear(nodes, length=length, attenuation=attenuation)
    generate_config(
        g,
        cc_delay=cc_delay,
        memory_size=memory_size,
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
    length: QCLength = 10,
    attenuation: QCAttenuation = 0.0002,
    cc_delay: CCDelay = 1,
    memory_size: MemorySize = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = None,
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
) -> None:
    template = get_template(template_path) if template_path else None
    g = build_mesh(size_x, size_y, length=length, attenuation=attenuation)
    generate_config(
        g,
        cc_delay=cc_delay,
        memory_size=memory_size,
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
    length: QCLength = 10,
    attenuation: QCAttenuation = 0.0002,
    cc_delay: CCDelay = 1,
    memory_size: MemorySize = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = None,
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
) -> None:
    template = get_template(template_path) if template_path else None
    g = build_ring(nodes, length=length, attenuation=attenuation)
    generate_config(
        g,
        cc_delay=cc_delay,
        memory_size=memory_size,
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
    attenuation: QCAttenuation = 0.0002,
    cc_delay: CCDelay = 1,
    memory_size: MemorySize = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = None,
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
    seed: Seed = None,
) -> None:
    template = get_template(template_path) if template_path else None
    g = build_waxman(nodes, seed=seed, attenuation=attenuation)
    generate_config(
        g,
        cc_delay=cc_delay,
        memory_size=memory_size,
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
    length: QCLength = 10,
    attenuation: QCAttenuation = 0.0002,
    cc_delay: CCDelay = 1,
    memory_size: MemorySize = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = None,
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
) -> None:
    template = get_template(template_path) if template_path else None
    g = build_tree(branching_factor, nodes, length=length, attenuation=attenuation)
    generate_config(
        g,
        cc_delay=cc_delay,
        memory_size=memory_size,
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
    length: QCLength = 10,
    attenuation: QCAttenuation = 0.0002,
    cc_delay: CCDelay = 1,
    memory_size: MemorySize = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = None,
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
    seed: Seed = None,
) -> None:
    template = get_template(template_path) if template_path else None
    g = build_autonomous_system(nodes, seed=seed, length=length, attenuation=attenuation)
    generate_config(
        g,
        cc_delay=cc_delay,
        memory_size=memory_size,
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
    length: QCLength = 10,
    attenuation: QCAttenuation = 0.0002,
    cc_delay: CCDelay = 1,
    memory_size: MemorySize = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = None,
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
) -> None:
    template = get_template(template_path) if template_path else None
    g = build_bcube(k, n, length=length, attenuation=attenuation)
    generate_config(
        g,
        cc_delay=cc_delay,
        memory_size=memory_size,
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
    length: QCLength = 10,
    attenuation: QCAttenuation = 0.0002,
    cc_delay: CCDelay = 1,
    memory_size: MemorySize = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = None,
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
) -> None:
    template = get_template(template_path) if template_path else None
    g = build_k_n(k, n, length=length, attenuation=attenuation)
    generate_config(
        g,
        cc_delay=cc_delay,
        memory_size=memory_size,
        output_file=output,
        output_directory=directory,
        stop_time=stop_time,
        formalism=formalism,
        node_template=template,
        meas_fid=measurement_fidelity,
        gate_fid=gate_fidelity,
    )


@app.command()
def custom(
    gml_path: GMLPath,
    cc_delay: CCDelay = 1,
    memory_size: MemorySize = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = None,
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
) -> None:
    template = get_template(template_path) if template_path else None
    g: nx.Graph = nx.read_gml(gml_path)
    generate_config(
        g,
        cc_delay=cc_delay,
        memory_size=memory_size,
        output_file=output,
        output_directory=directory,
        stop_time=stop_time,
        formalism=formalism,
        node_template=template,
        meas_fid=measurement_fidelity,
        gate_fid=gate_fidelity,
    )


if __name__ == "__main__":
    app()
