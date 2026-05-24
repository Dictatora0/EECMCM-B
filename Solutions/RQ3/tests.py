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
import csv


RQ3_DIR = Path(__file__).resolve().parent
RQ3_MAIN_PATH = RQ3_DIR / "3_1.py"
RQ3_SPEC = spec_from_file_location("rq3_main_module", RQ3_MAIN_PATH)
if RQ3_SPEC is None or RQ3_SPEC.loader is None:
    raise RuntimeError(f"Failed to load RQ3 main module from {RQ3_MAIN_PATH}")
RQ3_MAIN = module_from_spec(RQ3_SPEC)
sys.modules[RQ3_SPEC.name] = RQ3_MAIN
RQ3_SPEC.loader.exec_module(RQ3_MAIN)

RQ3_PARETO_REPORT_PATH = RQ3_DIR / "3_2_pareto_report.py"
RQ3_PARETO_SPEC = spec_from_file_location("rq3_pareto_report_module", RQ3_PARETO_REPORT_PATH)
if RQ3_PARETO_SPEC is None or RQ3_PARETO_SPEC.loader is None:
    raise RuntimeError(f"Failed to load RQ3 pareto report module from {RQ3_PARETO_REPORT_PATH}")
RQ3_PARETO = module_from_spec(RQ3_PARETO_SPEC)
sys.modules[RQ3_PARETO_SPEC.name] = RQ3_PARETO
RQ3_PARETO_SPEC.loader.exec_module(RQ3_PARETO)

enumerate_station_price_profiles = RQ3_MAIN.enumerate_station_price_profiles
generate_rescue_price_profiles = RQ3_MAIN.generate_rescue_price_profiles
price_profile_signature = RQ3_MAIN.price_profile_signature
compute_price_satisfaction = RQ3_MAIN.compute_price_satisfaction
meets_profit_rate_constraint = RQ3_MAIN.meets_profit_rate_constraint
fixed_point_converged = RQ3_MAIN.fixed_point_converged
detect_two_cycle_oscillation = RQ3_MAIN.detect_two_cycle_oscillation
detect_short_cycle_oscillation = RQ3_MAIN.detect_short_cycle_oscillation
average_cycle_states = RQ3_MAIN.average_cycle_states
apply_damping = RQ3_MAIN.apply_damping
evaluation_summary_row = RQ3_MAIN.evaluation_summary_row
joint_feasible_solution_exists = RQ3_MAIN.joint_feasible_solution_exists
select_primary_and_backup = RQ3_MAIN.select_primary_and_backup
solve_collaboration_lp = RQ3_MAIN.solve_collaboration_lp
CommunityChoice = RQ3_MAIN.CommunityChoice
CommunityStationChoiceCache = RQ3_MAIN.CommunityStationChoiceCache
PriceEvaluation = RQ3_MAIN.PriceEvaluation
IterationRecord = RQ3_MAIN.IterationRecord
select_financial_best = RQ3_MAIN.select_financial_best
satisfaction_best_selector = RQ3_MAIN.select_satisfaction_best
sort_price_evaluations = RQ3_MAIN.sort_price_evaluations
apply_targeted_subsidy_policy = RQ3_MAIN.apply_targeted_subsidy_policy
compute_equity_metrics = RQ3_MAIN.compute_equity_metrics
assign_pareto_ranks = RQ3_MAIN.assign_pareto_ranks
enumerate_service_level_price_vectors = RQ3_MAIN.enumerate_service_level_price_vectors
service_level_price_profile = RQ3_MAIN.service_level_price_profile
build_community_choices = RQ3_MAIN.build_community_choices
compute_station_profit_compliance = RQ3_MAIN.compute_station_profit_compliance
prune_station_candidates = RQ3_MAIN.prune_station_candidates
is_joint_feasible_service_level = RQ3_MAIN.is_joint_feasible_service_level
build_rq3_inputs_for_budget_scenario = RQ3_MAIN.build_rq3_inputs_for_budget_scenario
expanded_search_level_settings = RQ3_MAIN.expanded_search_level_settings
prune_station_candidates_expanded = RQ3_MAIN.prune_station_candidates_expanded
compose_expanded_global_profiles = RQ3_MAIN.compose_expanded_global_profiles
run_service_level_pricing_expanded_search = RQ3_MAIN.run_service_level_pricing_expanded_search
pareto_representative_rows = RQ3_PARETO.representative_rows
pareto_write_paper_notes = RQ3_PARETO.write_paper_notes


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
        satisfaction_compliant=1,
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
        satisfaction_compliant=0,
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
        satisfaction_compliant=1,
        low_income_service_satisfaction=0.78,
        low_income_served_coverage=0.9,
        iteration_trace=[IterationRecord(1, 0.01, 0.82, 0, 800.0)],
        station_financials=[{"station_community": "A", "profit_rate": -0.03}],
        community_results=[{"community": "A", "service_satisfaction": 0.72}],
        accessibility_groups=[],
    )
    assert select_financial_best([financial, fairness]) is financial
    assert satisfaction_best_selector([financial, fairness]) is fairness


def test_price_evaluation_legacy_fairness_property_remains_readable() -> None:
    profile = {
        "A": {"助餐": 10.0, "日间照料": 10.0, "上门护理": 10.0, "康复理疗": 10.0, "助浴": 10.0, "紧急救助": 0.0},
    }
    item = PriceEvaluation(
        station_prices=profile,
        iteration_count=1,
        converged=1,
        average_service_satisfaction=0.8,
        minimum_service_satisfaction=0.7,
        vulnerable_service_satisfaction=0.75,
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
        satisfaction_compliant=1,
        low_income_service_satisfaction=0.72,
        low_income_served_coverage=0.9,
        iteration_trace=[IterationRecord(1, 0.0, 0.8, 1, 1000.0, 0)],
        station_financials=[{"station_community": "A", "profit_rate": 0.04}],
        community_results=[{"community": "A", "service_satisfaction": 0.7}],
        accessibility_groups=[],
    )
    assert item.satisfaction_compliant == 1
    assert item.fair_satisfaction_compliant == 1


def test_evaluation_summary_row_accepts_legacy_fairness_only_stub() -> None:
    class StubEval:
        station_prices = {"A": {"助餐": 10.0, "日间照料": 10.0, "上门护理": 10.0, "康复理疗": 10.0, "助浴": 10.0, "紧急救助": 0.0}}
        subsidy_policy_label = "none"
        pareto_rank = 1
        iteration_count = 1
        converged = 1
        damping_used = 0
        profit_compliant = 1
        fair_satisfaction_compliant = 1
        feasible_station_count = 1
        average_service_satisfaction = 0.8
        minimum_service_satisfaction = 0.7
        average_service_access_performance = 0.6
        minimum_service_access_performance = 0.5
        vulnerable_service_satisfaction = 0.75
        low_income_service_satisfaction = 0.72
        low_income_served_coverage = 0.9
        served_population_coverage = 0.85
        weighted_served_population_coverage = 0.8
        served_demand_coverage = 0.78
        gini_access = 0.1
        theil_access = 0.02
        max_min_gap = 0.2
        annual_government_subsidy = 1000.0
        annual_service_revenue = 10000.0
        annual_direct_cost = 9000.0
        annual_fixed_cost = 1000.0
        annual_depreciation = 500.0
        annual_total_cost = 10500.0
        annual_net_profit_before_subsidy = -500.0
        annual_net_profit_after_subsidy = 500.0
        annual_net_profit = 500.0
        profit_rate = 500.0 / 10500.0

    row = evaluation_summary_row(StubEval())
    assert row["satisfaction_compliant"] == 1
    assert row["fair_satisfaction_compliant"] == 1


