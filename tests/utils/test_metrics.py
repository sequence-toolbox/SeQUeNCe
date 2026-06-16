import pytest

from sequence.utils import metrics


@pytest.fixture(autouse=True)
def reset_metrics():
    metrics._enabled = False
    metrics._enabled_events.clear()
    metrics.storage.clear()
    metrics.reset_counters()
    metrics.register_time_provider(metrics._system_time_provider)


# Tests that record doesn't do anything if the user has not enabled metrics
def test_record_before_enable_is_noop():
    metrics.record(metrics.EG_SUCCESS, "e0", fidelity=0.9)
    assert metrics.storage.get_all() == []


def test_enable_filters_event_types():
    metrics.enable([metrics.EG_SUCCESS])

    metrics.record(metrics.EG_FAILURE, "e0", initial_fidelity=0.9)
    metrics.record(metrics.EG_SUCCESS, "e0", fidelity=0.9)

    records = metrics.storage.get_all()
    assert len(records) == 1
    assert records[0]["event_type"] is metrics.EG_SUCCESS
    assert records[0]["owner_name"] == "e0"
    assert records[0]["fidelity"] == 0.9


def test_record_stores_arbitrary_kwargs():
    metrics.enable([metrics.EG_FAILURE])

    metrics.record(metrics.EG_FAILURE, "e1", initial_fidelity=0.8, custom_metric=42)

    record = metrics.storage.get_all()[0]
    assert record["initial_fidelity"] == 0.8
    assert record["custom_metric"] == 42


def test_configure_replaces_storage():
    metrics.enable([metrics.EG_FAILURE, metrics.EG_SUCCESS])
    metrics.record(metrics.EG_FAILURE, "e0")
    metrics.record(metrics.EG_SUCCESS, "e0")
    assert len(metrics.storage.get_all()) == 2

    metrics.configure(storage_type="in_memory")

    assert metrics.storage.get_all() == []


def test_reset_counters_clears_per_node_counts():
    metrics.enable([metrics.EG_FAILURE, metrics.EG_SUCCESS])
    metrics.record(metrics.EG_FAILURE, "e0")
    metrics.record(metrics.EG_SUCCESS, "e0")

    metrics.reset_counters()

    assert metrics.get_failures("e0") == 0
    assert metrics.get_successes("e0") == 0
    assert metrics.get_success_rate("e0") == 0.0


def test_per_node_counters_are_independent():
    metrics.enable([metrics.EG_FAILURE, metrics.EG_SUCCESS])

    metrics.record(metrics.EG_FAILURE, "e0")
    metrics.record(metrics.EG_FAILURE, "e0")
    metrics.record(metrics.EG_SUCCESS, "e0")
    metrics.record(metrics.EG_FAILURE, "e1")

    assert metrics.get_failures("e0") == 2
    assert metrics.get_successes("e0") == 1
    assert metrics.get_success_rate("e0") == pytest.approx(1 / 3)
    assert metrics.get_failures("e1") == 1
    assert metrics.get_successes("e1") == 0
    assert metrics.get_success_rate("e1") == 0.0


def test_completion_events_record_running_success_rate():
    metrics.enable([metrics.EG_FAILURE, metrics.EG_SUCCESS])

    metrics.record(metrics.EG_FAILURE, "e0")
    metrics.record(metrics.EG_SUCCESS, "e0")
    metrics.record(metrics.EG_FAILURE, "e0")

    failure_records = metrics.storage.get_by_event(metrics.EG_FAILURE)
    success_records = metrics.storage.get_by_event(metrics.EG_SUCCESS)

    assert failure_records[0]["success_rate"] == 0.0
    assert success_records[0]["success_rate"] == 0.5
    assert failure_records[1]["success_rate"] == pytest.approx(1 / 3)


def test_storage_query_helpers():
    metrics.enable([metrics.EG_FAILURE, metrics.EG_SUCCESS])

    metrics.record(metrics.EG_FAILURE, "e0", initial_fidelity=0.9)
    metrics.record(metrics.EG_SUCCESS, "e0", fidelity=0.9)
    metrics.record(metrics.EG_FAILURE, "e1", initial_fidelity=0.9)

    assert len(metrics.storage.get_by_event(metrics.EG_FAILURE)) == 2
    assert len(metrics.storage.get_by_owner("e0")) == 2
    assert len(metrics.storage.get_by_owner("e1")) == 1


def test_default_time_provider_uses_system_time(monkeypatch):
    monkeypatch.setattr(metrics._system_time_provider, "now", lambda: 42)
    metrics.register_time_provider(metrics._system_time_provider)
    metrics.enable([metrics.EG_SUCCESS])

    metrics.record(metrics.EG_SUCCESS, "e0", fidelity=0.9)

    assert metrics.storage.get_all()[0]["sim_time"] == 42


def test_register_time_provider_uses_registered_source():
    class StubTimeProvider:
        def now(self) -> int:
            return 12345

    metrics.register_time_provider(StubTimeProvider())
    metrics.enable([metrics.EG_SUCCESS])

    metrics.record(metrics.EG_SUCCESS, "e0", fidelity=0.9)

    assert metrics.storage.get_all()[0]["sim_time"] == 12345
