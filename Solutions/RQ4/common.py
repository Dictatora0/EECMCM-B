from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set
import csv
import json
import math
import sys


RQ4_DIR = Path(__file__).resolve().parent
ROOT = RQ4_DIR.parents[1]
OUTPUT_DIR = RQ4_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)
CACHE_DIR = RQ4_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)


def load_module(module_name: str, path: Path):
    spec = spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load module {module_name} from {path}")
    module = module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@contextmanager
def temporarily_bind_common(module):
    previous = sys.modules.get("common")
    sys.modules["common"] = module
    try:
        yield
    finally:
        if previous is None:
            sys.modules.pop("common", None)
        else:
            sys.modules["common"] = previous


RQ1_COMMON = load_module("rq4_rq1_common_module", ROOT / "Solutions" / "RQ1" / "common.py")
RQ2_COMMON = load_module("rq4_rq2_common_module", ROOT / "Solutions" / "RQ2" / "common.py")
RQ3_COMMON = load_module("rq4_rq3_common_module", ROOT / "Solutions" / "RQ3" / "common.py")
with temporarily_bind_common(RQ2_COMMON):
    RQ2_MAIN = load_module("rq4_rq2_main_module", ROOT / "Solutions" / "RQ2" / "2_1.py")
with temporarily_bind_common(RQ3_COMMON):
    RQ3_MAIN = load_module("rq4_rq3_main_module", ROOT / "Solutions" / "RQ3" / "3_1.py")

SERVICE_ORDER = RQ1_COMMON.SERVICE_ORDER
BASELINE_PARAMETERS = {
    "elderly_growth_rate": 0.07,
    "p12": 0.045,
    "p23": 0.10,
    "fixed_cost_multiplier": 1.0,
    "budget_limit": 120.0,
}
CAPACITY_SAFE_THRESHOLD = 0.85
CACHE_VERSION = "rq4_scenarios_v6"
PARAMETER_ALIASES = {
    "elder_growth_rate": "elderly_growth_rate",
    "self_to_semi": "p12",
    "semi_to_disabled": "p23",
}


@dataclass(frozen=True)
class ScenarioDefinition:
    code: str
    name: str
    parameter_changes: Dict[str, float]


@dataclass(frozen=True)
class ScenarioResult:
    scenario_code: str
    scenario_name: str
    financial_best: object
    satisfaction_best: object
    q2_best: object
    q2_safe: object


def scenario_definitions() -> List[ScenarioDefinition]:
    return [
        ScenarioDefinition(code="S0", name="基准情景", parameter_changes={}),
        ScenarioDefinition(code="S1", name="老人增长率提高", parameter_changes={"elderly_growth_rate": 0.08}),
        ScenarioDefinition(code="S2", name="转移概率变化", parameter_changes={"p12": 0.055, "p23": 0.095}),
        ScenarioDefinition(code="S3", name="固定成本上升", parameter_changes={"fixed_cost_multiplier": 1.2}),
        ScenarioDefinition(code="S4", name="预算提高", parameter_changes={"budget_limit": 140.0}),
    ]


def scenario_parameter_dict(scenario: ScenarioDefinition) -> Dict[str, float]:
    normalized_changes = {
        PARAMETER_ALIASES.get(key, key): value
        for key, value in scenario.parameter_changes.items()
    }
    return {**BASELINE_PARAMETERS, **normalized_changes}


def scenario_requires_rerun_from_rq1(scenario: ScenarioDefinition) -> bool:
    normalized_keys = {PARAMETER_ALIASES.get(key, key) for key in scenario.parameter_changes}
    return bool({"elderly_growth_rate", "p12", "p23"} & normalized_keys)


def scenario_execution_path(scenario: ScenarioDefinition) -> str:
    return "rerun_rq1_rq2_rq3" if scenario_requires_rerun_from_rq1(scenario) or scenario.code == "S0" else "reuse_rq1_rerun_rq2_rq3"


def compute_relative_change(new_value: float, baseline_value: float) -> float | str:
    if abs(baseline_value) <= 1e-12:
        return "NA"
    return (new_value - baseline_value) / baseline_value