def test_select_satisfaction_best_prefers_converged_candidate() -> None:
    profile = {
        "A": {"助餐": 10.0, "日间照料": 10.0, "上门护理": 10.0, "康复理疗": 10.0, "助浴": 10.0, "紧急救助": 0.0},
    }
    unconverged = PriceEvaluation(
        station_prices=profile,
        iteration_count=30,
        converged=0,
        average_service_satisfaction=0.9,
        minimum_service_satisfaction=0.85,
        average_service_access_performance=0.85,
        minimum_service_access_performance=0.8,
        vulnerable_service_satisfaction=0.86,
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
        satisfaction_compliant=1,
        low_income_service_satisfaction=0.84,
        low_income_served_coverage=1.0,
        iteration_trace=[IterationRecord(1, 0.1, 0.9, 1, 1000.0)],
        station_financials=[{"station_community": "A", "profit_rate": 0.04}],
        community_results=[{"community": "A", "service_satisfaction": 0.85, "service_access_performance": 0.8}],
        accessibility_groups=[],
    )
    converged = PriceEvaluation(
        station_prices=profile,
        iteration_count=3,
        converged=1,
        average_service_satisfaction=0.8,
        minimum_service_satisfaction=0.75,
        average_service_access_performance=0.7,
        minimum_service_access_performance=0.68,
        vulnerable_service_satisfaction=0.76,
        annual_government_subsidy=900.0,
        annual_service_revenue=10000.0,
        annual_direct_cost=9000.0,
        annual_fixed_cost=1000.0,
        annual_depreciation=500.0,
        annual_net_profit_before_subsidy=-500.0,
        annual_net_profit_after_subsidy=300.0,
        annual_net_profit=300.0,
        feasible_station_count=1,
        profit_compliant=1,
        satisfaction_compliant=1,
        low_income_service_satisfaction=0.75,
        low_income_served_coverage=1.0,
        iteration_trace=[IterationRecord(1, 0.0, 0.8, 1, 900.0)],
        station_financials=[{"station_community": "A", "profit_rate": 0.03}],
        community_results=[{"community": "A", "service_satisfaction": 0.75, "service_access_performance": 0.68}],
        accessibility_groups=[],
    )
    assert satisfaction_best_selector([unconverged, converged]) is converged


def test_compute_price_satisfaction_penalizes_premium_price() -> None:
    assert compute_price_satisfaction(base_price=10.0, actual_price=10.0) == 1.0
    assert abs(compute_price_satisfaction(base_price=10.0, actual_price=11.0) - 0.9) < 1e-9
    assert abs(compute_price_satisfaction(base_price=10.0, actual_price=12.0) - 0.75) < 1e-9
    assert abs(compute_price_satisfaction(base_price=10.0, actual_price=13.0) - 0.6) < 1e-9
    assert abs(compute_price_satisfaction(base_price=10.0, actual_price=20.0) - 0.6) < 1e-9


def test_enumerate_service_level_price_vectors_keeps_emergency_zero() -> None:
    vectors = enumerate_service_level_price_vectors(
        {
            "助餐": [10.0, 11.0],
            "日间照料": [20.0],
            "上门护理": [30.0],
            "康复理疗": [40.0],
            "助浴": [50.0],
            "紧急救助": [0.0],
        }
    )
    assert vectors
    assert all(vector["紧急救助"] == 0.0 for vector in vectors)


def test_service_level_price_profile_uses_independent_service_prices() -> None:
    inputs = make_stub_inputs()
    prices = service_level_price_profile(
        station_names=["A"],
        service_prices_by_station={"A": {"助餐": 10.0, "日间照料": 22.0, "上门护理": 36.0, "康复理疗": 40.0, "助浴": 55.0, "紧急救助": 0.0}},
    )
    assert prices["A"]["助餐"] == 10.0
    assert prices["A"]["日间照料"] == 22.0
    assert prices["A"]["上门护理"] == 36.0
    assert prices["A"]["紧急救助"] == 0.0
    del inputs


def test_compute_station_profit_compliance_is_station_level_only() -> None:
    station_rows = [
        {"station_community": "A", "profit_rate": 0.03},
        {"station_community": "B", "profit_rate": 0.07},
        {"station_community": "C", "profit_rate": -0.01},
    ]
    assert compute_station_profit_compliance(station_rows) == 0
    station_rows[-1]["profit_rate"] = 0.02
    assert compute_station_profit_compliance(station_rows) == 1


def test_prune_station_candidates_caps_candidate_count() -> None:
    candidates = []
    for idx in range(50):
        candidates.append(
            {
                "station": "A",
                "selected_prices_by_service": f"candidate_{idx}",
                "station_average_service_satisfaction": 0.9 - idx * 0.001,
                "station_minimum_service_access_performance": 0.8 - idx * 0.001,
                "profit_rate": 0.04 + (idx - 25) * 0.0005,
                "profit_compliant": 1 if idx < 40 else 0,
                "break_even_gap": float(idx),
                "over_8pct_excess": max(0.0, 0.09 - 0.04),
            }
        )
    kept = prune_station_candidates(candidates, max_candidates_per_station=12, top_k_satisfaction=4, top_k_min_access=4, top_k_profit_center=4)
    assert len(kept) <= 12
    assert len({row["selected_prices_by_service"] for row in kept}) == len(kept)


def test_joint_feasible_service_level_requires_stationwise_profit() -> None:
    feasible_row = {
        "converged": 1,
        "all_station_profit_compliant": 1,
        "minimum_service_satisfaction": 0.7,
    }
    infeasible_row = {
        "converged": 1,
        "all_station_profit_compliant": 0,
        "minimum_service_satisfaction": 0.95,
    }
    assert is_joint_feasible_service_level(feasible_row, min_service_access_threshold=0.6)
    assert not is_joint_feasible_service_level(infeasible_row, min_service_access_threshold=0.6)


def test_service_level_output_files_exist_if_generated() -> None:
    expected = [
        "3_5_satisfaction_objective_station_candidates.csv",
        "3_5_satisfaction_objective_global_candidates.csv",
        "3_5_satisfaction_objective_summary.csv",
        "3_5_satisfaction_objective_by_station.csv",
        "3_5_satisfaction_objective_community_satisfaction.csv",
        "3_5_satisfaction_objective_model_comparison.csv",
        "3_5_satisfaction_objective_notes.md",
    ]
    output_dir = Path(__file__).resolve().parent / "outputs"
    for name in expected:
        path = output_dir / name
        if path.suffix == ".csv" and path.exists():
            rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
            assert rows, f"{name} should not be empty"
        elif path.suffix == ".md" and path.exists():
            assert path.read_text(encoding="utf-8").strip(), f"{name} should not be empty"


def test_generated_service_level_station_financials_respect_subsidy_caps_if_present() -> None:
    path = Path(__file__).resolve().parent / "outputs" / "3_5_satisfaction_objective_by_station.csv"
    if not path.exists():
        return
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
    cap_by_scale = {"小型": 1000.0 * 365.0, "中型": 1800.0 * 365.0, "大型": 2600.0 * 365.0}
    for row in rows:
        assert float(row["annual_government_subsidy"]) <= cap_by_scale[row["scale"]] + 1e-6
        if int(row["profit_compliant"]) == 1:
            rate = float(row["profit_rate"])
            assert 0.0 - 1e-9 <= rate <= 0.08 + 1e-9


def test_generated_service_level_community_bounds_if_present() -> None:
    path = Path(__file__).resolve().parent / "outputs" / "3_5_satisfaction_objective_community_satisfaction.csv"
    if not path.exists():
        return
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
    for row in rows:
        service_satisfaction = float(row["service_satisfaction"])
        access = float(row["service_access_performance"])
        assert 0.0 - 1e-9 <= access <= 1.0 + 1e-9
        if service_satisfaction > 1e-12:
            assert 0.6 - 1e-9 <= service_satisfaction <= 1.0 + 1e-9


