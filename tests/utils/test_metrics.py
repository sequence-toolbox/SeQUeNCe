import math

import pytest

from sequence.utils import metrics
from sequence.utils.metrics import CounterPairMetric


@pytest.fixture(autouse=True)
def reset_metrics_state():
    metrics._recorder.shutdown()
    metrics._enabled = False
    metrics._enabled_events.clear()
    metrics.storage.clear()
    metrics._recorder.configure_handlers(metrics.storage, metrics.list_metrics)
    metrics.reset_metrics()
    metrics.register_time_provider(metrics._system_time_provider)
    yield
    metrics._recorder.shutdown()


def test_record_before_enable_is_noop():
    metrics.record(metrics.EG_SUCCESS, "e0", fidelity=0.9)
    assert metrics.storage.get_all() == []


def test_enable_filters_event_types():
    metrics.enable([metrics.EG_SUCCESS])

    metrics.record(metrics.EG_FAILURE, "e0", initial_fidelity=0.9)
    metrics.record(metrics.EG_SUCCESS, "e0", fidelity=0.9)
    metrics.flush()

    records = metrics.storage.get_all()
    assert len(records) == 1
    assert records[0]["event_type"] is metrics.EG_SUCCESS
    assert records[0]["owner_name"] == "e0"
    assert records[0]["fidelity"] == 0.9


def test_record_stores_arbitrary_kwargs():
    metrics.enable([metrics.EG_FAILURE])

    metrics.record(metrics.EG_FAILURE, "e1", initial_fidelity=0.8, custom_metric=42)
    metrics.flush()

    record = metrics.storage.get_all()[0]
    assert record["initial_fidelity"] == 0.8
    assert record["custom_metric"] == 42


def test_configure_replaces_storage():
    metrics.enable([metrics.EG_FAILURE, metrics.EG_SUCCESS])
    metrics.record(metrics.EG_FAILURE, "e0")
    metrics.record(metrics.EG_SUCCESS, "e0")
    metrics.flush()
    assert len(metrics.storage.get_all()) == 2

    metrics.configure(storage_type="in_memory")

    assert metrics.storage.get_all() == []


def test_reset_metrics_clears_per_node_counts():
    metrics.enable(
        [metrics.EG_FAILURE, metrics.EG_SUCCESS, metrics.EP_FAILURE, metrics.EP_SUCCESS]
    )
    metrics.record(metrics.EG_FAILURE, "e0")
    metrics.record(metrics.EG_SUCCESS, "e0")
    metrics.record(metrics.EP_FAILURE, "e0")
    metrics.record(metrics.EP_SUCCESS, "e0")

    metrics.reset_metrics()

    eg = metrics.get_counter_pair("eg")
    ep = metrics.get_counter_pair("ep")
    assert eg.failures("e0") == 0
    assert eg.successes("e0") == 0
    assert eg.success_rate("e0") == 0.0
    assert ep.failures("e0") == 0
    assert ep.successes("e0") == 0
    assert ep.success_rate("e0") == 0.0


def test_per_node_counters_are_independent():
    metrics.enable([metrics.EG_FAILURE, metrics.EG_SUCCESS])

    metrics.record(metrics.EG_FAILURE, "e0")
    metrics.record(metrics.EG_FAILURE, "e0")
    metrics.record(metrics.EG_SUCCESS, "e0")
    metrics.record(metrics.EG_FAILURE, "e1")
    metrics.flush()

    eg = metrics.get_counter_pair("eg")
    assert eg.failures("e0") == 2
    assert eg.successes("e0") == 1
    assert eg.success_rate("e0") == pytest.approx(1 / 3)
    assert eg.failures("e1") == 1
    assert eg.successes("e1") == 0
    assert eg.success_rate("e1") == 0.0


def test_completion_events_record_running_success_rate():
    metrics.enable([metrics.EG_FAILURE, metrics.EG_SUCCESS])

    metrics.record(metrics.EG_FAILURE, "e0")
    metrics.record(metrics.EG_SUCCESS, "e0")
    metrics.record(metrics.EG_FAILURE, "e0")
    metrics.flush()

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
    metrics.flush()

    assert len(metrics.storage.get_by_event(metrics.EG_FAILURE)) == 2
    assert len(metrics.storage.get_by_owner("e0")) == 2
    assert len(metrics.storage.get_by_owner("e1")) == 1


