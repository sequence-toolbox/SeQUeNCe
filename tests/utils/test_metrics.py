import math

import pytest

from sequence.kernel.timeline import Timeline
from sequence.utils import metrics
from sequence.utils.metrics import BellPairUtilizationMetric, CounterMetric
from sequence.utils.metrics.event_types import EventTypes


@pytest.fixture(autouse=True)
def reset_metrics_state():
    metrics._enabled = False
    metrics._enabled_events.clear()
    metrics.storage.clear()
    metrics.reset_metrics()
    Timeline(int(1e12))


def test_record_before_enable_is_noop():
    metrics.record(EventTypes.EG_SUCCESS, "e0", fidelity=0.9)
    assert metrics.storage.get_all() == []


def test_enable_filters_event_types():
    # Enable only EP_METRIC; EG events must be filtered out.
    metrics.enable([metrics.EP_METRIC])

    metrics.record(EventTypes.EG_FAILURE, "e0", fidelity=0.9)
    metrics.record(EventTypes.EG_SUCCESS, "e0", fidelity=0.9)
    metrics.record(EventTypes.EP_SUCCESS, "e0", fidelity=0.9)

    records = metrics.storage.get_all()
    assert len(records) == 1
    assert records[0]["event_type"] is EventTypes.EP_SUCCESS
    assert records[0]["owner_name"] == "e0"
    assert records[0]["fidelity"] == 0.9


def test_record_stores_arbitrary_kwargs():
    metrics.enable([metrics.EG_METRIC])

    metrics.record(EventTypes.EG_FAILURE, "e1", fidelity=0.8, custom_metric=42)

    record = metrics.storage.get_all()[0]
    assert record["fidelity"] == 0.8
    assert record["custom_metric"] == 42


def test_configure_replaces_storage():
    metrics.enable([metrics.EG_METRIC])
    metrics.record(EventTypes.EG_FAILURE, "e0")
    metrics.record(EventTypes.EG_SUCCESS, "e0")
    assert len(metrics.storage.get_all()) == 2

    metrics.configure(storage_type="in_memory")

    assert metrics.storage.get_all() == []


def test_reset_metrics_clears_per_node_counts():
    metrics.enable([metrics.EG_METRIC, metrics.EP_METRIC])
    metrics.record(EventTypes.EG_FAILURE, "e0")
    metrics.record(EventTypes.EG_SUCCESS, "e0")
    metrics.record(EventTypes.EP_FAILURE, "e0")
    metrics.record(EventTypes.EP_SUCCESS, "e0")

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

    metrics.record(EventTypes.EG_FAILURE, "e0")
    metrics.record(EventTypes.EG_FAILURE, "e0")
    metrics.record(EventTypes.EG_SUCCESS, "e0")
    metrics.record(EventTypes.EG_FAILURE, "e1")

    eg = metrics.get_counter("eg")
    assert eg.failures("e0") == 2
    assert eg.successes("e0") == 1
    assert eg.success_rate("e0") == pytest.approx(1 / 3)
    assert eg.failures("e1") == 1
    assert eg.successes("e1") == 0
    assert eg.success_rate("e1") == 0.0


def test_completion_events_record_running_success_rate():
    metrics.enable([metrics.EG_METRIC])

    metrics.record(EventTypes.EG_FAILURE, "e0")
    metrics.record(EventTypes.EG_SUCCESS, "e0")
    metrics.record(EventTypes.EG_FAILURE, "e0")

    failure_records = metrics.storage.get_by_event(EventTypes.EG_FAILURE)
    success_records = metrics.storage.get_by_event(EventTypes.EG_SUCCESS)

    assert failure_records[0]["success_rate"] == 0.0
    assert success_records[0]["success_rate"] == 0.5
    assert failure_records[1]["success_rate"] == pytest.approx(1 / 3)


def test_storage_query_helpers():
    metrics.enable([metrics.EG_METRIC])

    metrics.record(EventTypes.EG_FAILURE, "e0", fidelity=0.9)
    metrics.record(EventTypes.EG_SUCCESS, "e0", fidelity=0.9)
    metrics.record(EventTypes.EG_FAILURE, "e1", fidelity=0.9)

    assert len(metrics.storage.get_by_event(EventTypes.EG_FAILURE)) == 2
    assert len(metrics.storage.get_by_owner("e0")) == 2
    assert len(metrics.storage.get_by_owner("e1")) == 1


