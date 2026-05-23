from common import (
    AllocationRecord,
    NON_EMERGENCY_SERVICES,
    RQ3Inputs,
    SchemeSummaryRecord,
    StationRecord,
    Year5PopulationRecord,
    AdjustedDemandSummaryRecord,
    AdjustedDemandDetailRecord,
)
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


RQ3_DIR = Path(__file__).resolve().parent
RQ3_MAIN_PATH = RQ3_DIR / "3_1.py"
RQ3_SPEC = spec_from_file_location("rq3_main_module", RQ3_MAIN_PATH)
if RQ3_SPEC is None or RQ3_SPEC.loader is None:
    raise RuntimeError(f"Failed to load RQ3 main module from {RQ3_MAIN_PATH}")
RQ3_MAIN = module_from_spec(RQ3_SPEC)
sys.modules[RQ3_SPEC.name] = RQ3_MAIN
RQ3_SPEC.loader.exec_module(RQ3_MAIN)

enumerate_station_price_profiles = RQ3_MAIN.enumerate_station_price_profiles
generate_rescue_price_profiles = RQ3_MAIN.generate_rescue_price_profiles
price_profile_signature = RQ3_MAIN.price_profile_signature
compute_price_satisfaction = RQ3_MAIN.compute_price_satisfaction
meets_profit_rate_constraint = RQ3_MAIN.meets_profit_rate_constraint
fixed_point_converged = RQ3_MAIN.fixed_point_converged
select_primary_and_backup = RQ3_MAIN.select_primary_and_backup
solve_collaboration_lp = RQ3_MAIN.solve_collaboration_lp
CommunityChoice = RQ3_MAIN.CommunityChoice
PriceEvaluation = RQ3_MAIN.PriceEvaluation
IterationRecord = RQ3_MAIN.IterationRecord
select_financial_best = RQ3_MAIN.select_financial_best
select_fairness_best = RQ3_MAIN.select_fairness_best


def make_stub_inputs() -> RQ3Inputs:
    return RQ3Inputs(
        metadata={"source": "RQ1", "precision": "high"},
        year5_population=[
            Year5PopulationRecord("A", 5, 100.0, 20.0, 10.0, 130.0, 8.0),
        ],
        adjusted_demand_summary=[
            AdjustedDemandSummaryRecord("A", "助餐", 300.0),
            AdjustedDemandSummaryRecord("A", "日间照料", 120.0),
            AdjustedDemandSummaryRecord("A", "上门护理", 80.0),
            AdjustedDemandSummaryRecord("A", "康复理疗", 60.0),
            AdjustedDemandSummaryRecord("A", "助浴", 40.0),
            AdjustedDemandSummaryRecord("A", "紧急救助", 12.0),
        ],
        adjusted_demand_detail=[
            AdjustedDemandDetailRecord("A", "自理", "助餐", 3000.0, 600.0, 10.0, 10.0, 1.0, 100.0, 1000.0),
        ],
        q2_summary=SchemeSummaryRecord(
            scheme_type="coverage_priority",
            scheme_code="1000000000",
            scheme_detail="A-小型",
            station_count=1,
            build_cost_wan=18.0,
            geographic_population_coverage=1.0,
            served_population_coverage=1.0,
            served_demand_coverage=1.0,
            average_service_satisfaction=0.85,
            minimum_service_satisfaction=0.85,
            total_raw_served_demand_daily=20.0,
            total_effective_person_times_daily=17.0,
            capacity_safety_rate=1.0,
            max_station_utilization=0.4,
            fully_safe=1,
            fully_served_community_count=1,
            total_unmet_daily_demand=0.0,
            utilization_variance=0.0,
            annual_net_profit_before_subsidy=-1000.0,
            annual_net_profit_after_policy_subsidy=500.0,
        ),
        q2_stations=[
            StationRecord("A", "小型", 1000.0, 20.0, 0.0, 20.0, 0.02, 10000.0, 8000.0, 730000.0, 9000.0, 1000.0, -737000.0, -736000.0),
        ],
        q2_allocations=[
            AllocationRecord("A", "A", None, 1, 1, 130.0, 130.0, 20.0, 17.0, 20.0, 0.0, 0.0, 1.0, 0.93, 1.0, 0.85),
        ],
    )


