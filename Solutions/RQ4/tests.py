from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import json
import sys
import tempfile


RQ4_DIR = Path(__file__).resolve().parent
RQ4_COMMON_PATH = RQ4_DIR / "common.py"
RQ4_SPEC = spec_from_file_location("rq4_common_module", RQ4_COMMON_PATH)
if RQ4_SPEC is None or RQ4_SPEC.loader is None:
    raise RuntimeError(f"Failed to load RQ4 common module from {RQ4_COMMON_PATH}")
RQ4_COMMON = module_from_spec(RQ4_SPEC)
sys.modules[RQ4_SPEC.name] = RQ4_COMMON
RQ4_SPEC.loader.exec_module(RQ4_COMMON)

RQ4_MAIN_PATH = RQ4_DIR / "4_1.py"
with RQ4_COMMON.temporarily_bind_common(RQ4_COMMON):
    RQ4_MAIN_SPEC = spec_from_file_location("rq4_main_module", RQ4_MAIN_PATH)
    if RQ4_MAIN_SPEC is None or RQ4_MAIN_SPEC.loader is None:
        raise RuntimeError(f"Failed to load RQ4 main module from {RQ4_MAIN_PATH}")
    RQ4_MAIN = module_from_spec(RQ4_MAIN_SPEC)
    sys.modules[RQ4_MAIN_SPEC.name] = RQ4_MAIN
    RQ4_MAIN_SPEC.loader.exec_module(RQ4_MAIN)

ScenarioDefinition = RQ4_COMMON.ScenarioDefinition
scenario_definitions = RQ4_COMMON.scenario_definitions
scenario_requires_rerun_from_rq1 = RQ4_COMMON.scenario_requires_rerun_from_rq1
scenario_execution_path = RQ4_COMMON.scenario_execution_path
scenario_parameter_dict = RQ4_COMMON.scenario_parameter_dict
compute_relative_change = RQ4_COMMON.compute_relative_change
compute_scenario_parameter_relative_change = RQ4_COMMON.compute_scenario_parameter_relative_change
compute_sensitivity_coefficient = RQ4_COMMON.compute_sensitivity_coefficient
classify_sensitivity_level = RQ4_COMMON.classify_sensitivity_level
sensitivity_row = RQ4_COMMON.sensitivity_row
compute_jaccard_location_stability = RQ4_COMMON.compute_jaccard_location_stability
compute_layout_scale_consistency = RQ4_COMMON.compute_layout_scale_consistency
compute_stability_from_metric = RQ4_COMMON.compute_stability_from_metric
compute_financial_compliance_rate = RQ4_COMMON.compute_financial_compliance_rate
compute_capacity_safety_rate = RQ4_COMMON.compute_capacity_safety_rate
build_station_scale_map = RQ4_COMMON.build_station_scale_map
build_station_plan_text = RQ4_COMMON.build_station_plan_text
summarize_monte_carlo_metric = RQ4_COMMON.summarize_monte_carlo_metric
q3_summary_row = RQ4_COMMON.q3_summary_row
cache_is_current = RQ4_MAIN.cache_is_current
build_unified_summary_rows = RQ4_MAIN.build_unified_summary_rows


def test_scenario_config_contains_required_traceable_fields() -> None:
    scenario_map = {scenario.code: scenario for scenario in scenario_definitions()}
    assert set(scenario_map) == {"S0", "S1", "S2", "S3", "S4"}

    s0 = scenario_parameter_dict(scenario_map["S0"])
    s1 = scenario_parameter_dict(scenario_map["S1"])
    s2 = scenario_parameter_dict(scenario_map["S2"])
    s3 = scenario_parameter_dict(scenario_map["S3"])
    s4 = scenario_parameter_dict(scenario_map["S4"])

    assert s0 == {
        "elderly_growth_rate": 0.07,
        "p12": 0.045,
        "p23": 0.10,
        "fixed_cost_multiplier": 1.0,
        "budget_limit": 120.0,
    }
    assert s1["elderly_growth_rate"] == 0.08
    assert s2["p12"] == 0.055 and s2["p23"] == 0.095
    assert s3["fixed_cost_multiplier"] == 1.2
    assert s4["budget_limit"] == 140.0


