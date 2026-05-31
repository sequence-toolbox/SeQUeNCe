"""Observe-only helpers for derived memory stress metrics.

This module intentionally stays small and read-only. It derives bounded
observation values from existing ``Memory`` state without changing protocol
behavior or introducing a broader metrics framework.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..components.memory import Memory


PICOSECONDS_PER_SECOND = 1e12


@dataclass(frozen=True)
class MemoryObservation:
    """Derived, bounded observation for a single memory.

    Attributes:
        age_component: normalized age relative to the configured coherence time.
        bds_dispersion_component: concentration loss for Bell-diagonal state if available.
        cutoff_component: normalized progress toward configured cutoff time if enabled.
        score: aggregate observe-only stress value in ``[0, 1]``.
        has_bell_diagonal_state: whether a Bell-diagonal state was available.
    """

    age_component: float
    bds_dispersion_component: float
    cutoff_component: float
    score: float
    has_bell_diagonal_state: bool


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _coherence_window_ps(memory: "Memory") -> float | None:
    if memory.coherence_time <= 0:
        return None
    return memory.coherence_time * PICOSECONDS_PER_SECOND


def _memory_age_ps(memory: "Memory", now: int | None) -> int:
    observed_now = memory.timeline.now() if now is None else now
    reference_time = memory.last_update_time
    if reference_time < 0:
        reference_time = memory.generation_time
    if reference_time < 0:
        return 0
    return max(0, observed_now - reference_time)


def _bds_dispersion_component(memory: "Memory") -> tuple[float, bool]:
    try:
        state_obj = memory.timeline.quantum_manager.get(memory.qstate_key)
    except Exception:
        return 0.0, False

    state = getattr(state_obj, "state", None)
    if state is None or len(state) != 4:
        return 0.0, False

    max_entry = max(float(entry) for entry in state)
    return _clamp(1.0 - max_entry), True


def compute_memory_stress(memory: "Memory", now: int | None = None) -> MemoryObservation:
    """Compute a bounded observe-only stress metric for a memory.

    The metric uses only local memory state and returns a derived observation
    suitable for tests, reports, and future advisory layers.
    """

    coherence_window_ps = _coherence_window_ps(memory)
    age_ps = _memory_age_ps(memory, now)

    if coherence_window_ps is None:
        age_component = 0.0
        cutoff_component = 0.0
    else:
        age_component = _clamp(age_ps / coherence_window_ps)
        if memory.cutoff_flag:
            cutoff_window_ps = coherence_window_ps * memory.cutoff_ratio
            cutoff_component = _clamp(age_ps / cutoff_window_ps)
        else:
            cutoff_component = 0.0

    bds_dispersion_component, has_bell_diagonal_state = _bds_dispersion_component(memory)

    active_components = [age_component, cutoff_component]
    if has_bell_diagonal_state:
        active_components.append(bds_dispersion_component)

    score = _clamp(sum(active_components) / len(active_components))

    return MemoryObservation(
        age_component=age_component,
        bds_dispersion_component=bds_dispersion_component,
        cutoff_component=cutoff_component,
        score=score,
        has_bell_diagonal_state=has_bell_diagonal_state,
    )