def test_enumerate_station_price_profiles_respects_emergency_zero() -> None:
    inputs = make_stub_inputs()
    profiles = enumerate_station_price_profiles(inputs)
    assert profiles, "Expected at least one candidate price profile"
    assert all(profile["A"]["紧急救助"] == 0.0 for profile in profiles)


def test_enumerate_station_price_profiles_matches_non_emergency_grid() -> None:
    inputs = make_stub_inputs()
    profiles = enumerate_station_price_profiles(inputs)
    assert len(profiles) >= 9
    unique_meal_prices = sorted({profile["A"]["助餐"] for profile in profiles})
    assert unique_meal_prices == [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 18.0, 20.0]


def test_enumerate_station_price_profiles_uses_reduced_primary_layer() -> None:
    inputs = make_stub_inputs()
    inputs.q2_stations.extend(
        [
            StationRecord("B", "小型", 1000.0, 20.0, 0.0, 20.0, 0.02, 10000.0, 8000.0, 730000.0, 9000.0, 1000.0, -737000.0, -736000.0),
            StationRecord("C", "小型", 1000.0, 20.0, 0.0, 20.0, 0.02, 10000.0, 8000.0, 730000.0, 9000.0, 1000.0, -737000.0, -736000.0),
        ]
    )
    profiles = enumerate_station_price_profiles(inputs)
    assert len(profiles) == 217


def test_generate_rescue_price_profiles_only_uplifts_loss_stations() -> None:
    inputs = make_stub_inputs()
    inputs.q2_stations.extend(
        [
            StationRecord("B", "小型", 1000.0, 20.0, 0.0, 20.0, 0.02, 10000.0, 8000.0, 730000.0, 9000.0, 1000.0, -737000.0, -736000.0),
            StationRecord("C", "小型", 1000.0, 20.0, 0.0, 20.0, 0.02, 10000.0, 8000.0, 730000.0, 9000.0, 1000.0, -737000.0, -736000.0),
        ]
    )
    base_profile = {
        "A": {"助餐": 10.0, "日间照料": 10.0, "上门护理": 10.0, "康复理疗": 10.0, "助浴": 10.0, "紧急救助": 0.0},
        "B": {"助餐": 12.0, "日间照料": 12.0, "上门护理": 12.0, "康复理疗": 12.0, "助浴": 12.0, "紧急救助": 0.0},
        "C": {"助餐": 10.0, "日间照料": 10.0, "上门护理": 10.0, "康复理疗": 10.0, "助浴": 10.0, "紧急救助": 0.0},
    }
    source = PriceEvaluation(
        station_prices=base_profile,
        iteration_count=3,
        converged=1,
        average_service_satisfaction=0.82,
        minimum_service_satisfaction=0.72,
        vulnerable_service_satisfaction=0.80,
        annual_government_subsidy=1000.0,
        annual_service_revenue=10000.0,
        annual_direct_cost=12000.0,
        annual_fixed_cost=3000.0,
        annual_depreciation=1000.0,
        annual_net_profit_before_subsidy=-6000.0,
        annual_net_profit_after_subsidy=-5000.0,
        annual_net_profit=-5000.0,
        feasible_station_count=1,
        profit_compliant=0,
        fair_satisfaction_compliant=1,
        low_income_service_satisfaction=0.79,
        low_income_served_coverage=1.0,
        iteration_trace=[IterationRecord(1, 0.01, 0.82, 1, 1000.0)],
        station_financials=[
            {"station_community": "A", "profit_rate": -0.03},
            {"station_community": "B", "profit_rate": 0.02},
            {"station_community": "C", "profit_rate": -0.01},
        ],
        community_results=[
            {"community": "A", "service_satisfaction": 0.8},
        ],
        accessibility_groups=[],
    )
    rescue = generate_rescue_price_profiles(
        inputs,
        [source],
        near_feasible_top_k=1,
        overall_top_k=1,
        max_candidates=64,
    )
    assert rescue
    seen = {price_profile_signature(item.station_prices) for item in rescue}
    assert price_profile_signature(base_profile) not in seen
    for item in rescue:
        a_price = item.station_prices["A"]["助餐"]
        b_price = item.station_prices["B"]["助餐"]
        c_price = item.station_prices["C"]["助餐"]
        assert b_price == 12.0
        assert a_price >= 10.0
        assert c_price >= 10.0
        assert a_price > 10.0 or c_price > 10.0


