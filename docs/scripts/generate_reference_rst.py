#!/usr/bin/env python3
"""Generate Sphinx reference .rst stubs for SeQUeNCe modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class SectionSpec:
    output_dir: str
    source_dir: str
    title: str
    description: str
    static_entries: tuple[str, ...] = field(default_factory=tuple)


SECTIONS = (
    SectionSpec(
        output_dir="application",
        source_dir="app",
        title="Application",
        description="The Application module contains code to utilize and test quantum network resources.",
    ),
    SectionSpec(
        output_dir="components",
        source_dir="components",
        title="Components",
        description="The components module provides models for quantum hardware.",
    ),
    SectionSpec(
        output_dir="entanglement_management",
        source_dir="entanglement_management",
        title="Entanglement Management",
        description="The Entanglement Management module provides protocols for generating, purifying, and swapping quantum entanglement.",
    ),
    SectionSpec(
        output_dir="kernel",
        source_dir="kernel",
        title="Kernel",
        description="The Kernel module provides the discrete event simulator for SeQUeNCe.",
    ),
    SectionSpec(
        output_dir="misc",
        source_dir=".",
        title="Miscellaneous",
        description="Miscellaneous SeQUeNCe modules.",
        static_entries=("utils/top",),
    ),
    SectionSpec(
        output_dir="misc/utils",
        source_dir="utils",
        title="Utils",
        description="Utilities for SeQUeNCe.",
    ),
    SectionSpec(
        output_dir="network_management",
        source_dir="network_management",
        title="Network Management",
        description="The Network Management module allows nodes to interact easily with a broader quantum network.",
    ),
    SectionSpec(
        output_dir="qkd",
        source_dir="qkd",
        title="Quantum Key Distribution",
        description="Implementations of QKD protocols.",
    ),
    SectionSpec(
        output_dir="resource_management",
        source_dir="resource_management",
        title="Resource Management",
        description="The Resource Management module is responsible for managing the local resources (usually quantum memories) of a node.",
    ),
    SectionSpec(
        output_dir="topology",
        source_dir="topology",
        title="Topology",
        description="The Topology module provides definitions for network nodes and a tool to track network topologies.",
    ),
)

ROOT_MISC_MODULES = {"constants", "message", "protocol"}


def get_title(module_name: str) -> str:
    words = module_name.replace("_", " ")
    if any(char.isupper() for char in module_name):
        return words
    return words.title()


def discover_modules(source_dir: Path, relative_source_dir: str) -> list[str]:
    if relative_source_dir == ".":
        modules = [
            path.stem
            for path in source_dir.glob("*.py")
            if path.stem in ROOT_MISC_MODULES
        ]
        return sorted(modules, key=str.lower)

    target = source_dir / relative_source_dir
    modules = []

    for path in target.iterdir():
        if path.is_file() and path.suffix == ".py" and path.stem != "__init__":
            modules.append(path.stem)
        elif path.is_dir() and (path / "__init__.py").exists():
            modules.append(path.name)

    return sorted(modules, key=str.lower)


def write_module_rst(module_path: str, output_file: Path) -> None:
    module_name = module_path.split(".")[-1]
    title = get_title(module_name)
    content = (
        f"{title}\n"
        f"{'=' * len(title)}\n\n"
        f".. automodule:: {module_path}\n"
        f"    :members:\n"
    )
    output_file.write_text(content, encoding="utf-8")


def write_top_rst(spec: SectionSpec, top_file: Path, entries: list[str]) -> None:
    lines = [
        spec.title,
        "=" * len(spec.title),
        "",
        spec.description,
        "",
        ".. toctree::",
        "    :maxdepth: 2",
        "",
    ]
    lines.extend(f"    {entry}" for entry in entries)
    lines.append("")
    top_file.write_text("\n".join(lines), encoding="utf-8")


def prune_stale_files(output_dir: Path, expected_files: set[str]) -> None:
    for rst in output_dir.glob("*.rst"):
        if rst.name not in expected_files:
            rst.unlink()


def main() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    sequence_root = repo_root / "sequence"
    refs_root = repo_root / "docs" / "source" / "references"

    for spec in SECTIONS:
        output_dir = refs_root / spec.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        modules = discover_modules(sequence_root, spec.source_dir)
        entry_names = modules + list(spec.static_entries)

        for module in modules:
            module_path = "sequence" if spec.source_dir == "." else f"sequence.{spec.source_dir}"
            full_module_path = f"{module_path}.{module}"
            write_module_rst(full_module_path, output_dir / f"{module}.rst")

        write_top_rst(spec, output_dir / "top.rst", entry_names)

        expected = {"top.rst"} | {f"{module}.rst" for module in modules}
        prune_stale_files(output_dir, expected)

    print("Reference .rst files regenerated.")


if __name__ == "__main__":
    main()
