from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List

from common import (
    OUTPUT_DIR,
    RQ3Inputs,
    load_year5_population,
    load_adjusted_demand_summary,
    load_adjusted_demand_detail,
    load_station_scales,
    SchemeSummaryRecord,
    StationRecord,
    AllocationRecord,
    Year5PopulationRecord,
    AdjustedDemandSummaryRecord,
    AdjustedDemandDetailRecord,
    write_csv,
)

os.environ.setdefault("MPLCONFIGDIR", str(OUTPUT_DIR / ".mplconfig"))
Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt

from importlib.util import module_from_spec, spec_from_file_location
import sys


RQ3_DIR = Path(__file__).resolve().parent
ROOT = RQ3_DIR.parents[1]
RQ3_MAIN_PATH = RQ3_DIR / "3_1.py"
RQ3_SPEC = spec_from_file_location("rq3_extension_main_module", RQ3_MAIN_PATH)
if RQ3_SPEC is None or RQ3_SPEC.loader is None:
    raise RuntimeError(f"Failed to load RQ3 main module from {RQ3_MAIN_PATH}")
RQ3_MAIN = module_from_spec(RQ3_SPEC)
sys.modules[RQ3_SPEC.name] = RQ3_MAIN
RQ3_SPEC.loader.exec_module(RQ3_MAIN)

RQ4_CACHE_DIR = ROOT / "Solutions" / "RQ4" / "cache"
LAMBDA_GRID = [0.2, 0.3, 0.5, 0.7, 1.0]
EPSILON_GRID = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
SCENARIOS = {
    "S0_baseline": "S0",
    "S4_budget_140": "S4",
}
MAX_ANALYSIS_CANDIDATE_PROFILES = 60


@dataclass(frozen=True)
class ScenarioBundle:
    scenario_label: str
    scenario_code: str
    inputs: RQ3Inputs
    station_plan: str
    financial_summary: Dict[str, object]
    fairness_summary: Dict[str, object]
    candidate_profiles: List[Dict[str, Dict[str, float]]]


def read_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def station_records_from_plan(station_plan: str, station_financials: List[Dict[str, object]]) -> List[StationRecord]:
    scale_library = load_station_scales()
    financial_by_station = {str(row["station_community"]): row for row in station_financials}
    rows: List[StationRecord] = []
    for token in station_plan.split(";"):
        community, scale_name = token.split("-", 1)
        scale = scale_library[scale_name]
        row = financial_by_station[community]
        raw_daily_total = float(row["raw_served_demand_daily"])
        utilization = raw_daily_total / scale.daily_capacity if scale.daily_capacity > 0 else 0.0
        rows.append(
            StationRecord(
                station_community=community,
                scale=scale_name,
                daily_capacity=float(scale.daily_capacity),
                assigned_primary_load=raw_daily_total,
                assigned_overflow_load=float(row.get("assigned_overflow_load", 0.0)),
                total_load=raw_daily_total,
                utilization=utilization,
                annual_service_revenue=float(row["annual_service_revenue"]),
                annual_direct_cost=float(row["annual_direct_cost"]),
                annual_fixed_cost=float(row["annual_fixed_cost"]),
                annual_depreciation=float(row["annual_depreciation"]),
                annual_government_subsidy_baseline=float(row.get("annual_government_subsidy", row.get("annual_subsidy", 0.0))),
                annual_net_profit_before_subsidy=float(row["annual_net_profit_before_subsidy"]),
                annual_net_profit_after_policy_subsidy=float(row.get("annual_net_profit_after_subsidy", row["annual_net_profit"])),
                annual_revenue=float(row.get("annual_service_revenue", 0.0)),
                annual_subsidy=float(row.get("annual_government_subsidy", row.get("annual_subsidy", 0.0))),
                annual_total_cost=float(row["annual_total_cost"]),
                annual_net_profit=float(row["annual_net_profit"]),
                profit_rate=float(row["profit_rate"]),
                profit_compliant=int(row["profit_compliant"]),
            )
        )
    rows.sort(key=lambda item: item.station_community)
    return rows


