"""Background worker for asynchronous metrics recording."""

from __future__ import annotations

import multiprocessing as mp
from collections.abc import Callable
from typing import Any

from .event_types import EventType, get_event_type
from .metric_types import Metric
from .registry import reset_metrics as reset_registry_metrics
from .storage import InMemoryStorage


def _metrics_worker_main(command_queue: mp.Queue, response_queue: mp.Queue) -> None:
    """Run metrics recording in a separate Python interpreter process."""
    from .event_types import register_event_type
    from .registry import list_metrics, reset_metrics
    from .storage import InMemoryStorage as WorkerStorage

    storage = WorkerStorage()

    def process_record(
        event_type_name: str,
        owner_name: str,
        record_kwargs: dict[str, Any],
        sim_time: int,
    ) -> None:
        event_type = register_event_type(event_type_name)
        kwargs = dict(record_kwargs)
        for metric in list_metrics():
            if event_type in metric.event_types:
                metric.on_record(event_type, owner_name, kwargs)
        storage.append(
            {
                "event_type": event_type_name,
                "owner_name": owner_name,
                "sim_time": sim_time,
                **kwargs,
            }
        )

    def make_snapshot() -> dict[str, Any]:
        return {
            "records": [dict(record) for record in storage.get_all()],
        }

    while True:
        command = command_queue.get()
        op = command[0]
        if op == "shutdown":
            return
        if op == "record":
            _, event_type_name, owner_name, kwargs, sim_time = command
            process_record(event_type_name, owner_name, kwargs, sim_time)
        elif op == "flush":
            response_queue.put(make_snapshot())
        elif op == "reset":
            storage.clear()
            reset_metrics()
            response_queue.put(make_snapshot())


class BackgroundRecorder:
    """Process metrics records on a dedicated background process."""

    def __init__(self) -> None:
        self._ctx = mp.get_context("spawn")
        self._command_queue: mp.Queue[Any] | None = None
        self._response_queue: mp.Queue[Any] | None = None
        self._process: mp.Process | None = None
        self._storage = InMemoryStorage()
        self._list_metrics: Callable[[], list[Metric]] = lambda: []

    def configure_handlers(
        self,
        storage: InMemoryStorage,
        list_metrics_fn: Callable[[], list[Metric]],
    ) -> None:
        """Bind main-process storage synced from the worker."""
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
        assert self._command_queue is not None
        self._command_queue.put(
            (
                "record",
                event_type.name,
                owner_name,
                record_kwargs,
                sim_time,
            )
        )

    def flush(self) -> None:
        """Block until all queued records have been processed and synced."""
        if self._process is None or not self._process.is_alive():
            return
        assert self._command_queue is not None
        self._command_queue.put(("flush",))
        assert self._response_queue is not None
        self._sync_from_snapshot(self._response_queue.get())

    def reset(self, reset_fn: Callable[[], None]) -> None:
        """Reset worker and main-process metric state after pending records."""
        if self._process is None or not self._process.is_alive():
            reset_fn()
            return
        assert self._command_queue is not None
        self._command_queue.put(("reset",))
        assert self._response_queue is not None
        self._sync_from_snapshot(self._response_queue.get())

    def shutdown(self) -> None:
        """Stop the background worker process and wait for it to exit."""
        process = self._process
        command_queue = self._command_queue
        if process is None or not process.is_alive():
            self._process = None
            self._command_queue = None
            self._response_queue = None
            return
        assert command_queue is not None
        command_queue.put(("shutdown",))
        process.join(timeout=5.0)
        if process.is_alive():
            process.terminate()
            process.join(timeout=1.0)
        self._process = None
        self._command_queue = None
        self._response_queue = None

    def _ensure_started(self) -> None:
        if self._process is not None and self._process.is_alive():
            return
        self._command_queue = self._ctx.Queue()
        self._response_queue = self._ctx.Queue()
        self._process = self._ctx.Process(
            target=_metrics_worker_main,
            args=(self._command_queue, self._response_queue),
            name="metrics-recorder",
            daemon=True,
        )
        self._process.start()

    def _sync_from_snapshot(self, snapshot: dict[str, Any]) -> None:
        self._storage.clear()
        reset_registry_metrics()
        for raw in snapshot.get("records", []):
            event_type = get_event_type(raw["event_type"])
            owner_name = raw["owner_name"]
            sim_time = raw["sim_time"]
            record_kwargs = {
                key: value
                for key, value in raw.items()
                if key not in ("event_type", "owner_name", "sim_time")
            }
            kwargs = dict(record_kwargs)
            for metric in self._list_metrics():
                if event_type in metric.event_types:
                    metric.on_record(event_type, owner_name, kwargs)
            self._storage.append(
                {
                    "event_type": event_type,
                    "owner_name": owner_name,
                    "sim_time": sim_time,
                    **kwargs,
                }
            )
