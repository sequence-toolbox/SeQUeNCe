"""
Parse and validate a simulation configuration file.
"""
import json
import os
from collections import Counter
from importlib.util import find_spec
from pathlib import Path
from typing import Annotated, Any, Literal
from ..utils.graphs import TOPOLOGY_BUILDERS
import typer
import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeInt,
    PositiveFloat,
    PositiveInt,
    field_validator,
    model_validator,
)

from ..constants import (
    BARRETT_KOK,
    BBPSSW,
    BELL_DIAGONAL_STATE_FORMALISM,
    DENSITY_MATRIX_FORMALISM,
    FOCK_DENSITY_MATRIX_FORMALISM,
    KET_VECTOR_FORMALISM,
    NM_DISTRIBUTED,
    REQUEST_APP,
    ROUTING_DISTRIBUTED,
    ROUTING_STATIC,
    SINGLE_HERALDED,
    TELEPORT_APP,
)

BUILTIN_NAMES: set[str] = {KET_VECTOR_FORMALISM, DENSITY_MATRIX_FORMALISM, FOCK_DENSITY_MATRIX_FORMALISM,
                         BELL_DIAGONAL_STATE_FORMALISM, BARRETT_KOK, SINGLE_HERALDED, BBPSSW, NM_DISTRIBUTED,
                         ROUTING_STATIC, ROUTING_DISTRIBUTED, REQUEST_APP, TELEPORT_APP}

app = typer.Typer()

def check_unique(items: list, label: str) -> None:
    duplicates = [item for item, count in Counter(items).items() if count > 1]
    if duplicates:
        raise ValueError(f'Found duplicate {label}: {duplicates}')