def allocation_records_from_cache(rows: List[Dict[str, object]]) -> List[AllocationRecord]:
    result: List[AllocationRecord] = []
    for row in rows:
        result.append(
            AllocationRecord(
                community=str(row["community"]),
                primary_station=str(row.get("primary_station", "")).strip() or None,
                overflow_station=str(row.get("overflow_station", "")).strip() or None,
                geographic_reachable=int(float(row.get("served", 0))),
                actually_served=int(float(row.get("served", 0))),
                geographic_population_covered=0.0,
                served_population_covered=0.0,
                adjusted_demand_daily=float(row["adjusted_demand_daily"]),
                raw_served_demand_daily=float(row["raw_served_demand_daily"]),
                effective_person_times_daily=float(row["effective_person_times_daily"]),
                demand_service_ratio=float(row["demand_service_ratio"]),
                service_access_performance=float(row["service_access_performance"]),
                primary_load_daily=float(row.get("primary_load_daily", row["raw_served_demand_daily"])),
                overflow_load_daily=float(row.get("overflow_load_daily", 0.0)),
                unmet_load_daily=float(
                    row.get(
                        "unmet_load_daily",
                        max(0.0, float(row["adjusted_demand_daily"]) - float(row["raw_served_demand_daily"])),
                    )
                ),
                geographic_satisfaction=0.0,
                response_satisfaction=0.0,
                price_satisfaction=float(row.get("price_satisfaction", 0.0)),
                service_satisfaction=float(row["service_satisfaction"]),
            )
        )
    result.sort(key=lambda item: item.community)
    return result


def load_rq3_inputs_for_scenario(scenario_label: str, scenario_code: str) -> ScenarioBundle:
    payload = read_json(RQ4_CACHE_DIR / f"{scenario_code}.json")

    q2_summary = payload["q2_best_summary"]
    inputs = RQ3Inputs(
        metadata={
            "source": "RQ4_cache",
            "scenario": scenario_label,
            "scenario_code": scenario_code,
        },
        year5_population=load_year5_population(),
        adjusted_demand_summary=load_adjusted_demand_summary(),
        adjusted_demand_detail=load_adjusted_demand_detail(),
        q2_summary=SchemeSummaryRecord(
            scheme_type="coverage_priority",
            scheme_code=str(q2_summary["scheme_code"]),
            scheme_detail=str(q2_summary["scheme_detail"]),
            station_count=int(q2_summary["station_count"]),
            build_cost_wan=float(q2_summary["build_cost_wan"]),
            geographic_population_coverage=float(q2_summary["geographic_population_coverage"]),
            served_population_coverage=float(q2_summary["served_population_coverage"]),
            served_demand_coverage=float(q2_summary["served_demand_coverage"]),
            average_service_satisfaction=float(q2_summary["average_service_satisfaction"]),
            minimum_service_satisfaction=float(q2_summary["minimum_service_satisfaction"]),
            total_raw_served_demand_daily=float(q2_summary["total_raw_served_demand_daily"]),
            total_effective_person_times_daily=float(q2_summary["total_effective_person_times_daily"]),
            capacity_safety_rate=float(q2_summary["capacity_safety_rate"]),
            max_station_utilization=float(q2_summary["max_station_utilization"]),
            fully_safe=int(q2_summary["fully_safe"]),
            fully_served_community_count=int(q2_summary["fully_served_community_count"]),
            total_unmet_daily_demand=float(q2_summary["total_unmet_daily_demand"]),
            utilization_variance=float(q2_summary["utilization_variance"]),
            annual_net_profit_before_subsidy=float(q2_summary["annual_net_profit_before_subsidy"]),
            annual_net_profit_after_policy_subsidy=float(q2_summary["annual_net_profit_after_policy_subsidy"]),
            weighted_served_population_coverage=float(q2_summary["weighted_served_population_coverage"]),
            average_service_access_performance=float(q2_summary["average_service_access_performance"]),
            minimum_service_access_performance=float(q2_summary["minimum_service_access_performance"]),
            total_adjusted_demand_daily=float(q2_summary["total_adjusted_demand_daily"]),
            annual_revenue=float(q2_summary["annual_revenue"]),
            annual_subsidy=float(q2_summary["annual_subsidy"]),
            annual_direct_cost=float(q2_summary["annual_direct_cost"]),
            annual_fixed_cost=float(q2_summary["annual_fixed_cost"]),
            annual_depreciation=float(q2_summary["annual_depreciation"]),
            annual_total_cost=float(q2_summary["annual_total_cost"]),
            annual_net_profit=float(q2_summary["annual_net_profit"]),
            profit_rate=float(q2_summary["profit_rate"]),
            profit_compliant=int(q2_summary["profit_compliant"]),
        ),
        q2_stations=station_records_from_plan(
            str(payload["q2_best_station_plan"]),
            payload["financial_best_station_financials"],
        ),
        q2_allocations=allocation_records_from_cache(payload["financial_best_community_results"]),
    )
    candidate_profiles = RQ3_MAIN.enumerate_station_price_profiles(inputs)[:MAX_ANALYSIS_CANDIDATE_PROFILES]
    return ScenarioBundle(
        scenario_label=scenario_label,
        scenario_code=scenario_code,
        inputs=inputs,
        station_plan=str(payload["q2_best_station_plan"]),
        financial_summary=payload["financial_best_summary"],
        fairness_summary=payload["fairness_best_summary"],
        candidate_profiles=candidate_profiles,
    )