def test_register_time_provider_uses_registered_source():
    timeline = Timeline(int(1e12))
    timeline.time = 12345
    metrics.register_time_provider(timeline)
    metrics.enable([metrics.EG_METRIC])

    metrics.record(EventTypes.EG_SUCCESS, "e0", fidelity=0.9)

    assert metrics.storage.get_all()[0]["sim_time"] == 12345


def test_throughput_does_not_affect_eg_counters():
    metrics.enable([metrics.EG_METRIC])

    metrics.record(EventTypes.EG_FAILURE, "e0")
    metrics.record(EventTypes.EG_SUCCESS, "e0")

    eg = metrics.get_counter("eg")
    assert eg.failures("e0") == 1
    assert eg.successes("e0") == 1
    assert eg.success_rate("e0") == 0.5


def test_collect_trial_metrics_returns_node_snapshot():
    metrics.enable([metrics.EG_METRIC])

    metrics.record(EventTypes.EG_FAILURE, "e0", fidelity=0.8)
    metrics.record(EventTypes.EG_SUCCESS, "e0", fidelity=0.8)

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

    metrics.record(
        EventTypes.DELIVERY,
        "right",
        fidelity=0.9,
        pair_number=1,
        start_time=int(1e12),
    )
    timeline.time = int(2e12)
    metrics.record(
        EventTypes.DELIVERY,
        "right",
        fidelity=0.9,
        pair_number=2,
        start_time=int(1e12),
    )

    trial = metrics.collect_trial_metrics("left", delivery_owner="right")

    assert trial["app_throughput"] == pytest.approx(2.0)


def test_collect_trial_metrics_without_throughput_is_nan():
    metrics.enable([metrics.EG_METRIC])
    metrics.record(EventTypes.EG_SUCCESS, "e0", fidelity=0.9)

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
    metrics.enable([metrics.EP_METRIC])

    metrics.record(EventTypes.EP_FAILURE, "left")
    metrics.record(EventTypes.EP_SUCCESS, "left", fidelity=0.75)
    metrics.record(EventTypes.EP_FAILURE, "left")

    ep = metrics.get_counter("ep")
    assert ep.failures("left") == 2
    assert ep.successes("left") == 1
    assert ep.success_rate("left") == pytest.approx(1 / 3)

    success_records = metrics.storage.get_by_event(EventTypes.EP_SUCCESS)
    assert success_records[0]["ep_success_rate"] == pytest.approx(0.5)


def test_es_counters_and_success_rate():
    metrics.enable([metrics.ES_METRIC])

    metrics.record(EventTypes.ES_FAILURE, "middle")
    metrics.record(EventTypes.ES_SUCCESS, "middle", fidelity=0.75)
    metrics.record(EventTypes.ES_FAILURE, "middle")

    es = metrics.get_counter("es")
    assert es.failures("middle") == 2
    assert es.successes("middle") == 1
    assert es.success_rate("middle") == pytest.approx(1 / 3)

    success_records = metrics.storage.get_by_event(EventTypes.ES_SUCCESS)
    assert success_records[0]["es_success_rate"] == pytest.approx(0.5)


def test_collect_trial_metrics_swapped_fidelities():
    metrics.enable([metrics.ES_METRIC])

    metrics.record(EventTypes.ES_SUCCESS, "middle", fidelity=0.7)
    metrics.record(EventTypes.ES_SUCCESS, "middle", fidelity=0.75)

    trial = metrics.collect_trial_metrics("middle")
    assert trial["es_success"] == 2
    assert trial["swapped_fidelities"] == [0.7, 0.75]