def test_default_time_provider_uses_system_time(monkeypatch):
    monkeypatch.setattr(metrics._system_time_provider, "now", lambda: 42)
    metrics.register_time_provider(metrics._system_time_provider)
    metrics.enable([metrics.EG_SUCCESS])

    metrics.record(metrics.EG_SUCCESS, "e0", fidelity=0.9)
    metrics.flush()

    assert metrics.storage.get_all()[0]["sim_time"] == 42


def test_register_time_provider_uses_registered_source():
    class StubTimeProvider:
        def now(self) -> int:
            return 12345

    metrics.register_time_provider(StubTimeProvider())
    metrics.enable([metrics.EG_SUCCESS])

    metrics.record(metrics.EG_SUCCESS, "e0", fidelity=0.9)
    metrics.flush()

    assert metrics.storage.get_all()[0]["sim_time"] == 12345


def test_throughput_does_not_affect_eg_counters():
    metrics.enable([metrics.EG_FAILURE, metrics.EG_SUCCESS, metrics.THROUGHPUT])

    metrics.record(metrics.EG_FAILURE, "e0")
    metrics.record(metrics.EG_SUCCESS, "e0")
    metrics.record(metrics.THROUGHPUT, "e0", throughput=42.0)
    metrics.flush()

    eg = metrics.get_counter_pair("eg")
    assert eg.failures("e0") == 1
    assert eg.successes("e0") == 1
    assert eg.success_rate("e0") == 0.5


def test_collect_trial_metrics_returns_node_snapshot():
    metrics.enable([metrics.EG_FAILURE, metrics.EG_SUCCESS, metrics.THROUGHPUT])

    metrics.record(metrics.EG_FAILURE, "e0", initial_fidelity=0.8)
    metrics.record(metrics.EG_SUCCESS, "e0", fidelity=0.8)
    metrics.record(metrics.THROUGHPUT, "e0", throughput=12.5)

    trial = metrics.collect_trial_metrics("e0")

    assert trial["eg_failures"] == 1
    assert trial["eg_success"] == 1
    assert trial["eg_success_rate"] == 0.5
    assert trial["app_throughput"] == 12.5


def test_collect_trial_metrics_without_throughput_is_nan():
    metrics.enable([metrics.EG_SUCCESS])
    metrics.record(metrics.EG_SUCCESS, "e0", fidelity=0.9)

    trial = metrics.collect_trial_metrics("e0")

    assert math.isnan(trial["app_throughput"])


def test_aggregate_trial_metrics_computes_avg_and_std():
    trials = [
        {
            "eg_failures": 10,
            "eg_success": 5,
            "eg_success_rate": 0.5,
            "app_throughput": 1.0,
        },
        {
            "eg_failures": 12,
            "eg_success": 6,
            "eg_success_rate": 0.5,
            "app_throughput": 2.0,
        },
    ]

    aggregated = metrics.aggregate_trial_metrics(trials)

    assert aggregated["avg_eg_failures"] == 11
    assert aggregated["avg_eg_success"] == 5.5
    assert aggregated["avg_app_throughput"] == 1.5
    assert aggregated["std_eg_failures"] == pytest.approx(1.4142135623730951)


def test_aggregate_trial_metrics_single_trial_has_zero_std():
    trials = [
        {
            "eg_failures": 3,
            "eg_success": 1,
            "eg_success_rate": 0.25,
            "app_throughput": 4.0,
        }
    ]

    aggregated = metrics.aggregate_trial_metrics(trials)

    assert aggregated["avg_eg_failures"] == 3
    assert aggregated["std_eg_failures"] == 0.0


def test_aggregate_trial_metrics_empty_list_raises():
    with pytest.raises(ValueError, match="empty list"):
        metrics.aggregate_trial_metrics([])