def max_abs_delta(item) -> float:
    return max((float(row.max_satisfaction_delta) for row in item.iteration_trace), default=0.0)


def compute_joint_feasible_from_eval(item, threshold: float = 0.6) -> int:
    return int(
        item.profit_compliant == 1
        and item.minimum_service_access_performance >= threshold - 1e-9
        and item.converged == 1
    )


def aggregate_profit_rate_compliant(item) -> int:
    return int(
        RQ3_MAIN.meets_profit_rate_constraint(
            float(item.annual_net_profit),
            float(item.annual_total_cost),
        )
    )


def evaluate_all_candidates(bundle: ScenarioBundle) -> List:
    evaluations: List = []
    warm_start = RQ3_MAIN.initial_service_satisfaction_by_community(bundle.inputs.q2_allocations)
    for subsidy_budget in RQ3_MAIN.subsidy_budget_candidates():
        for profile in bundle.candidate_profiles:
            choice_cache = RQ3_MAIN.precompute_community_station_choice_cache(
                inputs=bundle.inputs,
                station_prices=profile,
                subsidy_budget_per_person=subsidy_budget,
            )
            evaluations.append(
                RQ3_MAIN.evaluate_price_profile(
                    bundle.inputs,
                    profile,
                    initial_satisfaction=warm_start,
                    subsidy_budget_per_person=subsidy_budget,
                    subsidy_policy_label=f"targeted_subsidy_{subsidy_budget:.1f}",
                    choice_cache=choice_cache,
                )
            )
    return evaluations


def compute_scenario_diagnostics(evaluations: List, threshold: float = 0.6) -> Dict[str, object]:
    aggregate_profit_band_count = sum(aggregate_profit_rate_compliant(item) for item in evaluations)
    station_profit_compliant_count = sum(int(item.profit_compliant) for item in evaluations)
    access_threshold_count = sum(
        int(float(item.minimum_service_access_performance) >= threshold - 1e-9)
        for item in evaluations
    )
    converged_count = sum(int(item.converged) for item in evaluations)
    aggregate_joint_feasible_count = sum(
        int(
            aggregate_profit_rate_compliant(item) == 1
            and float(item.minimum_service_access_performance) >= threshold - 1e-9
            and int(item.converged) == 1
        )
        for item in evaluations
    )
    station_joint_feasible_count = sum(
        int(
            int(item.profit_compliant) == 1
            and float(item.minimum_service_access_performance) >= threshold - 1e-9
            and int(item.converged) == 1
        )
        for item in evaluations
    )
    best_min_access = max(
        (float(item.minimum_service_access_performance) for item in evaluations),
        default=0.0,
    )
    best_converged_min_access = max(
        (
            float(item.minimum_service_access_performance)
            for item in evaluations
            if int(item.converged) == 1
        ),
        default=0.0,
    )
    return {
        "total_candidates": len(evaluations),
        "aggregate_profit_band_count": aggregate_profit_band_count,
        "station_profit_compliant_count": station_profit_compliant_count,
        "access_threshold_count": access_threshold_count,
        "converged_count": converged_count,
        "aggregate_joint_feasible_count": aggregate_joint_feasible_count,
        "station_joint_feasible_count": station_joint_feasible_count,
        "best_min_access": round(best_min_access, 6),
        "best_converged_min_access": round(best_converged_min_access, 6),
    }


def load_main_pareto_stats() -> Dict[str, int]:
    path = OUTPUT_DIR / "3_1_pareto_frontier.csv"
    if not path.exists():
        return {"count": 0, "converged_count": 0, "non_converged_count": 0}
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
    converged_count = sum(int(row["converged"]) for row in rows)
    return {
        "count": len(rows),
        "converged_count": converged_count,
        "non_converged_count": len(rows) - converged_count,
    }


