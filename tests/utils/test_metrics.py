import math

import pytest

from sequence.kernel.timeline import Timeline
from sequence.utils import metrics
from sequence.utils.metrics import CounterMetric
from sequence.utils.metrics.event_types import EventTypes


def _eg_success_kwargs(**overrides):
    return {"remote_node": "node_B", "fidelity": 0.9, **overrides}


def _eg_failure_kwargs(**overrides):
    return {"remote_node": "node_B", "fidelity": 0.0, **overrides}


def _ep_success_kwargs(**overrides):
    return {"remote_node": "node_B", "fidelity": 0.75, **overrides}


def _ep_failure_kwargs(**overrides):
    return {"remote_node": "node_B", **overrides}


def _es_success_kwargs(**overrides):
    return {"left_node": "node_A", "right_node": "node_C", "fidelity": 0.75, **overrides}


def _es_failure_kwargs(**overrides):
    return {"left_node": "node_A", "right_node": "node_C", **overrides}


def _delivery_kwargs(**overrides):
    return {
        "fidelity": 0.9,
        "identity": 1,
        "initiator": "n1",
        "responder": "n2",
        "start_time": int(1e12),
        "end_time": int(2e12),
        "memory_size": 5,
        "entanglement_number": 2,
        "target_fidelity": 0.9,
        "path": ["n1", "n2"],
        **overrides,
    }


@pytest.fixture(autouse=True)
def reset_metrics_state():
    metrics._enabled = False
    metrics._enabled_events.clear()
    metrics.storage.clear()
    metrics.reset_metrics()
    Timeline(int(1e12))


def test_record_before_enable_is_noop():
    metrics.record(EventTypes.EG_SUCCESS, "e0", **_eg_success_kwargs())
    assert metrics.storage.get_all() == []


def test_enable_filters_event_types():
    # Enable only EP_METRIC; EG events must be filtered out.
    metrics.enable([metrics.EP_METRIC])

    metrics.record(EventTypes.EG_FAILURE, "e0", **_eg_failure_kwargs())
    metrics.record(EventTypes.EG_SUCCESS, "e0", **_eg_success_kwargs())
    metrics.record(EventTypes.EP_SUCCESS, "e0", **_ep_success_kwargs())

    records = metrics.storage.get_all()
    assert len(records) == 1
    assert records[0].event_type is EventTypes.EP_SUCCESS
    assert records[0].owner_name == "e0"
    assert records[0].data.fidelity == 0.75


def test_record_rejects_unexpected_kwargs():
    metrics.enable([metrics.EG_METRIC])

    with pytest.raises(TypeError, match="unexpected keyword argument"):
        metrics.record(EventTypes.EG_FAILURE, "e1", **_eg_failure_kwargs(custom_metric=42))


def test_record_rejects_missing_required_kwargs():
    metrics.enable([metrics.EP_METRIC])

    with pytest.raises(TypeError):
        metrics.record(EventTypes.EP_SUCCESS, "e0", remote_node="node_B")
        # missing fidelity


def test_record_rejects_kwargs_on_none_payload_event():
    custom = metrics.register_event_type("BARE_EVENT")
    custom_metric = CounterMetric(
        prefix="bare",
        failure_event=custom,
        success_event=custom,
        rate_field="bare_rate",
    )
    metrics.register_metric(custom_metric)
    metrics.enable([custom_metric])

    with pytest.raises(TypeError, match="accepts no payload fields"):
        metrics.record(custom, "e0", stray_kwarg=1)

    metrics.unregister_metric(custom_metric)


def test_configure_replaces_storage():
    metrics.enable([metrics.EG_METRIC])
    metrics.record(EventTypes.EG_FAILURE, "e0", **_eg_failure_kwargs())
    metrics.record(EventTypes.EG_SUCCESS, "e0", **_eg_success_kwargs())
    assert len(metrics.storage.get_all()) == 2

    metrics.configure(storage_type="in_memory")

    assert metrics.storage.get_all() == []


def test_reset_metrics_clears_per_node_counts():
    metrics.enable([metrics.EG_METRIC, metrics.EP_METRIC])
    metrics.record(EventTypes.EG_FAILURE, "e0", **_eg_failure_kwargs())
    metrics.record(EventTypes.EG_SUCCESS, "e0", **_eg_success_kwargs())
    metrics.record(EventTypes.EP_FAILURE, "e0", **_ep_failure_kwargs())
    metrics.record(EventTypes.EP_SUCCESS, "e0", **_ep_success_kwargs())

    metrics.reset_metrics()

    eg = metrics.get_counter("eg")
    ep = metrics.get_counter("ep")
    assert eg.failures("e0") == 0
    assert eg.successes("e0") == 0
    assert eg.success_rate("e0") == 0.0
    assert ep.failures("e0") == 0
    assert ep.successes("e0") == 0
    assert ep.success_rate("e0") == 0.0


