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

CCDelay = Annotated[
    float, typer.Option(help="Constant delay of the classical channel (ms)")
]
MemorySize = Annotated[int, typer.Option(help="Number of quantum memories per node")]
OutputFile = Annotated[str, typer.Option(help="Name of the output file")]
OutputDirectory = Annotated[str, typer.Option(help="Name of the output directory")]
StopTime = Annotated[float, typer.Option(help="Stop time of the simulation (s)")]
Formalism = Annotated[str, typer.Option(help="Formalism of the QuantumManager")]
Template = Annotated[str, typer.Option(help="Path of the template JSON file")]
GateFidelity = Annotated[float, typer.Option(help="Fidelity of the CNOT Gate")]
MeasurementFidelity = Annotated[float, typer.Option(help="Fidelity of the Measurement")]
Seed = Annotated[int | None, typer.Option(help="RNG seed for random graph generation")]
GMLPath = Annotated[str, typer.Argument(help="Path of the .gml file.")]


def get_template(template_path: str) -> dict:
    with open(template_path, "r") as f:
        data = json.load(f)
    return data


@app.command()
def caveman(
    cliques: Annotated[int, typer.Argument(help="Number of cliques")],
    size: Annotated[int, typer.Argument(help="Size of cliques")],
    cc_delay: CCDelay = 1,
    memory_size: MemorySize = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = float("inf"),
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
) -> None:
    template = get_template(template_path) if template_path else None
    g = build_caveman(cliques, size)
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
    cc_delay: CCDelay = 1,
    memory_size: MemorySize = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = float("inf"),
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
) -> None:
    template = get_template(template_path) if template_path else None
    g = build_grid(size_x, size_y)
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
    cc_delay: CCDelay = 1,
    memory_size: MemorySize = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = float("inf"),
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
) -> None:
    template = get_template(template_path) if template_path else None
    g = build_star(outer_nodes)
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
    cc_delay: CCDelay = 1,
    memory_size: MemorySize = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = float("inf"),
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
) -> None:
    template = get_template(template_path) if template_path else None
    g = build_linear(nodes)
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
    cc_delay: CCDelay = 1,
    memory_size: MemorySize = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = float("inf"),
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
) -> None:
    template = get_template(template_path) if template_path else None
    g = build_mesh(size_x, size_y)
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
    cc_delay: CCDelay = 1,
    memory_size: MemorySize = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = float("inf"),
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
) -> None:
    template = get_template(template_path) if template_path else None
    g = build_ring(nodes)
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
    cc_delay: CCDelay = 1,
    memory_size: MemorySize = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = float("inf"),
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
    seed: Seed = None,
) -> None:
    template = get_template(template_path) if template_path else None
    g = build_waxman(nodes, seed=seed)
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
    cc_delay: CCDelay = 1,
    memory_size: MemorySize = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = float("inf"),
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
) -> None:
    template = get_template(template_path) if template_path else None
    g = build_tree(branching_factor, nodes)
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
    cc_delay: CCDelay = 1,
    memory_size: MemorySize = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = float("inf"),
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
    seed: Seed = None,
) -> None:
    template = get_template(template_path) if template_path else None
    g = build_autonomous_system(nodes, seed=seed)
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
    cc_delay: CCDelay = 1,
    memory_size: MemorySize = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = float("inf"),
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
) -> None:
    template = get_template(template_path) if template_path else None
    g = build_bcube(k, n)
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
    cc_delay: CCDelay = 1,
    memory_size: MemorySize = 1,
    output: OutputFile = "output.json",
    directory: OutputDirectory = "tmp",
    stop_time: StopTime = float("inf"),
    formalism: Formalism = "bell_diagonal",
    template_path: Template = "",
    measurement_fidelity: MeasurementFidelity = 1,
    gate_fidelity: GateFidelity = 1,
) -> None:
    template = get_template(template_path) if template_path else None
    g = build_k_n(k, n)
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
    stop_time: StopTime = float("inf"),
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