def damping_rows_for_bundle(bundle: ScenarioBundle) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    warm_start = RQ3_MAIN.initial_service_satisfaction_by_community(bundle.inputs.q2_allocations)
    for subsidy_budget in RQ3_MAIN.subsidy_budget_candidates():
        for profile_index, profile in enumerate(bundle.candidate_profiles, start=1):
            choice_cache = RQ3_MAIN.precompute_community_station_choice_cache(
                inputs=bundle.inputs,
                station_prices=profile,
                subsidy_budget_per_person=subsidy_budget,
            )
            baseline_eval = RQ3_MAIN.evaluate_price_profile(
                bundle.inputs,
                profile,
                initial_satisfaction=warm_start,
                subsidy_budget_per_person=subsidy_budget,
                subsidy_policy_label=f"targeted_subsidy_{subsidy_budget:.1f}",
                damping_lambda=1.0,
                enable_damping=False,
                choice_cache=choice_cache,
            )
            baseline_converged = int(baseline_eval.converged)
            for damping_lambda in LAMBDA_GRID:
                item = RQ3_MAIN.evaluate_price_profile(
                    bundle.inputs,
                    profile,
                    initial_satisfaction=warm_start,
                    subsidy_budget_per_person=subsidy_budget,
                    subsidy_policy_label=f"targeted_subsidy_{subsidy_budget:.1f}",
                    damping_lambda=damping_lambda,
                    enable_damping=(damping_lambda < 1.0),
                    choice_cache=choice_cache,
                )
                rows.append(
                    {
                        "scenario": bundle.scenario_label,
                        "candidate_id": f"{bundle.scenario_label}_P{profile_index:03d}_SB{subsidy_budget:.1f}",
                        "price_scheme_detail": RQ3_MAIN.evaluation_summary_row(item)["price_scheme_detail"],
                        "subsidy_policy": item.subsidy_policy_label,
                        "lambda": damping_lambda,
                        "baseline_converged_lambda_1_no_damping": baseline_converged,
                        "converged": int(item.converged),
                        "iterations": int(item.iteration_count),
                        "max_abs_delta": round(max_abs_delta(item), 8),
                        "average_service_access_performance": round(float(item.average_service_access_performance), 6),
                        "minimum_service_access_performance": round(float(item.minimum_service_access_performance), 6),
                        "annual_net_profit": round(float(item.annual_net_profit), 2),
                        "profit_rate": round(float(item.profit_rate), 6),
                        "profit_compliant": int(item.profit_compliant),
                        "aggregate_profit_rate_compliant": aggregate_profit_rate_compliant(item),
                        "station_profit_compliant": int(item.profit_compliant),
                        "feasible_station_count": int(item.feasible_station_count),
                        "joint_feasible_solution_exists": compute_joint_feasible_from_eval(item),
                    }
                )
    return rows


def fiscal_gap(item) -> float:
    annual_total_cost = float(item.annual_total_cost)
    annual_net_profit = float(item.annual_net_profit)
    profit_rate = float(item.profit_rate)
    if annual_net_profit < 0:
        return -annual_net_profit
    if profit_rate > 0.08 + 1e-9:
        return max(0.0, annual_net_profit - 0.08 * annual_total_cost)
    return 0.0


def compliance_distance_to_band(item) -> float:
    rate = float(item.profit_rate)
    if 0.0 - 1e-9 <= rate <= 0.08 + 1e-9:
        return 0.0
    if rate < 0.0:
        return -rate
    return rate - 0.08


def alpha_by_station(item) -> str:
    return RQ3_MAIN.evaluation_summary_row(item)["price_scheme_detail"]


