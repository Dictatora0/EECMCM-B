from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


RQ4_DIR = Path(__file__).resolve().parent
RQ4_COMMON_PATH = RQ4_DIR / "common.py"
RQ4_SPEC = spec_from_file_location("rq4_common_module", RQ4_COMMON_PATH)
if RQ4_SPEC is None or RQ4_SPEC.loader is None:
    raise RuntimeError(f"Failed to load RQ4 common module from {RQ4_COMMON_PATH}")
RQ4_COMMON = module_from_spec(RQ4_SPEC)
sys.modules[RQ4_SPEC.name] = RQ4_COMMON
RQ4_SPEC.loader.exec_module(RQ4_COMMON)

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
    ]
    for test in tests:
        test()
    print(f"Passed {len(tests)} tests.")


if __name__ == "__main__":
    run_all_tests()
