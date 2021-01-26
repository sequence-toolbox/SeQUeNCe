from typing import List, Any

from .event import Event
from .process import Process


class QuantumManagerEvent(Event):
    def __init__(self, dst: int, operation: str, args: List[Any]):
        super().__init__(-1, Process("quantum_manager", operation, args), -1)
        self.dst = dst
