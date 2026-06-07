"""Run Ruff against staged Python files for pre-commit hooks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def staged_python_files() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        check=True,
        capture_output=True,
        text=True,
    )
    files = []
    for line in result.stdout.splitlines():
        path = Path(line)
        if path.suffix in {".py", ".pyi"} and path.exists():
            files.append(line)
    return files


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"check", "format"}:
        print("Usage: run_staged_ruff.py {check|format}", file=sys.stderr)
        return 2

    files = staged_python_files()
    if not files:
        print("No staged Python files to check.")
        return 0

    command = ["uv", "run", "ruff", sys.argv[1]]
    if sys.argv[1] == "check":
        command.append("--fix")
    command.extend(files)
    return subprocess.run(command).returncode


if __name__ == "__main__":
    raise SystemExit(main())
