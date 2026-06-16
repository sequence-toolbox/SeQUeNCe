import pytest

from sequence.utils import metrics


@pytest.fixture(autouse=True)
def reset_metrics():
    metrics._enabled = False
    metrics._enabled_events.clear()
    metrics.storage.clear()
    metrics.register_time_provider(metrics._system_time_provider)


# Tests that record doesn't do anything if the user has not enabled metrics
def test_record_before_enable_is_noop():
    metrics.record(metrics.EG_SUCCESS, "e0", fidelity=0.9)
    assert metrics.storage.get_all() == []


def test_enable_filters_event_types():
    metrics.enable([metrics.EG_SUCCESS])

    metrics.record(metrics.EG_ATTEMPT, "e0", round=1)
    metrics.record(metrics.EG_SUCCESS, "e0", fidelity=0.9)

    records = metrics.storage.get_all()
    assert len(records) == 1
    assert records[0]["event_type"] is metrics.EG_SUCCESS
    assert records[0]["owner_name"] == "e0"
    assert records[0]["fidelity"] == 0.9


def test_record_stores_arbitrary_kwargs():
    metrics.enable([metrics.EG_ATTEMPT])

    metrics.record(metrics.EG_ATTEMPT, "e1", round=2, custom_metric=42)

    record = metrics.storage.get_all()[0]
    assert record["round"] == 2
    assert record["custom_metric"] == 42


def test_configure_uses_in_memory_storage():
    metrics.enable([metrics.EG_SUCCESS])
    metrics.record(metrics.EG_SUCCESS, "e0", fidelity=0.8)
    assert len(metrics.storage.get_all()) == 1

    metrics.configure(storage_type="in_memory")
    assert metrics.storage.get_all() == []


# In case a timeline is never created (rare but could happen?)
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


def test_storage_query_helpers():
    metrics.enable([metrics.EG_ATTEMPT, metrics.EG_SUCCESS])

    metrics.record(metrics.EG_ATTEMPT, "e0", round=1)
    metrics.record(metrics.EG_SUCCESS, "e0", fidelity=0.9)
    metrics.record(metrics.EG_ATTEMPT, "e1", round=1)

    assert len(metrics.storage.get_by_event(metrics.EG_ATTEMPT)) == 2
    assert len(metrics.storage.get_by_owner("e0")) == 2
    assert len(metrics.storage.get_by_owner("e1")) == 1