def test_delivery_does_not_affect_ep_counters():
    metrics.enable([metrics.EP_METRIC, metrics.DELIVERY_TIME_METRIC])

    metrics.record(EventTypes.EP_SUCCESS, "left", fidelity=0.8)
    metrics.record(EventTypes.DELIVERY, "right", fidelity=0.8, pair_number=1)

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

    metrics.record(EventTypes.EP_SUCCESS, "left", fidelity=0.7)
    metrics.record(EventTypes.EP_SUCCESS, "left", fidelity=0.75)

    for pair_number in range(1, 4):
        metrics.record(
            EventTypes.DELIVERY,
            "right",
            fidelity=0.7 + pair_number * 0.01,
            pair_number=pair_number,
            start_time=int(1e12),
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
    metrics.record(EventTypes.DELIVERY, "right", fidelity=0.9, pair_number=1)

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
        fidelity=0.9,
        pair_number=1,
        start_time=0,
    )

    trial = metrics.collect_trial_metrics(
        "right",
        target_pairs=1,
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


def test_purified_delivery_assigns_pair_index():
    metrics.enable([metrics.DELIVERY_TIME_METRIC])
    kwargs = {
        "identity": 7,
        "initiator": "n1",
        "responder": "n2",
        "start_time": 0,
        "end_time": int(1e12),
        "memory_size": 5,
        "entanglement_number": 2,
        "target_fidelity": 0.9,
        "path": ["n1", "n2"],
        "fidelity": 0.91,
    }
    metrics.record(EventTypes.DELIVERY, "n1", **kwargs)
    metrics.record(EventTypes.DELIVERY, "n1", **{**kwargs, "fidelity": 0.92})
    metrics.record(EventTypes.DELIVERY, "n2", **{**kwargs, "fidelity": 0.93})

    n1_records = metrics.storage.get_by_owner("n1")
    n2_records = metrics.storage.get_by_owner("n2")
    assert n1_records[0]["pair_index"] == 1
    assert n1_records[1]["pair_index"] == 2
    assert n2_records[0]["pair_index"] == 1


def test_collect_reservation_data_produces_expected_row():
    metrics.enable([metrics.DELIVERY_TIME_METRIC])
    start_time = int(1e12)
    end_time = int(2e12)
    base = {
        "identity": 1,
        "initiator": "n1",
        "responder": "n2",
        "start_time": start_time,
        "end_time": end_time,
        "memory_size": 5,
        "entanglement_number": 2,
        "target_fidelity": 0.9,
        "path": ["n1", "m1", "n2"],
    }

    class StubTimeProvider:
        def __init__(self) -> None:
            self._time = start_time + int(1e11)

        def now(self) -> int:
            current = self._time
            self._time += int(2e11)
            return current

    metrics.register_time_provider(StubTimeProvider())
    metrics.record(EventTypes.DELIVERY, "n1", fidelity=0.91, **base)
    metrics.record(EventTypes.DELIVERY, "n1", fidelity=0.92, **base)

    rows = metrics.collect_reservation_data("n1")
    assert len(rows) == 1
    row = rows[0]
    assert row[0] == "n1"
    assert row[1] == 1
    assert row[2] == "n1"
    assert row[3] == "n2"
    assert row[4] == start_time
    assert row[5] == end_time
    assert row[6] == end_time - start_time
    assert row[7] == 2
    assert row[8] == 2
    assert row[9] == pytest.approx(2 / (end_time - start_time) * 1e12)
    assert row[11] is True
    assert row[12] == 3
    assert row[14] == pytest.approx(0.915)
    assert row[16] == pytest.approx(int(2e11))


def test_eg_success_record_includes_reservation_id():
    metrics.enable([metrics.EG_METRIC])
    metrics.record(EventTypes.EG_SUCCESS, "n0", fidelity=0.9, reservation_id=5)

    record = metrics.storage.get_all()[0]
    assert record["reservation_id"] == 5


def test_bell_pair_utilization_nan_without_deliveries():
    metrics.enable([metrics.EG_METRIC])
    metrics.record(EventTypes.EG_SUCCESS, "left", fidelity=0.9, reservation_id=1)
    metrics.record(EventTypes.EG_FAILURE, "left", reservation_id=1)

    trial = metrics.collect_trial_metrics("left")
    assert math.isnan(trial["bell_pair_utilization"])


def test_bell_pair_utilization_basic_ratio():
    metrics.enable([metrics.EG_METRIC, metrics.DELIVERY_TIME_METRIC])

    # n_b: 6 generation attempts on "left"
    for _ in range(4):
        metrics.record(EventTypes.EG_SUCCESS, "left", fidelity=0.9, reservation_id=1)
    for _ in range(2):
        metrics.record(EventTypes.EG_FAILURE, "left", reservation_id=1)

    # n_s: 3 deliveries on "left"
    for pair in range(1, 4):
        metrics.record(EventTypes.DELIVERY, "left", fidelity=0.95, identity=1, pair_number=pair)

    trial = metrics.collect_trial_metrics("left")
    assert trial["bell_pair_utilization"] == pytest.approx(6 / 3)


def test_bell_pair_utilization_uses_owner_and_delivery_owner():
    metrics.enable([metrics.EG_METRIC, metrics.DELIVERY_TIME_METRIC])

    for _ in range(5):
        metrics.record(EventTypes.EG_SUCCESS, "left", fidelity=0.9, reservation_id=1)

    for pair in range(1, 3):
        metrics.record(EventTypes.DELIVERY, "right", fidelity=0.95, identity=1, pair_number=pair)

    trial = metrics.collect_trial_metrics("left", delivery_owner="right")
    assert trial["bell_pair_utilization"] == pytest.approx(5 / 2)


def test_bell_pair_utilization_per_reservation_filter():
    metrics.enable([metrics.EG_METRIC, metrics.DELIVERY_TIME_METRIC])

    # Reservation 1: 4 EG attempts, 2 deliveries -> U = 2.0
    for _ in range(3):
        metrics.record(EventTypes.EG_SUCCESS, "left", fidelity=0.9, reservation_id=1)
    metrics.record(EventTypes.EG_FAILURE, "left", reservation_id=1)
    for pair in range(1, 3):
        metrics.record(EventTypes.DELIVERY, "left", fidelity=0.95, identity=1, pair_number=pair)

    # Reservation 2: 6 EG attempts, 2 deliveries -> U = 3.0
    for _ in range(6):
        metrics.record(EventTypes.EG_SUCCESS, "left", fidelity=0.9, reservation_id=2)
    for pair in range(1, 3):
        metrics.record(EventTypes.DELIVERY, "left", fidelity=0.95, identity=2, pair_number=pair)

    metric_res1 = BellPairUtilizationMetric(key="bpu_res1", delivery_event=EventTypes.DELIVERY, reservation_id=1)
    metrics.register_metric(metric_res1)
    metric_res2 = BellPairUtilizationMetric(key="bpu_res2", delivery_event=EventTypes.DELIVERY, reservation_id=2)
    metrics.register_metric(metric_res2)
    try:
        trial = metrics.collect_trial_metrics("left")
        assert trial["bpu_res1"] == pytest.approx(4 / 2)
        assert trial["bpu_res2"] == pytest.approx(6 / 2)
        # Aggregate (per-node) counts all reservations: 10 EG / 4 deliveries.
        assert trial["bell_pair_utilization"] == pytest.approx(10 / 4)
    finally:
        metrics.unregister_metric(metric_res1)
        metrics.unregister_metric(metric_res2)


def test_collect_reservation_data_includes_bell_pair_utilization():
    metrics.enable([metrics.EG_METRIC, metrics.DELIVERY_TIME_METRIC])
    start_time = int(1e12)
    end_time = int(2e12)
    base = {
        "identity": 1,
        "initiator": "n1",
        "responder": "n2",
        "start_time": start_time,
        "end_time": end_time,
        "memory_size": 5,
        "entanglement_number": 2,
        "target_fidelity": 0.9,
        "path": ["n1", "m1", "n2"],
    }

    class StubTimeProvider:
        def __init__(self) -> None:
            self._time = start_time + int(1e11)

        def now(self) -> int:
            current = self._time
            self._time += int(2e11)
            return current

    metrics.register_time_provider(StubTimeProvider())

    # 6 EG attempts tied to reservation 1 on n1.
    for _ in range(4):
        metrics.record(EventTypes.EG_SUCCESS, "n1", fidelity=0.9, reservation_id=1)
    for _ in range(2):
        metrics.record(EventTypes.EG_FAILURE, "n1", reservation_id=1)

    metrics.record(EventTypes.DELIVERY, "n1", fidelity=0.91, **base)
    metrics.record(EventTypes.DELIVERY, "n1", fidelity=0.92, **base)

    rows = metrics.collect_reservation_data("n1")
    assert len(rows) == 1
    # BPU is the last column: n_b=6, served_pairs=2 -> 3.0
    assert rows[0][-1] == pytest.approx(6 / 2)
