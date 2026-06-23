"""Background worker for asynchronous metrics recording."""

from __future__ import annotations

import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .event_types import EventType
from .metric_types import Metric
from .storage import InMemoryStorage


@dataclass(frozen=True)
class _RecordTask:
    event_type: EventType
    owner_name: str
    record_kwargs: dict[str, Any]
    sim_time: int


@dataclass(frozen=True)
class _FlushCommand:
    done: threading.Event


@dataclass(frozen=True)
class _ResetCommand:
    done: threading.Event
    reset_fn: Callable[[], None]


@dataclass(frozen=True)
class _ShutdownCommand:
    pass


class BackgroundRecorder:
    """Process metrics records on a dedicated background thread."""

    def __init__(self) -> None:
        self._queue: queue.Queue[Any] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._storage = InMemoryStorage()
        self._list_metrics: Callable[[], list[Metric]] = lambda: []

    def configure_handlers(
        self,
        storage: InMemoryStorage,
        list_metrics_fn: Callable[[], list[Metric]],
    ) -> None:
        """Bind storage and metric lookup used by the worker."""
        self._storage = storage
        self._list_metrics = list_metrics_fn

    def submit_record(
        self,
        event_type: EventType,
        owner_name: str,
        record_kwargs: dict[str, Any],
        sim_time: int,
    ) -> None:
        """Enqueue a record for background processing."""
        self._ensure_started()
        self._queue.put(
            _RecordTask(
                event_type=event_type,
                owner_name=owner_name,
                record_kwargs=record_kwargs,
                sim_time=sim_time,
            )
        )

    def flush(self) -> None:
        """Block until all queued records have been processed."""
        if self._thread is None or not self._thread.is_alive():
            return
        done = threading.Event()
        self._queue.put(_FlushCommand(done))
        done.wait()

    def reset(self, reset_fn: Callable[[], None]) -> None:
        """Enqueue a metric reset after pending records are processed."""
        if self._thread is None or not self._thread.is_alive():
            reset_fn()
            return
        done = threading.Event()
        self._queue.put(_ResetCommand(done, reset_fn))
        done.wait()

    def shutdown(self) -> None:
        """Stop the background worker and wait for it to exit."""
        with self._lock:
            thread = self._thread
            if thread is None or not thread.is_alive():
                self._thread = None
                return
            self._queue.put(_ShutdownCommand())
        thread.join()
        with self._lock:
            self._thread = None

    def _ensure_started(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._thread = threading.Thread(
                target=self._worker_loop,
                name="metrics-recorder",
                daemon=True,
            )
            self._thread.start()

    def _worker_loop(self) -> None:
        while True:
            task = self._queue.get()
            try:
                if isinstance(task, _ShutdownCommand):
                    return
                if isinstance(task, _FlushCommand):
                    task.done.set()
                elif isinstance(task, _ResetCommand):
                    task.reset_fn()
                    task.done.set()
                elif isinstance(task, _RecordTask):
                    self._process_record(task)
            finally:
                self._queue.task_done()

    def _process_record(self, task: _RecordTask) -> None:
        record_kwargs = dict(task.record_kwargs)
        for metric in self._list_metrics():
            if task.event_type in metric.event_types:
                metric.on_record(task.event_type, task.owner_name, record_kwargs)

        self._storage.append(
            {
                "event_type": task.event_type,
                "owner_name": task.owner_name,
                "sim_time": task.sim_time,
                **record_kwargs,
            }
        )