def perturbed_parameter_label(scenario: ScenarioDefinition) -> str:
    keys = {PARAMETER_ALIASES.get(key, key) for key in scenario.parameter_changes}
    if keys == {"elderly_growth_rate"}:
        return "elderly_growth_rate"
    if keys == {"p12", "p23"}:
        return "transition_probabilities"
    if keys == {"fixed_cost_multiplier"}:
        return "fixed_cost_multiplier"
    if keys == {"budget_limit"}:
        return "budget_limit"
    return "+".join(sorted(keys)) if keys else "baseline"


def compute_scenario_parameter_relative_change(
    scenario: ScenarioDefinition,
    baseline_parameters: Dict[str, float],
) -> float:
    if not scenario.parameter_changes:
        return 0.0
    values: List[float] = []
    normalized_baseline = {
        PARAMETER_ALIASES.get(key, key): value
        for key, value in baseline_parameters.items()
    }
    normalized_changes = {
        PARAMETER_ALIASES.get(key, key): value
        for key, value in scenario.parameter_changes.items()
    }
    for key in sorted(normalized_changes):
        baseline = float(normalized_baseline[key])
        scenario_value = float(normalized_changes[key])
        if abs(baseline) <= 1e-12:
            raise ValueError(f"Baseline parameter {key} is zero; cannot compute relative change.")
        values.append(abs(scenario_value - baseline) / abs(baseline))
    return sum(values) / len(values)


def compute_sensitivity_coefficient(
    metric_relative_change: float | str,
    parameter_relative_change: float,
) -> float | str:
    if metric_relative_change == "NA" or abs(parameter_relative_change) <= 1e-12:
        return "NA"
    return float(metric_relative_change) / parameter_relative_change


def classify_sensitivity_level(sensitivity_coefficient: float | str) -> str:
    if sensitivity_coefficient == "NA":
        return "NA"
    value = abs(float(sensitivity_coefficient))
    if value < 0.3:
        return "low"
    if value < 0.8:
        return "medium"
    return "high"


def compute_jaccard_location_stability(baseline_locations: Set[str], scenario_locations: Set[str]) -> float:
    union = baseline_locations | scenario_locations
    if not union:
        return 1.0
    return len(baseline_locations & scenario_locations) / len(union)


def build_station_scale_map(station_plan: str) -> Dict[str, str]:
    result: Dict[str, str] = {}
    if not station_plan:
        return result
    for token in station_plan.split(";"):
        if not token:
            continue
        community, scale = token.split("-", 1)
        result[community] = scale
    return result


def build_station_plan_text(scale_map: Dict[str, str]) -> str:
    return ";".join(f"{community}-{scale_map[community]}" for community in sorted(scale_map))


def compute_layout_scale_consistency(
    baseline_scale_map: Dict[str, str],
    scenario_scale_map: Dict[str, str],
) -> float:
    union = set(baseline_scale_map) | set(scenario_scale_map)
    if not union:
        return 1.0
    consistent = sum(
        1
        for community in union
        if baseline_scale_map.get(community) == scenario_scale_map.get(community)
        and baseline_scale_map.get(community) is not None
        and scenario_scale_map.get(community) is not None
    )
    return consistent / len(union)


def compute_stability_from_metric(baseline_value: float, scenario_value: float) -> float:
    return max(0.0, 1.0 - abs(scenario_value - baseline_value))


def compute_financial_compliance_rate(financial_flags: Sequence[int]) -> float:
    if not financial_flags:
        return 1.0
    return sum(1 for flag in financial_flags if int(flag) == 1) / len(financial_flags)


def compute_capacity_safety_rate(utilizations: Sequence[float], threshold: float = CAPACITY_SAFE_THRESHOLD) -> float:
    if not utilizations:
        return 1.0
    return sum(1 for value in utilizations if float(value) <= threshold + 1e-12) / len(utilizations)


def compute_max_station_utilization(utilizations: Sequence[float]) -> float:
    return max((float(value) for value in utilizations), default=0.0)


def fully_safe_from_utilizations(utilizations: Sequence[float], threshold: float = CAPACITY_SAFE_THRESHOLD) -> int:
    return int(compute_max_station_utilization(utilizations) <= threshold + 1e-12)


