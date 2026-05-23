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
compute_relative_change = RQ4_COMMON.compute_relative_change
compute_sensitivity_coefficient = RQ4_COMMON.compute_sensitivity_coefficient
compute_average_relative_parameter_change = RQ4_COMMON.compute_average_relative_parameter_change
compute_location_stability = RQ4_COMMON.compute_location_stability
compute_coverage_stability = RQ4_COMMON.compute_coverage_stability
compute_satisfaction_stability = RQ4_COMMON.compute_satisfaction_stability
compute_financial_compliance_stability = RQ4_COMMON.compute_financial_compliance_stability
compute_capacity_safety_stability = RQ4_COMMON.compute_capacity_safety_stability
scenario_requires_rerun_from_rq1 = RQ4_COMMON.scenario_requires_rerun_from_rq1


def test_scenario_requires_rerun_from_rq1_only_for_population_and_transition_changes() -> None:
    growth = ScenarioDefinition(
        code="S1",
        name="老人增长率提高",
        parameter_changes={"elder_growth_rate": 0.08},
    )
    transition = ScenarioDefinition(
        code="S2",
        name="转移概率变化",
        parameter_changes={"self_to_semi": 0.055, "semi_to_disabled": 0.095},
    )
    cost = ScenarioDefinition(
        code="S3",
        name="固定成本上升",
        parameter_changes={"fixed_cost_multiplier": 1.2},
    )
    budget = ScenarioDefinition(
        code="S4",
        name="预算提高",
        parameter_changes={"budget_limit": 140.0},
    )
    assert scenario_requires_rerun_from_rq1(growth) is True
    assert scenario_requires_rerun_from_rq1(transition) is True
    assert scenario_requires_rerun_from_rq1(cost) is False
    assert scenario_requires_rerun_from_rq1(budget) is False


def test_sensitivity_helpers_follow_document_formulas() -> None:
    metric_change = compute_relative_change(110.0, 100.0)
    parameter_change = compute_average_relative_parameter_change(
        baseline_values={"elder_growth_rate": 0.07},
        scenario_values={"elder_growth_rate": 0.08},
    )
    coefficient = compute_sensitivity_coefficient(metric_change, parameter_change)
    assert abs(metric_change - 0.1) < 1e-9
    assert abs(parameter_change - (0.01 / 0.07)) < 1e-9
    assert abs(coefficient - 0.7) < 1e-9


def test_average_relative_parameter_change_supports_multi_parameter_scenarios() -> None:
    result = compute_average_relative_parameter_change(
        baseline_values={"self_to_semi": 0.05, "semi_to_disabled": 0.10},
        scenario_values={"self_to_semi": 0.055, "semi_to_disabled": 0.095},
    )
    expected = ((0.005 / 0.05) + (0.005 / 0.10)) / 2
    assert abs(result - expected) < 1e-9


def test_robustness_metrics_follow_current_definitions() -> None:
    assert abs(compute_location_stability({"A", "C", "F"}, {"A", "F", "J"}) - (2 / 3)) < 1e-9
    assert abs(compute_coverage_stability(0.92, 0.88) - 0.96) < 1e-9
    assert abs(compute_satisfaction_stability(0.81, 0.76) - 0.95) < 1e-9
    assert abs(compute_financial_compliance_stability([1, 0, 1, 1]) - 0.75) < 1e-9
    assert abs(compute_capacity_safety_stability([0.72, 0.84, 0.87, 0.91], threshold=0.85) - 0.5) < 1e-9


def run_all_tests() -> None:
    tests = [
        test_scenario_requires_rerun_from_rq1_only_for_population_and_transition_changes,
        test_sensitivity_helpers_follow_document_formulas,
        test_average_relative_parameter_change_supports_multi_parameter_scenarios,
        test_robustness_metrics_follow_current_definitions,
    ]
    for test in tests:
        test()
    print(f"Passed {len(tests)} tests.")


if __name__ == "__main__":
    run_all_tests()