def epsilon_rows_for_bundle(bundle: ScenarioBundle, evaluations: List) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for epsilon in EPSILON_GRID:
        feasible = [
            item for item in evaluations
            if float(item.minimum_service_access_performance) >= epsilon - 1e-9
        ]
        if not feasible:
            rows.append(
                {
                    "scenario": bundle.scenario_label,
                    "epsilon": epsilon,
                    "selection_rule": "none",
                    "feasible_count": 0,
                    "best_scheme_id": "",
                    "average_service_access_performance": "",
                    "minimum_service_access_performance": "",
                    "annual_net_profit": "",
                    "annual_total_cost": "",
                    "profit_rate": "",
                    "profit_compliant": "",
                    "aggregate_profit_rate_compliant": "NA",
                    "station_profit_compliant": "NA",
                    "feasible_station_count": "",
                    "fiscal_gap": "NA",
                    "annual_government_subsidy": "",
                    "station_plan": bundle.station_plan,
                    "alpha_by_station": "",
                    "converged": "",
                    "iterations": "",
                }
            )
            continue

        selectors = {
            "max_annual_net_profit": max(
                feasible,
                key=lambda item: (float(item.annual_net_profit), -fiscal_gap(item)),
            ),
            "closest_profit_rate_band": min(
                feasible,
                key=lambda item: (compliance_distance_to_band(item), fiscal_gap(item), -float(item.annual_net_profit)),
            ),
            "min_fiscal_gap": min(
                feasible,
                key=lambda item: (fiscal_gap(item), compliance_distance_to_band(item), -float(item.minimum_service_access_performance)),
            ),
        }
        for rule, item in selectors.items():
            rows.append(
                {
                    "scenario": bundle.scenario_label,
                    "epsilon": epsilon,
                    "selection_rule": rule,
                    "feasible_count": len(feasible),
                    "best_scheme_id": f"{bundle.scenario_label}_{rule}_{epsilon:.1f}",
                    "average_service_access_performance": round(float(item.average_service_access_performance), 6),
                    "minimum_service_access_performance": round(float(item.minimum_service_access_performance), 6),
                    "annual_net_profit": round(float(item.annual_net_profit), 2),
                    "annual_total_cost": round(float(item.annual_total_cost), 2),
                    "profit_rate": round(float(item.profit_rate), 6),
                    "profit_compliant": int(item.profit_compliant),
                    "aggregate_profit_rate_compliant": aggregate_profit_rate_compliant(item),
                    "station_profit_compliant": int(item.profit_compliant),
                    "feasible_station_count": int(item.feasible_station_count),
                    "fiscal_gap": round(fiscal_gap(item), 2),
                    "annual_government_subsidy": round(float(item.annual_government_subsidy), 2),
                    "station_plan": bundle.station_plan,
                    "alpha_by_station": alpha_by_station(item),
                    "converged": int(item.converged),
                    "iterations": int(item.iteration_count),
                }
            )
    return rows


def write_damping_notes(rows: List[Dict[str, object]], scenario_diagnostics: Dict[str, Dict[str, object]]) -> None:
    lines = [
        "# 3.3 Damping Notes",
        "",
        "## Main Findings",
        "",
    ]
    pareto_stats = load_main_pareto_stats()
    if pareto_stats["count"] > 0:
        lines.extend(
            [
                f"- RQ3 主 Pareto 前沿共 {pareto_stats['count']} 个点，其中收敛 {pareto_stats['converged_count']} 个，"
                f"未收敛 {pareto_stats['non_converged_count']} 个。",
                "- 这说明论文展示的候选点中，大部分点本身就位于离散跳变更强的高收益/高公平边界，"
                "因此非收敛并不是程序错误，而是固定点映射的结构性现象。",
                "",
            ]
        )
    for scenario in SCENARIOS:
        scenario_rows = [row for row in rows if row["scenario"] == scenario]
        by_lambda = {}
        for row in scenario_rows:
            by_lambda.setdefault(row["lambda"], []).append(row)
        lines.append(f"### {scenario}")
        diagnostics = scenario_diagnostics[scenario]
        lines.append(
            f"- evaluated_candidates={diagnostics['total_candidates']}, "
            f"aggregate_profit_band_count={diagnostics['aggregate_profit_band_count']}, "
            f"station_profit_compliant_count={diagnostics['station_profit_compliant_count']}."
        )
        for damping_lambda in LAMBDA_GRID:
            subset = by_lambda[damping_lambda]
            convergence_rate = sum(int(row["converged"]) for row in subset) / len(subset)
            lines.append(
                f"- lambda={damping_lambda:.1f}: convergence_rate={convergence_rate:.4f}, "
                f"mean_iterations={sum(int(row['iterations']) for row in subset)/len(subset):.2f}."
            )
        improved = [
            row for row in scenario_rows
            if row["baseline_converged_lambda_1_no_damping"] == 0 and row["converged"] == 1
        ]
        lines.append(
            f"- originally non-convergent but converged after damping: {len(improved)} candidate-lambda pairs."
        )
        if improved:
            sample_items = improved[:3]
            lines.append("- representative improved candidates:")
            for row in sample_items:
                lines.append(
                    f"  - {row['candidate_id']} | lambda={float(row['lambda']):.1f} | "
                    f"{row['subsidy_policy']} | min_access={float(row['minimum_service_access_performance']):.6f} | "
                    f"net_profit={float(row['annual_net_profit']):.2f}."
                )
        lines.append(
            "- if candidates still do not converge, the likely reason is the joint effect of "
            "piecewise response satisfaction, discrete primary-station switching, and capacity-driven overflow jumps."
        )
        lines.append("")
    (OUTPUT_DIR / "3_3_damping_notes.md").write_text("\n".join(lines), encoding="utf-8")


