from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set
import csv
import json
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
    fairness_best: object
    q2_best: object
    q2_safe: object


def scenario_definitions() -> List[ScenarioDefinition]:
    return [
        ScenarioDefinition(code="S0", name="基准情景", parameter_changes={}),
        ScenarioDefinition(code="S1", name="老人增长率提高", parameter_changes={"elder_growth_rate": 0.08}),
        ScenarioDefinition(
            code="S2",
            name="转移概率变化",
            parameter_changes={"self_to_semi": 0.055, "semi_to_disabled": 0.095},
        ),
        ScenarioDefinition(code="S3", name="固定成本上升", parameter_changes={"fixed_cost_multiplier": 1.2}),
        ScenarioDefinition(code="S4", name="预算提高", parameter_changes={"budget_limit": 140.0}),
    ]


def scenario_requires_rerun_from_rq1(scenario: ScenarioDefinition) -> bool:
    keys = set(scenario.parameter_changes)
    return bool({"elder_growth_rate", "self_to_semi", "semi_to_disabled"} & keys)


def compute_relative_change(new_value: float, baseline_value: float) -> float:
    if abs(baseline_value) <= 1e-12:
        return 0.0 if abs(new_value) <= 1e-12 else 1.0
    return (new_value - baseline_value) / baseline_value


def compute_average_relative_parameter_change(
    baseline_values: Dict[str, float],
    scenario_values: Dict[str, float],
) -> float:
    keys = sorted(set(baseline_values) & set(scenario_values))
    if not keys:
        return 0.0
    values = []
    for key in keys:
        baseline = baseline_values[key]
        scenario = scenario_values[key]
        if abs(baseline) <= 1e-12:
            values.append(0.0 if abs(scenario) <= 1e-12 else 1.0)
        else:
            values.append(abs(scenario - baseline) / abs(baseline))
    return sum(values) / len(values)


def compute_sensitivity_coefficient(metric_relative_change: float, parameter_relative_change: float) -> float:
    if abs(parameter_relative_change) <= 1e-12:
        return 0.0
    return metric_relative_change / parameter_relative_change


def compute_location_stability(baseline_locations: Set[str], scenario_locations: Set[str]) -> float:
    if not baseline_locations:
        return 1.0
    return len(baseline_locations & scenario_locations) / len(baseline_locations)


def compute_coverage_stability(baseline_coverage: float, scenario_coverage: float) -> float:
    return max(0.0, 1.0 - abs(scenario_coverage - baseline_coverage))


def compute_satisfaction_stability(baseline_satisfaction: float, scenario_satisfaction: float) -> float:
    return max(0.0, 1.0 - abs(scenario_satisfaction - baseline_satisfaction))


def compute_financial_compliance_stability(financial_flags: Sequence[int]) -> float:
    if not financial_flags:
        return 1.0
    return sum(1 for flag in financial_flags if flag == 1) / len(financial_flags)


def compute_capacity_safety_stability(utilizations: Sequence[float], threshold: float = 0.85) -> float:
    if not utilizations:
        return 1.0
    return sum(1 for value in utilizations if value <= threshold + 1e-12) / len(utilizations)


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


def station_location_set(q2_evaluation) -> Set[str]:
    return {station.community for station in q2_evaluation.stations}


def q2_summary_row(scenario: ScenarioDefinition, scheme_label: str, evaluation) -> Dict[str, object]:
    return {
        "scenario_code": scenario.code,
        "scenario_name": scenario.name,
        "scheme_label": scheme_label,
        "station_count": len(evaluation.stations),
        "station_locations": ";".join(sorted(station.community for station in evaluation.stations)),
        "build_cost_wan": round(sum(station.build_cost_wan for station in evaluation.stations), 4),
        "geographic_population_coverage": round(evaluation.geographic_population_coverage, 6),
        "served_population_coverage": round(evaluation.served_population_coverage, 6),
        "served_demand_coverage": round(evaluation.served_demand_coverage, 6),
        "average_service_satisfaction": round(evaluation.average_service_satisfaction, 6),
        "minimum_service_satisfaction": round(evaluation.minimum_service_satisfaction, 6),
        "annual_net_profit_before_subsidy": round(evaluation.annual_net_profit_before_subsidy, 2),
        "annual_net_profit_after_policy_subsidy": round(evaluation.annual_net_profit_after_policy_subsidy, 2),
        "capacity_safety_rate": round(evaluation.capacity_safety_rate, 6),
        "max_station_utilization": round(evaluation.max_station_utilization, 6),
        "fully_safe": evaluation.fully_safe,
    }


def q3_summary_row(scenario: ScenarioDefinition, scheme_label: str, evaluation) -> Dict[str, object]:
    return {
        "scenario_code": scenario.code,
        "scenario_name": scenario.name,
        "scheme_label": scheme_label,
        **RQ3_MAIN.evaluation_summary_row(evaluation),
    }


def sensitivity_row(
    scenario: ScenarioDefinition,
    scheme_label: str,
    metric_name: str,
    baseline_value: float,
    scenario_value: float,
    baseline_parameters: Dict[str, float],
    scenario_parameters: Dict[str, float],
) -> Dict[str, object]:
    metric_change = compute_relative_change(scenario_value, baseline_value)
    parameter_change = compute_average_relative_parameter_change(baseline_parameters, scenario_parameters)
    return {
        "scenario_code": scenario.code,
        "scenario_name": scenario.name,
        "scheme_label": scheme_label,
        "metric_name": metric_name,
        "baseline_value": round(baseline_value, 6),
        "scenario_value": round(scenario_value, 6),
        "metric_relative_change": round(metric_change, 6),
        "parameter_relative_change": round(parameter_change, 6),
        "sensitivity_coefficient": round(
            compute_sensitivity_coefficient(metric_change, parameter_change),
            6,
        ),
    }


def robustness_row(
    scenario: ScenarioDefinition,
    scheme_label: str,
    baseline_q2,
    scenario_q2,
    q3_evaluation,
) -> Dict[str, object]:
    station_profit_flags = [row["profit_compliant"] for row in q3_evaluation.station_financials]
    station_profit_rates = [row["profit_rate"] for row in q3_evaluation.station_financials]
    return {
        "scenario_code": scenario.code,
        "scenario_name": scenario.name,
        "scheme_label": scheme_label,
        "RS_loc": round(
            compute_location_stability(station_location_set(baseline_q2), station_location_set(scenario_q2)),
            6,
        ),
        "RS_cov": round(
            compute_coverage_stability(
                baseline_q2.served_demand_coverage,
                scenario_q2.served_demand_coverage,
            ),
            6,
        ),
        "RS_sat": round(
            compute_satisfaction_stability(
                baseline_q2.average_service_satisfaction,
                scenario_q2.average_service_satisfaction,
            ),
            6,
        ),
        "RS_fin": round(compute_financial_compliance_stability(station_profit_flags), 6),
        "RS_cap": round(
            compute_capacity_safety_stability(
                [metric.utilization for metric in scenario_q2.station_metrics],
                threshold=0.85,
            ),
            6,
        ),
        "profit_compliant": q3_evaluation.profit_compliant,
        "fair_satisfaction_compliant": q3_evaluation.fair_satisfaction_compliant,
        "minimum_service_satisfaction": round(q3_evaluation.minimum_service_satisfaction, 6),
        "max_station_utilization": round(scenario_q2.max_station_utilization, 6),
        "capacity_safety_rate": round(scenario_q2.capacity_safety_rate, 6),
        "avg_station_profit_rate": round(
            sum(station_profit_rates) / len(station_profit_rates) if station_profit_rates else 0.0,
            6,
        ),
    }