def test_scenario_execution_paths_follow_requirement() -> None:
    scenario_map = {scenario.code: scenario for scenario in scenario_definitions()}

    assert scenario_requires_rerun_from_rq1(scenario_map["S1"]) is True
    assert scenario_requires_rerun_from_rq1(scenario_map["S2"]) is True
    assert scenario_requires_rerun_from_rq1(scenario_map["S3"]) is False
    assert scenario_requires_rerun_from_rq1(scenario_map["S4"]) is False

    assert scenario_execution_path(scenario_map["S0"]) == "rerun_rq1_rq2_rq3"
    assert scenario_execution_path(scenario_map["S1"]) == "rerun_rq1_rq2_rq3"
    assert scenario_execution_path(scenario_map["S2"]) == "rerun_rq1_rq2_rq3"
    assert scenario_execution_path(scenario_map["S3"]) == "reuse_rq1_rerun_rq2_rq3"
    assert scenario_execution_path(scenario_map["S4"]) == "reuse_rq1_rerun_rq2_rq3"


def test_sensitivity_helpers_follow_document_formulas() -> None:
    metric_change = compute_relative_change(110.0, 100.0)
    parameter_change = compute_scenario_parameter_relative_change(
        ScenarioDefinition("S1", "老人增长率提高", {"elder_growth_rate": 0.08}),
        {
            "elderly_growth_rate": 0.07,
            "p12": 0.045,
            "p23": 0.10,
            "fixed_cost_multiplier": 1.0,
            "budget_limit": 120.0,
        },
    )
    coefficient = compute_sensitivity_coefficient(metric_change, parameter_change)
    assert abs(metric_change - 0.1) < 1e-9
    assert abs(parameter_change - (0.01 / 0.07)) < 1e-9
    assert abs(coefficient - 0.7) < 1e-9


def test_parameter_relative_change_uses_only_perturbed_parameters() -> None:
    baseline = {
        "elderly_growth_rate": 0.07,
        "p12": 0.045,
        "p23": 0.10,
        "fixed_cost_multiplier": 1.0,
        "budget_limit": 120.0,
    }
    s1 = ScenarioDefinition("S1", "老人增长率提高", {"elder_growth_rate": 0.08})
    s2 = ScenarioDefinition("S2", "转移概率变化", {"p12": 0.055, "p23": 0.095})
    s3 = ScenarioDefinition("S3", "固定成本上升", {"fixed_cost_multiplier": 1.2})
    s4 = ScenarioDefinition("S4", "预算提高", {"budget_limit": 140.0})

    assert abs(compute_scenario_parameter_relative_change(s1, baseline) - (0.01 / 0.07)) < 1e-9
    assert abs(
        compute_scenario_parameter_relative_change(s2, baseline)
        - ((abs(0.055 - 0.045) / 0.045 + abs(0.095 - 0.10) / 0.10) / 2)
    ) < 1e-9
    assert abs(compute_scenario_parameter_relative_change(s3, baseline) - 0.20) < 1e-9
    assert abs(compute_scenario_parameter_relative_change(s4, baseline) - (20.0 / 120.0)) < 1e-9