def test_aggregate_trial_metrics_ignores_non_finite_values():
    trials = [
        {"eg_success_rate": 0.5, "app_throughput": float("nan")},
        {"eg_success_rate": 0.6, "app_throughput": 2.0},
        {"eg_success_rate": 0.4, "app_throughput": 4.0},
    ]

    aggregated = metrics.aggregate_trial_metrics(trials)

    assert aggregated["avg_eg_success_rate"] == pytest.approx(0.5)
    assert aggregated["avg_app_throughput"] == 3.0
    assert aggregated["std_app_throughput"] == pytest.approx(1.4142135623730951)


def test_ep_counters_and_success_rate():
    metrics.enable([metrics.EP_FAILURE, metrics.EP_SUCCESS])

    metrics.record(metrics.EP_FAILURE, "left")
    metrics.record(metrics.EP_SUCCESS, "left", fidelity=0.75)
    metrics.record(metrics.EP_FAILURE, "left")
    metrics.flush()

    ep = metrics.get_counter_pair("ep")
    assert ep.failures("left") == 2
    assert ep.successes("left") == 1
    assert ep.success_rate("left") == pytest.approx(1 / 3)

    success_records = metrics.storage.get_by_event(metrics.EP_SUCCESS)
    assert success_records[0]["ep_success_rate"] == pytest.approx(0.5)


def test_purified_delivery_does_not_affect_ep_counters():
    metrics.enable([metrics.EP_FAILURE, metrics.EP_SUCCESS, metrics.PURIFIED_DELIVERY])

    metrics.record(metrics.EP_SUCCESS, "left", fidelity=0.8)
    metrics.record(metrics.PURIFIED_DELIVERY, "right", fidelity=0.8, pair_number=1)
    metrics.flush()

    ep = metrics.get_counter_pair("ep")
    assert ep.successes("left") == 1
    assert ep.failures("right") == 0


def test_collect_trial_metrics_ep_fields_and_delivery_time():
    class StubTimeProvider:
        def __init__(self) -> None:
            self._time = int(1e12)

        def now(self) -> int:
            current = self._time
            self._time += int(1e11)
            return current

    provider = StubTimeProvider()
    metrics.register_time_provider(provider)
    metrics.enable([metrics.EP_SUCCESS, metrics.PURIFIED_DELIVERY])

    metrics.record(metrics.EP_SUCCESS, "left", fidelity=0.7)
    metrics.record(metrics.EP_SUCCESS, "left", fidelity=0.75)

    for pair_number in range(1, 4):
        metrics.record(
            metrics.PURIFIED_DELIVERY,
            "right",
            fidelity=0.7 + pair_number * 0.01,
            pair_number=pair_number,
        )

    trial = metrics.collect_trial_metrics(
        "left",
        delivery_owner="right",
        target_pairs=3,
        reservation_start_time=int(1e12),
    )

    assert trial["ep_success"] == 2
    assert trial["purified_fidelities"] == [0.7, 0.75]
    assert trial["delivery_time"] == pytest.approx(0.4)


def test_collect_trial_metrics_delivery_time_nan_when_target_not_reached():
    metrics.enable([metrics.PURIFIED_DELIVERY])
    metrics.record(metrics.PURIFIED_DELIVERY, "right", fidelity=0.9, pair_number=1)

    trial = metrics.collect_trial_metrics(
        "left",
        delivery_owner="right",
        target_pairs=500,
        reservation_start_time=int(1e12),
    )

    assert math.isnan(trial["delivery_time"])


def test_collect_trial_metrics_delivery_owner_defaults_to_owner():
    metrics.enable([metrics.PURIFIED_DELIVERY])
    metrics.record(metrics.PURIFIED_DELIVERY, "right", fidelity=0.9, pair_number=1)

    trial = metrics.collect_trial_metrics(
        "right",
        target_pairs=1,
        reservation_start_time=0,
    )

    assert not math.isnan(trial["delivery_time"])