def plot_damping_convergence(rows: List[Dict[str, object]]) -> None:
    fig, ax = plt.subplots(figsize=(6.8, 4.8), dpi=220)
    for scenario in SCENARIOS:
        xs = []
        ys = []
        for damping_lambda in LAMBDA_GRID:
            subset = [row for row in rows if row["scenario"] == scenario and row["lambda"] == damping_lambda]
            xs.append(damping_lambda)
            ys.append(sum(int(row["converged"]) for row in subset) / len(subset))
        ax.plot(xs, ys, marker="o", linewidth=2, label=scenario)
    ax.set_xlabel("Damping lambda")
    ax.set_ylabel("Convergence rate")
    ax.set_title("RQ3 Damping Lambda vs Convergence Rate")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "3_3_damping_lambda_vs_convergence_rate.png", bbox_inches="tight")
    fig.savefig(OUTPUT_DIR / "3_3_damping_lambda_vs_convergence_rate.pdf", bbox_inches="tight")
    plt.close(fig)


def plot_epsilon_fiscal_gap(rows: List[Dict[str, object]]) -> None:
    fig, ax = plt.subplots(figsize=(6.8, 4.8), dpi=220)
    filtered = [row for row in rows if row["selection_rule"] == "min_fiscal_gap" and row["feasible_count"] > 0]
    for scenario in SCENARIOS:
        subset = [row for row in filtered if row["scenario"] == scenario]
        ax.plot(
            [float(row["epsilon"]) for row in subset],
            [float(row["fiscal_gap"]) / 1e4 for row in subset],
            marker="o",
            linewidth=2,
            label=scenario,
        )
    ax.set_xlabel("Minimum accessibility threshold epsilon")
    ax.set_ylabel("Fiscal gap (10^4 CNY/year)")
    ax.set_title("RQ3 Epsilon Constraint vs Minimum Fiscal Gap")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "3_3_epsilon_vs_fiscal_gap.png", bbox_inches="tight")
    fig.savefig(OUTPUT_DIR / "3_3_epsilon_vs_fiscal_gap.pdf", bbox_inches="tight")
    plt.close(fig)


def plot_epsilon_access(rows: List[Dict[str, object]]) -> None:
    fig, ax = plt.subplots(figsize=(6.8, 4.8), dpi=220)
    filtered = [row for row in rows if row["selection_rule"] == "max_annual_net_profit" and row["feasible_count"] > 0]
    for scenario in SCENARIOS:
        subset = [row for row in filtered if row["scenario"] == scenario]
        xs = [float(row["epsilon"]) for row in subset]
        ax.plot(xs, [float(row["average_service_access_performance"]) for row in subset], marker="o", linewidth=2, label=f"{scenario} avg")
        ax.plot(xs, [float(row["minimum_service_access_performance"]) for row in subset], marker="s", linewidth=2, linestyle="--", label=f"{scenario} min")
    ax.set_xlabel("Minimum accessibility threshold epsilon")
    ax.set_ylabel("Accessibility performance")
    ax.set_title("RQ3 Epsilon Constraint vs Best Accessibility")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(ncol=2, fontsize=8)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "3_3_epsilon_vs_access.png", bbox_inches="tight")
    fig.savefig(OUTPUT_DIR / "3_3_epsilon_vs_access.pdf", bbox_inches="tight")
    plt.close(fig)