def test_generated_service_level_summary_tracks_stationwise_profit_if_present() -> None:
    summary_path = Path(__file__).resolve().parent / "outputs" / "3_5_satisfaction_objective_summary.csv"
    station_path = Path(__file__).resolve().parent / "outputs" / "3_5_satisfaction_objective_by_station.csv"
    if not summary_path.exists() or not station_path.exists():
        return
    summary_rows = list(csv.DictReader(summary_path.open(encoding="utf-8-sig")))
    station_rows = list(csv.DictReader(station_path.open(encoding="utf-8-sig")))
    station_ok_by_scenario = {}
    for row in station_rows:
        station_ok_by_scenario.setdefault(row["scenario"], True)
        station_ok_by_scenario[row["scenario"]] = station_ok_by_scenario[row["scenario"]] and int(row["profit_compliant"]) == 1
    for row in summary_rows:
        if row["scheme_label"] != "financial_best":
            continue
        expected = int(station_ok_by_scenario.get(row["scenario"], False))
        assert int(row["all_station_profit_compliant"]) == expected


def test_expanded_search_level_settings_monotonic() -> None:
    light = expanded_search_level_settings("light")
    medium = expanded_search_level_settings("medium")
    heavy = expanded_search_level_settings("heavy")
    assert light["max_candidates_per_station"] < medium["max_candidates_per_station"] < heavy["max_candidates_per_station"]
    assert light["max_global_combinations"] < medium["max_global_combinations"] < heavy["max_global_combinations"]


def test_build_rq3_inputs_for_budget_scenario_keeps_s0_and_s4_layouts_distinct() -> None:
    try:
        s0 = build_rq3_inputs_for_budget_scenario("S0", 120.0)
        s4 = build_rq3_inputs_for_budget_scenario("S4", 140.0)
    except (AssertionError, FileNotFoundError) as exc:
        if "Missing rq1_high_precision_metadata.json" in str(exc) or "2_1_best_scheme_summary.csv" in str(exc):
            return
        raise
    s0_stations = [station.station_community for station in s0.q2_stations]
    s4_stations = [station.station_community for station in s4.q2_stations]
    assert s0.q2_summary.build_cost_wan <= 120.0 + 1e-9
    assert s4.q2_summary.build_cost_wan <= 140.0 + 1e-9
    assert s0.q2_summary.scheme_detail == ";".join(f"{station}-" + next(item.scale for item in s0.q2_stations if item.station_community == station) for station in s0_stations)
    assert s4.q2_summary.scheme_detail == ";".join(f"{station}-" + next(item.scale for item in s4.q2_stations if item.station_community == station) for station in s4_stations)
    assert s0.q2_summary.scheme_detail != ""
    assert s4.q2_summary.scheme_detail != ""
    assert s0_stations != s4_stations


def test_prune_station_candidates_expanded_keeps_boundary_and_diverse_rows() -> None:
    candidates = [
        {
            "station": "G",
            "selected_prices_by_service": "助餐:10|日间照料:20|上门护理:30|康复理疗:40|助浴:50|紧急救助:0",
            "selected_price_satisfaction_by_service": "助餐:1.00|日间照料:1.00|上门护理:1.00|康复理疗:1.00|助浴:1.00|紧急救助:1.00",
            "station_average_service_satisfaction": 0.84,
            "station_minimum_service_access_performance": 0.72,
            "profit_rate": -0.01,
            "profit_compliant": 0,
            "break_even_gap": 1000.0,
            "over_8pct_excess": 0.0,
        },
        {
            "station": "G",
            "selected_prices_by_service": "助餐:11|日间照料:22|上门护理:33|康复理疗:44|助浴:55|紧急救助:0",
            "selected_price_satisfaction_by_service": "助餐:0.90|日间照料:0.90|上门护理:0.90|康复理疗:0.90|助浴:0.90|紧急救助:1.00",
            "station_average_service_satisfaction": 0.81,
            "station_minimum_service_access_performance": 0.71,
            "profit_rate": 0.0005,
            "profit_compliant": 1,
            "break_even_gap": 0.0,
            "over_8pct_excess": 0.0,
        },
        {
            "station": "G",
            "selected_prices_by_service": "助餐:12|日间照料:24|上门护理:36|康复理疗:48|助浴:60|紧急救助:0",
            "selected_price_satisfaction_by_service": "助餐:0.75|日间照料:0.75|上门护理:0.75|康复理疗:0.75|助浴:0.75|紧急救助:1.00",
            "station_average_service_satisfaction": 0.78,
            "station_minimum_service_access_performance": 0.70,
            "profit_rate": 0.079,
            "profit_compliant": 1,
            "break_even_gap": 0.0,
            "over_8pct_excess": 0.0,
        },
        {
            "station": "G",
            "selected_prices_by_service": "助餐:13|日间照料:26|上门护理:39|康复理疗:52|助浴:65|紧急救助:0",
            "selected_price_satisfaction_by_service": "助餐:0.60|日间照料:0.60|上门护理:0.60|康复理疗:0.60|助浴:0.60|紧急救助:1.00",
            "station_average_service_satisfaction": 0.74,
            "station_minimum_service_access_performance": 0.66,
            "profit_rate": 0.095,
            "profit_compliant": 0,
            "break_even_gap": 0.0,
            "over_8pct_excess": 0.015,
        },
    ]
    kept = prune_station_candidates_expanded(
        candidates,
        station_name="G",
        max_candidates_per_station=4,
        keep_near_boundary=True,
    )
    kept_rates = {round(float(row["profit_rate"]), 4) for row in kept}
    assert len(kept) <= 4
    assert 0.0005 in kept_rates
    assert -0.01 in kept_rates
    assert 0.079 in kept_rates
    assert 0.095 in kept_rates


def test_compose_expanded_global_profiles_is_reproducible_with_seed() -> None:
    kept = {
        "A": [
            {"station": "A", "selected_prices_by_service": "助餐:10|日间照料:20|上门护理:30|康复理疗:40|助浴:50|紧急救助:0", "profit_rate": 0.01, "profit_compliant": 1, "station_average_service_satisfaction": 0.8, "station_minimum_service_access_performance": 0.7, "break_even_gap": 0.0, "over_8pct_excess": 0.0},
            {"station": "A", "selected_prices_by_service": "助餐:11|日间照料:22|上门护理:33|康复理疗:44|助浴:55|紧急救助:0", "profit_rate": 0.07, "profit_compliant": 1, "station_average_service_satisfaction": 0.79, "station_minimum_service_access_performance": 0.69, "break_even_gap": 0.0, "over_8pct_excess": 0.0},
        ],
        "B": [
            {"station": "B", "selected_prices_by_service": "助餐:10|日间照料:20|上门护理:30|康复理疗:40|助浴:50|紧急救助:0", "profit_rate": -0.01, "profit_compliant": 0, "station_average_service_satisfaction": 0.82, "station_minimum_service_access_performance": 0.68, "break_even_gap": 100.0, "over_8pct_excess": 0.0},
            {"station": "B", "selected_prices_by_service": "助餐:12|日间照料:24|上门护理:36|康复理疗:48|助浴:60|紧急救助:0", "profit_rate": 0.02, "profit_compliant": 1, "station_average_service_satisfaction": 0.76, "station_minimum_service_access_performance": 0.65, "break_even_gap": 0.0, "over_8pct_excess": 0.0},
        ],
    }
    first = compose_expanded_global_profiles(
        kept_by_station=kept,
        scenario_code="S0",
        search_level="light",
        max_global_combinations=10,
        keep_near_boundary=True,
        random_seed=7,
    )
    second = compose_expanded_global_profiles(
        kept_by_station=kept,
        scenario_code="S0",
        search_level="light",
        max_global_combinations=10,
        keep_near_boundary=True,
        random_seed=7,
    )
    assert first == second