def test_aggregate_trial_metrics_flattens_purified_fidelities():
    trials = [
        {
            "ep_success_rate": 0.6,
            "purified_fidelities": [0.7, 0.75],
            "delivery_time": 10.0,
        },
        {
            "ep_success_rate": 0.7,
            "purified_fidelities": [0.8],
            "delivery_time": 9.0,
        },
    ]

    aggregated = metrics.aggregate_trial_metrics(trials)

    assert aggregated["avg_purified_fidelities"] == pytest.approx(0.75)
    assert aggregated["std_purified_fidelities"] == pytest.approx(0.05)
    assert aggregated["avg_delivery_time"] == 9.5


def test_aggregate_trial_metrics_handles_nan_delivery_time():
    trials = [
        {"delivery_time": float("nan"), "purified_fidelities": [0.7]},
        {"delivery_time": 12.0, "purified_fidelities": [0.8]},
    ]

    aggregated = metrics.aggregate_trial_metrics(trials)

    assert aggregated["avg_delivery_time"] == 12.0
    assert aggregated["std_delivery_time"] == 0.0


def test_register_event_type_is_idempotent():
    type_a = metrics.register_event_type("CUSTOM_EVENT")
    type_b = metrics.register_event_type("CUSTOM_EVENT")
    assert type_a is type_b


def test_register_metric_adds_to_collect_trial_metrics():
    swap_failure = metrics.register_event_type("SWAP_FAILURE")
    swap_success = metrics.register_event_type("SWAP_SUCCESS")
    swap_metric = CounterPairMetric(
        prefix="swap",
        failure_event=swap_failure,
        success_event=swap_success,
        rate_field="swap_success_rate",
    )
    metrics.register_metric(swap_metric)

    metrics.enable([swap_failure, swap_success])
    metrics.record(swap_failure, "n0")
    metrics.record(swap_success, "n0")

    trial = metrics.collect_trial_metrics("n0")
    assert trial["swap_failures"] == 1
    assert trial["swap_success"] == 1
    assert trial["swap_success_rate"] == 0.5

    metrics.unregister_metric(swap_metric)


def test_register_metric_rejects_duplicate_output_keys():
    duplicate = CounterPairMetric(
        prefix="eg",
        failure_event=metrics.register_event_type("DUP_FAIL"),
        success_event=metrics.register_event_type("DUP_SUCCESS"),
        rate_field="dup_success_rate",
    )
    with pytest.raises(ValueError, match="already registered"):
        metrics.register_metric(duplicate)


def test_sim_time_captured_on_calling_thread():
    class AdvancingTimeProvider:
        def __init__(self) -> None:
            self._time = 100

        def now(self) -> int:
            current = self._time
            self._time += 1000
            return current

    provider = AdvancingTimeProvider()
    metrics.register_time_provider(provider)
    metrics.enable([metrics.EG_SUCCESS])

    metrics.record(metrics.EG_SUCCESS, "e0", fidelity=0.9)
    metrics.flush()

    assert metrics.storage.get_all()[0]["sim_time"] == 100


def test_collect_trial_metrics_flushes_pending_records():
    metrics.enable([metrics.EG_FAILURE, metrics.EG_SUCCESS])

    metrics.record(metrics.EG_FAILURE, "e0")
    metrics.record(metrics.EG_SUCCESS, "e0")

    trial = metrics.collect_trial_metrics("e0")

    assert trial["eg_failures"] == 1
    assert trial["eg_success"] == 1
    assert trial["eg_success_rate"] == 0.5


def test_reset_metrics_clears_after_async_records():
    metrics.enable([metrics.EG_FAILURE, metrics.EG_SUCCESS])

    metrics.record(metrics.EG_FAILURE, "e0")
    metrics.record(metrics.EG_SUCCESS, "e0")
    metrics.reset_metrics()

    eg = metrics.get_counter_pair("eg")
    assert eg.failures("e0") == 0
    assert eg.successes("e0") == 0


def test_flush_waits_for_background_processing():
    metrics.enable([metrics.EG_SUCCESS])

    metrics.record(metrics.EG_SUCCESS, "e0", fidelity=0.9)
    assert metrics.storage.get_all() == []

    metrics.flush()
    assert len(metrics.storage.get_all()) == 1