def plot_s0_s4_gap_comparison(rows: List[Dict[str, object]]) -> None:
    fig, ax = plt.subplots(figsize=(7.2, 4.8), dpi=220)
    comparison_rows = [
        row
        for row in rows
        if row["selection_rule"] == "min_fiscal_gap"
        or (row["selection_rule"] == "none" and row["feasible_count"] == "0")
    ]
    epsilons = sorted({float(row["epsilon"]) for row in comparison_rows})
    width = 0.35
    s0 = {}
    s4 = {}
    infeasible_annotations = []
    for row in comparison_rows:
        epsilon = float(row["epsilon"])
        if row["feasible_count"] == "0":
            infeasible_annotations.append((row["scenario"], epsilon))
            continue
        value = float(row["fiscal_gap"]) / 1e4
        if row["scenario"] == "S0_baseline":
            s0[epsilon] = value
        else:
            s4[epsilon] = value
    x_positions = list(range(len(epsilons)))
    s0_values = [s0.get(e, float("nan")) for e in epsilons]
    s4_values = [s4.get(e, float("nan")) for e in epsilons]
    s0_heights = [0.0 if value != value else value for value in s0_values]
    s4_heights = [0.0 if value != value else value for value in s4_values]
    ax.bar([x - width / 2 for x in x_positions], s0_heights, width=width, label="S0_baseline")
    ax.bar([x + width / 2 for x in x_positions], s4_heights, width=width, label="S4_budget_140")
    ymax = max(s0_heights + s4_heights + [0.0])
    offset = max(0.15, ymax * 0.03)
    for scenario, epsilon in infeasible_annotations:
        idx = epsilons.index(epsilon)
        xpos = idx - width / 2 if scenario == "S0_baseline" else idx + width / 2
        ax.text(
            xpos,
            ymax + offset,
            "NA",
            ha="center",
            va="bottom",
            rotation=90,
            fontsize=8,
            color="#444444",
        )
    ax.set_xticks(x_positions)
    ax.set_xticklabels([f"{e:.1f}" for e in epsilons])
    ax.set_xlabel("Minimum accessibility threshold epsilon")
    ax.set_ylabel("Fiscal gap (10^4 CNY/year)")
    ax.set_title("S0 vs S4 Fiscal Gap Comparison (NA = infeasible)")
    ax.grid(True, axis="y", linestyle="--", alpha=0.5)
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "3_3_s0_vs_s4_fiscal_gap_comparison.png", bbox_inches="tight")
    fig.savefig(OUTPUT_DIR / "3_3_s0_vs_s4_fiscal_gap_comparison.pdf", bbox_inches="tight")
    plt.close(fig)