def test_expanded_search_output_files_exist_if_generated() -> None:
    expected = [
        "3_5_expanded_search_summary.csv",
        "3_5_expanded_search_global_candidates.csv",
        "3_5_expanded_search_by_station.csv",
        "3_5_expanded_search_notes.md",
    ]
    output_dir = Path(__file__).resolve().parent / "outputs"
    for name in expected:
        path = output_dir / name
        if path.suffix == ".csv" and path.exists():
            rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
            assert rows, f"{name} should not be empty"
        elif path.suffix == ".md" and path.exists():
            assert path.read_text(encoding="utf-8").strip(), f"{name} should not be empty"


def test_generated_expanded_search_outputs_respect_stationwise_rules_if_present() -> None:
    output_dir = Path(__file__).resolve().parent / "outputs"
    global_path = output_dir / "3_5_expanded_search_global_candidates.csv"
    station_path = output_dir / "3_5_expanded_search_by_station.csv"
    if not global_path.exists() or not station_path.exists():
        return
    global_rows = list(csv.DictReader(global_path.open(encoding="utf-8-sig")))
    station_rows = list(csv.DictReader(station_path.open(encoding="utf-8-sig")))
    cap_by_scale = {"小型": 1000.0 * 365.0, "中型": 1800.0 * 365.0, "大型": 2600.0 * 365.0}
    by_candidate = {}
    for row in station_rows:
        key = (row["scenario"], row["search_level"], row["candidate_id"])
        by_candidate.setdefault(key, []).append(row)
        prices = row["selected_prices_by_service"]
        assert "紧急救助:0" in prices or "紧急救助:0.0" in prices
        assert float(row["annual_government_subsidy"]) <= cap_by_scale[row["scale"]] + 1e-6
        if int(row["profit_compliant"]) == 1:
            assert 0.0 - 1e-9 <= float(row["profit_rate"]) <= 0.08 + 1e-9
    for row in global_rows:
        key = (row["scenario"], row["search_level"], row["candidate_id"])
        station_set = by_candidate.get(key, [])
        stationwise = int(all(0.0 - 1e-9 <= float(item["profit_rate"]) <= 0.08 + 1e-9 for item in station_set)) if station_set else 0
        assert int(row["all_station_profit_compliant"]) == stationwise
        if int(row["joint_feasible"]) == 1:
            assert int(row["converged"]) == 1
            assert int(row["all_station_profit_compliant"]) == 1


def test_expanded_search_run_can_skip_existing_main_outputs() -> None:
    result = run_service_level_pricing_expanded_search(
        scenarios=(),
        search_levels=("light",),
        price_grid_level="basic",
        max_candidates_per_station=4,
        max_global_combinations=4,
        keep_near_boundary=True,
        random_seed=5,
        write_outputs=False,
    )
    assert "summary_rows" in result
    assert result["summary_rows"] == []


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


def test_detect_two_cycle_oscillation_finds_simple_abab_pattern() -> None:
    history = [
        {"A": 0.8, "B": 0.6},
        {"A": 0.7, "B": 0.5},
        {"A": 0.8, "B": 0.6},
        {"A": 0.7, "B": 0.5},
    ]
    assert detect_two_cycle_oscillation(history, tolerance=1e-9)


def test_detect_short_cycle_oscillation_finds_ababc_cycle() -> None:
    history = [
        {"A": 0.80, "B": 0.60},
        {"A": 0.90, "B": 0.70},
        {"A": 0.85, "B": 0.65},
        {"A": 0.80, "B": 0.60},
        {"A": 0.90, "B": 0.70},
        {"A": 0.85, "B": 0.65},
    ]
    assert detect_short_cycle_oscillation(history, max_cycle_length=3, tolerance=1e-9) == 3


def test_average_cycle_states_returns_componentwise_mean() -> None:
    states = [
        {"A": 0.80, "B": 0.60},
        {"A": 0.90, "B": 0.70},
        {"A": 0.85, "B": 0.65},
    ]
    averaged = average_cycle_states(states)
    assert abs(averaged["A"] - 0.85) < 1e-9
    assert abs(averaged["B"] - 0.65) < 1e-9


def test_apply_damping_blends_candidate_with_previous_state() -> None:
    damped = apply_damping(
        previous={"A": 0.8, "B": 0.4},
        candidate={"A": 0.6, "B": 0.8},
        damping_lambda=0.5,
    )
    assert abs(damped["A"] - 0.7) < 1e-9
    assert abs(damped["B"] - 0.6) < 1e-9


def test_select_primary_and_backup_follows_utility_order() -> None:
    primary, backup = select_primary_and_backup({"E": 0.81, "J": 0.86, "F": 0.79})
    assert primary == "J"
    assert backup == "E"


def test_build_community_choices_breaks_ties_by_distance_then_station_name() -> None:
    demand = {
        "助餐": 10.0,
        "日间照料": 0.0,
        "上门护理": 0.0,
        "康复理疗": 0.0,
        "助浴": 0.0,
        "紧急救助": 0.0,
    }
    choices = build_community_choices(
        choice_cache={
            "C": {
                "B": CommunityStationChoiceCache(
                    distance_satisfaction=0.9,
                    demand_by_service=demand,
                    price_satisfaction=0.8,
                    distance_meters=350.0,
                ),
                "A": CommunityStationChoiceCache(
                    distance_satisfaction=0.9,
                    demand_by_service=demand,
                    price_satisfaction=0.8,
                    distance_meters=350.0,
                ),
                "D": CommunityStationChoiceCache(
                    distance_satisfaction=0.9,
                    demand_by_service=demand,
                    price_satisfaction=0.8,
                    distance_meters=450.0,
                ),
            }
        },
        response_by_station={"A": 1.0, "B": 1.0, "D": 1.0},
    )
    assert len(choices) == 1
    assert choices[0].primary_station == "A"
    assert choices[0].backup_station is None


