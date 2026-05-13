"""
Parse and validate a simulation configuration file.
"""
import os
from importlib.util import find_spec
from pathlib import Path
from typing import Any, Literal

import typer
import yaml
import json
from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..constants import (KET_VECTOR_FORMALISM, DENSITY_MATRIX_FORMALISM, FOCK_DENSITY_MATRIX_FORMALISM,
                         BELL_DIAGONAL_STATE_FORMALISM, BARRET_KOK, SINGLE_HERALDED, BBPSSW, NM_DISTRIBUTED,
                         ROUTING_STATIC, ROUTING_DISTRIBUTED, REQUEST_APP, TELEPORT_APP)

app = typer.Typer()


class Module(BaseModel):
    model_config = ConfigDict(extra='forbid')
    name: str
    kwargs: dict[str, Any] = {}


class Logging(BaseModel):
    model_config = ConfigDict(extra='forbid')
    enabled: bool
    level: Literal['INFO', 'DEBUG', 'WARNING', 'ERROR', 'CRITICAL'] = 'INFO'
    modules: list[str] = []

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
    custom_modules: list[Module] = []


class Repetitions(BaseModel):
    model_config = ConfigDict(extra='forbid')
    reps: int
    seed: Literal['random'] | list[int] = 'random'

    @model_validator(mode='after')
    def check_seed_length(self):
        if isinstance(self.seed, list) and len(self.seed) != self.reps:
            raise ValueError(f'Seed list length ({len(self.seed)}) must match the number of repetitions {self.reps}')
        return self


class StochasticPattern(BaseModel):
    model_config = ConfigDict(extra='forbid')
    type: Literal['stochastic']
    maximum_duration: int
    pairs: int
    distribution: Literal['poisson', 'bernoulli']
    rate: float


class ManualPattern(BaseModel):
    model_config = ConfigDict(extra='forbid')
    type: Literal['manual']
    maximum_duration: int
    pairs: int
    connections: list[tuple[str, str, float]]


TrafficPattern = StochasticPattern | ManualPattern


class Experiment(BaseModel):
    model_config = ConfigDict(extra='forbid')
    cores: int = Field(default_factory=lambda: os.cpu_count() or 1)
    repetitions: Repetitions
    topologies: list[str]
    traffic_pattern: TrafficPattern | None = Field(default=None, discriminator='type')


class Simulation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    imports: list[str] = []
    configuration: Configuration
    experiment: Experiment

    @model_validator(mode='after')
    def check_imports_exist(self):
        for name in self.imports:
            if find_spec(name) is None:
                raise ValueError(
                    f"Import '{name}' is not findable on sys.path"
                )
        return self

    @model_validator(mode='after')
    def check_module_names(self):
        user_imports = set(self.imports)
        slots = [
            ('formalism', self.configuration.formalism.name, {KET_VECTOR_FORMALISM, DENSITY_MATRIX_FORMALISM,
                                                              FOCK_DENSITY_MATRIX_FORMALISM,
                                                              BELL_DIAGONAL_STATE_FORMALISM}),
            ('generation_protocol', self.configuration.generation_protocol.name, {BARRET_KOK, SINGLE_HERALDED}),
            ('purification_protocol', self.configuration.purification_protocol.name, {BBPSSW}),
            ('network_manager', self.configuration.network_manager.name, {NM_DISTRIBUTED}),
            ('routing_protocol', self.configuration.routing_protocol.name, {ROUTING_STATIC, ROUTING_DISTRIBUTED}),
            ('application', self.configuration.application.name, {REQUEST_APP, TELEPORT_APP}),
        ]

        for field, name, builtins in slots:
            if name not in builtins and name not in user_imports:
                raise ValueError(
                    f'{field} references {name} that is not a SeQUeNCe builtin and is not in config imports')
        for module in self.configuration.custom_modules:
            if module.name not in user_imports:
                raise ValueError(f'Custom module entry is not in config imports: {module.name}')
        return self


def load_config(path: str | Path) -> Simulation:
    path = Path(path)
    suffix = path.suffix.lower()
    loaders = {'.yml': yaml.safe_load, '.yaml': yaml.safe_load, '.json': json.load}
    loader = loaders.get(suffix)
    if loaders is None:
        raise ValueError(f'Unsupported config extension: {suffix}')
    with open(path, 'r') as f:
        raw = loader(f)
    if raw is None:
        raise ValueError(f'Config file is empty: {path}')

    return Simulation(**raw)


@app.command()
def validate(path: str):
    schema = load_config(path)
    typer.echo(schema.model_dump_json(indent=2))


if __name__ == '__main__':
    app()