def write_stability_notes(
    damping_rows: List[Dict[str, object]],
    epsilon_rows: List[Dict[str, object]],
    scenario_diagnostics: Dict[str, Dict[str, object]],
) -> None:
    lines = [
        "# 3.3 Stability Enhancement Notes",
        "",
        "## 1. 为什么固定点可能不收敛",
        "",
        "- 当前迭代不是连续光滑映射，而是受到响应满意度分段函数、主站离散改选和容量分流线性规划共同影响。",
        "- 当若干社区在两个候选主站之间来回切换时，站点负载与响应满意度会形成跳变，导致 ABAB 型振荡。",
        "",
        "## 2. 阻尼是否改善收敛",
        "",
    ]
    for scenario in SCENARIOS:
        scenario_rows = [row for row in damping_rows if row["scenario"] == scenario]
        diagnostics = scenario_diagnostics[scenario]
        lines.append(f"### {scenario}")
        for damping_lambda in LAMBDA_GRID:
            subset = [row for row in scenario_rows if row["lambda"] == damping_lambda]
            rate = sum(int(row["converged"]) for row in subset) / len(subset)
            lines.append(f"- lambda={damping_lambda:.1f}: convergence_rate={rate:.4f}.")
        lines.append(
            f"- aggregate_profit_band_count={diagnostics['aggregate_profit_band_count']}, "
            f"station_profit_compliant_count={diagnostics['station_profit_compliant_count']}, "
            f"access_threshold_count@0.6={diagnostics['access_threshold_count']}, "
            f"converged_count={diagnostics['converged_count']}."
        )
        lines.append(
            f"- aggregate_joint_feasible_count={diagnostics['aggregate_joint_feasible_count']}, "
            f"station_joint_feasible_count={diagnostics['station_joint_feasible_count']}."
        )
        lines.append("")

    lines.extend(
        [
            "## 3. 不同公平阈值下财务可持续性变化",
            "",
            "- 采用 epsilon-constraint 后，可以直接读取达到不同最低可及性阈值所需的最小财政缺口。",
            "- 若 fiscal_gap=0 且 aggregate_profit_rate_compliant=1，但 station_profit_compliant=0，说明方案总利润率已落入 [0,0.08]，"
            "但仍有至少一个站点未满足主模型的逐站利润率约束，因此 joint_feasible_solution_exists 仍为 false。",
            "- 如果某个 epsilon 下 feasible_count=0，表示在当前候选空间和定价口径下不存在达到该阈值的候选方案；这时不能把财政缺口解释为 0，而应解释为“当前候选空间内不可达”。",
            "",
            "## 4. S4 扩容是否降低公平达标财政缺口",
            "",
        ]
    )
    gap_rows = [row for row in epsilon_rows if row["selection_rule"] == "min_fiscal_gap"]
    for epsilon in [0.7, 0.8]:
        s0 = next((row for row in gap_rows if row["scenario"] == "S0_baseline" and abs(float(row["epsilon"]) - epsilon) < 1e-9), None)
        s4 = next((row for row in gap_rows if row["scenario"] == "S4_budget_140" and abs(float(row["epsilon"]) - epsilon) < 1e-9), None)
        s0_msg = (
            f"feasible_count={s0['feasible_count']}, fiscal_gap={s0['fiscal_gap']}"
            if s0 and s0["feasible_count"] != "0"
            else "feasible_count=0, fiscal_gap=NA"
        )
        s4_msg = (
            f"feasible_count={s4['feasible_count']}, fiscal_gap={s4['fiscal_gap']}, "
            f"aggregate_profit_rate_compliant={s4['aggregate_profit_rate_compliant']}, "
            f"station_profit_compliant={s4['station_profit_compliant']}, converged={s4['converged']}"
            if s4 and s4["feasible_count"] != "0"
            else "feasible_count=0, fiscal_gap=NA"
        )
        lines.append(f"- epsilon={epsilon:.1f}: S0 {s0_msg}; S4 {s4_msg}.")
    lines.extend(
        [
            "",
            "## 5. 适合写进正文的结论",
            "",
            "- 可以强调：Pareto 前沿中多数点不收敛，主要来自离散选站与容量分流导致的结构性振荡，而不是程序计算错误。",
            "- 可以强调：阻尼在 S0 基本无改善，在 S4 仅对少量边界候选点有效，因此阻尼是数值稳定化手段，不是可行性创造手段。",
            "- 可以强调：S0 在当前布局下连 epsilon=0.4 都无法达到，说明高公平阈值不是简单追加补贴即可解决，而需要预算扩容或站点布局升级。",
            "- 可以强调：S4 扩容后，epsilon=0.7 与 0.8 均已有候选方案，且存在 fiscal_gap=0 的方案；但由于逐站利润率尚未全部合规，joint_feasible_solution_exists 仍然为 false。",
            "",
            "## 6. 适合放附录的结果",
            "",
            "- 全部 lambda x 候选点的明细表。",
            "- 全部 epsilon x 选择规则的对照表。",
            "- 站点级利润率未达标但方案总利润率达标的诊断明细。",
            "",
            "## 7. 不得夸大的结论",
            "",
            "- 不能写成“阻尼后模型全部收敛”。",
            "- 不能写成“当前政策已实现财务与公平双达标”；S4 只能写成“总利润率与公平阈值可同时达到，但逐站利润率约束仍未全部满足”。",
            "- 不能把 epsilon-constraint 下的财政缺口理解为现实中唯一所需财政投入，只能解释为在当前候选空间下的模型内最小补足量。",
        ]
    )
    (OUTPUT_DIR / "3_3_stability_enhancement_notes.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    bundles = [load_rq3_inputs_for_scenario(label, code) for label, code in SCENARIOS.items()]
    damping_rows: List[Dict[str, object]] = []
    epsilon_rows: List[Dict[str, object]] = []
    scenario_diagnostics: Dict[str, Dict[str, object]] = {}
    for bundle in bundles:
        evaluations = evaluate_all_candidates(bundle)
        scenario_diagnostics[bundle.scenario_label] = compute_scenario_diagnostics(evaluations)
        damping_rows.extend(damping_rows_for_bundle(bundle))
        epsilon_rows.extend(epsilon_rows_for_bundle(bundle, evaluations))

    write_csv(OUTPUT_DIR / "3_3_damping_sensitivity.csv", damping_rows)
    write_csv(OUTPUT_DIR / "3_3_epsilon_constraint_summary.csv", epsilon_rows)
    write_damping_notes(damping_rows, scenario_diagnostics)
    write_stability_notes(damping_rows, epsilon_rows, scenario_diagnostics)
    plot_damping_convergence(damping_rows)
    plot_epsilon_fiscal_gap(epsilon_rows)
    plot_epsilon_access(epsilon_rows)
    plot_s0_s4_gap_comparison(epsilon_rows)
    print("Generated RQ3 stability extension outputs for S0 and S4.")


if __name__ == "__main__":
    main()
