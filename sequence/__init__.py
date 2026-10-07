"""SeQUeNCe Quantum Network Simulator. Documentation is provided at https://sequence-rtd-tutorial.readthedocs.io/stable/index.html

Example usage:
    ```
    import sequence as sq
    timeline = sq.Timeline()
    memory = sq.Memory(...)
    ```
"""

from pathlib import Path

import lazy_loader as lazy

__getattr__, __dir__, __all__ = lazy.attach_stub(__name__, __file__)


def read_version_from_pyproject() -> str:
    """Read the project version from a source checkout."""
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    if not pyproject.exists():
        return "unknown"

    try:
        import tomllib

        with pyproject.open("rb") as file:
            return tomllib.load(file)["project"]["version"]
    except (ImportError, KeyError, OSError, TypeError):
        return "unknown"


__version__ = read_version_from_pyproject()