def test_sensitivity_row_contains_requested_fields_and_levels() -> None:
    scenario = ScenarioDefinition("S4", "预算提高", {"budget_limit": 140.0})
    baseline = {
        "elderly_growth_rate": 0.07,
        "p12": 0.045,
        "p23": 0.10,
        "fixed_cost_multiplier": 1.0,
        "budget_limit": 120.0,
    }
    row = sensitivity_row(
        scenario=scenario,
        metric_name="served_demand_coverage",
        baseline_value=0.8,
        scenario_value=1.0,
        baseline_parameters=baseline,
    )
    assert row["scenario"] == "S4"
    assert row["perturbed_parameter"] == "budget_limit"
    assert row["parameter_relative_change"] == round(20.0 / 120.0, 6)
    assert row["metric_absolute_change"] == 0.2
    assert row["metric_relative_change"] == 0.25
    assert row["sensitivity_coefficient"] == 1.5
    assert row["sensitivity_level"] == "high"

    na_row = sensitivity_row(
        scenario=scenario,
        metric_name="fiscal_gap_if_any",
        baseline_value=0.0,
        scenario_value=2.0,
        baseline_parameters=baseline,
    )
    assert na_row["metric_relative_change"] == "NA"
    assert na_row["sensitivity_coefficient"] == "NA"


def test_sensitivity_level_thresholds() -> None:
    assert classify_sensitivity_level(0.29) == "low"
    assert classify_sensitivity_level(-0.79) == "medium"
    assert classify_sensitivity_level(0.8) == "high"
    assert classify_sensitivity_level("NA") == "NA"


def test_robustness_helpers_follow_new_definitions() -> None:
    assert abs(compute_jaccard_location_stability({"A", "C", "F"}, {"A", "F", "J"}) - 0.5) < 1e-9

    baseline_scale_map = {"A": "小型", "C": "大型", "F": "小型"}
    scenario_scale_map = {"A": "小型", "F": "中型", "J": "小型"}
    assert abs(compute_layout_scale_consistency(baseline_scale_map, scenario_scale_map) - (1 / 4)) < 1e-9

    assert abs(compute_stability_from_metric(0.92, 0.88) - 0.96) < 1e-9
    assert abs(compute_financial_compliance_rate([1, 0, 1, 1]) - 0.75) < 1e-9
    assert abs(compute_capacity_safety_rate([0.72, 0.84, 0.87, 0.91], threshold=0.85) - 0.5) < 1e-9


def test_station_plan_helpers_build_consistent_strings_and_maps() -> None:
    plan = "A-小型;C-大型;F-小型"
    scale_map = build_station_scale_map(plan)
    assert scale_map == {"A": "小型", "C": "大型", "F": "小型"}
    assert build_station_plan_text(scale_map) == plan


def test_q2_progress_plan_text_should_be_built_from_station_mapping() -> None:
    class StubStation:
        def __init__(self, community: str, scale: str) -> None:
            self.community = community
            self.scale = scale

    stations = [StubStation("C", "大型"), StubStation("A", "小型")]
    scale_map = {station.community: station.scale for station in stations}
    assert build_station_plan_text(scale_map) == "A-小型;C-大型"


def test_monte_carlo_metric_summary_reports_mean_quantiles_and_risk() -> None:
    summary = summarize_monte_carlo_metric(
        name="annual_net_profit",
        values=[-10.0, 0.0, 10.0, 20.0, 30.0],
        risk_threshold=0.0,
        lower_is_risk=True,
    )
    assert summary["metric"] == "annual_net_profit"
    assert summary["mean"] == 10.0
    assert summary["p10"] <= summary["p50"] <= summary["p90"]
    assert summary["risk_probability"] == 0.2