def test_per_node_counters_are_independent():
    metrics.enable([metrics.EG_METRIC])

    metrics.record(EventTypes.EG_FAILURE, "e0", **_eg_failure_kwargs())
    metrics.record(EventTypes.EG_FAILURE, "e0", **_eg_failure_kwargs())
    metrics.record(EventTypes.EG_SUCCESS, "e0", **_eg_success_kwargs())
    metrics.record(EventTypes.EG_FAILURE, "e1", **_eg_failure_kwargs())

    eg = metrics.get_counter("eg")
    assert eg.failures("e0") == 2
    assert eg.successes("e0") == 1
    assert eg.success_rate("e0") == pytest.approx(1 / 3)
    assert eg.failures("e1") == 1
    assert eg.successes("e1") == 0
    assert eg.success_rate("e1") == 0.0


def test_counter_tracks_running_success_rate():
    metrics.enable([metrics.EG_METRIC])

    eg = metrics.get_counter("eg")

    metrics.record(EventTypes.EG_FAILURE, "e0", **_eg_failure_kwargs())
    assert eg.success_rate("e0") == 0.0

    metrics.record(EventTypes.EG_SUCCESS, "e0", **_eg_success_kwargs())
    assert eg.success_rate("e0") == 0.5

    metrics.record(EventTypes.EG_FAILURE, "e0", **_eg_failure_kwargs())
    assert eg.success_rate("e0") == pytest.approx(1 / 3)


def test_storage_query_helpers():
    metrics.enable([metrics.EG_METRIC])

    metrics.record(EventTypes.EG_FAILURE, "e0", **_eg_failure_kwargs())
    metrics.record(EventTypes.EG_SUCCESS, "e0", **_eg_success_kwargs())
    metrics.record(EventTypes.EG_FAILURE, "e1", **_eg_failure_kwargs())

    assert len(metrics.storage.get_by_event(EventTypes.EG_FAILURE)) == 2
    assert len(metrics.storage.get_by_owner("e0")) == 2
    assert len(metrics.storage.get_by_owner("e1")) == 1


def test_stored_record_has_typed_data():
    metrics.enable([metrics.EG_METRIC])

    metrics.record(EventTypes.EG_SUCCESS, "e0", **_eg_success_kwargs(fidelity=0.85))

    record = metrics.storage.get_all()[0]
    assert record.event_type is EventTypes.EG_SUCCESS
    assert record.owner_name == "e0"
    assert record.data.remote_node == "node_B"
    assert record.data.fidelity == 0.85


def test_register_time_provider_uses_registered_source():
    timeline = Timeline(int(1e12))
    timeline.time = 12345
    metrics.register_time_provider(timeline)
    metrics.enable([metrics.EG_METRIC])

    metrics.record(EventTypes.EG_SUCCESS, "e0", **_eg_success_kwargs())

    assert metrics.storage.get_all()[0].sim_time == 12345


def test_throughput_does_not_affect_eg_counters():
    metrics.enable([metrics.EG_METRIC])

    metrics.record(EventTypes.EG_FAILURE, "e0", **_eg_failure_kwargs())
    metrics.record(EventTypes.EG_SUCCESS, "e0", **_eg_success_kwargs())

    eg = metrics.get_counter("eg")
    assert eg.failures("e0") == 1
    assert eg.successes("e0") == 1
    assert eg.success_rate("e0") == 0.5


def test_collect_trial_metrics_returns_node_snapshot():
    metrics.enable([metrics.EG_METRIC])

    metrics.record(EventTypes.EG_FAILURE, "e0", **_eg_failure_kwargs(fidelity=0.8))
    metrics.record(EventTypes.EG_SUCCESS, "e0", **_eg_success_kwargs(fidelity=0.8))

    trial = metrics.collect_trial_metrics("e0")

    assert trial["eg_failures"] == 1
    assert trial["eg_success"] == 1
    assert trial["eg_success_rate"] == 0.5
    assert math.isnan(trial["app_throughput"])


def test_collect_trial_metrics_computes_throughput_from_deliveries():
    timeline = Timeline(int(1e12))
    timeline.time = int(1e12)
    metrics.register_time_provider(timeline)
    metrics.enable([metrics.DELIVERY_TIME_METRIC])

    metrics.record(EventTypes.DELIVERY, "right", **_delivery_kwargs())
    timeline.time = int(2e12)
    metrics.record(EventTypes.DELIVERY, "right", **_delivery_kwargs(fidelity=0.91))

    trial = metrics.collect_trial_metrics("left", delivery_owner="right")

    assert trial["app_throughput"] == pytest.approx(2.0)


def test_collect_trial_metrics_without_throughput_is_nan():
    metrics.enable([metrics.EG_METRIC])
    metrics.record(EventTypes.EG_SUCCESS, "e0", **_eg_success_kwargs())

    trial = metrics.collect_trial_metrics("e0")

    assert math.isnan(trial["app_throughput"])