def test_solve_collaboration_lp_uses_single_station_and_leaves_unmet() -> None:
    choices = [
        CommunityChoice(
            community="A",
            primary_station="P",
            backup_station="B",
            utility_primary=0.9,
            utility_backup=0.8,
            price_satisfaction_primary=1.0,
            price_satisfaction_backup=0.9,
            distance_satisfaction_primary=1.0,
            distance_satisfaction_backup=0.9,
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
    assert abs(row["overflow_load_daily"]) < 1e-9
    assert abs(row["unmet_load_daily"] - 5.0) < 1e-9
    assert abs(station_raw["P"]["助餐"] - 5.0) < 1e-9
    assert abs(station_raw["B"]["助餐"]) < 1e-9
    assert abs(station_effective["B"]["助餐"]) < 1e-9


def test_solve_collaboration_lp_scales_all_selected_communities_by_same_station_ratio() -> None:
    choices = [
        CommunityChoice(
            community="A",
            primary_station="P",
            backup_station=None,
            utility_primary=0.9,
            utility_backup=0.0,
            price_satisfaction_primary=1.0,
            price_satisfaction_backup=0.0,
            distance_satisfaction_primary=1.0,
            distance_satisfaction_backup=0.0,
            demand_by_service={
                "助餐": 6.0,
                "日间照料": 0.0,
                "上门护理": 0.0,
                "康复理疗": 0.0,
                "助浴": 0.0,
                "紧急救助": 0.0,
            },
        ),
        CommunityChoice(
            community="B",
            primary_station="P",
            backup_station=None,
            utility_primary=0.9,
            utility_backup=0.0,
            price_satisfaction_primary=1.0,
            price_satisfaction_backup=0.0,
            distance_satisfaction_primary=1.0,
            distance_satisfaction_backup=0.0,
            demand_by_service={
                "助餐": 4.0,
                "日间照料": 0.0,
                "上门护理": 0.0,
                "康复理疗": 0.0,
                "助浴": 0.0,
                "紧急救助": 0.0,
            },
        ),
    ]
    allocations, station_raw, _station_effective = solve_collaboration_lp(
        choices=choices,
        station_capacities={"P": 5.0},
    )
    row_map = {row["community"]: row for row in allocations}
    assert abs(row_map["A"]["primary_load_daily"] - 3.0) < 1e-9
    assert abs(row_map["A"]["unmet_load_daily"] - 3.0) < 1e-9
    assert abs(row_map["A"]["demand_service_ratio"] - 0.5) < 1e-9
    assert abs(row_map["B"]["primary_load_daily"] - 2.0) < 1e-9
    assert abs(row_map["B"]["unmet_load_daily"] - 2.0) < 1e-9
    assert abs(row_map["B"]["demand_service_ratio"] - 0.5) < 1e-9
    assert abs(station_raw["P"]["助餐"] - 5.0) < 1e-9


def test_evaluation_summary_row_reports_joint_feasibility_and_financial_gap() -> None:
    profile = {
        "A": {"助餐": 10.0, "日间照料": 10.0, "上门护理": 10.0, "康复理疗": 10.0, "助浴": 10.0, "紧急救助": 0.0},
    }
    item = PriceEvaluation(
        station_prices=profile,
        iteration_count=4,
        converged=0,
        average_service_satisfaction=0.82,
        minimum_service_satisfaction=0.72,
        average_service_access_performance=0.58,
        minimum_service_access_performance=0.41,
        vulnerable_service_satisfaction=0.80,
        annual_government_subsidy=800.0,
        annual_service_revenue=9000.0,
        annual_direct_cost=8800.0,
        annual_fixed_cost=1000.0,
        annual_depreciation=500.0,
        annual_total_cost=10300.0,
        annual_net_profit_before_subsidy=-1300.0,
        annual_net_profit_after_subsidy=-500.0,
        annual_net_profit=-500.0,
        profit_rate=-500.0 / 10300.0,
        feasible_station_count=0,
        profit_compliant=0,
        satisfaction_compliant=1,
        low_income_service_satisfaction=0.78,
        low_income_served_coverage=0.9,
        weighted_served_population_coverage=0.66,
        served_demand_coverage=0.7,
        damping_used=1,
        iteration_trace=[IterationRecord(1, 0.01, 0.82, 0, 800.0, 1)],
        station_financials=[{"station_community": "A", "profit_rate": -0.03}],
        community_results=[{"community": "A", "service_satisfaction": 0.72, "service_access_performance": 0.41}],
        accessibility_groups=[],
    )
    row = evaluation_summary_row(item)
    assert row["minimum_service_satisfaction"] == 0.72
    assert row["minimum_service_access_performance"] == 0.41
    assert row["damping_used"] == 1
    assert row["profit_compliant"] == 0
    assert row["financial_gap_to_break_even"] == 500.0


def test_joint_feasible_solution_requires_profit_fairness_and_convergence() -> None:
    profile = {
        "A": {"助餐": 10.0, "日间照料": 10.0, "上门护理": 10.0, "康复理疗": 10.0, "助浴": 10.0, "紧急救助": 0.0},
    }
    ok = PriceEvaluation(
        station_prices=profile,
        iteration_count=3,
        converged=1,
        average_service_satisfaction=0.82,
        minimum_service_satisfaction=0.72,
        average_service_access_performance=0.76,
        minimum_service_access_performance=0.7,
        vulnerable_service_satisfaction=0.80,
        annual_government_subsidy=800.0,
        annual_service_revenue=9000.0,
        annual_direct_cost=8800.0,
        annual_fixed_cost=1000.0,
        annual_depreciation=500.0,
        annual_total_cost=10300.0,
        annual_net_profit_before_subsidy=-300.0,
        annual_net_profit_after_subsidy=300.0,
        annual_net_profit=300.0,
        profit_rate=300.0 / 10300.0,
        feasible_station_count=1,
        profit_compliant=1,
        satisfaction_compliant=1,
        low_income_service_satisfaction=0.78,
        low_income_served_coverage=0.9,
        weighted_served_population_coverage=0.66,
        served_demand_coverage=0.7,
        damping_used=0,
        iteration_trace=[IterationRecord(1, 0.01, 0.82, 1, 800.0, 0)],
        station_financials=[{"station_community": "A", "profit_rate": 0.03}],
        community_results=[{"community": "A", "service_satisfaction": 0.72, "service_access_performance": 0.7}],
        accessibility_groups=[],
    )
    bad = PriceEvaluation(
        station_prices=profile,
        iteration_count=30,
        converged=0,
        average_service_satisfaction=0.83,
        minimum_service_satisfaction=0.8,
        average_service_access_performance=0.79,
        minimum_service_access_performance=0.75,
        vulnerable_service_satisfaction=0.81,
        annual_government_subsidy=1200.0,
        annual_service_revenue=9200.0,
        annual_direct_cost=9100.0,
        annual_fixed_cost=1000.0,
        annual_depreciation=500.0,
        annual_total_cost=10600.0,
        annual_net_profit_before_subsidy=-1400.0,
        annual_net_profit_after_subsidy=-200.0,
        annual_net_profit=-200.0,
        profit_rate=-200.0 / 10600.0,
        feasible_station_count=0,
        profit_compliant=0,
        satisfaction_compliant=1,
        low_income_service_satisfaction=0.8,
        low_income_served_coverage=0.91,
        weighted_served_population_coverage=0.7,
        served_demand_coverage=0.71,
        damping_used=1,
        iteration_trace=[IterationRecord(1, 0.01, 0.83, 0, 1200.0, 1)],
        station_financials=[{"station_community": "A", "profit_rate": -0.02}],
        community_results=[{"community": "A", "service_satisfaction": 0.8, "service_access_performance": 0.75}],
        accessibility_groups=[],
    )
    assert joint_feasible_solution_exists([ok, bad], min_service_access_threshold=0.70)
    assert not joint_feasible_solution_exists([bad], min_service_access_threshold=0.0)


def test_sort_price_evaluations_prefers_higher_average_service_satisfaction_for_main_goal() -> None:
    profile = {
        "A": {"助餐": 10.0, "日间照料": 10.0, "上门护理": 10.0, "康复理疗": 10.0, "助浴": 10.0, "紧急救助": 0.0},
    }
    high_satisfaction = PriceEvaluation(
        station_prices=profile,
        iteration_count=5,
        converged=1,
        average_service_satisfaction=0.88,
        minimum_service_satisfaction=0.72,
        average_service_access_performance=0.61,
        minimum_service_access_performance=0.40,
        vulnerable_service_satisfaction=0.86,
        annual_government_subsidy=900.0,
        annual_service_revenue=9000.0,
        annual_direct_cost=8600.0,
        annual_fixed_cost=1000.0,
        annual_depreciation=500.0,
        annual_total_cost=10100.0,
        annual_net_profit_before_subsidy=-1100.0,
        annual_net_profit_after_subsidy=-200.0,
        annual_net_profit=-200.0,
        profit_rate=-200.0 / 10100.0,
        feasible_station_count=0,
        profit_compliant=0,
        satisfaction_compliant=1,
        low_income_service_satisfaction=0.84,
        low_income_served_coverage=0.88,
        weighted_served_population_coverage=0.70,
        served_demand_coverage=0.74,
        damping_used=0,
        iteration_trace=[IterationRecord(1, 0.0, 0.88, 0, 900.0, 0)],
        station_financials=[{"station_community": "A", "profit_rate": -0.02}],
        community_results=[{"community": "A", "service_satisfaction": 0.72, "service_access_performance": 0.40}],
        accessibility_groups=[],
        gini_access=0.20,
        theil_access=0.03,
        max_min_gap=0.25,
    )
    low_satisfaction_but_high_access = PriceEvaluation(
        station_prices=profile,
        iteration_count=4,
        converged=1,
        average_service_satisfaction=0.81,
        minimum_service_satisfaction=0.70,
        average_service_access_performance=0.82,
        minimum_service_access_performance=0.75,
        vulnerable_service_satisfaction=0.80,
        annual_government_subsidy=950.0,
        annual_service_revenue=9200.0,
        annual_direct_cost=8700.0,
        annual_fixed_cost=1000.0,
        annual_depreciation=500.0,
        annual_total_cost=10200.0,
        annual_net_profit_before_subsidy=-1000.0,
        annual_net_profit_after_subsidy=-50.0,
        annual_net_profit=-50.0,
        profit_rate=-50.0 / 10200.0,
        feasible_station_count=0,
        profit_compliant=0,
        satisfaction_compliant=1,
        low_income_service_satisfaction=0.79,
        low_income_served_coverage=0.90,
        weighted_served_population_coverage=0.84,
        served_demand_coverage=0.86,
        damping_used=0,
        iteration_trace=[IterationRecord(1, 0.0, 0.81, 0, 950.0, 0)],
        station_financials=[{"station_community": "A", "profit_rate": -0.005}],
        community_results=[{"community": "A", "service_satisfaction": 0.70, "service_access_performance": 0.75}],
        accessibility_groups=[],
        gini_access=0.10,
        theil_access=0.01,
        max_min_gap=0.10,
    )
    ranked = sort_price_evaluations([low_satisfaction_but_high_access, high_satisfaction])
    assert ranked[0] is high_satisfaction


def test_targeted_subsidy_policy_is_disabled_in_mainline_model() -> None:
    subsidy = apply_targeted_subsidy_policy(
        community="A",
        service="助餐",
        posted_price=20.0,
        low_income_communities={"A"},
        vulnerable_weight=0.6,
        low_income_weight=0.4,
        service_priority={"助餐": 0.5},
        subsidy_budget_per_person=6.0,
        is_vulnerable=True,
    )
    assert subsidy == 0.0


def test_evaluation_summary_row_marks_subsidy_policy_as_none() -> None:
    profile = {
        "A": {"助餐": 10.0, "日间照料": 10.0, "上门护理": 10.0, "康复理疗": 10.0, "助浴": 10.0, "紧急救助": 0.0},
    }
    item = PriceEvaluation(
        station_prices=profile,
        iteration_count=1,
        converged=1,
        average_service_satisfaction=0.8,
        minimum_service_satisfaction=0.7,
        average_service_access_performance=0.7,
        minimum_service_access_performance=0.65,
        vulnerable_service_satisfaction=0.75,
        annual_government_subsidy=1000.0,
        annual_service_revenue=10000.0,
        annual_direct_cost=9000.0,
        annual_fixed_cost=1000.0,
        annual_depreciation=500.0,
        annual_total_cost=10500.0,
        annual_net_profit_before_subsidy=-500.0,
        annual_net_profit_after_subsidy=500.0,
        annual_net_profit=500.0,
        profit_rate=500.0 / 10500.0,
        feasible_station_count=1,
        profit_compliant=1,
        satisfaction_compliant=1,
        low_income_service_satisfaction=0.72,
        low_income_served_coverage=0.9,
        served_population_coverage=0.85,
        weighted_served_population_coverage=0.7,
        served_demand_coverage=0.8,
        damping_used=0,
        iteration_trace=[IterationRecord(1, 0.0, 0.8, 1, 1000.0, 0)],
        station_financials=[{"station_community": "A", "profit_rate": 0.04}],
        community_results=[{"community": "A", "service_satisfaction": 0.7, "service_access_performance": 0.65}],
        accessibility_groups=[],
    )
    row = evaluation_summary_row(item)
    assert row["subsidy_policy"] == "none"
    assert row["served_population_coverage"] == 0.85


def test_equity_metrics_capture_dispersion_and_extremes() -> None:
    metrics = compute_equity_metrics(
        community_rows=[
            {"community": "A", "service_access_performance": 0.9},
            {"community": "B", "service_access_performance": 0.6},
            {"community": "C", "service_access_performance": 0.3},
        ],
        population_weights={"A": 100.0, "B": 100.0, "C": 100.0},
    )
    assert 0.0 <= metrics["gini_access"] <= 1.0
    assert abs(metrics["max_min_gap"] - 0.6) < 1e-9


def test_assign_pareto_ranks_uses_non_dominated_front_layers() -> None:
    profile = {
        "A": {"助餐": 10.0, "日间照料": 10.0, "上门护理": 10.0, "康复理疗": 10.0, "助浴": 10.0, "紧急救助": 0.0},
    }

    def make_item(avg_access: float, profit_rate: float, gini: float) -> PriceEvaluation:
        return PriceEvaluation(
            station_prices=profile,
            iteration_count=1,
            converged=1,
            average_service_satisfaction=avg_access,
            minimum_service_satisfaction=avg_access,
            average_service_access_performance=avg_access,
            minimum_service_access_performance=avg_access,
            vulnerable_service_satisfaction=avg_access,
            annual_government_subsidy=0.0,
            annual_service_revenue=10000.0,
            annual_direct_cost=9000.0,
            annual_fixed_cost=1000.0,
            annual_depreciation=0.0,
            annual_total_cost=10000.0,
            annual_net_profit_before_subsidy=profit_rate * 10000.0,
            annual_net_profit_after_subsidy=profit_rate * 10000.0,
            annual_net_profit=profit_rate * 10000.0,
            profit_rate=profit_rate,
            feasible_station_count=1,
            profit_compliant=1,
            satisfaction_compliant=1,
            low_income_service_satisfaction=avg_access,
            low_income_served_coverage=1.0,
            weighted_served_population_coverage=avg_access,
            served_demand_coverage=avg_access,
            damping_used=0,
            iteration_trace=[IterationRecord(1, 0.0, avg_access, 1, 0.0, 0)],
            station_financials=[{"station_community": "A", "profit_rate": profit_rate}],
            community_results=[{"community": "A", "service_satisfaction": avg_access, "service_access_performance": avg_access}],
            accessibility_groups=[],
            gini_access=gini,
            theil_access=gini,
            max_min_gap=0.0,
        )

    frontier_a = make_item(avg_access=0.80, profit_rate=0.04, gini=0.30)
    frontier_b = make_item(avg_access=0.78, profit_rate=0.05, gini=0.28)
    second_front = make_item(avg_access=0.72, profit_rate=0.03, gini=0.35)
    third_front = make_item(avg_access=0.68, profit_rate=0.02, gini=0.40)

    assign_pareto_ranks([frontier_a, frontier_b, second_front, third_front])

    assert frontier_a.pareto_rank == 1
    assert frontier_b.pareto_rank == 1
    assert second_front.pareto_rank == 2
    assert third_front.pareto_rank == 3


def test_satisfaction_selector_prefers_converged_result_over_unconverged_reference() -> None:
    profile = {
        "A": {"助餐": 10.0, "日间照料": 10.0, "上门护理": 10.0, "康复理疗": 10.0, "助浴": 10.0, "紧急救助": 0.0},
    }
    converged_but_unfair = PriceEvaluation(
        station_prices=profile,
        iteration_count=3,
        converged=1,
        average_service_satisfaction=0.75,
        minimum_service_satisfaction=0.65,
        average_service_access_performance=0.60,
        minimum_service_access_performance=0.10,
        vulnerable_service_satisfaction=0.55,
        annual_government_subsidy=1000.0,
        annual_service_revenue=10000.0,
        annual_direct_cost=9600.0,
        annual_fixed_cost=1000.0,
        annual_depreciation=500.0,
        annual_total_cost=11100.0,
        annual_net_profit_before_subsidy=-1100.0,
        annual_net_profit_after_subsidy=-100.0,
        annual_net_profit=-100.0,
        profit_rate=-100.0 / 11100.0,
        feasible_station_count=0,
        profit_compliant=0,
        satisfaction_compliant=0,
        low_income_service_satisfaction=0.45,
        low_income_served_coverage=0.6,
        weighted_served_population_coverage=0.5,
        served_demand_coverage=0.55,
        damping_used=0,
        iteration_trace=[IterationRecord(1, 0.0, 0.75, 0, 1000.0, 0)],
        station_financials=[{"station_community": "A", "profit_rate": -0.01}],
        community_results=[{"community": "A", "service_satisfaction": 0.65, "service_access_performance": 0.10}],
        accessibility_groups=[],
        gini_access=0.50,
        theil_access=0.20,
        max_min_gap=0.80,
    )
    non_converged_but_fairer = PriceEvaluation(
        station_prices=profile,
        iteration_count=30,
        converged=0,
        average_service_satisfaction=0.85,
        minimum_service_satisfaction=0.78,
        average_service_access_performance=0.76,
        minimum_service_access_performance=0.39,
        vulnerable_service_satisfaction=0.84,
        annual_government_subsidy=1000.0,
        annual_service_revenue=10000.0,
        annual_direct_cost=9800.0,
        annual_fixed_cost=1000.0,
        annual_depreciation=500.0,
        annual_total_cost=11300.0,
        annual_net_profit_before_subsidy=-1300.0,
        annual_net_profit_after_subsidy=-300.0,
        annual_net_profit=-300.0,
        profit_rate=-300.0 / 11300.0,
        feasible_station_count=0,
        profit_compliant=0,
        satisfaction_compliant=0,
        low_income_service_satisfaction=0.83,
        low_income_served_coverage=0.95,
        weighted_served_population_coverage=0.82,
        served_demand_coverage=0.84,
        damping_used=1,
        iteration_trace=[IterationRecord(1, 0.2, 0.85, 0, 1000.0, 1)],
        station_financials=[{"station_community": "A", "profit_rate": -0.03}],
        community_results=[{"community": "A", "service_satisfaction": 0.78, "service_access_performance": 0.39}],
        accessibility_groups=[],
        gini_access=0.22,
        theil_access=0.03,
        max_min_gap=0.50,
    )
    assert satisfaction_best_selector([converged_but_unfair, non_converged_but_fairer]) is converged_but_unfair


def test_select_financial_best_prefers_converged_profit_compliant_candidate() -> None:
    profile = {
        "A": {"助餐": 10.0, "日间照料": 10.0, "上门护理": 10.0, "康复理疗": 10.0, "助浴": 10.0, "紧急救助": 0.0},
    }
    unconverged_but_stronger = PriceEvaluation(
        station_prices=profile,
        iteration_count=30,
        converged=0,
        average_service_satisfaction=0.88,
        minimum_service_satisfaction=0.82,
        average_service_access_performance=0.78,
        minimum_service_access_performance=0.72,
        vulnerable_service_satisfaction=0.87,
        annual_government_subsidy=1200.0,
        annual_service_revenue=12000.0,
        annual_direct_cost=9800.0,
        annual_fixed_cost=1000.0,
        annual_depreciation=500.0,
        annual_total_cost=11300.0,
        annual_net_profit_before_subsidy=700.0,
        annual_net_profit_after_subsidy=1900.0,
        annual_net_profit=1900.0,
        profit_rate=1900.0 / 11300.0,
        feasible_station_count=1,
        profit_compliant=1,
        satisfaction_compliant=1,
        low_income_service_satisfaction=0.85,
        low_income_served_coverage=0.9,
        weighted_served_population_coverage=0.82,
        served_demand_coverage=0.84,
        damping_used=1,
        iteration_trace=[IterationRecord(1, 0.02, 0.88, 1, 1200.0, 1)],
        station_financials=[{"station_community": "A", "profit_rate": 0.06}],
        community_results=[{"community": "A", "service_satisfaction": 0.82, "service_access_performance": 0.72}],
        accessibility_groups=[],
        gini_access=0.18,
        theil_access=0.03,
        max_min_gap=0.22,
    )
    converged_and_profit_compliant = PriceEvaluation(
        station_prices=profile,
        iteration_count=4,
        converged=1,
        average_service_satisfaction=0.81,
        minimum_service_satisfaction=0.74,
        average_service_access_performance=0.73,
        minimum_service_access_performance=0.68,
        vulnerable_service_satisfaction=0.8,
        annual_government_subsidy=1000.0,
        annual_service_revenue=11800.0,
        annual_direct_cost=9800.0,
        annual_fixed_cost=1000.0,
        annual_depreciation=500.0,
        annual_total_cost=11300.0,
        annual_net_profit_before_subsidy=500.0,
        annual_net_profit_after_subsidy=1500.0,
        annual_net_profit=1500.0,
        profit_rate=1500.0 / 11300.0,
        feasible_station_count=1,
        profit_compliant=1,
        satisfaction_compliant=1,
        low_income_service_satisfaction=0.78,
        low_income_served_coverage=0.86,
        weighted_served_population_coverage=0.78,
        served_demand_coverage=0.8,
        damping_used=0,
        iteration_trace=[IterationRecord(1, 0.0, 0.81, 1, 1000.0, 0)],
        station_financials=[{"station_community": "A", "profit_rate": 0.05}],
        community_results=[{"community": "A", "service_satisfaction": 0.74, "service_access_performance": 0.68}],
        accessibility_groups=[],
        gini_access=0.2,
        theil_access=0.04,
        max_min_gap=0.25,
    )
    assert select_financial_best([unconverged_but_stronger, converged_and_profit_compliant]) is converged_and_profit_compliant


def test_joint_feasibility_station_direction_labels_profit_boundaries() -> None:
    path = Path(__file__).resolve().parent / "3_4_joint_feasibility_diagnostics.py"
    spec = spec_from_file_location("rq3_joint_diag_test_module", path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    assert module.station_direction(-0.01) == "raise_revenue_or_cut_cost"
    assert module.station_direction(0.09) == "lower_price_or_expand_public_service_mix"
    assert module.station_direction(0.04) == "within_band"


def test_pareto_representative_rows_include_satisfaction_metrics() -> None:
    frontier_rows = [
        {
            "subsidy_policy": "none",
            "price_scheme_detail": "A:助餐=10.00,日间照料=10.00,上门护理=10.00,康复理疗=10.00,助浴=10.00",
            "pareto_rank": "1",
            "profit_rate": "0.04",
            "annual_net_profit": "10000",
            "average_service_satisfaction": "0.84",
            "minimum_service_satisfaction": "0.72",
            "average_service_access_performance": "0.66",
            "minimum_service_access_performance": "0.41",
            "gini_access": "0.12",
            "theil_access": "0.03",
            "max_min_gap": "0.25",
            "profit_compliant": "1",
            "fair_satisfaction_compliant": "1",
            "satisfaction_compliant": "1",
            "converged": "1",
        }
    ]
    dual_rows = [
        {"scheme_label": "financial_sustainable_scheme", **frontier_rows[0]},
        {"scheme_label": "satisfaction_priority_scheme", **frontier_rows[0]},
    ]
    rows = pareto_representative_rows(frontier_rows, dual_rows)
    assert rows
    assert "average_service_satisfaction" in rows[0]
    assert "minimum_service_satisfaction" in rows[0]
    assert any(row["representative_label"] == "frontier_satisfaction_peak" for row in rows)


def test_pareto_selector_accepts_legacy_fairness_scheme_key() -> None:
    row = {
        "scheme_label": "fairness_priority_scheme",
        "subsidy_policy": "none",
        "price_scheme_detail": "A:助餐=10.00,日间照料=10.00,上门护理=10.00,康复理疗=10.00,助浴=10.00",
        "pareto_rank": "1",
        "profit_rate": "0.04",
        "annual_net_profit": "10000",
        "average_service_satisfaction": "0.84",
        "minimum_service_satisfaction": "0.72",
        "average_service_access_performance": "0.66",
        "minimum_service_access_performance": "0.41",
        "gini_access": "0.12",
        "theil_access": "0.03",
        "max_min_gap": "0.25",
        "profit_compliant": "1",
        "fair_satisfaction_compliant": "1",
        "satisfaction_compliant": "1",
        "converged": "1",
    }
    selected = RQ3_PARETO.select_dual_scheme([row], "satisfaction_priority_scheme")
    assert selected["scheme_label"] == "fairness_priority_scheme"


def test_rq3_main_writes_canonical_satisfaction_aux_prefix() -> None:
    text = Path(__file__).resolve().parent.joinpath("3_1.py").read_text(encoding="utf-8")
    assert 'write_price_evaluation_bundle("3_1_aux_satisfaction_best_price_scheme", satisfaction_best)' in text
    assert '"satisfaction_priority_scheme": "3_1_aux_satisfaction_best_price_scheme"' in text
    assert "3_1_aux_fairness_best_price_scheme" not in text


def test_pareto_notes_use_satisfaction_primary_wording() -> None:
    frontier_rows = [
        {
            "subsidy_policy": "none",
            "price_scheme_detail": "A:助餐=10.00,日间照料=10.00,上门护理=10.00,康复理疗=10.00,助浴=10.00",
            "pareto_rank": "1",
            "profit_rate": "0.04",
            "annual_net_profit": "10000",
            "average_service_satisfaction": "0.84",
            "minimum_service_satisfaction": "0.72",
            "average_service_access_performance": "0.66",
            "minimum_service_access_performance": "0.41",
            "gini_access": "0.12",
            "theil_access": "0.03",
            "max_min_gap": "0.25",
            "profit_compliant": "1",
            "fair_satisfaction_compliant": "1",
            "satisfaction_compliant": "1",
            "converged": "1",
        }
    ]
    dual_rows = [
        {"scheme_label": "financial_sustainable_scheme", **frontier_rows[0]},
        {"scheme_label": "satisfaction_priority_scheme", **frontier_rows[0]},
    ]
    policy_rows = RQ3_PARETO.policy_summary_rows(frontier_rows)
    representative = pareto_representative_rows(frontier_rows, dual_rows)
    pareto_write_paper_notes(frontier_rows, dual_rows, policy_rows, representative)
    notes_path = Path(__file__).resolve().parent / "outputs" / "3_2_aux_satisfaction_tradeoff_paper_notes.md"
    text = notes_path.read_text(encoding="utf-8")
    assert "average service satisfaction" in text
    assert "minimum service satisfaction threshold" in text
    assert "3_2_aux_satisfaction_tradeoff_profit_vs_avg_satisfaction" in text
    assert "targeted_subsidy" not in text
    assert "3_2_pareto_profit_vs_avg_satisfaction" not in text
    assert "3_2_pareto_paper_notes.md" not in text


def test_evaluation_summary_row_uses_service_level_pricing_formula() -> None:
    profile = {
        "A": {"助餐": 10.0, "日间照料": 11.0, "上门护理": 12.0, "康复理疗": 13.0, "助浴": 14.0, "紧急救助": 0.0},
    }
    item = PriceEvaluation(
        station_prices=profile,
        iteration_count=1,
        converged=1,
        average_service_satisfaction=0.8,
        minimum_service_satisfaction=0.7,
        average_service_access_performance=0.7,
        minimum_service_access_performance=0.65,
        vulnerable_service_satisfaction=0.75,
        annual_government_subsidy=1000.0,
        annual_service_revenue=10000.0,
        annual_direct_cost=9000.0,
        annual_fixed_cost=1000.0,
        annual_depreciation=500.0,
        annual_total_cost=10500.0,
        annual_net_profit_before_subsidy=-500.0,
        annual_net_profit_after_subsidy=500.0,
        annual_net_profit=500.0,
        profit_rate=500.0 / 10500.0,
        feasible_station_count=1,
        profit_compliant=1,
        satisfaction_compliant=1,
        low_income_service_satisfaction=0.72,
        low_income_served_coverage=0.9,
        served_population_coverage=0.85,
        weighted_served_population_coverage=0.7,
        served_demand_coverage=0.8,
        damping_used=0,
        iteration_trace=[IterationRecord(1, 0.0, 0.8, 1, 1000.0, 0)],
        station_financials=[{"station_community": "A", "profit_rate": 0.04}],
        community_results=[{"community": "A", "service_satisfaction": 0.7, "service_access_performance": 0.65}],
        accessibility_groups=[],
    )
    row = evaluation_summary_row(item)
    assert row["pricing_model"] == "station_service_level_pricing"
    assert row["pricing_formula"] == "p_{j,r} independent for r=1,...,5; p_{j,6}=0"
    assert "alpha=" not in str(row["price_scheme_detail"])


def test_stability_extension_reads_aux_pareto_frontier() -> None:
    text = (RQ3_DIR / "3_3_stability_extension.py").read_text(encoding="utf-8")
    assert 'OUTPUT_DIR / "3_1_aux_pareto_frontier.csv"' in text
    assert 'OUTPUT_DIR / "3_1_pareto_frontier.csv"' not in text


def run_all_tests() -> None:
    tests = [
        test_enumerate_station_price_profiles_respects_emergency_zero,
        test_enumerate_station_price_profiles_matches_non_emergency_grid,
        test_enumerate_station_price_profiles_uses_reduced_primary_layer,
        test_generate_rescue_price_profiles_only_uplifts_loss_stations,
        test_dual_selectors_can_choose_different_schemes,
        test_select_satisfaction_best_prefers_converged_candidate,
        test_pareto_representative_rows_include_satisfaction_metrics,
        test_pareto_notes_use_satisfaction_primary_wording,
        test_compute_price_satisfaction_penalizes_premium_price,
        test_enumerate_service_level_price_vectors_keeps_emergency_zero,
        test_service_level_price_profile_uses_independent_service_prices,
        test_compute_station_profit_compliance_is_station_level_only,
        test_prune_station_candidates_caps_candidate_count,
        test_joint_feasible_service_level_requires_stationwise_profit,
        test_service_level_output_files_exist_if_generated,
        test_generated_service_level_station_financials_respect_subsidy_caps_if_present,
        test_generated_service_level_community_bounds_if_present,
        test_generated_service_level_summary_tracks_stationwise_profit_if_present,
        test_expanded_search_level_settings_monotonic,
        test_build_rq3_inputs_for_budget_scenario_keeps_s0_and_s4_layouts_distinct,
        test_prune_station_candidates_expanded_keeps_boundary_and_diverse_rows,
        test_compose_expanded_global_profiles_is_reproducible_with_seed,
        test_expanded_search_output_files_exist_if_generated,
        test_generated_expanded_search_outputs_respect_stationwise_rules_if_present,
        test_expanded_search_run_can_skip_existing_main_outputs,
        test_profit_rate_constraint_is_bounded_between_zero_and_eight_percent,
        test_fixed_point_converged_uses_max_absolute_difference,
        test_detect_two_cycle_oscillation_finds_simple_abab_pattern,
        test_detect_short_cycle_oscillation_finds_ababc_cycle,
        test_average_cycle_states_returns_componentwise_mean,
        test_apply_damping_blends_candidate_with_previous_state,
        test_select_primary_and_backup_follows_utility_order,
        test_build_community_choices_breaks_ties_by_distance_then_station_name,
        test_solve_collaboration_lp_uses_single_station_and_leaves_unmet,
        test_solve_collaboration_lp_scales_all_selected_communities_by_same_station_ratio,
        test_evaluation_summary_row_reports_joint_feasibility_and_financial_gap,
        test_joint_feasible_solution_requires_profit_fairness_and_convergence,
        test_targeted_subsidy_policy_is_disabled_in_mainline_model,
        test_evaluation_summary_row_marks_subsidy_policy_as_none,
        test_equity_metrics_capture_dispersion_and_extremes,
        test_assign_pareto_ranks_uses_non_dominated_front_layers,
        test_satisfaction_selector_prefers_converged_result_over_unconverged_reference,
        test_select_financial_best_prefers_converged_profit_compliant_candidate,
        test_joint_feasibility_station_direction_labels_profit_boundaries,
    ]
    for test in tests:
        test()
    print(f"Passed {len(tests)} tests.")


if __name__ == "__main__":
    run_all_tests()
