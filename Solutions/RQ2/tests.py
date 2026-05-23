from common import (
    MOVABLE_SERVICES,
    RADIUS_LIMIT,
    SchemeEvaluation,
    StationMetrics,
    CommunityAllocation,
    CandidateStation,
    choose_overflow_station,
    choose_primary_station,
    distance_satisfaction,
    response_satisfaction,
    select_safe_scheme,
    sort_scheme_evaluations_safe,
    sort_scheme_evaluations,
)


def test_distance_satisfaction_respects_radius_limit() -> None:
    rules = [(300.0, 1.0), (500.0, 0.9), (650.0, 0.75), (1000.0, 0.6)]
    assert distance_satisfaction(250.0, rules) == 1.0
    assert distance_satisfaction(600.0, rules) == 0.75
    assert distance_satisfaction(RADIUS_LIMIT + 1.0, rules) == 0.0


def test_response_satisfaction_piecewise_rule() -> None:
    rules = [(0.60, 1.0), (0.75, 0.93), (0.85, 0.85), (0.95, 0.72), (1.00, 0.60)]
    assert response_satisfaction(0.58, rules) == 1.0
    assert response_satisfaction(0.80, rules) == 0.85
    assert response_satisfaction(1.10, rules) == 0.60


def test_only_non_emergency_services_are_movable() -> None:
    assert "紧急救助" not in MOVABLE_SERVICES
    assert {"助餐", "日间照料", "上门护理", "康复理疗", "助浴"} == MOVABLE_SERVICES


def test_lexicographic_sorting_priority() -> None:
    stations = [
        CandidateStation("A", "小型", 18.0, 2000.0, 1000.0),
    ]
    allocations = [
        CommunityAllocation("A", "A", None, 1, 1, 100, 100, 200, 180, 10, 0, 0, 1.0, 1.0, 1.0, 1.0),
    ]
    metrics = [
        StationMetrics("A", "小型", 1000, 10, 0, 10, 0.01, 1000, 800, 730000, 9000, 0, -738800, -738800),
    ]
    low = SchemeEvaluation((1,), stations, allocations, metrics, 0.8, 0.8, 0.9, 0.9, 0.7, 180, 150, 0.8, 0.9, 0, 0.02, 100, 100)
    high_pop = SchemeEvaluation((2,), stations, allocations, metrics, 0.9, 0.9, 0.1, 0.1, 0.1, 20, 10, 0.1, 1.0, 0, 999, -999, -999)
    high_dem = SchemeEvaluation((3,), stations, allocations, metrics, 0.8, 0.8, 0.95, 0.1, 0.1, 50, 20, 0.1, 1.0, 0, 999, -999, -999)
    ranked = sort_scheme_evaluations([low, high_pop, high_dem])
    assert ranked[0].scheme_code == (2,)
    assert ranked[1].scheme_code == (3,)


def test_safe_sorting_prefers_capacity_safety() -> None:
    stations = [CandidateStation("A", "小型", 18.0, 2000.0, 1000.0)]
    allocations = [CommunityAllocation("A", "A", None, 1, 1, 100, 100, 200, 180, 10, 0, 0, 1.0, 1.0, 1.0, 1.0)]
    metrics = [StationMetrics("A", "小型", 1000, 10, 0, 10, 0.01, 1000, 800, 730000, 9000, 0, -738800, -738800)]
    dense = SchemeEvaluation((1,), stations, allocations, metrics, 1.0, 1.0, 0.95, 0.92, 0.80, 180, 150, 0.0, 1.0, 0, 0.0, 100, 100)
    safe = SchemeEvaluation((2,), stations, allocations, metrics, 1.0, 1.0, 0.90, 0.90, 0.82, 160, 130, 1.0, 0.8, 1, 0.01, 90, 90)
    ranked = sort_scheme_evaluations_safe([dense, safe])
    assert ranked[0].scheme_code == (2,)