def test_q3_summary_row_contains_coverage_fields() -> None:
    class StubEval:
        pass

    evaluation = StubEval()
    evaluation.station_prices = {"A": {"助餐": 10.0, "日间照料": 10.0, "上门护理": 10.0, "康复理疗": 10.0, "助浴": 10.0, "紧急救助": 0.0}}
    evaluation.iteration_count = 1
    evaluation.converged = 1
    evaluation.damping_used = 0
    evaluation.profit_compliant = 1
    evaluation.satisfaction_compliant = 1
    evaluation.feasible_station_count = 1
    evaluation.average_service_satisfaction = 0.8
    evaluation.minimum_service_satisfaction = 0.7
    evaluation.average_service_access_performance = 0.75
    evaluation.minimum_service_access_performance = 0.65
    evaluation.vulnerable_service_satisfaction = 0.72
    evaluation.low_income_service_satisfaction = 0.7
    evaluation.low_income_served_coverage = 1.0
    evaluation.served_population_coverage = 0.78
    evaluation.weighted_served_population_coverage = 0.8
    evaluation.served_demand_coverage = 0.82
    evaluation.gini_access = 0.1
    evaluation.theil_access = 0.01
    evaluation.max_min_gap = 0.2
    evaluation.annual_government_subsidy = 1000.0
    evaluation.annual_service_revenue = 9000.0
    evaluation.annual_direct_cost = 8000.0
    evaluation.annual_fixed_cost = 1000.0
    evaluation.annual_depreciation = 500.0
    evaluation.annual_total_cost = 9500.0
    evaluation.annual_net_profit_before_subsidy = -500.0
    evaluation.annual_net_profit_after_subsidy = 500.0
    evaluation.annual_net_profit = 500.0
    evaluation.profit_rate = 500.0 / 9500.0
    evaluation.pareto_rank = 1
    evaluation.subsidy_policy_label = "none"

    scenario = ScenarioDefinition("S0", "基准", {})
    row = q3_summary_row(
        scenario=scenario,
        scheme_type="financial_sustainable_scheme",
        evaluation=evaluation,
        station_plan="A-小型",
        fiscal_gap_if_any=0.0,
    )
    assert "served_population_coverage" in row
    assert "weighted_served_population_coverage" in row
    assert "served_demand_coverage" in row
    assert row["served_population_coverage"] == 0.78
    assert row["weighted_served_population_coverage"] == 0.8


