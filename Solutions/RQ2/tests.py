from common import (
    MOVABLE_SERVICES,
    RADIUS_LIMIT,
    SchemeEvaluation,
    StationMetrics,
    CommunityAllocation,
    CommunityDemand,
    CandidateStation,
    StationScale,
    choose_overflow_station,
    choose_primary_station,
    compute_annual_financial_metrics,
    compute_service_metrics,
    compute_weighted_served_population_coverage,
    distance_satisfaction,
    evaluate_scheme,
    response_satisfaction,
    scheme_profit_compliance,
    solve_location_milp,
    select_safe_scheme,
    sort_scheme_evaluations_safe,
    sort_scheme_evaluations,
    SERVICE_ORDER,
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


def test_service_metrics_separate_satisfaction_from_access_performance() -> None:
    metrics = compute_service_metrics(
        raw_served_demand_daily=30.0,
        adjusted_demand_daily=60.0,
        service_satisfaction=0.8,
    )
    assert abs(metrics["effective_person_times_daily"] - 24.0) < 1e-9
    assert abs(metrics["demand_service_ratio"] - 0.5) < 1e-9
    assert abs(metrics["service_access_performance"] - 0.4) < 1e-9


def test_weighted_served_population_coverage_uses_fractional_service_ratio() -> None:
    allocations = [
        CommunityAllocation(
            "A",
            "A",
            None,
            1,
            1,
            100.0,
            100.0,
            10.0,
            8.0,
            10.0,
            0.0,
            0.0,
            1.0,
            1.0,
            1.0,
            0.8,
            adjusted_demand_daily=10.0,
            demand_service_ratio=1.0,
            service_access_performance=0.8,
        ),
        CommunityAllocation(
            "B",
            "B",
            None,
            1,
            1,
            100.0,
            100.0,
            5.0,
            4.0,
            5.0,
            0.0,
            5.0,
            1.0,
            1.0,
            1.0,
            0.8,
            adjusted_demand_daily=10.0,
            demand_service_ratio=0.5,
            service_access_performance=0.4,
        ),
    ]
    coverage = compute_weighted_served_population_coverage(allocations)
    assert abs(coverage - 0.75) < 1e-9


def test_annual_financial_metrics_use_effective_revenue_and_raw_cost() -> None:
    metrics = compute_annual_financial_metrics(
        scale="小型",
        build_cost_wan=18.0,
        daily_fixed_cost=2000.0,
        raw_daily_by_service={
            "助餐": 10.0,
            "日间照料": 0.0,
            "上门护理": 0.0,
            "康复理疗": 0.0,
            "助浴": 0.0,
            "紧急救助": 2.0,
        },
        effective_daily_by_service={
            "助餐": 8.0,
            "日间照料": 0.0,
            "上门护理": 0.0,
            "康复理疗": 0.0,
            "助浴": 0.0,
            "紧急救助": 1.8,
        },
        service_costs={
            "助餐": {"price": 10.0, "direct_cost": 4.0},
            "日间照料": {"price": 20.0, "direct_cost": 8.0},
            "上门护理": {"price": 30.0, "direct_cost": 12.0},
            "康复理疗": {"price": 40.0, "direct_cost": 16.0},
            "助浴": {"price": 50.0, "direct_cost": 20.0},
            "紧急救助": {"price": 0.0, "direct_cost": 6.0},
        },
    )
    assert abs(metrics["annual_revenue"] - 8.0 * 10.0 * 365.0) < 1e-9
    assert abs(metrics["annual_direct_cost"] - (10.0 * 4.0 + 2.0 * 6.0) * 365.0) < 1e-9
    assert abs(metrics["annual_subsidy"] - 8.0 * 2.0 * 365.0) < 1e-9
    assert abs(metrics["annual_total_cost"] - (10.0 * 4.0 + 2.0 * 6.0) * 365.0 - 0.0 + 730000.0 + 9000.0) > 1e-9
    assert abs(metrics["profit_rate"] - metrics["annual_net_profit"] / metrics["annual_total_cost"]) < 1e-9


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


def test_primary_station_always_prefers_highest_satisfaction_choice() -> None:
    reachable = [
        ("B", 300.0, 1.0, 0.99),
        ("A", 400.0, 0.9, 0.97),
    ]
    remaining = {"A": 800.0, "B": 100.0}
    selected = choose_primary_station(reachable, remaining, total_daily_demand=700.0, emergency_daily_demand=50.0)
    assert selected == "B"


def test_overflow_station_skips_primary_and_zero_capacity_station() -> None:
    reachable = [
        ("B", 300.0, 1.0, 0.99),
        ("A", 400.0, 0.9, 0.97),
        ("C", 500.0, 0.9, 0.95),
    ]
    remaining = {"A": 0.0, "B": 500.0, "C": 300.0}
    selected = choose_overflow_station(reachable, primary_name="B", remaining_capacity=remaining)
    assert selected == "C"


def test_evaluate_scheme_respects_custom_budget_limit() -> None:
    communities = [
        CommunityDemand(
            community=name,
            elderly_population=100.0,
            adjusted_monthly_demand={service: 0.0 for service in SERVICE_ORDER},
        )
        for name in ["A", "B", "C"]
    ]
    for community in communities:
        community.adjusted_monthly_demand["助餐"] = 30.0
    distance_matrix = {
        src: {dst: 0.0 if src == dst else 100.0 for dst in ["A", "B", "C"]}
        for src in ["A", "B", "C"]
    }
    scales = {
        "小型": StationScale("小型", 18.0, 2000.0, 1000.0),
        "中型": StationScale("中型", 32.0, 3200.0, 2000.0),
        "大型": StationScale("大型", 45.0, 4400.0, 3000.0),
    }
    satisfaction_rules = {
        "distance": [(300.0, 1.0), (500.0, 0.9), (650.0, 0.75), (1000.0, 0.6)],
        "response": [(0.60, 1.0), (0.75, 0.93), (0.85, 0.85), (0.95, 0.72), (1.0, 0.60)],
    }
    service_costs = {
        service: {"price": 10.0, "direct_cost": 5.0}
        for service in SERVICE_ORDER
    }

    assert evaluate_scheme(
        scheme_code=(3, 3, 3),
        communities=communities,
        distance_matrix=distance_matrix,
        scales=scales,
        satisfaction_rules=satisfaction_rules,
        service_costs=service_costs,
    ) is None
    assert evaluate_scheme(
        scheme_code=(3, 3, 3),
        communities=communities,
        distance_matrix=distance_matrix,
        scales=scales,
        satisfaction_rules=satisfaction_rules,
        service_costs=service_costs,
        budget_limit=140.0,
    ) is not None


def test_scheme_profit_compliance_requires_all_station_flags() -> None:
    metrics = [
        StationMetrics("A", "小型", 1000, 10, 0, 10, 0.01, 1000, 800, 730000, 9000, 0, -738800, -738800, annual_revenue=1000, annual_subsidy=200, annual_total_cost=1200, annual_net_profit=0, profit_rate=0.0, profit_compliant=1),
        StationMetrics("B", "小型", 1000, 10, 0, 10, 0.01, 1000, 800, 730000, 9000, 0, -738800, -738800, annual_revenue=1000, annual_subsidy=200, annual_total_cost=1200, annual_net_profit=-10, profit_rate=-0.01, profit_compliant=0),
    ]
    assert scheme_profit_compliance(metrics) == 0


def test_solve_location_milp_returns_budget_feasible_layout() -> None:
    communities = [
        CommunityDemand(
            community=name,
            elderly_population=100.0,
            adjusted_monthly_demand={service: (60.0 if service == "助餐" else 0.0) for service in SERVICE_ORDER},
        )
        for name in ["A", "B", "C"]
    ]
    distance_matrix = {
        "A": {"A": 0.0, "B": 150.0, "C": 900.0},
        "B": {"A": 150.0, "B": 0.0, "C": 180.0},
        "C": {"A": 900.0, "B": 180.0, "C": 0.0},
    }
    scales = {
        "小型": StationScale("小型", 18.0, 2000.0, 3.0),
        "中型": StationScale("中型", 32.0, 3200.0, 6.0),
        "大型": StationScale("大型", 45.0, 4400.0, 9.0),
    }
    scheme_code = solve_location_milp(
        communities=communities,
        distance_matrix=distance_matrix,
        scales=scales,
        budget_limit=50.0,
        fairness_weight=0.2,
        safety_capacity_factor=0.85,
    )
    assert scheme_code is not None
    assert len(scheme_code) == 3
    spent = sum({1: 18.0, 2: 32.0, 3: 45.0}.get(token, 0.0) for token in scheme_code)
    assert spent <= 50.0 + 1e-9


def run_all_tests() -> None:
    tests = [
        test_distance_satisfaction_respects_radius_limit,
        test_response_satisfaction_piecewise_rule,
        test_service_metrics_separate_satisfaction_from_access_performance,
        test_weighted_served_population_coverage_uses_fractional_service_ratio,
        test_annual_financial_metrics_use_effective_revenue_and_raw_cost,
        test_only_non_emergency_services_are_movable,
        test_lexicographic_sorting_priority,
        test_safe_sorting_prefers_capacity_safety,
        test_select_safe_scheme_uses_threshold_then_fallback,
        test_select_safe_scheme_respects_higher_threshold,
        test_primary_station_always_prefers_highest_satisfaction_choice,
        test_overflow_station_skips_primary_and_zero_capacity_station,
        test_evaluate_scheme_respects_custom_budget_limit,
        test_scheme_profit_compliance_requires_all_station_flags,
        test_solve_location_milp_returns_budget_feasible_layout,
    ]
    for test in tests:
        test()
    print(f"Passed {len(tests)} tests.")


if __name__ == "__main__":
    run_all_tests()
