"""
Takes a sequence .yaml file as input and validates it against the schema.
"""
from typing import Any, Literal
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator
import os
from pathlib import Path
import typer

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
    resource_manager: Module
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


def load_config(path: str | Path) -> Simulation:
    with open(path, 'r') as f:
        raw = yaml.safe_load(f)
    if raw is None:
        raise ValueError(f'Config file is empty: {path}')

    return Simulation(**raw)

@app.command()
def validate(path: str):
    schema = load_config(path)
    typer.echo(schema)


if __name__ == '__main__':
    app()