def test_ep_counters_and_success_rate():
    metrics.enable([metrics.EP_METRIC])

    metrics.record(EventTypes.EP_FAILURE, "left", **_ep_failure_kwargs())
    metrics.record(EventTypes.EP_SUCCESS, "left", **_ep_success_kwargs())
    metrics.record(EventTypes.EP_FAILURE, "left", **_ep_failure_kwargs())

    ep = metrics.get_counter("ep")
    assert ep.failures("left") == 2
    assert ep.successes("left") == 1
    assert ep.success_rate("left") == pytest.approx(1 / 3)


def test_es_counters_and_success_rate():
    metrics.enable([metrics.ES_METRIC])

    metrics.record(EventTypes.ES_FAILURE, "middle", **_es_failure_kwargs())
    metrics.record(EventTypes.ES_SUCCESS, "middle", **_es_success_kwargs())
    metrics.record(EventTypes.ES_FAILURE, "middle", **_es_failure_kwargs())

    es = metrics.get_counter("es")
    assert es.failures("middle") == 2
    assert es.successes("middle") == 1
    assert es.success_rate("middle") == pytest.approx(1 / 3)


def test_collect_trial_metrics_swapped_fidelities():
    metrics.enable([metrics.ES_METRIC])

    metrics.record(EventTypes.ES_SUCCESS, "middle", **_es_success_kwargs(fidelity=0.7))
    metrics.record(EventTypes.ES_SUCCESS, "middle", **_es_success_kwargs(fidelity=0.75))

    trial = metrics.collect_trial_metrics("middle")
    assert trial["es_success"] == 2
    assert trial["swapped_fidelities"] == [0.7, 0.75]


def test_delivery_does_not_affect_ep_counters():
    metrics.enable([metrics.EP_METRIC, metrics.DELIVERY_TIME_METRIC])

    metrics.record(EventTypes.EP_SUCCESS, "left", **_ep_success_kwargs(fidelity=0.8))
    metrics.record(EventTypes.DELIVERY, "right", **_delivery_kwargs(fidelity=0.8))

    ep = metrics.get_counter("ep")
    assert ep.successes("left") == 1
    assert ep.failures("right") == 0


def test_collect_trial_metrics_ep_fields_and_delivery_time():
    class AdvancingTimeline(Timeline):
        def __init__(self) -> None:
            super().__init__(int(1e12))
            self.time = int(1e12)

        def now(self) -> int:
            current = self.time
            self.time += int(1e11)
            return current

    metrics.register_time_provider(AdvancingTimeline())
    metrics.enable([metrics.EP_METRIC, metrics.DELIVERY_TIME_METRIC])

    metrics.record(EventTypes.EP_SUCCESS, "left", **_ep_success_kwargs(fidelity=0.7))
    metrics.record(EventTypes.EP_SUCCESS, "left", **_ep_success_kwargs(fidelity=0.75))

    for i in range(1, 4):
        metrics.record(
            EventTypes.DELIVERY,
            "right",
            **_delivery_kwargs(fidelity=0.7 + i * 0.01),
        )

    trial = metrics.collect_trial_metrics(
        "left",
        delivery_owner="right",
        target_pairs=3,
    )

    assert trial["ep_success"] == 2
    assert trial["purified_fidelities"] == [0.7, 0.75]
    assert trial["delivery_time"] == pytest.approx(0.4)
    assert trial["app_throughput"] == pytest.approx(7.5)


def test_collect_trial_metrics_delivery_time_nan_when_target_not_reached():
    metrics.enable([metrics.DELIVERY_TIME_METRIC])
    metrics.record(EventTypes.DELIVERY, "right", **_delivery_kwargs())

    trial = metrics.collect_trial_metrics(
        "left",
        delivery_owner="right",
        target_pairs=500,
    )

    assert math.isnan(trial["delivery_time"])


def test_collect_trial_metrics_delivery_owner_defaults_to_owner():
    metrics.enable([metrics.DELIVERY_TIME_METRIC])
    metrics.record(
        EventTypes.DELIVERY,
        "right",
        **_delivery_kwargs(start_time=0),
    )

    trial = metrics.collect_trial_metrics(
        "right",
        target_pairs=1,
    )

    assert not math.isnan(trial["delivery_time"])


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
    swap_metric = CounterMetric(
        prefix="swap",
        failure_event=swap_failure,
        success_event=swap_success,
        rate_field="swap_success_rate",
    )
    metrics.register_metric(swap_metric)

    metrics.enable([swap_metric])
    metrics.record(swap_failure, "n0")
    metrics.record(swap_success, "n0")

    trial = metrics.collect_trial_metrics("n0")
    assert trial["swap_failures"] == 1
    assert trial["swap_success"] == 1
    assert trial["swap_success_rate"] == 0.5

    metrics.unregister_metric(swap_metric)


def test_register_metric_rejects_duplicate_output_keys():
    duplicate = CounterMetric(
        prefix="eg",
        failure_event=metrics.register_event_type("DUP_FAIL"),
        success_event=metrics.register_event_type("DUP_SUCCESS"),
        rate_field="dup_success_rate",
    )
    with pytest.raises(ValueError, match="already registered"):
        metrics.register_metric(duplicate)
