"""CreateTopo — programmatic topology construction without JSON config files.

Instead of writing a config file and passing its path, users pass Python
dicts directly. This is the recommended entry point for interactive use,
notebooks, and rapid prototyping.
"""

from .topology import Topology, NetworkImpl
from .const_topo import (
    ALL_C_CHANNEL, ALL_C_CONNECT, ALL_NODE, ALL_Q_CHANNEL,
    ALL_Q_CONNECT, ALL_TEMPLATES, STOP_TIME, TRUNC, FORMALISM,
)


class CreateTopo(Topology):
    """Topology built from Python dicts — no config file required.

    Accepts the same data that would go in a JSON config, but as keyword
    arguments. Ideal for notebooks, quick experiments, and programmatic
    network generation.

    Args:
        impl (NetworkImpl):      the implementor for this topology family
        nodes (list[dict]):      node descriptors (name, type, seed, ...)
        templates (dict):        hardware templates keyed by template name
        qconnections (list):     quantum connection descriptors
        cconnections (list):     classical connection descriptors
        qchannels (list):        explicit quantum channel descriptors (optional)
        cchannels (list):        explicit classical channel descriptors (optional)
        stop_time (float):       simulation stop time
        formalism (str):         quantum state formalism (default: ket state)
        truncation (int):        Hilbert space truncation for Fock formalism
        **extra:                 any additional top-level config keys
                                 (e.g. QLAN structural params like local_memories)
    """

    def __init__(
        self,
        impl: NetworkImpl,
        nodes: list[dict],
        templates: dict | None = None,
        qconnections: list[dict] | None = None,
        cconnections: list[dict] | None = None,
        qchannels: list[dict] | None = None,
        cchannels: list[dict] | None = None,
        stop_time: float = float('inf'),
        formalism: str | None = None,
        truncation: int = 1,
        **extra,
    ):
        config = {
            ALL_NODE:      nodes,
            ALL_TEMPLATES: templates    or {},
            ALL_Q_CONNECT: qconnections or [],
            ALL_C_CONNECT: cconnections or [],
            ALL_Q_CHANNEL: qchannels    or [],
            ALL_C_CHANNEL: cchannels    or [],
            STOP_TIME:     stop_time,
            TRUNC:         truncation,
            **extra,
        }
        if formalism is not None:
            config[FORMALISM] = formalism

        self._raw_cfg = config
        self._setup(config, impl)