def test_select_safe_scheme_uses_threshold_then_fallback() -> None:
    stations = [CandidateStation("A", "小型", 18.0, 2000.0, 1000.0)]
    allocations = [CommunityAllocation("A", "A", None, 1, 1, 100, 100, 200, 180, 10, 0, 0, 1.0, 1.0, 1.0, 1.0)]
    metrics = [StationMetrics("A", "小型", 1000, 10, 0, 10, 0.01, 1000, 800, 730000, 9000, 0, -738800, -738800)]
    a = SchemeEvaluation((1,), stations, allocations, metrics, 1.0, 1.0, 0.95, 0.92, 0.80, 180, 150, 0.0, 1.0, 0, 0.0, 100, 100)
    b = SchemeEvaluation((2,), stations, allocations, metrics, 1.0, 1.0, 0.90, 0.90, 0.82, 160, 130, 0.5, 0.8, 0, 0.01, 90, 90)
    picked, threshold = select_safe_scheme([a, b], capacity_safety_threshold=0.5)
    assert picked.scheme_code == (2,)
    assert threshold == 0.5

    picked2, threshold2 = select_safe_scheme([a], capacity_safety_threshold=0.5)
    assert picked2.scheme_code == (1,)
    assert threshold2 == 0.0


def test_select_safe_scheme_respects_higher_threshold() -> None:
    stations = [CandidateStation("A", "小型", 18.0, 2000.0, 1000.0)]
    allocations = [CommunityAllocation("A", "A", None, 1, 1, 100, 100, 200, 180, 10, 0, 0, 1.0, 1.0, 1.0, 1.0)]
    metrics = [StationMetrics("A", "小型", 1000, 10, 0, 10, 0.01, 1000, 800, 730000, 9000, 0, -738800, -738800)]
    a = SchemeEvaluation((1,), stations, allocations, metrics, 1.0, 1.0, 0.95, 0.92, 0.80, 180, 150, 0.25, 1.0, 0, 0.0, 100, 100)
    b = SchemeEvaluation((2,), stations, allocations, metrics, 1.0, 1.0, 0.80, 0.88, 0.82, 160, 130, 0.75, 0.8, 1, 0.01, 90, 90)
    picked, threshold = select_safe_scheme([a, b], capacity_safety_threshold=0.75)
    assert picked.scheme_code == (2,)
    assert threshold == 0.75


def test_primary_station_prefers_capacity_feasible_choice() -> None:
    reachable = [
        ("B", 300.0, 1.0, 0.99),
        ("A", 400.0, 0.9, 0.97),
    ]
    remaining = {"A": 800.0, "B": 100.0}
    selected = choose_primary_station(reachable, remaining, total_daily_demand=700.0, emergency_daily_demand=50.0)
    assert selected == "A"


def test_overflow_station_skips_primary_and_zero_capacity_station() -> None:
    reachable = [
        ("B", 300.0, 1.0, 0.99),
        ("A", 400.0, 0.9, 0.97),
        ("C", 500.0, 0.9, 0.95),
    ]
    remaining = {"A": 0.0, "B": 500.0, "C": 300.0}
    selected = choose_overflow_station(reachable, primary_name="B", remaining_capacity=remaining)
    assert selected == "C"


def run_all_tests() -> None:
    tests = [
        test_distance_satisfaction_respects_radius_limit,
        test_response_satisfaction_piecewise_rule,
        test_only_non_emergency_services_are_movable,
        test_lexicographic_sorting_priority,
        test_safe_sorting_prefers_capacity_safety,
        test_select_safe_scheme_uses_threshold_then_fallback,
        test_select_safe_scheme_respects_higher_threshold,
        test_primary_station_prefers_capacity_feasible_choice,
        test_overflow_station_skips_primary_and_zero_capacity_station,
    ]
    for test in tests:
        test()
    print(f"Passed {len(tests)} tests.")


if __name__ == "__main__":
    run_all_tests()