class Module(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str = Field(description='Registered module name or user-supplied import name')
    kwargs: dict[str, Any] = Field(default_factory=dict, description='Module-specific configuration')


class Logging(BaseModel):
    model_config = ConfigDict(extra='forbid')
    enabled: bool
    level: Literal['INFO', 'DEBUG', 'WARNING', 'ERROR', 'CRITICAL'] = 'INFO'
    modules: list[str] = Field(default_factory=list, description='Modules to be logged')

    @model_validator(mode='after')
    def check_modules_when_enabled(self):
        if self.enabled and not self.modules:
            raise ValueError('Modules must be specified when logging is enabled')
        return self


class Configuration(BaseModel):
    model_config = ConfigDict(extra='forbid')
    formalism: Module
    generation_protocol: Module
    purification_protocol: Module
    network_manager: Module
    routing_protocol: Module
    application: Module
    stop_time: float = Field(gt=0)
    logging: Logging | None = Field(default=None)
    custom_modules: list[Module] = Field(default_factory=list, description='Custom modules to be used. Must appear in imports.')

    @field_validator('custom_modules', mode='after')
    @classmethod
    def is_custom_modules_unique(cls, v: list[Module]) -> list[Module]:
        check_unique([m.name for m in v], 'custom_modules names')
        return v


class Repetitions(BaseModel):
    model_config = ConfigDict(extra='forbid')
    reps: PositiveInt
    seed: Literal['random'] | list[NonNegativeInt] = 'random'

    @model_validator(mode='after')
    def check_seed_length(self):
        if isinstance(self.seed, list) and len(self.seed) != self.reps:
            raise ValueError(f'Seed list length ({len(self.seed)}) must match the number of repetitions {self.reps}')
        return self


class StochasticPattern(BaseModel):
    model_config = ConfigDict(extra='forbid')
    type: Literal['stochastic']
    maximum_duration: PositiveInt
    pairs: PositiveInt
    distribution: Literal['poisson', 'bernoulli']
    rate: PositiveFloat # Poisson rate (lambda), Bernoulli prob (p)

    @model_validator(mode='after')
    def check_rate(self):
        if self.distribution == 'bernoulli' and self.rate > 1:
            raise ValueError('Bernoulli rate must be in (0,1]')
        return self

class ManualPattern(BaseModel):
    model_config = ConfigDict(extra='forbid')
    type: Literal['manual']
    maximum_duration: PositiveInt
    pairs: PositiveInt
    connections: list[tuple[str, str, PositiveFloat]] # src, dst, rate


class Experiment(BaseModel):
    model_config = ConfigDict(extra='forbid')
    cores: PositiveInt = Field(default_factory=lambda: os.cpu_count() or 1)
    repetitions: Repetitions
    topologies: list[str] = Field(min_length=1)
    traffic_pattern: Annotated[StochasticPattern | ManualPattern, Field(discriminator="type")]

    @field_validator('topologies', mode='after')
    @classmethod
    def is_topologies_unique(cls, v: list[str]) -> list[str]:
        check_unique(v, 'topologies')
        return v

class Simulation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    imports: list[str] = Field(default_factory=list)
    configuration: Configuration
    experiment: Experiment

    @field_validator('imports', mode='after')
    @classmethod
    def is_imports_unique(cls, v: list[str]) -> list[str]:
        check_unique(v, 'imports')
        return v

    @model_validator(mode='after')
    def check_imports_exist(self):
        for name in self.imports:
            try:
                spec = find_spec(name)
            except (ImportError, ValueError):
                spec = None
            if spec is None:
                raise ValueError(f'Import '{name}' is not findable on sys.path')
        return self

    @model_validator(mode='after')
    def check_module_names(self):
        user_imports = set(self.imports)
        slots = [
            ('formalism', self.configuration.formalism.name, {KET_VECTOR_FORMALISM, DENSITY_MATRIX_FORMALISM,
                                                              FOCK_DENSITY_MATRIX_FORMALISM,
                                                              BELL_DIAGONAL_STATE_FORMALISM}),
            ('generation_protocol', self.configuration.generation_protocol.name, {BARRETT_KOK, SINGLE_HERALDED}),
            ('purification_protocol', self.configuration.purification_protocol.name, {BBPSSW}),
            ('network_manager', self.configuration.network_manager.name, {NM_DISTRIBUTED}),
            ('routing_protocol', self.configuration.routing_protocol.name, {ROUTING_STATIC, ROUTING_DISTRIBUTED}),
            ('application', self.configuration.application.name, {REQUEST_APP, TELEPORT_APP}),
        ]

        all_builtins: set[str] = BUILTIN_NAMES | TOPOLOGY_BUILDERS.keys()
        shadowed: set[str] = user_imports & all_builtins
        if shadowed:
            raise ValueError(f'Imports shadow built-in modules: {sorted(shadowed)}')
        
        for field, name, builtins in slots:
            if name not in builtins and name not in user_imports:
                raise ValueError(
                    f'{field} references {name} that is not a SeQUeNCe builtin and is not in config imports.')
        for module in self.configuration.custom_modules:
            if module.name not in user_imports:
                raise ValueError(f'Custom module entry is not in config imports: {module.name!r}.')
        for topology in self.experiment.topologies:
            if topology not in user_imports and topology not in TOPOLOGY_BUILDERS:
                raise ValueError(f'Custom topology entry not in config imports and is not a SeQUeNCe built-in: {topology!r}')

        return self


def load_config(path: str | Path) -> Simulation:
    """
    Takes the config file (.yml, .yaml, .json) as input and returns a validated Simulation() object.
    Args:
        path: str or pathlib.Path object of the configuration file.

    Returns: Validated Simulation object

    """
    path = Path(path)
    suffix = path.suffix.lower()
    loaders = {'.yml': yaml.safe_load, '.yaml': yaml.safe_load, '.json': json.load}
    loader = loaders.get(suffix)
    if loader is None:
        raise ValueError(f'Unsupported config extension: {suffix}')
    with open(path, 'r', encoding='utf-8') as f:
        raw = loader(f)
    if raw is None:
        raise ValueError(f'Config file is empty: {path}')

    return Simulation(**raw)


@app.command()
def check(path: str):
    """Check a SeQUeNCe experiment config file."""
    schema = load_config(path)
    typer.echo(schema.model_dump_json(indent=2))

if __name__ == '__main__':
    app()