def test_dual_selectors_can_choose_different_schemes() -> None:
    profile = {
        "A": {"助餐": 10.0, "日间照料": 10.0, "上门护理": 10.0, "康复理疗": 10.0, "助浴": 10.0, "紧急救助": 0.0},
    }
    financial = PriceEvaluation(
        station_prices=profile,
        iteration_count=3,
        converged=1,
        average_service_satisfaction=0.55,
        minimum_service_satisfaction=0.10,
        vulnerable_service_satisfaction=0.43,
        annual_government_subsidy=1000.0,
        annual_service_revenue=10000.0,
        annual_direct_cost=9000.0,
        annual_fixed_cost=1000.0,
        annual_depreciation=500.0,
        annual_net_profit_before_subsidy=-500.0,
        annual_net_profit_after_subsidy=500.0,
        annual_net_profit=500.0,
        feasible_station_count=1,
        profit_compliant=1,
        fair_satisfaction_compliant=0,
        low_income_service_satisfaction=0.40,
        low_income_served_coverage=0.8,
        iteration_trace=[IterationRecord(1, 0.01, 0.55, 1, 1000.0)],
        station_financials=[{"station_community": "A", "profit_rate": 0.04}],
        community_results=[{"community": "A", "service_satisfaction": 0.10}],
        accessibility_groups=[],
    )
    fairness = PriceEvaluation(
        station_prices=profile,
        iteration_count=4,
        converged=1,
        average_service_satisfaction=0.82,
        minimum_service_satisfaction=0.72,
        vulnerable_service_satisfaction=0.80,
        annual_government_subsidy=800.0,
        annual_service_revenue=9000.0,
        annual_direct_cost=8800.0,
        annual_fixed_cost=1000.0,
        annual_depreciation=500.0,
        annual_net_profit_before_subsidy=-1300.0,
        annual_net_profit_after_subsidy=-500.0,
        annual_net_profit=-500.0,
        feasible_station_count=0,
        profit_compliant=0,
        fair_satisfaction_compliant=1,
        low_income_service_satisfaction=0.78,
        low_income_served_coverage=0.9,
        iteration_trace=[IterationRecord(1, 0.01, 0.82, 0, 800.0)],
        station_financials=[{"station_community": "A", "profit_rate": -0.03}],
        community_results=[{"community": "A", "service_satisfaction": 0.72}],
        accessibility_groups=[],
    )
    assert select_financial_best([financial, fairness]) is financial
    assert select_fairness_best([financial, fairness]) is fairness


def test_compute_price_satisfaction_penalizes_premium_price() -> None:
    assert compute_price_satisfaction(base_price=10.0, actual_price=10.0) == 1.0
    assert abs(compute_price_satisfaction(base_price=10.0, actual_price=11.0) - 0.8) < 1e-9
    assert abs(compute_price_satisfaction(base_price=10.0, actual_price=12.0) - 0.6) < 1e-9
    assert abs(compute_price_satisfaction(base_price=10.0, actual_price=13.0) - 0.6) < 1e-9


def test_profit_rate_constraint_is_bounded_between_zero_and_eight_percent() -> None:
    assert meets_profit_rate_constraint(net_profit=0.0, total_cost=100.0)
    assert meets_profit_rate_constraint(net_profit=8.0, total_cost=100.0)
    assert not meets_profit_rate_constraint(net_profit=-1.0, total_cost=100.0)
    assert not meets_profit_rate_constraint(net_profit=9.0, total_cost=100.0)