def round_or_na(value: float | str, digits: int = 6) -> float | str:
    if value == "NA":
        return value
    return round(float(value), digits)


def write_csv(path: Path, rows: List[Dict[str, object]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, payload: Dict[str, object]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> Dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def summarize_monte_carlo_metric(
    name: str,
    values: Sequence[float],
    risk_threshold: float,
    lower_is_risk: bool,
) -> Dict[str, float | str]:
    ordered = sorted(float(value) for value in values)
    assert ordered, f"{name} requires at least one Monte Carlo sample"

    def percentile(p: float) -> float:
        if len(ordered) == 1:
            return ordered[0]
        position = (len(ordered) - 1) * p
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return ordered[lower]
        weight = position - lower
        return ordered[lower] * (1.0 - weight) + ordered[upper] * weight

    mean = sum(ordered) / len(ordered)
    if lower_is_risk:
        risk_count = sum(1 for value in ordered if value < risk_threshold - 1e-12)
    else:
        risk_count = sum(1 for value in ordered if value > risk_threshold + 1e-12)
    return {
        "metric": name,
        "mean": mean,
        "min": ordered[0],
        "p10": percentile(0.10),
        "p50": percentile(0.50),
        "p90": percentile(0.90),
        "max": ordered[-1],
        "risk_probability": risk_count / len(ordered),
    }


def station_location_set(q2_evaluation) -> Set[str]:
    return {station.community for station in q2_evaluation.stations}


def q2_summary_row(scenario: ScenarioDefinition, evaluation) -> Dict[str, object]:
    row = RQ2_MAIN.evaluation_to_summary_row(evaluation)
    parameters = scenario_parameter_dict(scenario)
    return {
        "scenario": scenario.code,
        "budget_limit": parameters["budget_limit"],
        "fixed_cost_multiplier": parameters["fixed_cost_multiplier"],
        "p12": parameters["p12"],
        "p23": parameters["p23"],
        "elderly_growth_rate": parameters["elderly_growth_rate"],
        "station_plan": row["scheme_detail"],
        "total_construction_cost": row["build_cost_wan"],
        "geographic_population_coverage": row["geographic_population_coverage"],
        "served_population_coverage": row["served_population_coverage"],
        "weighted_served_population_coverage": row["weighted_served_population_coverage"],
        "served_demand_coverage": row["served_demand_coverage"],
        "average_service_access_performance": row["average_service_access_performance"],
        "minimum_service_access_performance": row["minimum_service_access_performance"],
        "capacity_safety_rate": row["capacity_safety_rate"],
        "max_station_utilization": row["max_station_utilization"],
        "fully_safe": row["fully_safe"],
        "annual_net_profit_before_subsidy": row["annual_net_profit_before_subsidy"],
        "annual_net_profit_after_policy_subsidy": row["annual_net_profit_after_policy_subsidy"],
    }


def q3_summary_row(
    scenario: ScenarioDefinition,
    scheme_type: str,
    evaluation,
    station_plan: str,
    fiscal_gap_if_any: float,
) -> Dict[str, object]:
    summary = RQ3_MAIN.evaluation_summary_row(evaluation)
    parameters = scenario_parameter_dict(scenario)
    return {
        "scenario": scenario.code,
        "budget_limit": parameters["budget_limit"],
        "fixed_cost_multiplier": parameters["fixed_cost_multiplier"],
        "p12": parameters["p12"],
        "p23": parameters["p23"],
        "elderly_growth_rate": parameters["elderly_growth_rate"],
        "scheme_type": scheme_type,
        "station_plan": station_plan,
        "served_population_coverage": summary["served_population_coverage"],
        "weighted_served_population_coverage": summary["weighted_served_population_coverage"],
        "served_demand_coverage": summary["served_demand_coverage"],
        "average_service_access_performance": summary["average_service_access_performance"],
        "minimum_service_access_performance": summary["minimum_service_access_performance"],
        "annual_government_subsidy": summary["annual_government_subsidy"],
        "annual_net_profit": summary["annual_net_profit"],
        "profit_rate": summary["profit_rate"],
        "profit_compliant": summary["profit_compliant"],
        "converged": summary["converged"],
        "iterations": summary["iterations"],
        "fiscal_gap_if_any": round(fiscal_gap_if_any, 2),
    }


def sensitivity_row(
    scenario: ScenarioDefinition,
    metric_name: str,
    baseline_value: float,
    scenario_value: float,
    baseline_parameters: Dict[str, float],
) -> Dict[str, object]:
    absolute_change = scenario_value - baseline_value
    metric_relative_change = compute_relative_change(scenario_value, baseline_value)
    parameter_relative_change = compute_scenario_parameter_relative_change(scenario, baseline_parameters)
    coefficient = compute_sensitivity_coefficient(metric_relative_change, parameter_relative_change)
    return {
        "scenario": scenario.code,
        "perturbed_parameter": perturbed_parameter_label(scenario),
        "parameter_relative_change": round(parameter_relative_change, 6),
        "metric": metric_name,
        "baseline_value": round(float(baseline_value), 6),
        "scenario_value": round(float(scenario_value), 6),
        "metric_absolute_change": round(float(absolute_change), 6),
        "metric_relative_change": round_or_na(metric_relative_change, 6),
        "sensitivity_coefficient": round_or_na(coefficient, 6),
        "sensitivity_level": classify_sensitivity_level(coefficient),
    }


def robustness_row(
    scenario: ScenarioDefinition,
    baseline_station_plan: str,
    scenario_station_plan: str,
    baseline_q2_metric_map: Dict[str, float],
    scenario_q2_metric_map: Dict[str, float],
    baseline_q3_financial_performance: float,
    scenario_q3_financial_performance: float,
    baseline_q3_satisfaction_performance: float,
    scenario_q3_satisfaction_performance: float,
    station_profit_flags: Sequence[int],
    station_utilizations: Sequence[float],
) -> Dict[str, object]:
    baseline_scale_map = build_station_scale_map(baseline_station_plan)
    scenario_scale_map = build_station_scale_map(scenario_station_plan)
    max_station_utilization = compute_max_station_utilization(station_utilizations)
    return {
        "scenario": scenario.code,
        "RS_loc": round(compute_jaccard_location_stability(set(baseline_scale_map), set(scenario_scale_map)), 6),
        "RS_layout": round(compute_layout_scale_consistency(baseline_scale_map, scenario_scale_map), 6),
        "geographic_population_coverage_stability": round(
            compute_stability_from_metric(
                baseline_q2_metric_map["geographic_population_coverage"],
                scenario_q2_metric_map["geographic_population_coverage"],
            ),
            6,
        ),
        "served_population_coverage_stability": round(
            compute_stability_from_metric(
                baseline_q2_metric_map["served_population_coverage"],
                scenario_q2_metric_map["served_population_coverage"],
            ),
            6,
        ),
        "weighted_served_population_coverage_stability": round(
            compute_stability_from_metric(
                baseline_q2_metric_map["weighted_served_population_coverage"],
                scenario_q2_metric_map["weighted_served_population_coverage"],
            ),
            6,
        ),
        "served_demand_coverage_stability": round(
            compute_stability_from_metric(
                baseline_q2_metric_map["served_demand_coverage"],
                scenario_q2_metric_map["served_demand_coverage"],
            ),
            6,
        ),
        "q2_service_access_performance_stability": round(
            compute_stability_from_metric(
                baseline_q2_metric_map["average_service_access_performance"],
                scenario_q2_metric_map["average_service_access_performance"],
            ),
            6,
        ),
        "q3_financial_scheme_performance_stability": round(
            compute_stability_from_metric(
                baseline_q3_financial_performance,
                scenario_q3_financial_performance,
            ),
            6,
        ),
        "q3_satisfaction_scheme_performance_stability": round(
            compute_stability_from_metric(
                baseline_q3_satisfaction_performance,
                scenario_q3_satisfaction_performance,
            ),
            6,
        ),
        "financial_compliance_rate": round(compute_financial_compliance_rate(station_profit_flags), 6),
        "capacity_safety_rate": round(compute_capacity_safety_rate(station_utilizations), 6),
        "max_station_utilization": round(max_station_utilization, 6),
        "fully_safe": fully_safe_from_utilizations(station_utilizations),
    }