def test_cache_is_current_rejects_legacy_alpha_and_overflow_payload() -> None:
    legacy_payload = {
        "cache_version": RQ4_COMMON.CACHE_VERSION,
        "financial_best_summary": {
            "pricing_model": "station_service_level_pricing",
            "pricing_formula": "p_{j,r}=alpha_j*p_r^0,r=1,...,5; p_{j,6}=0",
        },
        "fairness_best_summary": {
            "pricing_model": "station_service_level_pricing",
            "pricing_formula": "p_{j,r}=alpha_j*p_r^0,r=1,...,5; p_{j,6}=0",
        },
        "coordination_note": "老人仍选择满意度最高的主服务站。容量不足时，协同站点分流表示由主站或街道平台进行派单协同，不表示老人自主改选其他站点。",
        "financial_best_community_results": [{"community": "A", "overflow_station": "B"}],
        "satisfaction_best_community_results": [{"community": "A", "overflow_station": ""}],
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "legacy.json"
        path.write_text(json.dumps(legacy_payload, ensure_ascii=False), encoding="utf-8")
        assert cache_is_current(path) is False


def test_cache_is_current_accepts_current_single_station_payload() -> None:
    current_payload = {
        "cache_version": RQ4_COMMON.CACHE_VERSION,
        "financial_best_summary": {
            "pricing_model": "station_service_level_pricing",
            "pricing_formula": "p_{j,r} independent for r=1,...,5; p_{j,6}=0",
        },
        "satisfaction_best_summary": {
            "pricing_model": "station_service_level_pricing",
            "pricing_formula": "p_{j,r} independent for r=1,...,5; p_{j,6}=0",
        },
        "financial_best_community_results": [{"community": "A", "overflow_station": ""}],
        "satisfaction_best_community_results": [{"community": "A", "overflow_station": ""}],
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "current.json"
        path.write_text(json.dumps(current_payload, ensure_ascii=False), encoding="utf-8")
        assert cache_is_current(path) is True


def test_rq4_source_uses_single_station_ratio_wording() -> None:
    text = RQ4_MAIN_PATH.read_text(encoding="utf-8")
    assert "不再分流至第二站" in text
    assert "协同站点分流" not in text


def test_build_unified_summary_rows_reads_canonical_satisfaction_stability_field() -> None:
    scenario = ScenarioDefinition("S4", "预算提高", {"budget_limit": 140.0})
    result_map = {
        "S4": {
            "scenario_name": "预算提高",
            "execution_path": "reuse_rq1_rerun_rq2_rq3",
            "scenario_parameters": {
                "budget_limit": 140.0,
                "fixed_cost_multiplier": 1.0,
                "p12": 0.045,
                "p23": 0.10,
                "elderly_growth_rate": 0.07,
            },
            "q2_best_station_plan": "A-小型;C-中型",
            "q2_best_summary": {
                "build_cost_wan": 138.0,
                "served_demand_coverage": 0.85,
                "average_service_access_performance": 0.83,
                "minimum_service_access_performance": 0.77,
                "capacity_safety_rate": 0.5,
                "max_station_utilization": 0.91,
                "fully_safe": 0,
            },
            "financial_best_summary": {
                "subsidy_policy": "none",
                "pareto_rank": 1,
                "annual_government_subsidy": 1000.0,
                "annual_net_profit": 500.0,
                "profit_rate": 0.02,
                "average_service_access_performance": 0.8,
                "minimum_service_access_performance": 0.75,
                "profit_compliant": 1,
                "converged": 1,
            },
            "satisfaction_best_summary": {
                "subsidy_policy": "none",
                "pareto_rank": 2,
                "annual_government_subsidy": 1200.0,
                "annual_net_profit": -50.0,
                "profit_rate": -0.002,
                "average_service_access_performance": 0.86,
                "minimum_service_access_performance": 0.8,
                "profit_compliant": 0,
                "converged": 1,
            },
            "joint_feasible_solution_exists": False,
        }
    }
    sensitivity_rows = [
        {
            "scenario": "S4",
            "metric": "q2_served_demand_coverage",
            "sensitivity_coefficient": 0.3,
            "sensitivity_level": "medium",
            "perturbed_parameter": "budget_limit",
        }
    ]
    robustness_rows = [
        {
            "scenario": "S4",
            "RS_loc": 0.75,
            "RS_layout": 0.5,
            "served_demand_coverage_stability": 0.95,
            "q3_financial_scheme_performance_stability": 0.96,
            "q3_satisfaction_scheme_performance_stability": 0.97,
            "financial_compliance_rate": 0.5,
            "capacity_safety_rate": 0.75,
        }
    ]
    rows = build_unified_summary_rows([scenario], result_map, sensitivity_rows, robustness_rows)
    assert len(rows) == 1
    assert rows[0]["q3_satisfaction_scheme_performance_stability"] == 0.97


def run_all_tests() -> None:
    tests = [
        test_scenario_config_contains_required_traceable_fields,
        test_scenario_execution_paths_follow_requirement,
        test_sensitivity_helpers_follow_document_formulas,
        test_parameter_relative_change_uses_only_perturbed_parameters,
        test_sensitivity_row_contains_requested_fields_and_levels,
        test_sensitivity_level_thresholds,
        test_robustness_helpers_follow_new_definitions,
        test_station_plan_helpers_build_consistent_strings_and_maps,
        test_q2_progress_plan_text_should_be_built_from_station_mapping,
        test_monte_carlo_metric_summary_reports_mean_quantiles_and_risk,
        test_q3_summary_row_contains_coverage_fields,
        test_cache_is_current_rejects_legacy_alpha_and_overflow_payload,
        test_cache_is_current_accepts_current_single_station_payload,
        test_rq4_source_uses_single_station_ratio_wording,
        test_build_unified_summary_rows_reads_canonical_satisfaction_stability_field,
    ]
    for test in tests:
        test()
    print(f"Passed {len(tests)} tests.")


if __name__ == "__main__":
    run_all_tests()
