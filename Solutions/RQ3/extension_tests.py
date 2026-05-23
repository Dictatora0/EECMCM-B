from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import csv
import math
import sys


RQ3_DIR = Path(__file__).resolve().parent
EXT_PATH = RQ3_DIR / "3_3_stability_extension.py"
EXT_SPEC = spec_from_file_location("rq3_extension_module", EXT_PATH)
if EXT_SPEC is None or EXT_SPEC.loader is None:
    raise RuntimeError(f"Failed to load extension module from {EXT_PATH}")
EXT = module_from_spec(EXT_SPEC)
sys.modules[EXT_SPEC.name] = EXT
EXT_SPEC.loader.exec_module(EXT)


def test_fiscal_gap_formula_matches_requirement() -> None:
    class Dummy:
        def __init__(self, annual_net_profit: float, annual_total_cost: float, profit_rate: float):
            self.annual_net_profit = annual_net_profit
            self.annual_total_cost = annual_total_cost
            self.profit_rate = profit_rate

    assert abs(EXT.fiscal_gap(Dummy(-100.0, 1000.0, -0.1)) - 100.0) < 1e-9
    assert abs(EXT.fiscal_gap(Dummy(120.0, 1000.0, 0.12)) - (120.0 - 80.0)) < 1e-9
    assert abs(EXT.fiscal_gap(Dummy(50.0, 1000.0, 0.05))) < 1e-9


def test_output_tables_cover_required_scenarios_and_epsilons() -> None:
    path = RQ3_DIR / "outputs" / "3_3_epsilon_constraint_summary.csv"
    if not path.exists():
        return
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
    scenario_eps = {(row["scenario"], row["epsilon"]) for row in rows}
    for scenario in ["S0_baseline", "S4_budget_140"]:
        for epsilon in ["0.1", "0.2", "0.3", "0.4", "0.5", "0.6", "0.7", "0.8"]:
            assert (scenario, epsilon) in scenario_eps


def test_epsilon_rows_have_explicit_none_for_infeasible_cases() -> None:
    path = RQ3_DIR / "outputs" / "3_3_epsilon_constraint_summary.csv"
    if not path.exists():
        return
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
    grouped = {}
    for row in rows:
        grouped.setdefault((row["scenario"], row["epsilon"]), []).append(row)
    for key, subset in grouped.items():
        feasible_counts = {row["feasible_count"] for row in subset}
        assert len(feasible_counts) == 1
        feasible_count = int(next(iter(feasible_counts)))
        if feasible_count == 0:
            assert len(subset) == 1
            assert subset[0]["selection_rule"] == "none"
            assert subset[0]["best_scheme_id"] == ""
        else:
            assert {row["selection_rule"] for row in subset} == {
                "max_annual_net_profit",
                "closest_profit_rate_band",
                "min_fiscal_gap",
            }


def test_damping_table_is_not_empty_if_generated() -> None:
    path = RQ3_DIR / "outputs" / "3_3_damping_sensitivity.csv"
    if not path.exists():
        return
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
    assert rows


def test_lambda_one_matches_no_damping_reference_for_real_case() -> None:
    bundle = EXT.load_rq3_inputs_for_scenario("S0_baseline", "S0")
    profile = bundle.candidate_profiles[0]
    subsidy_budget = EXT.RQ3_MAIN.subsidy_budget_candidates()[0]
    warm_start = EXT.RQ3_MAIN.initial_service_satisfaction_by_community(bundle.inputs.q2_allocations)
    choice_cache = EXT.RQ3_MAIN.precompute_community_station_choice_cache(
        inputs=bundle.inputs,
        station_prices=profile,
        subsidy_budget_per_person=subsidy_budget,
    )
    baseline = EXT.RQ3_MAIN.evaluate_price_profile(
        bundle.inputs,
        profile,
        initial_satisfaction=warm_start,
        subsidy_budget_per_person=subsidy_budget,
        subsidy_policy_label=f"targeted_subsidy_{subsidy_budget:.1f}",
        damping_lambda=1.0,
        enable_damping=False,
        choice_cache=choice_cache,
    )
    damped = EXT.RQ3_MAIN.evaluate_price_profile(
        bundle.inputs,
        profile,
        initial_satisfaction=warm_start,
        subsidy_budget_per_person=subsidy_budget,
        subsidy_policy_label=f"targeted_subsidy_{subsidy_budget:.1f}",
        damping_lambda=1.0,
        enable_damping=False,
        choice_cache=choice_cache,
    )
    assert baseline.converged == damped.converged
    assert baseline.iteration_count == damped.iteration_count
    assert math.isclose(
        baseline.average_service_access_performance,
        damped.average_service_access_performance,
        rel_tol=0.0,
        abs_tol=1e-12,
    )
    assert math.isclose(
        baseline.minimum_service_access_performance,
        damped.minimum_service_access_performance,
        rel_tol=0.0,
        abs_tol=1e-12,
    )
    assert math.isclose(
        baseline.annual_net_profit,
        damped.annual_net_profit,
        rel_tol=0.0,
        abs_tol=1e-9,
    )


def test_summary_marks_infeasible_s0_high_epsilons_explicitly() -> None:
    path = RQ3_DIR / "outputs" / "3_3_epsilon_constraint_summary.csv"
    if not path.exists():
        return
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
    for epsilon in ["0.7", "0.8"]:
        subset = [
            row for row in rows
            if row["scenario"] == "S0_baseline" and row["epsilon"] == epsilon
        ]
        assert len(subset) == 1
        row = subset[0]
        assert row["selection_rule"] == "none"
        assert row["feasible_count"] == "0"
        assert row["fiscal_gap"] in {"", "NA"}


def test_generated_plot_files_exist() -> None:
    expected = [
        "3_3_damping_lambda_vs_convergence_rate.pdf",
        "3_3_damping_lambda_vs_convergence_rate.png",
        "3_3_epsilon_vs_fiscal_gap.pdf",
        "3_3_epsilon_vs_fiscal_gap.png",
        "3_3_epsilon_vs_access.pdf",
        "3_3_epsilon_vs_access.png",
        "3_3_s0_vs_s4_fiscal_gap_comparison.pdf",
        "3_3_s0_vs_s4_fiscal_gap_comparison.png",
    ]
    for name in expected:
        assert (RQ3_DIR / "outputs" / name).exists()


def test_summary_contains_aggregate_profit_band_diagnostics() -> None:
    path = RQ3_DIR / "outputs" / "3_3_epsilon_constraint_summary.csv"
    if not path.exists():
        return
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
    row = next(
        row
        for row in rows
        if row["scenario"] == "S4_budget_140"
        and row["epsilon"] == "0.7"
        and row["selection_rule"] == "min_fiscal_gap"
    )
    assert "aggregate_profit_rate_compliant" in row
    assert "station_profit_compliant" in row
    assert row["aggregate_profit_rate_compliant"] == "1"
    assert row["station_profit_compliant"] == "0"


def run_all_tests() -> None:
    tests = [
        test_fiscal_gap_formula_matches_requirement,
        test_output_tables_cover_required_scenarios_and_epsilons,
        test_epsilon_rows_have_explicit_none_for_infeasible_cases,
        test_damping_table_is_not_empty_if_generated,
        test_lambda_one_matches_no_damping_reference_for_real_case,
        test_summary_marks_infeasible_s0_high_epsilons_explicitly,
        test_generated_plot_files_exist,
        test_summary_contains_aggregate_profit_band_diagnostics,
    ]
    for test in tests:
        test()
    print(f"Passed {len(tests)} extension tests.")


if __name__ == "__main__":
    run_all_tests()