def test_fixed_point_converged_uses_max_absolute_difference() -> None:
    old = {"A": 0.80, "B": 0.75}
    new = {"A": 0.80001, "B": 0.75002}
    assert fixed_point_converged(old, new, epsilon=1e-3)
    assert not fixed_point_converged(old, new, epsilon=1e-6)


def test_select_primary_and_backup_follows_utility_order() -> None:
    primary, backup = select_primary_and_backup({"E": 0.81, "J": 0.86, "F": 0.79})
    assert primary == "J"
    assert backup == "E"


def test_solve_collaboration_lp_sends_movable_overflow_to_backup() -> None:
    choices = [
        CommunityChoice(
            community="A",
            primary_station="P",
            backup_station="B",
            utility_primary=0.9,
            utility_backup=0.8,
            price_satisfaction_primary=1.0,
            demand_by_service={
                "助餐": 10.0,
                "日间照料": 0.0,
                "上门护理": 0.0,
                "康复理疗": 0.0,
                "助浴": 0.0,
                "紧急救助": 0.0,
            },
        )
    ]
    allocations, station_raw, station_effective = solve_collaboration_lp(
        choices=choices,
        station_capacities={"P": 5.0, "B": 10.0},
    )
    row = allocations[0]
    assert abs(row["primary_load_daily"] - 5.0) < 1e-9
    assert abs(row["overflow_load_daily"] - 5.0) < 1e-9
    assert abs(row["unmet_load_daily"]) < 1e-9
    assert abs(station_raw["P"]["助餐"] - 5.0) < 1e-9
    assert abs(station_raw["B"]["助餐"] - 5.0) < 1e-9
    assert station_effective["B"]["助餐"] > 0


def test_solve_collaboration_lp_keeps_emergency_at_primary_or_unmet() -> None:
    choices = [
        CommunityChoice(
            community="A",
            primary_station="P",
            backup_station="B",
            utility_primary=0.9,
            utility_backup=0.8,
            price_satisfaction_primary=1.0,
            demand_by_service={
                "助餐": 0.0,
                "日间照料": 0.0,
                "上门护理": 0.0,
                "康复理疗": 0.0,
                "助浴": 0.0,
                "紧急救助": 4.0,
            },
        )
    ]
    allocations, station_raw, _station_effective = solve_collaboration_lp(
        choices=choices,
        station_capacities={"P": 2.0, "B": 10.0},
    )
    row = allocations[0]
    assert abs(row["primary_load_daily"] - 2.0) < 1e-9
    assert abs(row["overflow_load_daily"]) < 1e-9
    assert abs(row["unmet_load_daily"] - 2.0) < 1e-9
    assert abs(row["service_satisfaction"] - 0.45) < 1e-9
    assert abs(station_raw["B"]["紧急救助"]) < 1e-9


def run_all_tests() -> None:
    tests = [
        test_enumerate_station_price_profiles_respects_emergency_zero,
        test_enumerate_station_price_profiles_matches_non_emergency_grid,
        test_enumerate_station_price_profiles_uses_reduced_primary_layer,
        test_generate_rescue_price_profiles_only_uplifts_loss_stations,
        test_dual_selectors_can_choose_different_schemes,
        test_compute_price_satisfaction_penalizes_premium_price,
        test_profit_rate_constraint_is_bounded_between_zero_and_eight_percent,
        test_fixed_point_converged_uses_max_absolute_difference,
        test_select_primary_and_backup_follows_utility_order,
        test_solve_collaboration_lp_sends_movable_overflow_to_backup,
        test_solve_collaboration_lp_keeps_emergency_at_primary_or_unmet,
    ]
    for test in tests:
        test()
    print(f"Passed {len(tests)} tests.")


if __name__ == "__main__":
    run_all_tests()
