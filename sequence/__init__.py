from pathlib import Path

__all__ = ['app', 'components', 'entanglement_management', 'kernel', 'network_management', 'qkd', 'resource_management',
           'topology', 'utils', 'message', 'protocol', 'gui', 'qlan', 'read_version_from_pyproject']


def read_version_from_pyproject() -> str:
    pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
    if not pyproject.exists():
        return "unknown"
    try:
        import tomllib
    except Exception:
        return "unknown"

    try:
        with pyproject.open("rb") as f:
            return tomllib.load(f)["project"]["version"]
    except Exception:
        return "unknown"


__version__ = read_version_from_pyproject()


def __dir__():
    return sorted(__all__)
