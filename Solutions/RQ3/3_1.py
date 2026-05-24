from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
import argparse
import json
import math
import random
import sys
import time
from scipy.optimize import linprog

from common import (
    AdjustedDemandDetailRecord,
    AdjustedDemandSummaryRecord,
    AllocationRecord,
    DAYS_PER_MONTH,
    NON_EMERGENCY_SERVICES,
    OUTPUT_DIR,
    RQ3Inputs,
    SchemeSummaryRecord,
    SERVICE_ORDER,
    StationRecord,
    Year5PopulationRecord,
    CARE_LEVEL_ORDER,
    adjusted_demand_summary_map,
    adjusted_demand_detail_map,
    allocations_by_community,
    base_price_by_service,
    load_distance_matrix,
    load_satisfaction_rules,
    direct_cost_by_service,
    initial_service_satisfaction_by_community,
    load_community_data,
    load_adjusted_demand_detail,
    load_adjusted_demand_summary,
    load_year5_population,
    load_rq3_inputs,
    population_by_community,
    recommended_price_candidates,
    stations_by_community,
    write_csv,
)


RQ3_DIR = Path(__file__).resolve().parent
ROOT = RQ3_DIR.parents[1]
RQ2_COMMON_PATH = ROOT / "Solutions" / "RQ2" / "common.py"
RQ2_COMMON_SPEC = spec_from_file_location("rq3_rq2_common_module", RQ2_COMMON_PATH)
if RQ2_COMMON_SPEC is None or RQ2_COMMON_SPEC.loader is None:
    raise RuntimeError(f"Failed to load RQ2 common module from {RQ2_COMMON_PATH}")
RQ2_COMMON = module_from_spec(RQ2_COMMON_SPEC)
sys.modules[RQ2_COMMON_SPEC.name] = RQ2_COMMON
RQ2_COMMON_SPEC.loader.exec_module(RQ2_COMMON)


FIXED_POINT_EPSILON = 1e-4
MAX_FIXED_POINT_ITERATIONS = 30
SUBSIDY_PER_EFFECTIVE_PERSON_TIME = 2.0
MAX_PROFIT_RATE = 0.08
MIN_PROFIT_RATE = 0.0
DEFAULT_DAMPING_LAMBDA = 0.5
DEFAULT_MIN_SERVICE_ACCESS_THRESHOLD = 0.6
SATISFACTION_WEIGHTS = {"distance": 0.2, "response": 0.3, "price": 0.5}
OVERFLOW_UTILITY_PENALTY = 0.08
EARLY_STOP_NEGATIVE_PROFIT_MARGIN = -0.05
PRICE_PREMIUM_MULTIPLIERS = [1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.8, 2.0]
RESCUE_NEAR_FEASIBLE_TOP_K = 16
RESCUE_OVERALL_TOP_K = 8
MAX_RESCUE_CANDIDATES = 96
DEFAULT_TARGETED_SUBSIDY_BUDGET_PER_PERSON = 6.0
LOW_INCOME_SUBSIDY_WEIGHT = 0.4
VULNERABLE_SUBSIDY_WEIGHT = 0.6
SERVICE_PRIORITY_WEIGHTS = {
    "助餐": 0.5,
    "日间照料": 0.4,
    "上门护理": 0.8,
    "康复理疗": 0.7,
    "助浴": 0.9,
    "紧急救助": 0.0,
}
SERVICE_LEVEL_SCENARIOS = ("S0", "S4")
SERVICE_LEVEL_FAIRNESS_THRESHOLD = 0.6
DEFAULT_MAX_CANDIDATES_PER_STATION = 30
DEFAULT_GLOBAL_ANCHOR_COUNT = 2
DEFAULT_NEIGHBOR_SEED_COUNT = 4
DEFAULT_PROFIT_CENTER = 0.04
SERVICE_LEVEL_OUTPUT_PREFIX = "3_5_satisfaction_objective"
EXPANDED_SEARCH_LEVEL_DEFAULTS = {
    "light": {"max_candidates_per_station": 30, "max_global_combinations": 5000, "deterministic_depth": 3, "boundary_depth": 4, "diversity_depth": 3},
    "medium": {"max_candidates_per_station": 80, "max_global_combinations": 20000, "deterministic_depth": 4, "boundary_depth": 6, "diversity_depth": 4},
    "heavy": {"max_candidates_per_station": 150, "max_global_combinations": 100000, "deterministic_depth": 5, "boundary_depth": 8, "diversity_depth": 5},
    "extreme": {"max_candidates_per_station": 250, "max_global_combinations": 300000, "deterministic_depth": 6, "boundary_depth": 10, "diversity_depth": 6},
}
EXPANDED_SEARCH_FOCUS_STATIONS = {
    "S0": {"loss": ("G", "I"), "cap": ()},
    "S4": {"loss": ("J",), "cap": ("C",)},
}
GLOBAL_PROGRESS_INTERVAL = 50
STATION_VECTOR_PROGRESS_INTERVAL = 2000


def progress_print(message: str) -> None:
    print(f"[RQ3] {message}", flush=True)


def format_elapsed(seconds: float) -> str:
    total = max(0, int(seconds))
    minutes, sec = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{sec:02d}"
    return f"{minutes:02d}:{sec:02d}"


def format_eta(start_time: float, done: int, total: int) -> str:
    if done <= 0 or total <= 0 or done > total:
        return "--:--"
    elapsed = max(0.0, time.time() - start_time)
    remaining = elapsed * (total - done) / max(done, 1)
    return format_elapsed(remaining)


@dataclass(frozen=True)
class IterationRecord:
    iteration: int
    max_satisfaction_delta: float
    average_service_satisfaction: float
    feasible_station_count: int
    total_subsidy: float
    damping_used: int = 0


@dataclass
class PriceEvaluation:
    station_prices: Dict[str, Dict[str, float]]
    iteration_count: int
    converged: int
    average_service_satisfaction: float
    minimum_service_satisfaction: float
    vulnerable_service_satisfaction: float
    annual_government_subsidy: float
    annual_service_revenue: float
    annual_direct_cost: float
    annual_fixed_cost: float
    annual_depreciation: float
    annual_net_profit_before_subsidy: float
    annual_net_profit_after_subsidy: float
    annual_net_profit: float
    feasible_station_count: int
    profit_compliant: int
    satisfaction_compliant: int
    low_income_service_satisfaction: float
    low_income_served_coverage: float
    iteration_trace: List[IterationRecord]
    station_financials: List[Dict[str, float]]
    community_results: List[Dict[str, float]]
    accessibility_groups: List[Dict[str, object]]
    average_service_access_performance: float = 0.0
    minimum_service_access_performance: float = 0.0
    annual_total_cost: float = 0.0
    profit_rate: float = 0.0
    served_population_coverage: float = 0.0
    weighted_served_population_coverage: float = 0.0
    served_demand_coverage: float = 0.0
    damping_used: int = 0
    pareto_rank: int = 0
    subsidy_policy_label: str = "none"
    gini_access: float = 0.0
    theil_access: float = 0.0
    max_min_gap: float = 0.0

    @property
    def fair_satisfaction_compliant(self) -> int:
        return self.satisfaction_compliant

    @fair_satisfaction_compliant.setter
    def fair_satisfaction_compliant(self, value: int) -> None:
        self.satisfaction_compliant = value


@dataclass(frozen=True)
class CommunityChoice:
    community: str
    primary_station: str
    backup_station: str | None
    utility_primary: float
    utility_backup: float
    demand_by_service: Dict[str, float]
    price_satisfaction_primary: float
    price_satisfaction_backup: float
    distance_satisfaction_primary: float
    distance_satisfaction_backup: float


@dataclass(frozen=True)
class RescueCandidate:
    station_prices: Dict[str, Dict[str, float]]
    warm_start_satisfaction: Dict[str, float]
    subsidy_budget_per_person: float = 0.0
    subsidy_policy_label: str = "none"


@dataclass(frozen=True)
class CommunityStationChoiceCache:
    distance_satisfaction: float
    demand_by_service: Dict[str, float]
    price_satisfaction: float
    distance_meters: float


def enumerate_service_level_price_vectors(
    price_candidates_by_service: Dict[str, List[float]],
) -> List[Dict[str, float]]:
    ordered_candidates = [
        price_candidates_by_service[service]
        for service in SERVICE_ORDER
    ]
    vectors: List[Dict[str, float]] = []
    for values in product(*ordered_candidates):
        vector = {
            service: float(value)
            for service, value in zip(SERVICE_ORDER, values)
        }
        vector["紧急救助"] = 0.0
        vectors.append(vector)
    return vectors


def service_level_price_profile(
    station_names: List[str],
    service_prices_by_station: Dict[str, Dict[str, float]],
) -> Dict[str, Dict[str, float]]:
    return {
        station_name: {
            service: 0.0 if service == "紧急救助" else float(service_prices_by_station[station_name][service])
            for service in SERVICE_ORDER
        }
        for station_name in station_names
    }


def compute_station_profit_compliance(
    station_financial_rows: List[Dict[str, float]],
) -> int:
    if not station_financial_rows:
        return 0
    return int(
        all(
            MIN_PROFIT_RATE - 1e-9 <= float(row["profit_rate"]) <= MAX_PROFIT_RATE + 1e-9
            for row in station_financial_rows
        )
    )


def prune_station_candidates(
    candidates: List[Dict[str, object]],
    max_candidates_per_station: int = DEFAULT_MAX_CANDIDATES_PER_STATION,
    top_k_satisfaction: int = 10,
    top_k_min_access: int = 10,
    top_k_profit_center: int = 10,
    target_profit_rate: float = DEFAULT_PROFIT_CENTER,
) -> List[Dict[str, object]]:
    if len(candidates) <= max_candidates_per_station:
        return candidates

    compliant = [row for row in candidates if int(row["profit_compliant"]) == 1]
    selected: List[Dict[str, object]] = []
    seen: set[str] = set()

    def row_key(row: Dict[str, object]) -> str:
        return str(row["selected_prices_by_service"])

    def keep(rows: Iterable[Dict[str, object]]) -> None:
        for row in rows:
            key = row_key(row)
            if key in seen:
                continue
            seen.add(key)
            selected.append(row)
            if len(selected) >= max_candidates_per_station:
                return

    if compliant:
        keep(sorted(compliant, key=lambda row: (-float(row["station_average_service_satisfaction"]), row_key(row)))[:top_k_satisfaction])
        if len(selected) < max_candidates_per_station:
            keep(sorted(compliant, key=lambda row: (-float(row["station_minimum_service_access_performance"]), row_key(row)))[:top_k_min_access])
        if len(selected) < max_candidates_per_station:
            keep(
                sorted(
                    compliant,
                    key=lambda row: (abs(float(row["profit_rate"]) - target_profit_rate), row_key(row)),
                )[:top_k_profit_center]
            )
    else:
        keep(sorted(candidates, key=lambda row: (float(row["break_even_gap"]), row_key(row)))[:1])
        if len(selected) < max_candidates_per_station:
            keep(sorted(candidates, key=lambda row: (float(row["over_8pct_excess"]), row_key(row)))[:1])
        if len(selected) < max_candidates_per_station:
            keep(sorted(candidates, key=lambda row: (float(row["break_even_gap"]), row_key(row)))[:1])
        if len(selected) < max_candidates_per_station:
            keep(sorted(candidates, key=lambda row: (-float(row["station_average_service_satisfaction"]), row_key(row)))[:1])
        if len(selected) < max_candidates_per_station:
            keep(sorted(candidates, key=lambda row: (-float(row["station_minimum_service_access_performance"]), row_key(row)))[:1])

    if len(selected) < max_candidates_per_station:
        keep(
            sorted(
                candidates,
                key=lambda row: (
                    -int(row["profit_compliant"]),
                    float(row["break_even_gap"]),
                    float(row["over_8pct_excess"]),
                    -float(row["station_average_service_satisfaction"]),
                    -float(row["station_minimum_service_access_performance"]),
                    row_key(row),
                ),
            )
        )
    return selected[:max_candidates_per_station]


def expanded_search_level_settings(search_level: str) -> Dict[str, int]:
    if search_level not in EXPANDED_SEARCH_LEVEL_DEFAULTS:
        raise ValueError(f"Unsupported search level: {search_level}")
    return dict(EXPANDED_SEARCH_LEVEL_DEFAULTS[search_level])


def price_structure_signature(row: Dict[str, object]) -> str:
    text = str(row["selected_prices_by_service"])
    parts = []
    for token in text.split("|"):
        service, value = token.split(":", 1)
        if service == "紧急救助":
            parts.append(f"{service}:0")
            continue
        parts.append(f"{service}:{float(value):.2f}")
    return "|".join(parts)


def station_candidate_sort_key(row: Dict[str, object]) -> Tuple[float, float, float, float, str]:
    return (
        -float(row["station_average_service_satisfaction"]),
        -float(row["station_minimum_service_access_performance"]),
        float(row["break_even_gap"]),
        float(row["over_8pct_excess"]),
        price_structure_signature(row),
    )


def prune_station_candidates_expanded(
    candidates: List[Dict[str, object]],
    station_name: str,
    max_candidates_per_station: int,
    keep_near_boundary: bool,
) -> List[Dict[str, object]]:
    if len(candidates) <= max_candidates_per_station:
        return sorted(candidates, key=station_candidate_sort_key)

    selected: List[Dict[str, object]] = []
    seen: set[str] = set()

    def keep(rows: Iterable[Dict[str, object]]) -> None:
        for row in rows:
            signature = price_structure_signature(row)
            if signature in seen:
                continue
            seen.add(signature)
            selected.append(row)
            if len(selected) >= max_candidates_per_station:
                return

    compliant = [row for row in candidates if int(row["profit_compliant"]) == 1]
    if compliant:
        keep(sorted(compliant, key=lambda row: (-float(row["station_average_service_satisfaction"]), price_structure_signature(row)))[: max(4, max_candidates_per_station // 6)])
        if len(selected) < max_candidates_per_station:
            keep(sorted(compliant, key=lambda row: (-float(row["station_minimum_service_access_performance"]), price_structure_signature(row)))[: max(4, max_candidates_per_station // 6)])
        if len(selected) < max_candidates_per_station:
            keep(sorted(compliant, key=lambda row: (abs(float(row["profit_rate"]) - 0.0), price_structure_signature(row)))[: max(3, max_candidates_per_station // 8)])
        if len(selected) < max_candidates_per_station:
            keep(sorted(compliant, key=lambda row: (abs(float(row["profit_rate"]) - 0.08), price_structure_signature(row)))[: max(3, max_candidates_per_station // 8)])

    if keep_near_boundary:
        keep(
            sorted(
                [row for row in candidates if -0.03 - 1e-9 <= float(row["profit_rate"]) <= 0.0 + 1e-9],
                key=lambda row: (abs(float(row["profit_rate"])), price_structure_signature(row)),
            )[: max(3, max_candidates_per_station // 10)]
        )
        if len(selected) < max_candidates_per_station:
            keep(
                sorted(
                    [row for row in candidates if 0.08 - 1e-9 <= float(row["profit_rate"]) <= 0.12 + 1e-9],
                    key=lambda row: (abs(float(row["profit_rate"]) - 0.08), price_structure_signature(row)),
                )[: max(3, max_candidates_per_station // 10)]
            )

    if len(selected) < max_candidates_per_station:
        keep(sorted(candidates, key=lambda row: (-float(row["station_average_service_satisfaction"]), price_structure_signature(row)))[: max(2, max_candidates_per_station // 12)])
    if len(selected) < max_candidates_per_station:
        keep(sorted(candidates, key=lambda row: (-float(row["station_minimum_service_access_performance"]), price_structure_signature(row)))[: max(2, max_candidates_per_station // 12)])
    if len(selected) < max_candidates_per_station:
        keep(sorted(candidates, key=lambda row: (float(row["break_even_gap"]), price_structure_signature(row)))[: max(2, max_candidates_per_station // 12)])
    if len(selected) < max_candidates_per_station:
        keep(sorted(candidates, key=lambda row: (float(row["over_8pct_excess"]), price_structure_signature(row)))[: max(2, max_candidates_per_station // 12)])

    if len(selected) < max_candidates_per_station:
        by_price_shape: Dict[str, Dict[str, object]] = {}
        for row in sorted(candidates, key=station_candidate_sort_key):
            first_token = str(row["selected_prices_by_service"]).split("|", 1)[0]
            by_price_shape.setdefault(first_token, row)
        keep(by_price_shape.values())

    if len(selected) < max_candidates_per_station:
        keep(sorted(candidates, key=station_candidate_sort_key))
    return selected[:max_candidates_per_station]


def is_joint_feasible_service_level(
    global_row: Dict[str, object],
    min_service_access_threshold: float = SERVICE_LEVEL_FAIRNESS_THRESHOLD,
) -> bool:
    return (
        int(global_row["converged"]) == 1
        and int(global_row["all_station_profit_compliant"]) == 1
        and float(global_row["minimum_service_satisfaction"]) >= min_service_access_threshold - 1e-9
    )


def build_rq3_inputs_for_budget_scenario(
    scenario_code: str,
    budget_limit: float,
) -> RQ3Inputs:
    if scenario_code == "S0" and abs(budget_limit - 120.0) <= 1e-12:
        progress_print(f"{scenario_code}: reuse baseline RQ3 inputs.")
        return load_rq3_inputs()

    progress_print(f"{scenario_code}: build RQ3 inputs from RQ2 layout, budget_limit={budget_limit}.")
    year5_population = load_year5_population()
    adjusted_summary = load_adjusted_demand_summary()
    adjusted_detail = load_adjusted_demand_detail()
    scales = RQ2_COMMON.load_station_scales()
    distance_matrix = RQ2_COMMON.load_distance_matrix()
    satisfaction_rules = RQ2_COMMON.load_satisfaction_rules()
    service_costs = RQ2_COMMON.load_service_costs()
    communities = [
        RQ2_COMMON.CommunityDemand(
            community=record.community,
            elderly_population=record.elderly_total,
            adjusted_monthly_demand=adjusted_demand_summary_map(adjusted_summary)[record.community],
        )
        for record in year5_population
    ]
    optimized_scheme_code = RQ2_COMMON.solve_location_milp(
        communities=communities,
        distance_matrix=distance_matrix,
        scales=scales,
        budget_limit=budget_limit,
        fairness_weight=0.25,
        safety_capacity_factor=0.85,
    )
    progress_print(f"{scenario_code}: RQ2 MILP layout solved.")
    q2_best = None
    if optimized_scheme_code is not None:
        q2_best = RQ2_COMMON.evaluate_scheme(
            scheme_code=optimized_scheme_code,
            communities=communities,
            distance_matrix=distance_matrix,
            scales=scales,
            satisfaction_rules=satisfaction_rules,
            service_costs=service_costs,
            budget_limit=budget_limit,
        )
    if q2_best is None:
        progress_print(f"{scenario_code}: MILP layout unavailable, fallback to feasible-scheme enumeration.")
        evaluations = []
        for idx, scheme_code in enumerate(RQ2_COMMON.enumerate_feasible_scheme_codes(
            [item.community for item in communities],
            scales,
            budget_limit=budget_limit,
        ), start=1):
            result = RQ2_COMMON.evaluate_scheme(
                scheme_code=scheme_code,
                communities=communities,
                distance_matrix=distance_matrix,
                scales=scales,
                satisfaction_rules=satisfaction_rules,
                service_costs=service_costs,
                budget_limit=budget_limit,
            )
            if result is not None:
                evaluations.append(result)
            if idx % 100 == 0:
                progress_print(f"{scenario_code}: evaluated {idx} fallback RQ2 schemes, feasible={len(evaluations)}.")
        if not evaluations:
            raise RuntimeError(
                f"No feasible RQ2 layout found for scenario {scenario_code} with budget_limit={budget_limit}."
            )
        q2_best = RQ2_COMMON.sort_scheme_evaluations(evaluations)[0]
    progress_print(f"{scenario_code}: RQ3 inputs ready, stations={len(q2_best.stations)}.")

    q2_summary_data = {
        "scheme_type": "coverage_fairness_capacity_milp",
        "scheme_code": "".join(str(token) for token in q2_best.scheme_code),
        "scheme_detail": ";".join(f"{station.community}-{station.scale}" for station in q2_best.stations),
        "station_count": len(q2_best.stations),
        "build_cost_wan": round(sum(station.build_cost_wan for station in q2_best.stations), 4),
        "geographic_population_coverage": q2_best.geographic_population_coverage,
        "served_population_coverage": q2_best.served_population_coverage,
        "weighted_served_population_coverage": q2_best.weighted_served_population_coverage,
        "served_demand_coverage": q2_best.served_demand_coverage,
        "average_service_satisfaction": q2_best.average_service_satisfaction,
        "minimum_service_satisfaction": q2_best.minimum_service_satisfaction,
        "average_service_access_performance": q2_best.average_service_access_performance,
        "minimum_service_access_performance": q2_best.minimum_service_access_performance,
        "total_adjusted_demand_daily": q2_best.total_adjusted_demand_daily,
        "total_raw_served_demand_daily": q2_best.total_raw_served_demand_daily,
        "total_effective_person_times_daily": q2_best.total_effective_person_times_daily,
        "capacity_safety_rate": q2_best.capacity_safety_rate,
        "max_station_utilization": q2_best.max_station_utilization,
        "fully_safe": q2_best.fully_safe,
        "fully_served_community_count": sum(1 for allocation in q2_best.allocations if allocation.unmet_load <= 1e-8),
        "total_unmet_daily_demand": sum(allocation.unmet_load for allocation in q2_best.allocations),
        "utilization_variance": q2_best.utilization_variance,
        "annual_revenue": q2_best.annual_revenue,
        "annual_subsidy": q2_best.annual_subsidy,
        "annual_direct_cost": q2_best.annual_direct_cost,
        "annual_fixed_cost": q2_best.annual_fixed_cost,
        "annual_depreciation": q2_best.annual_depreciation,
        "annual_total_cost": q2_best.annual_total_cost,
        "annual_net_profit_before_subsidy": q2_best.annual_net_profit_before_subsidy,
        "annual_net_profit_after_policy_subsidy": q2_best.annual_net_profit_after_policy_subsidy,
        "annual_net_profit": q2_best.annual_net_profit,
        "profit_rate": q2_best.profit_rate,
        "profit_compliant": q2_best.profit_compliant,
    }
    q2_summary = SchemeSummaryRecord(
        scheme_type=q2_summary_data["scheme_type"],
        scheme_code=q2_summary_data["scheme_code"],
        scheme_detail=q2_summary_data["scheme_detail"],
        station_count=q2_summary_data["station_count"],
        build_cost_wan=q2_summary_data["build_cost_wan"],
        geographic_population_coverage=q2_summary_data["geographic_population_coverage"],
        served_population_coverage=q2_summary_data["served_population_coverage"],
        weighted_served_population_coverage=q2_summary_data["weighted_served_population_coverage"],
        served_demand_coverage=q2_summary_data["served_demand_coverage"],
        average_service_satisfaction=q2_summary_data["average_service_satisfaction"],
        minimum_service_satisfaction=q2_summary_data["minimum_service_satisfaction"],
        average_service_access_performance=q2_summary_data["average_service_access_performance"],
        minimum_service_access_performance=q2_summary_data["minimum_service_access_performance"],
        total_adjusted_demand_daily=q2_summary_data["total_adjusted_demand_daily"],
        total_raw_served_demand_daily=q2_summary_data["total_raw_served_demand_daily"],
        total_effective_person_times_daily=q2_summary_data["total_effective_person_times_daily"],
        capacity_safety_rate=q2_summary_data["capacity_safety_rate"],
        max_station_utilization=q2_summary_data["max_station_utilization"],
        fully_safe=q2_summary_data["fully_safe"],
        fully_served_community_count=q2_summary_data["fully_served_community_count"],
        total_unmet_daily_demand=q2_summary_data["total_unmet_daily_demand"],
        utilization_variance=q2_summary_data["utilization_variance"],
        annual_revenue=q2_summary_data["annual_revenue"],
        annual_subsidy=q2_summary_data["annual_subsidy"],
        annual_direct_cost=q2_summary_data["annual_direct_cost"],
        annual_fixed_cost=q2_summary_data["annual_fixed_cost"],
        annual_depreciation=q2_summary_data["annual_depreciation"],
        annual_total_cost=q2_summary_data["annual_total_cost"],
        annual_net_profit_before_subsidy=q2_summary_data["annual_net_profit_before_subsidy"],
        annual_net_profit_after_policy_subsidy=q2_summary_data["annual_net_profit_after_policy_subsidy"],
        annual_net_profit=q2_summary_data["annual_net_profit"],
        profit_rate=q2_summary_data["profit_rate"],
        profit_compliant=q2_summary_data["profit_compliant"],
    )
    q2_stations = [
        StationRecord(
            station_community=item.community,
            scale=item.scale,
            daily_capacity=item.daily_capacity,
            assigned_primary_load=item.assigned_primary_load,
            assigned_overflow_load=item.assigned_overflow_load,
            total_load=item.total_load,
            utilization=item.utilization,
            annual_service_revenue=item.annual_service_revenue,
            annual_revenue=item.annual_revenue,
            annual_subsidy=item.annual_subsidy,
            annual_direct_cost=item.annual_direct_cost,
            annual_fixed_cost=item.annual_fixed_cost,
            annual_depreciation=item.annual_depreciation,
            annual_government_subsidy_baseline=item.annual_government_subsidy_baseline,
            annual_total_cost=item.annual_total_cost,
            annual_net_profit_before_subsidy=item.annual_net_profit_before_subsidy,
            annual_net_profit_after_policy_subsidy=item.annual_net_profit_after_policy_subsidy,
            annual_net_profit=item.annual_net_profit,
            profit_rate=item.profit_rate,
            profit_compliant=item.profit_compliant,
        )
        for item in q2_best.station_metrics
    ]
    q2_allocations = [
        AllocationRecord(
            community=item.community,
            primary_station=item.primary_station,
            overflow_station=item.overflow_station,
            geographic_reachable=item.geographic_reachable,
            actually_served=item.actually_served,
            geographic_population_covered=item.geographic_population_covered,
            served_population_covered=item.served_population_covered,
            adjusted_demand_daily=item.adjusted_demand_daily,
            raw_served_demand_daily=item.raw_served_demand_daily,
            effective_person_times_daily=item.effective_person_times_daily,
            demand_service_ratio=item.demand_service_ratio,
            service_access_performance=item.service_access_performance,
            primary_load_daily=item.primary_load,
            overflow_load_daily=item.overflow_load,
            unmet_load_daily=item.unmet_load,
            geographic_satisfaction=item.geographic_satisfaction,
            response_satisfaction=item.response_satisfaction,
            price_satisfaction=item.price_satisfaction,
            service_satisfaction=item.service_satisfaction,
        )
        for item in q2_best.allocations
    ]
    return RQ3Inputs(
        metadata={
            "source": "RQ3_service_level",
            "scenario": scenario_code,
            "budget_limit": budget_limit,
        },
        year5_population=year5_population,
        adjusted_demand_summary=adjusted_summary,
        adjusted_demand_detail=adjusted_detail,
        q2_summary=q2_summary,
        q2_stations=q2_stations,
        q2_allocations=q2_allocations,
    )


def apply_targeted_subsidy_policy(
    community: str,
    service: str,
    posted_price: float,
    low_income_communities: set[str],
    vulnerable_weight: float,
    low_income_weight: float,
    service_priority: Dict[str, float],
    subsidy_budget_per_person: float,
    is_vulnerable: bool,
) -> float:
    del (
        community,
        service,
        posted_price,
        low_income_communities,
        vulnerable_weight,
        low_income_weight,
        service_priority,
        subsidy_budget_per_person,
        is_vulnerable,
    )
    return 0.0


def compute_equity_metrics(
    community_rows: List[Dict[str, float]],
    population_weights: Dict[str, float],
) -> Dict[str, float]:
    weighted_values: List[tuple[float, float]] = []
    for row in community_rows:
        community = row["community"]
        weight = max(float(population_weights.get(community, 0.0)), 0.0)
        if weight <= 0:
            continue
        weighted_values.append((float(row["service_access_performance"]), weight))
    if not weighted_values:
        return {"gini_access": 0.0, "theil_access": 0.0, "max_min_gap": 0.0}

    expanded: List[tuple[float, float]] = sorted(weighted_values, key=lambda item: item[0])
    total_weight = sum(weight for _, weight in expanded)
    mean = sum(value * weight for value, weight in expanded) / max(total_weight, 1e-12)
    if mean <= 1e-12:
        return {"gini_access": 0.0, "theil_access": 0.0, "max_min_gap": max(value for value, _ in expanded)}

    gini_sum = 0.0
    for i, (value_i, weight_i) in enumerate(expanded):
        for value_j, weight_j in expanded[i + 1:]:
            gini_sum += abs(value_i - value_j) * weight_i * weight_j
    gini = gini_sum * 2.0 / max(total_weight * total_weight * mean, 1e-12)

    theil = 0.0
    for value, weight in expanded:
        if value <= 1e-12:
            continue
        ratio = value / mean
        theil += weight * ratio * math.log(ratio)
    theil /= max(total_weight, 1e-12)

    values = [value for value, _ in expanded]
    return {
        "gini_access": gini,
        "theil_access": theil,
        "max_min_gap": max(values) - min(values),
    }


def enumerate_station_price_profiles(inputs: RQ3Inputs) -> List[Dict[str, Dict[str, float]]]:
    station_names = [station.station_community for station in inputs.q2_stations]
    base_prices = base_price_by_service()
    station_profile_by_multiplier = {
        multiplier: {
            service: 0.0 if service == "紧急救助" else float(base_prices[service] * multiplier)
            for service in SERVICE_ORDER
        }
        for multiplier in PRICE_PREMIUM_MULTIPLIERS
    }

    result: List[Dict[str, Dict[str, float]]] = []
    seen_signatures: set[tuple[tuple[str, float], ...]] = set()

    def add_candidate(multiplier_by_station: Dict[str, float]) -> None:
        signature = tuple(sorted(multiplier_by_station.items()))
        if signature in seen_signatures:
            return
        seen_signatures.add(signature)
        result.append(
            {
                station_name: station_profile_by_multiplier[multiplier_by_station[station_name]]
                for station_name in station_names
            }
        )

    base_candidate = {station_name: 1.0 for station_name in station_names}
    add_candidate(base_candidate)

    for station_name in station_names:
        for multiplier in PRICE_PREMIUM_MULTIPLIERS:
            add_candidate({**base_candidate, station_name: multiplier})

    for station_a, station_b in combinations(station_names, 2):
        for multiplier_a in PRICE_PREMIUM_MULTIPLIERS:
            for multiplier_b in PRICE_PREMIUM_MULTIPLIERS:
                add_candidate(
                    {
                        **base_candidate,
                        station_a: multiplier_a,
                        station_b: multiplier_b,
                    }
                )

    return result


def station_multiplier(
    station_price_vector: Dict[str, float],
    base_prices: Dict[str, float],
) -> float:
    for service in NON_EMERGENCY_SERVICES:
        base_price = base_prices[service]
        if base_price > 0:
            return round(station_price_vector[service] / base_price, 10)
    return 1.0


def price_profile_signature(
    station_prices: Dict[str, Dict[str, float]],
    base_prices: Dict[str, float] | None = None,
) -> tuple[tuple[str, float], ...]:
    resolved_base_prices = base_prices or base_price_by_service()
    return tuple(
        sorted(
            (
                station_name,
                station_multiplier(price_vector, resolved_base_prices),
            )
            for station_name, price_vector in station_prices.items()
        )
    )


def station_profit_gap(station_financial_row: Dict[str, float]) -> float:
    profit_rate = float(station_financial_row["profit_rate"])
    if profit_rate < MIN_PROFIT_RATE:
        return MIN_PROFIT_RATE - profit_rate
    if profit_rate > MAX_PROFIT_RATE:
        return profit_rate - MAX_PROFIT_RATE
    return 0.0


def evaluation_profit_gap(item: PriceEvaluation) -> float:
    return sum(station_profit_gap(row) for row in item.station_financials)


def near_feasible_sort_key(item: PriceEvaluation) -> tuple[float, int, int, float, float]:
    return (
        evaluation_profit_gap(item),
        -item.feasible_station_count,
        -item.satisfaction_compliant,
        -item.vulnerable_service_satisfaction,
        -item.average_service_satisfaction,
    )


def generate_rescue_price_profiles(
    inputs: RQ3Inputs,
    ranked_primary: List[PriceEvaluation],
    near_feasible_top_k: int = RESCUE_NEAR_FEASIBLE_TOP_K,
    overall_top_k: int = RESCUE_OVERALL_TOP_K,
    max_candidates: int = MAX_RESCUE_CANDIDATES,
) -> List[RescueCandidate]:
    base_prices = base_price_by_service()
    station_names = [station.station_community for station in inputs.q2_stations]
    primary_signatures = {
        price_profile_signature(item.station_prices, base_prices)
        for item in ranked_primary
    }
    rescue_candidates: List[RescueCandidate] = []
    seen_signatures = set(primary_signatures)

    def build_station_price_vector(multiplier: float) -> Dict[str, float]:
        return {
            service: 0.0 if service == "紧急救助" else float(base_prices[service] * multiplier)
            for service in SERVICE_ORDER
        }

    def add_candidate(
        source: PriceEvaluation,
        multiplier_by_station: Dict[str, float],
    ) -> bool:
        if len(rescue_candidates) >= max_candidates:
            return False
        signature = tuple(sorted((station_name, round(multiplier_by_station[station_name], 10)) for station_name in station_names))
        if signature in seen_signatures:
            return True
        seen_signatures.add(signature)
        rescue_candidates.append(
            RescueCandidate(
                station_prices={
                    station_name: build_station_price_vector(multiplier_by_station[station_name])
                    for station_name in station_names
                },
                warm_start_satisfaction={
                    row["community"]: row["service_satisfaction"]
                    for row in source.community_results
                },
                subsidy_budget_per_person=max(
                    0.0,
                    float(source.subsidy_policy_label.rsplit("_", 1)[-1]) if source.subsidy_policy_label.startswith("targeted_subsidy_") else 0.0,
                ),
                subsidy_policy_label=source.subsidy_policy_label,
            )
        )
        return len(rescue_candidates) < max_candidates

    source_candidates: List[PriceEvaluation] = []
    source_seen = set()
    for item in ranked_primary[:overall_top_k]:
        signature = price_profile_signature(item.station_prices, base_prices)
        if signature in source_seen:
            continue
        source_seen.add(signature)
        source_candidates.append(item)
    for item in sorted(ranked_primary, key=near_feasible_sort_key)[:near_feasible_top_k]:
        signature = price_profile_signature(item.station_prices, base_prices)
        if signature in source_seen:
            continue
        source_seen.add(signature)
        source_candidates.append(item)

    for item in source_candidates:
        current_multiplier_by_station = {
            station_name: station_multiplier(item.station_prices[station_name], base_prices)
            for station_name in station_names
        }
        loss_rows = sorted(
            (
                row
                for row in item.station_financials
                if float(row["profit_rate"]) < MIN_PROFIT_RATE - 1e-9
            ),
            key=station_profit_gap,
            reverse=True,
        )
        if not loss_rows:
            continue

        higher_multiplier_by_station = {
            row["station_community"]: [
                multiplier
                for multiplier in PRICE_PREMIUM_MULTIPLIERS
                if multiplier > current_multiplier_by_station[row["station_community"]]
            ]
            for row in loss_rows
        }

        for row in loss_rows:
            station_name = row["station_community"]
            for multiplier in higher_multiplier_by_station[station_name]:
                should_continue = add_candidate(
                    item,
                    {**current_multiplier_by_station, station_name: multiplier},
                )
                if not should_continue:
                    return rescue_candidates

        active_loss_stations = [
            row["station_community"]
            for row in loss_rows
            if higher_multiplier_by_station[row["station_community"]]
        ]
        for station_a, station_b in combinations(active_loss_stations[:2], 2):
            for multiplier_a in higher_multiplier_by_station[station_a]:
                for multiplier_b in higher_multiplier_by_station[station_b]:
                    should_continue = add_candidate(
                        item,
                        {
                            **current_multiplier_by_station,
                            station_a: multiplier_a,
                            station_b: multiplier_b,
                        },
                    )
                    if not should_continue:
                        return rescue_candidates

        if len(active_loss_stations) >= 2:
            joint_threshold = max(current_multiplier_by_station[station_name] for station_name in active_loss_stations)
            for multiplier in PRICE_PREMIUM_MULTIPLIERS:
                if multiplier <= joint_threshold:
                    continue
                should_continue = add_candidate(
                    item,
                    {
                        **current_multiplier_by_station,
                        **{station_name: multiplier for station_name in active_loss_stations},
                    },
                )
                if not should_continue:
                    return rescue_candidates

    return rescue_candidates


def subsidy_budget_candidates() -> List[float]:
    return [0.0]


def assign_pareto_ranks(evaluations: List[PriceEvaluation]) -> List[PriceEvaluation]:
    def dominates(left: PriceEvaluation, right: PriceEvaluation) -> bool:
        no_worse = (
            left.average_service_satisfaction >= right.average_service_satisfaction - 1e-9
            and left.profit_rate >= right.profit_rate - 1e-9
            and left.gini_access <= right.gini_access + 1e-9
        )
        strictly_better = (
            left.average_service_satisfaction > right.average_service_satisfaction + 1e-9
            or left.profit_rate > right.profit_rate + 1e-9
            or left.gini_access < right.gini_access - 1e-9
        )
        return no_worse and strictly_better

    dominated_count = {id(item): 0 for item in evaluations}
    dominates_map = {id(item): [] for item in evaluations}
    current_front: List[PriceEvaluation] = []

    for item in evaluations:
        for other in evaluations:
            if other is item:
                continue
            if dominates(item, other):
                dominates_map[id(item)].append(other)
            elif dominates(other, item):
                dominated_count[id(item)] += 1
        if dominated_count[id(item)] == 0:
            item.pareto_rank = 1
            current_front.append(item)

    rank = 1
    while current_front:
        next_front: List[PriceEvaluation] = []
        for item in current_front:
            for dominated_item in dominates_map[id(item)]:
                dominated_count[id(dominated_item)] -= 1
                if dominated_count[id(dominated_item)] == 0:
                    dominated_item.pareto_rank = rank + 1
                    next_front.append(dominated_item)
        rank += 1
        current_front = next_front

    for item in evaluations:
        if item.pareto_rank <= 0:
            item.pareto_rank = rank
    return evaluations


def compute_price_satisfaction(base_price: float, actual_price: float) -> float:
    if base_price <= 0:
        return 1.0
    premium_ratio = actual_price / base_price - 1.0
    if premium_ratio <= 1e-12:
        return 1.0
    if premium_ratio <= 0.10 + 1e-12:
        return 0.90
    if premium_ratio <= 0.20 + 1e-12:
        return 0.75
    return 0.60


def distance_satisfaction(distance: float, rules: List[tuple[float, float]]) -> float:
    if distance > 1000.0:
        return 0.0
    for threshold, score in rules:
        if distance <= threshold + 1e-12:
            return score
    return 0.0


def response_satisfaction_from_utilization(utilization: float, rules: List[tuple[float, float]]) -> float:
    for threshold, score in rules:
        if utilization <= threshold + 1e-12:
            return score
    return rules[-1][1]


def fixed_point_converged(
    old_satisfaction: Dict[str, float],
    new_satisfaction: Dict[str, float],
    epsilon: float = FIXED_POINT_EPSILON,
) -> bool:
    max_delta = max(
        abs(new_satisfaction[community] - old_satisfaction[community])
        for community in old_satisfaction
    )
    return max_delta < epsilon


def detect_two_cycle_oscillation(
    history: List[Dict[str, float]],
    tolerance: float = 1e-8,
) -> bool:
    if len(history) < 4:
        return False
    a_prev, b_prev, a_curr, b_curr = history[-4:]
    communities = sorted(a_prev)
    return (
        all(abs(a_prev[c] - a_curr[c]) <= tolerance for c in communities)
        and all(abs(b_prev[c] - b_curr[c]) <= tolerance for c in communities)
    )


def apply_damping(
    previous: Dict[str, float],
    candidate: Dict[str, float],
    damping_lambda: float = DEFAULT_DAMPING_LAMBDA,
) -> Dict[str, float]:
    return {
        community: damping_lambda * candidate[community] + (1.0 - damping_lambda) * previous[community]
        for community in previous
    }


def meets_profit_rate_constraint(net_profit: float, total_cost: float) -> bool:
    if total_cost <= 0:
        return False
    profit_rate = net_profit / total_cost
    return MIN_PROFIT_RATE - 1e-9 <= profit_rate <= MAX_PROFIT_RATE + 1e-9


def service_satisfaction_from_weighted_score(weighted_score: float, served: bool) -> float:
    if not served:
        return 0.0
    return min(1.0, max(0.6, weighted_score))


def service_access_performance(
    effective_person_times_daily: float,
    adjusted_demand_daily: float,
) -> float:
    if adjusted_demand_daily <= 1e-12 or effective_person_times_daily <= 1e-12:
        return 0.0
    return min(1.0, effective_person_times_daily / adjusted_demand_daily)


def financial_gap_to_break_even(item: PriceEvaluation) -> float:
    return max(0.0, -item.annual_net_profit)


def joint_feasible_solution_exists(
    evaluations: List[PriceEvaluation],
    min_service_access_threshold: float = DEFAULT_MIN_SERVICE_ACCESS_THRESHOLD,
) -> bool:
    return any(
        item.profit_compliant == 1
        and item.minimum_service_satisfaction >= min_service_access_threshold - 1e-9
        and item.converged == 1
        for item in evaluations
    )


def select_primary_and_backup(utility_by_station: Dict[str, float]) -> tuple[str | None, str | None]:
    ranked = sorted(
        utility_by_station.items(),
        key=lambda item: (item[1], item[0]),
        reverse=True,
    )
    if not ranked:
        return None, None
    primary = ranked[0][0]
    backup = ranked[1][0] if len(ranked) >= 2 else None
    return primary, backup


def compute_weighted_price_satisfaction_for_community(
    demand_by_service: Dict[str, float],
    station_price_vector: Dict[str, float],
    base_prices: Dict[str, float],
) -> float:
    denominator = sum(demand_by_service[service] for service in SERVICE_ORDER)
    if denominator <= 0:
        return 0.0
    numerator = 0.0
    for service in SERVICE_ORDER:
        satisfaction = compute_price_satisfaction(
            base_price=base_prices[service],
            actual_price=station_price_vector[service],
        )
        numerator += demand_by_service[service] * satisfaction
    return numerator / denominator


def compute_price_adjusted_monthly_demand_for_station(
    community: str,
    station_price_vector: Dict[str, float],
    detail_map: Dict[str, Dict[str, Dict[str, object]]],
    low_income_set: set[str] | None = None,
    subsidy_budget_per_person: float = 0.0,
) -> Dict[str, float]:
    result = {service: 0.0 for service in SERVICE_ORDER}
    community_details = detail_map[community]
    low_income_communities_set = low_income_set or set()
    for care_level in CARE_LEVEL_ORDER:
        rows_by_service = community_details[care_level]
        budget_limit = rows_by_service["助餐"].budget_limit
        is_vulnerable = care_level in {"半失能", "失能"}
        net_price_by_service = {}
        for service in SERVICE_ORDER:
            posted_price = station_price_vector[service]
            subsidy = apply_targeted_subsidy_policy(
                community=community,
                service=service,
                posted_price=posted_price,
                low_income_communities=low_income_communities_set,
                vulnerable_weight=VULNERABLE_SUBSIDY_WEIGHT,
                low_income_weight=LOW_INCOME_SUBSIDY_WEIGHT,
                service_priority=SERVICE_PRIORITY_WEIGHTS,
                subsidy_budget_per_person=subsidy_budget_per_person,
                is_vulnerable=is_vulnerable,
            )
            net_price_by_service[service] = max(0.0, posted_price - subsidy)
        theoretical_fee = sum(
            rows_by_service[service].theoretical_per_person * net_price_by_service[service]
            for service in SERVICE_ORDER
            if service != "紧急救助"
        )
        affordability_scale = min(1.0, budget_limit / theoretical_fee) if theoretical_fee > 1e-12 else 1.0
        for service in SERVICE_ORDER:
            if service == "紧急救助":
                adjusted_per_person = rows_by_service[service].theoretical_per_person
            else:
                adjusted_per_person = rows_by_service[service].theoretical_per_person * affordability_scale
            result[service] += adjusted_per_person * rows_by_service[service].population
    return result


def annual_subsidy_limit_for_station(scale: str) -> float:
    daily_limit_map = {"小型": 1000.0, "中型": 1800.0, "大型": 2600.0}
    return 365.0 * daily_limit_map[scale]


def low_income_communities() -> set[str]:
    communities = load_community_data()
    incomes = sorted(item.monthly_income for item in communities)
    median_income = (incomes[4] + incomes[5]) / 2
    return {
        item.community
        for item in communities
        if item.monthly_income < median_income
    }


def solve_collaboration_lp(
    choices: List[CommunityChoice],
    station_capacities: Dict[str, float],
) -> tuple[List[Dict[str, float]], Dict[str, Dict[str, float]], Dict[str, Dict[str, float]]]:
    station_names = sorted(station_capacities)
    station_raw = {
        station_name: {service: 0.0 for service in SERVICE_ORDER}
        for station_name in station_names
    }
    station_effective = {
        station_name: {service: 0.0 for service in SERVICE_ORDER}
        for station_name in station_names
    }
    community_rows: List[Dict[str, float]] = []

    grouped_choices: Dict[str, List[CommunityChoice]] = {}
    for choice in choices:
        grouped_choices.setdefault(choice.primary_station, []).append(choice)

    station_ratio: Dict[str, float] = {}
    for station_name in station_names:
        total_demand = sum(
            sum(choice.demand_by_service.values())
            for choice in grouped_choices.get(station_name, [])
        )
        if total_demand <= 1e-12:
            station_ratio[station_name] = 0.0
        else:
            station_ratio[station_name] = min(1.0, station_capacities[station_name] / total_demand)

    for choice in choices:
        ratio = station_ratio.get(choice.primary_station, 0.0)
        total_demand = sum(choice.demand_by_service.values())
        primary_load = total_demand * ratio
        overflow_load = 0.0
        unmet = total_demand - primary_load
        effective_total = primary_load * choice.utility_primary
        served_ratio = primary_load / total_demand if total_demand > 1e-12 else 0.0
        service_satisfaction = service_satisfaction_from_weighted_score(
            choice.utility_primary,
            served=primary_load > 1e-12,
        )
        access_performance = service_access_performance(effective_total, total_demand)
        primary_response = (
            choice.utility_primary
            - SATISFACTION_WEIGHTS["distance"] * choice.distance_satisfaction_primary
            - SATISFACTION_WEIGHTS["price"] * choice.price_satisfaction_primary
        ) / SATISFACTION_WEIGHTS["response"]

        for service, demand in choice.demand_by_service.items():
            served_amount = demand * ratio
            station_raw[choice.primary_station][service] += served_amount
            station_effective[choice.primary_station][service] += served_amount * choice.utility_primary

        community_rows.append(
            {
                "community": choice.community,
                "primary_station": choice.primary_station,
                "overflow_station": "",
                "primary_load_daily": primary_load,
                "overflow_load_daily": overflow_load,
                "unmet_load_daily": unmet,
                "raw_served_demand_daily": primary_load,
                "effective_person_times_daily": effective_total,
                "adjusted_demand_daily": total_demand,
                "demand_service_ratio": min(1.0, served_ratio),
                "service_satisfaction": service_satisfaction,
                "service_access_performance": access_performance,
                "served": int(primary_load > 1e-9),
                "price_satisfaction": choice.price_satisfaction_primary if primary_load > 1e-9 else 0.0,
                "distance_satisfaction": choice.distance_satisfaction_primary if primary_load > 1e-9 else 0.0,
                "response_satisfaction": primary_response if primary_load > 1e-9 else 0.0,
            }
        )

    return community_rows, station_raw, station_effective


def precompute_community_station_choice_cache(
    inputs: RQ3Inputs,
    station_prices: Dict[str, Dict[str, float]],
    subsidy_budget_per_person: float = 0.0,
) -> Dict[str, Dict[str, CommunityStationChoiceCache]]:
    distance_matrix = load_distance_matrix()
    satisfaction_rules = load_satisfaction_rules()
    detail_map = adjusted_demand_detail_map(inputs.adjusted_demand_detail)
    station_names = [station.station_community for station in inputs.q2_stations]
    base_prices = base_price_by_service()
    low_income_set = low_income_communities()

    cache: Dict[str, Dict[str, CommunityStationChoiceCache]] = {}
    for community in sorted(detail_map):
        station_cache: Dict[str, CommunityStationChoiceCache] = {}
        for station_name in station_names:
            distance = distance_matrix[community][station_name]
            distance_score = distance_satisfaction(distance, satisfaction_rules["distance"])
            if distance_score <= 0:
                continue
            demand_by_service = compute_price_adjusted_monthly_demand_for_station(
                community=community,
                station_price_vector=station_prices[station_name],
                detail_map=detail_map,
                low_income_set=low_income_set,
                subsidy_budget_per_person=subsidy_budget_per_person,
            )
            price_score = compute_weighted_price_satisfaction_for_community(
                demand_by_service=demand_by_service,
                station_price_vector=station_prices[station_name],
                base_prices=base_prices,
            )
            station_cache[station_name] = CommunityStationChoiceCache(
                distance_satisfaction=distance_score,
                demand_by_service=demand_by_service,
                price_satisfaction=price_score,
                distance_meters=distance,
            )
        cache[community] = station_cache
    return cache


def build_community_choices(
    choice_cache: Dict[str, Dict[str, CommunityStationChoiceCache]],
    response_by_station: Dict[str, float],
) -> List[CommunityChoice]:
    choices: List[CommunityChoice] = []
    for community in sorted(choice_cache):
        utility_by_station: Dict[str, float] = {}
        for station_name, station_cache in choice_cache[community].items():
            utility_by_station[station_name] = (
                SATISFACTION_WEIGHTS["distance"] * station_cache.distance_satisfaction
                + SATISFACTION_WEIGHTS["response"] * response_by_station[station_name]
                + SATISFACTION_WEIGHTS["price"] * station_cache.price_satisfaction
            )
        ranked = sorted(
            utility_by_station.items(),
            key=lambda item: (
                -item[1],
                choice_cache[community][item[0]].distance_meters,
                item[0],
            ),
        )
        if not ranked:
            continue
        primary = ranked[0][0]
        primary_cache = choice_cache[community][primary]
        choices.append(
            CommunityChoice(
                community=community,
                primary_station=primary,
                backup_station=None,
                utility_primary=utility_by_station[primary],
                utility_backup=0.0,
                demand_by_service={
                    service: primary_cache.demand_by_service[service] / DAYS_PER_MONTH
                    for service in SERVICE_ORDER
                },
                price_satisfaction_primary=primary_cache.price_satisfaction,
                price_satisfaction_backup=0.0,
                distance_satisfaction_primary=primary_cache.distance_satisfaction,
                distance_satisfaction_backup=0.0,
            )
        )
    return choices


def evaluate_price_profile(
    inputs: RQ3Inputs,
    station_prices: Dict[str, Dict[str, float]],
    max_iterations: int = MAX_FIXED_POINT_ITERATIONS,
    epsilon: float = FIXED_POINT_EPSILON,
    initial_satisfaction: Dict[str, float] | None = None,
    damping_lambda: float = DEFAULT_DAMPING_LAMBDA,
    subsidy_budget_per_person: float = 0.0,
    subsidy_policy_label: str = "none",
    enable_damping: bool = True,
    choice_cache: Dict[str, Dict[str, CommunityStationChoiceCache]] | None = None,
) -> PriceEvaluation:
    populations = population_by_community(inputs.year5_population)
    stations = stations_by_community(inputs.q2_stations)
    direct_costs = direct_cost_by_service()
    satisfaction_rules = load_satisfaction_rules()
    low_income_set = low_income_communities()
    baseline_adjusted_summary = adjusted_demand_summary_map(inputs.adjusted_demand_summary)
    resolved_choice_cache = choice_cache or precompute_community_station_choice_cache(
        inputs=inputs,
        station_prices=station_prices,
        subsidy_budget_per_person=subsidy_budget_per_person,
    )

    old_satisfaction = initial_satisfaction or initial_service_satisfaction_by_community(inputs.q2_allocations)
    satisfaction_history: List[Dict[str, float]] = [old_satisfaction.copy()]
    iteration_trace: List[IterationRecord] = []
    station_financials: List[Dict[str, float]] = []
    community_results: List[Dict[str, float]] = []
    final_station_net_profits: Dict[str, float] = {}
    final_station_total_costs: Dict[str, float] = {}
    damping_used = 0
    state_station_total_load = {
        station_name: max(0.0, float(station.total_load))
        for station_name, station in stations.items()
    }

    for iteration in range(1, max_iterations + 1):
        response_by_station = {}
        for station_name, station in stations.items():
            utilization = (
                state_station_total_load[station_name] / station.daily_capacity
                if station.daily_capacity > 0
                else 1.0
            )
            response_by_station[station_name] = response_satisfaction_from_utilization(
                utilization,
                satisfaction_rules["response"],
            )

        choices = build_community_choices(
            choice_cache=resolved_choice_cache,
            response_by_station=response_by_station,
        )
        station_capacities = {station_name: station.daily_capacity for station_name, station in stations.items()}
        community_results, station_raw_demand, station_effective_demand = solve_collaboration_lp(
            choices=choices,
            station_capacities=station_capacities,
        )

        community_results_map = {row["community"]: row for row in community_results}
        candidate_satisfaction = {
            community: community_results_map.get(community, {}).get("service_satisfaction", 0.0)
            for community in old_satisfaction
        }
        candidate_station_total_load = {
            station_name: sum(station_raw_demand[station_name].values())
            for station_name in stations
        }
        iteration_damping_used = 0
        if enable_damping and detect_two_cycle_oscillation(satisfaction_history + [candidate_satisfaction]):
            new_satisfaction = apply_damping(
                previous=old_satisfaction,
                candidate=candidate_satisfaction,
                damping_lambda=damping_lambda,
            )
            state_station_total_load = apply_damping(
                previous=state_station_total_load,
                candidate=candidate_station_total_load,
                damping_lambda=damping_lambda,
            )
            damping_used = 1
            iteration_damping_used = 1
        else:
            new_satisfaction = candidate_satisfaction
            state_station_total_load = {
                station_name: float(candidate_station_total_load[station_name])
                for station_name in candidate_station_total_load
            }

        community_choice_map = {choice.community: choice for choice in choices}
        for row in community_results:
            if row["served"] == 0:
                row["price_satisfaction"] = 0.0
                row["distance_satisfaction"] = 0.0
                row["response_satisfaction"] = 0.0
                continue
            choice = community_choice_map[row["community"]]
            row["price_satisfaction"] = choice.price_satisfaction_primary
            row["distance_satisfaction"] = choice.distance_satisfaction_primary
            row["response_satisfaction"] = response_by_station[choice.primary_station]

        for community in sorted(populations):
            if community not in community_results_map:
                unmet_daily = sum(
                    baseline_adjusted_summary[community][service]
                    for service in SERVICE_ORDER
                ) / DAYS_PER_MONTH
                community_results.append(
                    {
                        "community": community,
                        "primary_station": "",
                        "overflow_station": "",
                        "primary_load_daily": 0.0,
                        "overflow_load_daily": 0.0,
                        "unmet_load_daily": unmet_daily if unmet_daily else 0.0,
                        "raw_served_demand_daily": 0.0,
                        "effective_person_times_daily": 0.0,
                        "adjusted_demand_daily": unmet_daily if unmet_daily else 0.0,
                        "demand_service_ratio": 0.0,
                        "service_satisfaction": 0.0,
                        "service_access_performance": 0.0,
                        "served": 0,
                        "price_satisfaction": 0.0,
                        "distance_satisfaction": 0.0,
                        "response_satisfaction": 0.0,
                    }
                )
        community_results.sort(key=lambda row: row["community"])
        community_results_map = {row["community"]: row for row in community_results}

        station_financials = []
        feasible_station_count = 0
        total_subsidy = 0.0
        total_revenue = 0.0
        total_direct_cost = 0.0
        total_fixed_cost = 0.0
        total_depreciation = 0.0
        total_total_cost = 0.0
        total_net_profit_before_subsidy = 0.0
        total_net_profit = 0.0
        final_station_net_profits = {}
        final_station_total_costs = {}

        for station_name, station in stations.items():
            raw_daily_total = sum(station_raw_demand[station_name].values())
            effective_daily_total = sum(station_effective_demand[station_name].values())

            annual_revenue = sum(
                station_effective_demand[station_name][service] * station_prices[station_name][service] * 365.0
                for service in SERVICE_ORDER
            )
            annual_direct_cost = sum(
                station_raw_demand[station_name][service] * direct_costs[service] * 365.0
                for service in SERVICE_ORDER
            )
            annual_fixed_cost = station.annual_fixed_cost
            annual_depreciation = station.annual_depreciation
            annual_subsidy = min(
                SUBSIDY_PER_EFFECTIVE_PERSON_TIME
                * sum(station_effective_demand[station_name][service] * 365.0 for service in NON_EMERGENCY_SERVICES),
                annual_subsidy_limit_for_station(station.scale),
            )
            annual_total_cost = annual_direct_cost + annual_fixed_cost + annual_depreciation
            annual_net_profit_before_subsidy = annual_revenue - annual_total_cost
            annual_net_profit = annual_revenue + annual_subsidy - annual_total_cost
            profit_compliant = int(meets_profit_rate_constraint(annual_net_profit, annual_total_cost))
            feasible_station_count += profit_compliant

            final_station_net_profits[station_name] = annual_net_profit
            final_station_total_costs[station_name] = annual_total_cost
            total_subsidy += annual_subsidy
            total_revenue += annual_revenue
            total_direct_cost += annual_direct_cost
            total_fixed_cost += annual_fixed_cost
            total_depreciation += annual_depreciation
            total_total_cost += annual_total_cost
            total_net_profit_before_subsidy += annual_net_profit_before_subsidy
            total_net_profit += annual_net_profit
            emergency_public_loss = station_raw_demand[station_name]["紧急救助"] * direct_costs["紧急救助"] * 365.0

            station_financials.append(
                {
                    "station_community": station_name,
                    "scale": station.scale,
                    "raw_served_demand_daily": raw_daily_total,
                    "effective_person_times_daily": effective_daily_total,
                    "annual_service_revenue": annual_revenue,
                    "annual_direct_cost": annual_direct_cost,
                    "annual_fixed_cost": annual_fixed_cost,
                    "annual_depreciation": annual_depreciation,
                    "annual_government_subsidy": annual_subsidy,
                    "annual_subsidy": annual_subsidy,
                    "annual_total_cost": annual_total_cost,
                    "annual_net_profit_before_subsidy": annual_net_profit_before_subsidy,
                    "annual_net_profit_after_subsidy": annual_net_profit,
                    "annual_net_profit": annual_net_profit,
                    "profit_rate": annual_net_profit / annual_total_cost if annual_total_cost > 0 else -1.0,
                    "profit_compliant": profit_compliant,
                    "emergency_public_loss": emergency_public_loss,
                }
            )

        max_delta = max(
            abs(new_satisfaction[community] - old_satisfaction[community])
            for community in old_satisfaction
        )
        served_satisfaction_values = [row["service_satisfaction"] for row in community_results if row["served"] == 1]
        average_service_satisfaction = (
            sum(served_satisfaction_values) / len(served_satisfaction_values)
            if served_satisfaction_values
            else 0.0
        )
        iteration_trace.append(
            IterationRecord(
                iteration=iteration,
                max_satisfaction_delta=max_delta,
                average_service_satisfaction=average_service_satisfaction,
                feasible_station_count=feasible_station_count,
                total_subsidy=total_subsidy,
                damping_used=iteration_damping_used,
            )
        )
        if iteration >= 3:
            profit_rates = [
                final_station_net_profits[station_name] / final_station_total_costs[station_name]
                for station_name in final_station_net_profits
                if final_station_total_costs[station_name] > 0
            ]
            if profit_rates and max(profit_rates) < EARLY_STOP_NEGATIVE_PROFIT_MARGIN:
                old_satisfaction = new_satisfaction
                break
        if fixed_point_converged(old_satisfaction, new_satisfaction, epsilon=epsilon):
            old_satisfaction = new_satisfaction
            satisfaction_history.append(new_satisfaction.copy())
            break
        old_satisfaction = new_satisfaction
        satisfaction_history.append(new_satisfaction.copy())

    served_communities = [row for row in community_results if row["served"] == 1]
    served_satisfaction_values = [row["service_satisfaction"] for row in served_communities]
    total_effective_person_times = sum(row["effective_person_times_daily"] for row in community_results)
    total_raw_served_demand_daily = sum(row["raw_served_demand_daily"] for row in community_results)
    total_adjusted_demand_daily = sum(row["adjusted_demand_daily"] for row in community_results)
    average_service_satisfaction = (
        sum(served_satisfaction_values) / len(served_satisfaction_values)
        if served_satisfaction_values
        else 0.0
    )
    minimum_service_satisfaction = min(served_satisfaction_values) if served_satisfaction_values else 0.0
    average_service_access_performance = (
        total_effective_person_times / total_adjusted_demand_daily
        if total_adjusted_demand_daily > 1e-12
        else 0.0
    )
    minimum_service_access_performance = min(
        (row["service_access_performance"] for row in community_results),
        default=0.0,
    )
    vulnerable_population = sum(
        populations[row["community"]].semi_disabled + populations[row["community"]].disabled
        for row in community_results
    )
    vulnerable_service_satisfaction = (
        sum(
            (populations[row["community"]].semi_disabled + populations[row["community"]].disabled)
            * row["service_satisfaction"]
            for row in community_results
        )
        / vulnerable_population
        if vulnerable_population > 0
        else 0.0
    )
    low_income_rows = [row for row in community_results if row["community"] in low_income_set]
    low_income_population = sum(populations[row["community"]].elderly_total for row in low_income_rows)
    low_income_served_population = sum(
        populations[row["community"]].elderly_total * row["demand_service_ratio"]
        for row in low_income_rows
    )
    low_income_service_satisfaction = (
        sum(
            populations[row["community"]].elderly_total * row["service_satisfaction"]
            for row in low_income_rows
        )
        / low_income_population
        if low_income_population > 0
        else 0.0
    )
    low_income_served_coverage = (
        low_income_served_population / low_income_population
        if low_income_population > 0
        else 0.0
    )
    total_population = sum(populations[row["community"]].elderly_total for row in community_results)
    served_population_coverage = (
        sum(
            populations[row["community"]].elderly_total * row["demand_service_ratio"]
            for row in community_results
        )
        / total_population
        if total_population > 0
        else 0.0
    )
    weighted_served_population_coverage = (
        sum(
            populations[row["community"]].elderly_total * row["demand_service_ratio"]
            for row in community_results
        )
        / total_population
        if total_population > 0
        else 0.0
    )
    served_demand_coverage = (
        total_raw_served_demand_daily / total_adjusted_demand_daily
        if total_adjusted_demand_daily > 1e-12
        else 0.0
    )
    satisfaction_compliant = int(
        minimum_service_satisfaction >= DEFAULT_MIN_SERVICE_ACCESS_THRESHOLD - 1e-9
    )
    profit_compliant = int(
        all(
            meets_profit_rate_constraint(
                net_profit=final_station_net_profits[station_name],
                total_cost=final_station_total_costs[station_name],
            )
            for station_name in final_station_net_profits
        )
    )
    accessibility_groups = [
        {
            "group": "自理",
            "economic_accessibility": "高",
            "geographic_accessibility": "较高",
            "service_accessibility": round(
                sum(populations[row["community"]].self_care * row["service_satisfaction"] for row in community_results)
                / max(sum(populations[row["community"]].self_care for row in community_results), 1e-9),
                6,
            ),
            "key_factor": "消费约束较弱，主要受距离与主站选择影响",
        },
        {
            "group": "半失能",
            "economic_accessibility": "中",
            "geographic_accessibility": "中",
            "service_accessibility": round(
                sum(populations[row["community"]].semi_disabled * row["service_satisfaction"] for row in community_results)
                / max(sum(populations[row["community"]].semi_disabled for row in community_results), 1e-9),
                6,
            ),
            "key_factor": "服务频次较高，价格与协同分流均会影响可及性",
        },
        {
            "group": "失能",
            "economic_accessibility": "较低",
            "geographic_accessibility": "较低",
            "service_accessibility": round(
                sum(populations[row["community"]].disabled * row["service_satisfaction"] for row in community_results)
                / max(sum(populations[row["community"]].disabled for row in community_results), 1e-9),
                6,
            ),
            "key_factor": "高需求服务占比更大，对价格、响应与公益服务保障更敏感",
        },
        {
            "group": "低收入小区",
            "economic_accessibility": "较低",
            "geographic_accessibility": "因布局而异",
            "service_accessibility": round(low_income_service_satisfaction, 6),
            "key_factor": "收入约束更强，对补贴与定价更敏感",
        },
    ]
    equity_metrics = compute_equity_metrics(
        community_rows=community_results,
        population_weights={community: item.elderly_total for community, item in populations.items()},
    )

    return PriceEvaluation(
        station_prices=station_prices,
        iteration_count=len(iteration_trace),
        converged=int(iteration_trace[-1].max_satisfaction_delta < epsilon) if iteration_trace else 0,
        average_service_satisfaction=average_service_satisfaction,
        minimum_service_satisfaction=minimum_service_satisfaction,
        average_service_access_performance=average_service_access_performance,
        minimum_service_access_performance=minimum_service_access_performance,
        vulnerable_service_satisfaction=vulnerable_service_satisfaction,
        annual_government_subsidy=sum(row["annual_government_subsidy"] for row in station_financials),
        annual_service_revenue=sum(row["annual_service_revenue"] for row in station_financials),
        annual_direct_cost=sum(row["annual_direct_cost"] for row in station_financials),
        annual_fixed_cost=sum(row["annual_fixed_cost"] for row in station_financials),
        annual_depreciation=sum(row["annual_depreciation"] for row in station_financials),
        annual_total_cost=total_total_cost,
        annual_net_profit_before_subsidy=total_net_profit_before_subsidy,
        annual_net_profit_after_subsidy=total_net_profit,
        annual_net_profit=sum(row["annual_net_profit"] for row in station_financials),
        profit_rate=total_net_profit / total_total_cost if total_total_cost > 1e-12 else -1.0,
        feasible_station_count=sum(row["profit_compliant"] for row in station_financials),
        profit_compliant=profit_compliant,
        satisfaction_compliant=satisfaction_compliant,
        low_income_service_satisfaction=low_income_service_satisfaction,
        low_income_served_coverage=low_income_served_coverage,
        served_population_coverage=served_population_coverage,
        weighted_served_population_coverage=weighted_served_population_coverage,
        served_demand_coverage=served_demand_coverage,
        damping_used=damping_used,
        iteration_trace=iteration_trace,
        station_financials=station_financials,
        community_results=community_results,
        accessibility_groups=accessibility_groups,
        subsidy_policy_label=subsidy_policy_label,
        gini_access=equity_metrics["gini_access"],
        theil_access=equity_metrics["theil_access"],
        max_min_gap=equity_metrics["max_min_gap"],
    )


def station_price_vector_to_text(price_vector: Dict[str, float]) -> str:
    parts = []
    for service in SERVICE_ORDER:
        parts.append(f"{service}:{price_vector[service]:.2f}")
    return "|".join(parts)


def station_price_satisfaction_to_text(price_vector: Dict[str, float]) -> str:
    base_prices = base_price_by_service()
    parts = []
    for service in SERVICE_ORDER:
        parts.append(f"{service}:{compute_price_satisfaction(base_prices[service], price_vector[service]):.2f}")
    return "|".join(parts)


def build_station_candidate_context(inputs: RQ3Inputs) -> Dict[str, object]:
    return {
        "base_prices": base_price_by_service(),
        "direct_costs": direct_cost_by_service(),
        "stations": stations_by_community(inputs.q2_stations),
        "distance_matrix": load_distance_matrix(),
        "satisfaction_rules": load_satisfaction_rules(),
        "detail_map": adjusted_demand_detail_map(inputs.adjusted_demand_detail),
    }


def approximate_station_candidate_row(
    inputs: RQ3Inputs,
    station_name: str,
    price_vector: Dict[str, float],
    context: Dict[str, object] | None = None,
) -> Dict[str, object]:
    resolved_context = context or build_station_candidate_context(inputs)
    base_prices = resolved_context["base_prices"]
    direct_costs = resolved_context["direct_costs"]
    stations = resolved_context["stations"]
    station = stations[station_name]
    distance_matrix = resolved_context["distance_matrix"]
    satisfaction_rules = resolved_context["satisfaction_rules"]
    detail_map = resolved_context["detail_map"]

    reachable_communities = [
        community
        for community in sorted(detail_map)
        if distance_matrix[community][station_name] <= 1000.0 + 1e-12
    ]
    raw_monthly_by_service = {service: 0.0 for service in SERVICE_ORDER}
    distance_scores: List[float] = []
    for community in reachable_communities:
        demand = compute_price_adjusted_monthly_demand_for_station(
            community=community,
            station_price_vector=price_vector,
            detail_map=detail_map,
        )
        for service in SERVICE_ORDER:
            raw_monthly_by_service[service] += demand[service]
        distance_scores.append(
            distance_satisfaction(distance_matrix[community][station_name], satisfaction_rules["distance"])
        )
    raw_daily_by_service = {
        service: raw_monthly_by_service[service] / DAYS_PER_MONTH
        for service in SERVICE_ORDER
    }
    raw_total_daily = sum(raw_daily_by_service.values())
    utilization = raw_total_daily / station.daily_capacity if station.daily_capacity > 0 else 1.0
    response_score = response_satisfaction_from_utilization(utilization, satisfaction_rules["response"])
    price_scores = {
        service: compute_price_satisfaction(base_prices[service], price_vector[service])
        for service in SERVICE_ORDER
    }
    avg_distance = sum(distance_scores) / len(distance_scores) if distance_scores else 0.0
    avg_price = sum(price_scores[service] for service in SERVICE_ORDER) / len(SERVICE_ORDER)
    station_average_service_satisfaction = (
        SATISFACTION_WEIGHTS["distance"] * avg_distance
        + SATISFACTION_WEIGHTS["response"] * response_score
        + SATISFACTION_WEIGHTS["price"] * avg_price
    )
    if station_average_service_satisfaction > 0:
        station_average_service_satisfaction = min(1.0, max(0.6, station_average_service_satisfaction))
    effective_daily_by_service = {
        service: raw_daily_by_service[service] * station_average_service_satisfaction
        for service in SERVICE_ORDER
    }
    annual_service_revenue = sum(
        effective_daily_by_service[service] * price_vector[service] * 365.0
        for service in SERVICE_ORDER
    )
    annual_government_subsidy = min(
        SUBSIDY_PER_EFFECTIVE_PERSON_TIME
        * sum(effective_daily_by_service[service] * 365.0 for service in NON_EMERGENCY_SERVICES),
        annual_subsidy_limit_for_station(station.scale),
    )
    annual_direct_cost = sum(
        raw_daily_by_service[service] * direct_costs[service] * 365.0
        for service in SERVICE_ORDER
    )
    annual_fixed_cost = station.annual_fixed_cost
    annual_depreciation = station.annual_depreciation
    annual_total_cost = annual_direct_cost + annual_fixed_cost + annual_depreciation
    annual_net_profit = annual_service_revenue + annual_government_subsidy - annual_total_cost
    profit_rate = annual_net_profit / annual_total_cost if annual_total_cost > 1e-12 else -1.0
    profit_compliant = int(MIN_PROFIT_RATE - 1e-9 <= profit_rate <= MAX_PROFIT_RATE + 1e-9)
    return {
        "station": station_name,
        "scale": station.scale,
        "selected_prices_by_service": station_price_vector_to_text(price_vector),
        "selected_price_satisfaction_by_service": station_price_satisfaction_to_text(price_vector),
        "station_average_price_satisfaction": round(avg_price, 6),
        "station_average_service_satisfaction": round(station_average_service_satisfaction, 6),
        "station_minimum_service_access_performance": round(
            0.0 if raw_total_daily <= 1e-12 else min(1.0, sum(effective_daily_by_service.values()) / max(raw_total_daily, 1e-12)),
            6,
        ),
        "annual_revenue": round(annual_service_revenue, 2),
        "annual_government_subsidy": round(annual_government_subsidy, 2),
        "annual_direct_cost": round(annual_direct_cost, 2),
        "annual_fixed_cost": round(annual_fixed_cost, 2),
        "annual_depreciation": round(annual_depreciation, 2),
        "annual_total_cost": round(annual_total_cost, 2),
        "annual_net_profit": round(annual_net_profit, 2),
        "profit_rate": round(profit_rate, 6),
        "profit_compliant": profit_compliant,
        "break_even_gap": round(max(0.0, -annual_net_profit), 2),
        "over_8pct_excess": round(max(0.0, profit_rate - MAX_PROFIT_RATE), 6),
    }


def generate_station_service_level_candidates(
    inputs: RQ3Inputs,
    price_grid_level: str = "full",
    max_candidates_per_station: int = DEFAULT_MAX_CANDIDATES_PER_STATION,
) -> Tuple[List[Dict[str, object]], Dict[str, List[Dict[str, object]]]]:
    candidate_grid = recommended_price_candidates(price_grid_level)
    context = build_station_candidate_context(inputs)
    station_rows: List[Dict[str, object]] = []
    kept_by_station: Dict[str, List[Dict[str, object]]] = {}
    for station in sorted(item.station_community for item in inputs.q2_stations):
        raw_candidates = [
            approximate_station_candidate_row(inputs, station, vector, context=context)
            for vector in enumerate_service_level_price_vectors(candidate_grid)
        ]
        kept = prune_station_candidates(
            raw_candidates,
            max_candidates_per_station=max_candidates_per_station,
        )
        for rank, row in enumerate(kept, start=1):
            row = dict(row)
            row["candidate_rank_within_station"] = rank
            station_rows.append(row)
            kept_by_station.setdefault(station, []).append(row)
    return station_rows, kept_by_station


def parse_price_vector_text(text: str) -> Dict[str, float]:
    result: Dict[str, float] = {}
    for token in text.split("|"):
        service, value = token.split(":", 1)
        result[service] = float(value)
    result["紧急救助"] = 0.0
    return result


def compose_global_profiles_from_station_candidates(
    kept_by_station: Dict[str, List[Dict[str, object]]],
    anchor_count: int = DEFAULT_GLOBAL_ANCHOR_COUNT,
    neighbor_seed_count: int = DEFAULT_NEIGHBOR_SEED_COUNT,
) -> List[Dict[str, Dict[str, float]]]:
    station_names = sorted(kept_by_station)
    anchor_choices = [
        rows[: min(anchor_count, len(rows))]
        for _, rows in sorted(kept_by_station.items())
    ]
    global_profiles: List[Dict[str, Dict[str, float]]] = []
    seen: set[str] = set()

    def add(profile_rows: Dict[str, Dict[str, object]]) -> None:
        profile = service_level_price_profile(
            station_names=station_names,
            service_prices_by_station={
                station_name: parse_price_vector_text(str(profile_rows[station_name]["selected_prices_by_service"]))
                for station_name in station_names
            },
        )
        signature = json.dumps(profile, ensure_ascii=False, sort_keys=True)
        if signature in seen:
            return
        seen.add(signature)
        global_profiles.append(profile)

    for combo in product(*anchor_choices):
        add({row["station"]: row for row in combo})

    baseline = {
        station_name: kept_by_station[station_name][0]
        for station_name in station_names
    }
    for station_name in station_names:
        for row in kept_by_station[station_name][: min(neighbor_seed_count, len(kept_by_station[station_name]))]:
            candidate = dict(baseline)
            candidate[station_name] = row
            add(candidate)
    return global_profiles


def select_focus_station_candidates(
    scenario_code: str,
    station_name: str,
    rows: List[Dict[str, object]],
    boundary_depth: int,
) -> List[Dict[str, object]]:
    focus = EXPANDED_SEARCH_FOCUS_STATIONS.get(scenario_code, {"loss": (), "cap": ()})
    selected: List[Dict[str, object]] = []
    seen: set[str] = set()

    def keep(candidates: Iterable[Dict[str, object]]) -> None:
        for row in candidates:
            signature = price_structure_signature(row)
            if signature in seen:
                continue
            seen.add(signature)
            selected.append(row)
            if len(selected) >= boundary_depth:
                return

    if station_name in focus.get("loss", ()):
        keep(sorted(rows, key=lambda row: (abs(float(row["profit_rate"]) - 0.0), -float(row["station_average_service_satisfaction"]), price_structure_signature(row))))
    if len(selected) < boundary_depth and station_name in focus.get("cap", ()):
        keep(sorted(rows, key=lambda row: (abs(float(row["profit_rate"]) - 0.08), -float(row["station_average_service_satisfaction"]), price_structure_signature(row))))
    if len(selected) < boundary_depth:
        keep(sorted(rows, key=lambda row: (float(row["break_even_gap"]), float(row["over_8pct_excess"]), price_structure_signature(row))))
    return selected[:boundary_depth]


def compose_expanded_global_profiles(
    kept_by_station: Dict[str, List[Dict[str, object]]],
    scenario_code: str,
    search_level: str,
    max_global_combinations: int,
    keep_near_boundary: bool,
    random_seed: int,
) -> List[Dict[str, Dict[str, float]]]:
    settings = expanded_search_level_settings(search_level)
    station_names = sorted(kept_by_station)
    rng = random.Random(f"{scenario_code}-{search_level}-{random_seed}")
    profiles: List[Dict[str, Dict[str, float]]] = []
    seen: set[str] = set()

    ranked_by_station = {
        station_name: sorted(rows, key=station_candidate_sort_key)
        for station_name, rows in kept_by_station.items()
    }

    def add(profile_rows: Dict[str, Dict[str, object]]) -> None:
        profile = service_level_price_profile(
            station_names=station_names,
            service_prices_by_station={
                station_name: parse_price_vector_text(str(profile_rows[station_name]["selected_prices_by_service"]))
                for station_name in station_names
            },
        )
        signature = json.dumps(profile, ensure_ascii=False, sort_keys=True)
        if signature in seen:
            return
        seen.add(signature)
        profiles.append(profile)

    deterministic_choices = [
        ranked_by_station[station_name][: min(settings["deterministic_depth"], len(ranked_by_station[station_name]))]
        for station_name in station_names
    ]
    for combo in product(*deterministic_choices):
        add({row["station"]: row for row in combo})
        if len(profiles) >= max_global_combinations:
            return profiles[:max_global_combinations]

    baseline_rows = {
        station_name: ranked_by_station[station_name][0]
        for station_name in station_names
    }
    for station_name in station_names:
        for row in ranked_by_station[station_name][: min(settings["diversity_depth"], len(ranked_by_station[station_name]))]:
            candidate = dict(baseline_rows)
            candidate[station_name] = row
            add(candidate)
            if len(profiles) >= max_global_combinations:
                return profiles[:max_global_combinations]

    if keep_near_boundary:
        boundary_choices = {
            station_name: select_focus_station_candidates(
                scenario_code=scenario_code,
                station_name=station_name,
                rows=ranked_by_station[station_name],
                boundary_depth=min(settings["boundary_depth"], len(ranked_by_station[station_name])),
            )
            for station_name in station_names
        }
        for combo in product(*(boundary_choices[station_name] for station_name in station_names)):
            add({row["station"]: row for row in combo})
            if len(profiles) >= max_global_combinations:
                return profiles[:max_global_combinations]

    diversity_buckets = {}
    for station_name in station_names:
        buckets: Dict[str, Dict[str, object]] = {}
        for row in ranked_by_station[station_name]:
            lead_token = str(row["selected_prices_by_service"]).split("|", 1)[0]
            buckets.setdefault(lead_token, row)
        diversity_buckets[station_name] = list(buckets.values())
    if all(diversity_buckets.values()):
        for combo in product(*(diversity_buckets[station_name][: min(settings["diversity_depth"], len(diversity_buckets[station_name]))] for station_name in station_names)):
            add({row["station"]: row for row in combo})
            if len(profiles) >= max_global_combinations:
                return profiles[:max_global_combinations]

    max_attempts = max_global_combinations * 20
    attempts = 0
    while len(profiles) < max_global_combinations and attempts < max_attempts:
        attempts += 1
        sampled = {
            station_name: rng.choice(ranked_by_station[station_name])
            for station_name in station_names
        }
        before = len(profiles)
        add(sampled)
        if len(profiles) == before:
            if len(seen) >= math.prod(len(ranked_by_station[station_name]) for station_name in station_names):
                break
    return profiles[:max_global_combinations]


def financial_gap_to_break_even_from_summary(row: Dict[str, object]) -> float:
    return max(0.0, -float(row["annual_net_profit"]))


def aggregate_profit_compliant_from_evaluation(item: PriceEvaluation) -> int:
    return int(MIN_PROFIT_RATE - 1e-9 <= float(item.profit_rate) <= MAX_PROFIT_RATE + 1e-9)


def evaluate_service_level_global_profiles(
    inputs: RQ3Inputs,
    global_profiles: List[Dict[str, Dict[str, float]]],
) -> List[Tuple[PriceEvaluation, Dict[str, object]]]:
    evaluated: List[Tuple[PriceEvaluation, Dict[str, object]]] = []
    for rank, profile in enumerate(global_profiles, start=1):
        item = evaluate_price_profile(
            inputs,
            profile,
            initial_satisfaction=initial_service_satisfaction_by_community(inputs.q2_allocations),
            subsidy_policy_label="none",
        )
        station_profit_ok = compute_station_profit_compliance(item.station_financials)
        summary = {
            "global_candidate_rank": rank,
            "pricing_model": "service_level_station_service_pricing",
            "price_scheme_detail": json.dumps(profile, ensure_ascii=False, sort_keys=True),
            "converged": item.converged,
            "all_station_profit_compliant": station_profit_ok,
            "average_service_access_performance": round(item.average_service_access_performance, 6),
            "minimum_service_access_performance": round(item.minimum_service_access_performance, 6),
            "average_service_satisfaction": round(item.average_service_satisfaction, 6),
            "minimum_service_satisfaction": round(item.minimum_service_satisfaction, 6),
            "annual_government_subsidy": round(item.annual_government_subsidy, 2),
            "annual_net_profit": round(item.annual_net_profit, 2),
            "profit_rate": round(item.profit_rate, 6),
            "joint_feasible_solution_exists": int(
                is_joint_feasible_service_level(
                    {
                        "converged": item.converged,
                        "all_station_profit_compliant": station_profit_ok,
                        "minimum_service_satisfaction": item.minimum_service_satisfaction,
                    }
                )
            ),
        }
        evaluated.append((item, summary))
    return evaluated


def closest_candidate_sort_key(item: PriceEvaluation, summary: Dict[str, object]) -> Tuple[float, float, float, float]:
    station_rates = [
        float(row["profit_rate"])
        for row in item.station_financials
    ]
    max_excess = max(max(0.0, rate - MAX_PROFIT_RATE) for rate in station_rates) if station_rates else 0.0
    max_shortfall = max(max(0.0, MIN_PROFIT_RATE - rate) for rate in station_rates) if station_rates else 0.0
    return (
        int(summary["converged"]) * -1,
        max(max_excess, max_shortfall),
        -float(summary["minimum_service_satisfaction"]),
        -float(summary["average_service_satisfaction"]),
    )


def generate_station_service_level_candidates_expanded(
    inputs: RQ3Inputs,
    scenario_code: str,
    price_grid_level: str,
    max_candidates_per_station: int,
    keep_near_boundary: bool,
) -> Tuple[List[Dict[str, object]], Dict[str, List[Dict[str, object]]]]:
    candidate_grid = recommended_price_candidates(price_grid_level)
    context = build_station_candidate_context(inputs)
    station_rows: List[Dict[str, object]] = []
    kept_by_station: Dict[str, List[Dict[str, object]]] = {}
    vectors = enumerate_service_level_price_vectors(candidate_grid)
    stage_start = time.time()
    progress_print(
        f"{scenario_code} | station-candidates start | elapsed={format_elapsed(0)} | eta=--:-- "
        f"| stations={len(inputs.q2_stations)} | raw_vectors_per_station={len(vectors)} | keep={max_candidates_per_station}."
    )
    station_names = sorted(item.station_community for item in inputs.q2_stations)
    for station_index, station in enumerate(station_names, start=1):
        station_start = time.time()
        raw_candidates = []
        for idx, vector in enumerate(vectors, start=1):
            raw_candidates.append(approximate_station_candidate_row(inputs, station, vector, context=context))
            if idx % STATION_VECTOR_PROGRESS_INTERVAL == 0:
                progress_print(
                    f"{scenario_code} | station={station} approx | elapsed={format_elapsed(time.time() - station_start)} "
                    f"| eta={format_eta(station_start, idx, len(vectors))} | done={idx}/{len(vectors)}."
                )
        kept = prune_station_candidates_expanded(
            candidates=raw_candidates,
            station_name=station,
            max_candidates_per_station=max_candidates_per_station,
            keep_near_boundary=keep_near_boundary,
        )
        progress_print(
            f"{scenario_code} | station={station} pruned | elapsed={format_elapsed(time.time() - station_start)} "
            f"| eta=00:00 | kept={len(kept)}/{len(raw_candidates)} | stage={station_index}/{len(station_names)}."
        )
        for rank, row in enumerate(kept, start=1):
            extended_row = dict(row)
            extended_row["scenario"] = scenario_code
            extended_row["candidate_rank_within_station"] = rank
            station_rows.append(extended_row)
            kept_by_station.setdefault(station, []).append(extended_row)
    progress_print(
        f"{scenario_code} | station-candidates done | elapsed={format_elapsed(time.time() - stage_start)} "
        f"| eta=00:00 | kept_total={len(station_rows)}."
    )
    return station_rows, kept_by_station


def evaluate_expanded_search_global_profiles(
    inputs: RQ3Inputs,
    scenario_code: str,
    search_level: str,
    global_profiles: List[Dict[str, Dict[str, float]]],
) -> List[Tuple[PriceEvaluation, Dict[str, object]]]:
    stage_start = time.time()
    progress_print(
        f"{scenario_code}/{search_level} | global-eval start | elapsed={format_elapsed(0)} | eta=--:-- "
        f"| combinations={len(global_profiles)}."
    )
    output: List[Tuple[PriceEvaluation, Dict[str, object]]] = []
    station_feasible_count = 0
    aggregate_feasible_count = 0
    for idx, profile in enumerate(global_profiles, start=1):
        item = evaluate_price_profile(
            inputs,
            profile,
            initial_satisfaction=initial_service_satisfaction_by_community(inputs.q2_allocations),
            subsidy_policy_label="none",
        )
        summary = {
            "global_candidate_rank": idx,
            "pricing_model": "service_level_station_service_pricing",
            "price_scheme_detail": json.dumps(profile, ensure_ascii=False, sort_keys=True),
            "converged": item.converged,
            "all_station_profit_compliant": compute_station_profit_compliance(item.station_financials),
            "average_service_access_performance": round(item.average_service_access_performance, 6),
            "minimum_service_access_performance": round(item.minimum_service_access_performance, 6),
            "average_service_satisfaction": round(item.average_service_satisfaction, 6),
            "minimum_service_satisfaction": round(item.minimum_service_satisfaction, 6),
            "annual_government_subsidy": round(item.annual_government_subsidy, 2),
            "annual_net_profit": round(item.annual_net_profit, 2),
            "profit_rate": round(item.profit_rate, 6),
            "joint_feasible_solution_exists": int(
                is_joint_feasible_service_level(
                    {
                        "converged": item.converged,
                        "all_station_profit_compliant": compute_station_profit_compliance(item.station_financials),
                        "minimum_service_satisfaction": item.minimum_service_satisfaction,
                    }
                )
            ),
        }
        station_rates = {
            row["station_community"]: round(float(row["profit_rate"]), 6)
            for row in item.station_financials
        }
        max_rate = max(station_rates.values()) if station_rates else -1.0
        min_rate = min(station_rates.values()) if station_rates else -1.0
        max_excess = max(max(0.0, rate - MAX_PROFIT_RATE) for rate in station_rates.values()) if station_rates else 0.0
        max_shortfall = max(max(0.0, MIN_PROFIT_RATE - rate) for rate in station_rates.values()) if station_rates else 0.0
        enriched = {
            "scenario": scenario_code,
            "search_level": search_level,
            "candidate_id": f"{scenario_code}_{search_level}_{idx:05d}",
            "converged": item.converged,
            "aggregate_profit_compliant": aggregate_profit_compliant_from_evaluation(item),
            "all_station_profit_compliant": compute_station_profit_compliance(item.station_financials),
            "joint_feasible": int(
                is_joint_feasible_service_level(
                    {
                        "converged": item.converged,
                        "all_station_profit_compliant": compute_station_profit_compliance(item.station_financials),
                        "minimum_service_satisfaction": item.minimum_service_satisfaction,
                    }
                )
            ),
            "average_service_access_performance": round(item.average_service_access_performance, 6),
            "minimum_service_access_performance": round(item.minimum_service_access_performance, 6),
            "annual_government_subsidy": round(item.annual_government_subsidy, 2),
            "annual_net_profit": round(item.annual_net_profit, 2),
            "aggregate_profit_rate": round(item.profit_rate, 6),
            "max_station_profit_rate": round(max_rate, 6),
            "min_station_profit_rate": round(min_rate, 6),
            "max_profit_excess_above_8pct": round(max_excess, 6),
            "max_profit_shortfall_below_0": round(max_shortfall, 6),
            "station_profit_rates": json.dumps(station_rates, ensure_ascii=False, sort_keys=True),
            "selected_prices_by_station_service": json.dumps(item.station_prices, ensure_ascii=False, sort_keys=True),
        }
        output.append((item, enriched))
        station_feasible_count += int(enriched["joint_feasible"])
        aggregate_feasible_count += int(
            enriched["converged"] == 1
            and enriched["aggregate_profit_compliant"] == 1
            and float(enriched["minimum_service_satisfaction"]) >= SERVICE_LEVEL_FAIRNESS_THRESHOLD - 1e-9
        )
        if idx % GLOBAL_PROGRESS_INTERVAL == 0 or idx == len(global_profiles):
            progress_print(
                f"{scenario_code}/{search_level} | global-eval progress | elapsed={format_elapsed(time.time() - stage_start)} "
                f"| eta={format_eta(stage_start, idx, len(global_profiles))} | done={idx}/{len(global_profiles)} "
                f"| station_feasible={station_feasible_count} | aggregate_feasible={aggregate_feasible_count}."
            )
    return output


def summarize_expanded_search_level(
    scenario_code: str,
    search_level: str,
    max_candidates_per_station: int,
    max_global_combinations: int,
    evaluated: List[Tuple[PriceEvaluation, Dict[str, object]]],
) -> Dict[str, object]:
    if not evaluated:
        return {
            "scenario": scenario_code,
            "search_level": search_level,
            "max_candidates_per_station": max_candidates_per_station,
            "max_global_combinations": max_global_combinations,
            "evaluated_global_combinations": 0,
            "converged_count": 0,
            "aggregate_joint_feasible_count": 0,
            "station_joint_feasible_count": 0,
            "best_joint_feasible_candidate_id": "",
            "best_average_access": 0.0,
            "best_minimum_access": 0.0,
            "best_station_profit_violation": 0.0,
            "closest_candidate_id": "",
            "closest_candidate_max_profit_rate": 0.0,
            "closest_candidate_min_profit_rate": 0.0,
            "closest_candidate_max_profit_excess_above_8pct": 0.0,
            "closest_candidate_max_profit_shortfall_below_0": 0.0,
        }
    converged_count = sum(int(summary["converged"]) for _item, summary in evaluated)
    aggregate_joint_feasible_count = sum(
        int(summary["converged"]) == 1 and int(summary["aggregate_profit_compliant"]) == 1 and float(summary["minimum_service_satisfaction"]) >= SERVICE_LEVEL_FAIRNESS_THRESHOLD - 1e-9
        for _item, summary in evaluated
    )
    station_joint_feasible = [
        (item, summary) for item, summary in evaluated if int(summary["joint_feasible"]) == 1
    ]
    closest_item, closest_summary = sorted(evaluated, key=lambda pair: closest_candidate_sort_key(pair[0], pair[1]))[0]
    if station_joint_feasible:
        best_item, best_summary = sorted(
            station_joint_feasible,
            key=lambda pair: (
                -pair[0].average_service_satisfaction,
                -pair[0].minimum_service_satisfaction,
                -pair[0].average_service_access_performance,
                pair[0].annual_government_subsidy,
            ),
        )[0]
        best_violation = 0.0
    else:
        best_item, best_summary = closest_item, closest_summary
        best_violation = max(
            float(best_summary["max_profit_excess_above_8pct"]),
            float(best_summary["max_profit_shortfall_below_0"]),
        )
    return {
        "scenario": scenario_code,
        "search_level": search_level,
        "max_candidates_per_station": max_candidates_per_station,
        "max_global_combinations": max_global_combinations,
        "evaluated_global_combinations": len(evaluated),
        "converged_count": converged_count,
        "aggregate_joint_feasible_count": aggregate_joint_feasible_count,
        "station_joint_feasible_count": len(station_joint_feasible),
        "best_joint_feasible_candidate_id": best_summary["candidate_id"] if station_joint_feasible else "",
        "best_average_access": round(best_item.average_service_access_performance, 6),
        "best_minimum_access": round(best_item.minimum_service_access_performance, 6),
        "best_station_profit_violation": round(best_violation, 6),
        "closest_candidate_id": closest_summary["candidate_id"],
        "closest_candidate_max_profit_rate": round(float(closest_summary["max_station_profit_rate"]), 6),
        "closest_candidate_min_profit_rate": round(float(closest_summary["min_station_profit_rate"]), 6),
        "closest_candidate_max_profit_excess_above_8pct": round(float(closest_summary["max_profit_excess_above_8pct"]), 6),
        "closest_candidate_max_profit_shortfall_below_0": round(float(closest_summary["max_profit_shortfall_below_0"]), 6),
    }


def build_expanded_search_station_rows(
    evaluated: List[Tuple[PriceEvaluation, Dict[str, object]]],
) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for item, summary in evaluated:
        for station_row in item.station_financials:
            rows.append(
                {
                    "scenario": summary["scenario"],
                    "search_level": summary["search_level"],
                    "candidate_id": summary["candidate_id"],
                    "station": station_row["station_community"],
                    "scale": station_row["scale"],
                    "selected_prices_by_service": station_price_vector_to_text(item.station_prices[station_row["station_community"]]),
                    "annual_service_revenue": round(station_row["annual_service_revenue"], 2),
                    "annual_government_subsidy": round(station_row["annual_government_subsidy"], 2),
                    "annual_direct_cost": round(station_row["annual_direct_cost"], 2),
                    "annual_fixed_cost": round(station_row["annual_fixed_cost"], 2),
                    "annual_depreciation": round(station_row["annual_depreciation"], 2),
                    "annual_total_cost": round(station_row["annual_total_cost"], 2),
                    "annual_net_profit": round(station_row["annual_net_profit"], 2),
                    "profit_rate": round(float(station_row["profit_rate"]), 6),
                    "profit_compliant": int(station_row["profit_compliant"]),
                    "break_even_gap": round(max(0.0, -float(station_row["annual_net_profit"])), 2),
                    "over_8pct_excess": round(max(0.0, float(station_row["profit_rate"]) - MAX_PROFIT_RATE), 6),
                }
            )
    return rows


def write_expanded_search_notes(
    summary_rows: List[Dict[str, object]],
    evaluated_by_key: Dict[Tuple[str, str], List[Tuple[PriceEvaluation, Dict[str, object]]]],
) -> None:
    lines = [
        "# 3.5 Expanded Search Notes",
        "",
        "本轮扩搜在不改变 3_5 主模型口径的前提下，扩大了逐站候选保留规模与全局组合预算，并继续以全局固定点复算后的逐站利润率作为唯一财务合规判断口径。",
        "",
    ]
    for summary in summary_rows:
        scenario = str(summary["scenario"])
        search_level = str(summary["search_level"])
        lines.append(f"## {scenario} / {search_level}")
        lines.append(f"- evaluated_global_combinations = {summary['evaluated_global_combinations']}")
        lines.append(f"- converged_count = {summary['converged_count']}")
        lines.append(f"- aggregate_joint_feasible_count = {summary['aggregate_joint_feasible_count']}")
        lines.append(f"- station_joint_feasible_count = {summary['station_joint_feasible_count']}")
        if int(summary["station_joint_feasible_count"]) > 0:
            lines.append(f"- 在扩展候选搜索中找到可行方案，best_joint_feasible_candidate_id = {summary['best_joint_feasible_candidate_id']}。")
        else:
            lines.append("- 在当前扩展候选网格、候选保留规模和全局组合预算下仍未找到。")
            candidate_list = evaluated_by_key.get((scenario, search_level), [])
            if candidate_list:
                closest_item, closest_summary = sorted(candidate_list, key=lambda pair: closest_candidate_sort_key(pair[0], pair[1]))[0]
                lines.append(
                    "- 最接近可行方案的逐站利润率为："
                    + ", ".join(
                        f"{row['station_community']}={float(row['profit_rate']):.6f}"
                        for row in closest_item.station_financials
                    )
                    + "。"
                )
        if scenario == "S0":
            lines.append("- S0 重点观察 G、I 等亏损边界站点；若仍不可行，说明基准预算下容量与收益结构仍不足以支撑逐站保本微利。")
        if scenario == "S4":
            lines.append("- S4 重点观察 C 站 8% 上界与 J 站保本下界；若仍不可行，说明扩容虽改善公平可及性，但逐站财务边界仍未同时满足。")
        lines.append("")
    (OUTPUT_DIR / "3_5_expanded_search_notes.md").write_text("\n".join(lines), encoding="utf-8")


def run_service_level_pricing_expanded_search(
    scenarios: Tuple[str, ...] = SERVICE_LEVEL_SCENARIOS,
    search_levels: Tuple[str, ...] = ("light", "medium", "heavy"),
    price_grid_level: str = "full",
    max_candidates_per_station: int | None = None,
    max_global_combinations: int | None = None,
    keep_near_boundary: bool = True,
    random_seed: int = 42,
    write_outputs: bool = True,
) -> Dict[str, List[Dict[str, object]]]:
    budget_by_scenario = {"S0": 120.0, "S4": 140.0}
    all_summary_rows: List[Dict[str, object]] = []
    all_global_rows: List[Dict[str, object]] = []
    all_station_rows: List[Dict[str, object]] = []
    evaluated_by_key: Dict[Tuple[str, str], List[Tuple[PriceEvaluation, Dict[str, object]]]] = {}

    for scenario_code in scenarios:
        scenario_start = time.time()
        progress_print(f"{scenario_code} | expanded-search start | elapsed={format_elapsed(0)} | eta=--:--.")
        inputs = build_rq3_inputs_for_budget_scenario(scenario_code, budget_by_scenario[scenario_code])
        for level_index, search_level in enumerate(search_levels, start=1):
            level_start = time.time()
            settings = expanded_search_level_settings(search_level)
            candidate_cap = max_candidates_per_station or settings["max_candidates_per_station"]
            combination_cap = max_global_combinations or settings["max_global_combinations"]
            progress_print(
                f"{scenario_code}/{search_level} | search-level start | elapsed={format_elapsed(time.time() - scenario_start)} "
                f"| eta=--:-- | level={level_index}/{len(search_levels)} | candidate_cap={candidate_cap} "
                f"| global_cap={combination_cap} | keep_near_boundary={int(keep_near_boundary)} | seed={random_seed}."
            )
            _station_candidates, kept_by_station = generate_station_service_level_candidates_expanded(
                inputs=inputs,
                scenario_code=scenario_code,
                price_grid_level=price_grid_level,
                max_candidates_per_station=candidate_cap,
                keep_near_boundary=keep_near_boundary,
            )
            global_profiles = compose_expanded_global_profiles(
                kept_by_station=kept_by_station,
                scenario_code=scenario_code,
                search_level=search_level,
                max_global_combinations=combination_cap,
                keep_near_boundary=keep_near_boundary,
                random_seed=random_seed,
            )
            evaluated = evaluate_expanded_search_global_profiles(
                inputs=inputs,
                scenario_code=scenario_code,
                search_level=search_level,
                global_profiles=global_profiles,
            )
            evaluated_by_key[(scenario_code, search_level)] = evaluated
            all_global_rows.extend(summary for _item, summary in evaluated)
            all_station_rows.extend(build_expanded_search_station_rows(evaluated))
            all_summary_rows.append(
                summarize_expanded_search_level(
                    scenario_code=scenario_code,
                    search_level=search_level,
                    max_candidates_per_station=candidate_cap,
                    max_global_combinations=combination_cap,
                    evaluated=evaluated,
                )
            )
            summary = all_summary_rows[-1]
            progress_print(
                f"{scenario_code}/{search_level} | search-level done | elapsed={format_elapsed(time.time() - level_start)} "
                f"| eta=00:00 | evaluated={summary['evaluated_global_combinations']} "
                f"| station_feasible={summary['station_joint_feasible_count']} "
                f"| aggregate_feasible={summary['aggregate_joint_feasible_count']}."
            )
        progress_print(
            f"{scenario_code} | expanded-search done | elapsed={format_elapsed(time.time() - scenario_start)} | eta=00:00."
        )

    if write_outputs:
        write_csv(OUTPUT_DIR / "3_5_expanded_search_summary.csv", all_summary_rows)
        write_csv(OUTPUT_DIR / "3_5_expanded_search_global_candidates.csv", all_global_rows)
        write_csv(OUTPUT_DIR / "3_5_expanded_search_by_station.csv", all_station_rows)
        write_expanded_search_notes(all_summary_rows, evaluated_by_key)
    return {
        "summary_rows": all_summary_rows,
        "global_rows": all_global_rows,
        "station_rows": all_station_rows,
    }


def select_service_level_schemes(
    evaluated: List[Tuple[PriceEvaluation, Dict[str, object]]],
) -> Dict[str, Tuple[PriceEvaluation, Dict[str, object]]]:
    joint_feasible = [
        pair for pair in evaluated
        if int(pair[1]["joint_feasible_solution_exists"]) == 1
    ]
    financial_ok = [
        pair for pair in evaluated
        if int(pair[1]["all_station_profit_compliant"]) == 1 and pair[0].converged == 1
    ]
    if joint_feasible:
        best_joint = sorted(
            joint_feasible,
            key=lambda pair: (
                -pair[0].average_service_satisfaction,
                -pair[0].minimum_service_satisfaction,
                -pair[0].average_service_access_performance,
                pair[0].annual_government_subsidy,
            ),
        )[0]
    else:
        best_joint = sorted(
            evaluated,
            key=lambda pair: (
                -int(pair[1]["all_station_profit_compliant"]),
                -pair[0].converged,
                -pair[0].average_service_satisfaction,
                -pair[0].minimum_service_satisfaction,
                -pair[0].average_service_access_performance,
                pair[0].annual_government_subsidy,
            ),
        )[0]
    financial_best = sorted(
        financial_ok or evaluated,
        key=lambda pair: (
            -int(pair[1]["all_station_profit_compliant"]),
            -pair[0].average_service_satisfaction,
            -pair[0].minimum_service_satisfaction,
            -pair[0].average_service_access_performance,
            pair[0].annual_government_subsidy,
        ),
    )[0]
    satisfaction_best = sorted(
        evaluated,
        key=lambda pair: (
            -pair[0].minimum_service_satisfaction,
            -pair[0].average_service_satisfaction,
            -pair[0].minimum_service_access_performance,
            int(pair[1]["all_station_profit_compliant"]),
            pair[0].annual_government_subsidy,
        ),
    )[0]
    return {
        "joint_feasible_best_satisfaction": best_joint,
        "financial_best": financial_best,
        "satisfaction_best": satisfaction_best,
        "fairness_best": satisfaction_best,
    }


def write_service_level_outputs_for_scenario(
    scenario_code: str,
    selected_schemes: Dict[str, Tuple[PriceEvaluation, Dict[str, object]]],
    station_candidates: List[Dict[str, object]],
    global_candidates: List[Tuple[PriceEvaluation, Dict[str, object]]],
) -> Dict[str, List[Dict[str, object]]]:
    station_candidate_rows = [{"scenario": scenario_code, **row} for row in station_candidates]
    global_candidate_rows = [{"scenario": scenario_code, **summary} for _item, summary in global_candidates]
    summary_rows = []
    for label, (item, summary) in selected_schemes.items():
        summary_rows.append(
            {
                "scenario": scenario_code,
                "scheme_label": label,
                **summary,
                "average_service_satisfaction": round(item.average_service_satisfaction, 6),
                "minimum_service_satisfaction": round(item.minimum_service_satisfaction, 6),
                "served_population_coverage": round(item.served_population_coverage, 6),
                "weighted_served_population_coverage": round(item.weighted_served_population_coverage, 6),
                "served_demand_coverage": round(item.served_demand_coverage, 6),
            }
        )
    best_joint_item = selected_schemes["joint_feasible_best_satisfaction"][0]
    station_rows = [
        {
            "scenario": scenario_code,
            "station": row["station_community"],
            "scale": row["scale"],
            "annual_service_revenue": round(row["annual_service_revenue"], 2),
            "annual_government_subsidy": round(row["annual_government_subsidy"], 2),
            "annual_direct_cost": round(row["annual_direct_cost"], 2),
            "annual_fixed_cost": round(row["annual_fixed_cost"], 2),
            "annual_depreciation": round(row["annual_depreciation"], 2),
            "annual_total_cost": round(row["annual_total_cost"], 2),
            "annual_net_profit": round(row["annual_net_profit"], 2),
            "profit_rate": round(row["profit_rate"], 6),
            "profit_compliant": int(row["profit_compliant"]),
        }
        for row in best_joint_item.station_financials
    ]
    community_rows = [
        {
            "scenario": scenario_code,
            "community": row["community"],
            "assigned_station": row.get("primary_station", ""),
            "distance_satisfaction": round(row["distance_satisfaction"], 6),
            "response_satisfaction": round(row["response_satisfaction"], 6),
            "price_satisfaction": round(row["price_satisfaction"], 6),
            "service_satisfaction": round(row["service_satisfaction"], 6),
            "demand_service_ratio": round(row["demand_service_ratio"], 6),
            "service_access_performance": round(row["service_access_performance"], 6),
        }
        for row in best_joint_item.community_results
    ]
    return {
        "station_candidates": station_candidate_rows,
        "global_candidates": global_candidate_rows,
        "summary_rows": summary_rows,
        "station_rows": station_rows,
        "community_rows": community_rows,
    }


def write_service_level_notes(
    scenario_results: Dict[str, Dict[str, Tuple[PriceEvaluation, Dict[str, object]]]],
) -> None:
    lines = [
        "# 3.5 Satisfaction-Objective Pricing Notes",
        "",
        "## 结论",
        "",
        "问题3主目标现已统一为“最大化老人满意度”，具体落实为最大化社区平均满意度；`service_access_performance` 仅保留为辅助可及绩效指标，不再承担主目标含义。",
        "",
        "站点级统一溢价要求同一站 5 项收费服务共用同一溢价系数，会压缩可行域；站点—服务项目级定价允许不同服务承担不同保本压力，因此理论上扩大可行域。",
        "",
    ]
    for scenario_code in SERVICE_LEVEL_SCENARIOS:
        joint_item, joint_summary = scenario_results[scenario_code]["joint_feasible_best_satisfaction"]
        financial_item, _ = scenario_results[scenario_code]["financial_best"]
        satisfaction_item, _ = scenario_results[scenario_code]["satisfaction_best"]
        lines.append(f"## {scenario_code}")
        lines.append(
            f"- joint_feasible_solution_exists = {int(joint_summary['joint_feasible_solution_exists'])}."
        )
        lines.append(
            f"- financial_best: avg_satisfaction={financial_item.average_service_satisfaction:.6f}, min_satisfaction={financial_item.minimum_service_satisfaction:.6f}, station_profit_ok={compute_station_profit_compliance(financial_item.station_financials)}."
        )
        lines.append(
            f"- satisfaction_priority_best: avg_satisfaction={satisfaction_item.average_service_satisfaction:.6f}, min_satisfaction={satisfaction_item.minimum_service_satisfaction:.6f}, station_profit_ok={compute_station_profit_compliance(satisfaction_item.station_financials)}."
        )
        lines.append(
            f"- auxiliary_access_metrics: avg_access={joint_item.average_service_access_performance:.6f}, min_access={joint_item.minimum_service_access_performance:.6f}."
        )
        if int(joint_summary["joint_feasible_solution_exists"]) == 1:
            lines.append(
                "- 找到逐站利润率合规、收敛且满足满意度阈值的联合可行解，可将其作为严格满足题目硬约束的主推荐方案。"
            )
        else:
            infeasible_stations = [
                f"{row['station_community']}:{row['profit_rate']:.6f}"
                for row in joint_item.station_financials
                if not (MIN_PROFIT_RATE - 1e-9 <= float(row["profit_rate"]) <= MAX_PROFIT_RATE + 1e-9)
            ]
            lines.append(
                "- 未找到联合可行解。最接近方案仍受逐站利润率硬约束或满意度阈值限制，问题站点为："
                + (", ".join(infeasible_stations) if infeasible_stations else "无")
                + "。"
            )
        lines.append(
            "- 区域统筹、站点间调剂或统收统支仅能作为扩展政策建议，未被用作主模型可行性判断。"
        )
        lines.append("")
    (OUTPUT_DIR / f"{SERVICE_LEVEL_OUTPUT_PREFIX}_notes.md").write_text("\n".join(lines), encoding="utf-8")


def run_service_level_pricing(
    max_candidates_per_station: int = DEFAULT_MAX_CANDIDATES_PER_STATION,
    price_grid_level: str = "full",
) -> None:
    comparison_rows = []
    scenario_results: Dict[str, Dict[str, Tuple[PriceEvaluation, Dict[str, object]]]] = {}
    all_station_candidate_rows: List[Dict[str, object]] = []
    all_global_candidate_rows: List[Dict[str, object]] = []
    all_summary_rows: List[Dict[str, object]] = []
    all_station_rows: List[Dict[str, object]] = []
    all_community_rows: List[Dict[str, object]] = []
    for scenario_code, budget_limit in [("S0", 120.0), ("S4", 140.0)]:
        progress_print(f"3_5 main scenario {scenario_code}: start.")
        inputs = build_rq3_inputs_for_budget_scenario(scenario_code, budget_limit)
        station_candidates, kept_by_station = generate_station_service_level_candidates(
            inputs,
            price_grid_level=price_grid_level,
            max_candidates_per_station=max_candidates_per_station,
        )
        progress_print(
            f"3_5 main scenario {scenario_code}: station_candidates={len(station_candidates)}, "
            f"stations={len(kept_by_station)}."
        )
        global_profiles = compose_global_profiles_from_station_candidates(kept_by_station)[:48]
        progress_print(f"3_5 main scenario {scenario_code}: evaluating {len(global_profiles)} global profiles.")
        evaluated = evaluate_service_level_global_profiles(inputs, global_profiles)
        selected = select_service_level_schemes(evaluated)
        scenario_results[scenario_code] = selected
        written_rows = write_service_level_outputs_for_scenario(scenario_code, selected, station_candidates, evaluated)
        all_station_candidate_rows.extend(written_rows["station_candidates"])
        all_global_candidate_rows.extend(written_rows["global_candidates"])
        all_summary_rows.extend(written_rows["summary_rows"])
        all_station_rows.extend(written_rows["station_rows"])
        all_community_rows.extend(written_rows["community_rows"])

        baseline_inputs = inputs
        baseline_profiles = enumerate_station_price_profiles(baseline_inputs)
        baseline_evaluations = evaluate_candidate_profiles(baseline_inputs, baseline_profiles[:64])
        old_financial = select_financial_best(baseline_evaluations)
        new_financial = selected["financial_best"][0]
        comparison_rows.append(
            {
                "scenario": scenario_code,
                "old_pricing_model": "station_level_uniform_premium",
                "new_pricing_model": "service_level_station_service_pricing",
                "old_joint_feasible_solution_exists": int(joint_feasible_solution_exists(baseline_evaluations)),
                "new_joint_feasible_solution_exists": int(selected["joint_feasible_best_satisfaction"][1]["joint_feasible_solution_exists"]),
                "old_average_service_access_performance": round(old_financial.average_service_access_performance, 6),
                "new_average_service_access_performance": round(new_financial.average_service_access_performance, 6),
                "old_minimum_service_access_performance": round(old_financial.minimum_service_access_performance, 6),
                "new_minimum_service_access_performance": round(new_financial.minimum_service_access_performance, 6),
                "old_profit_compliant_station_count": int(old_financial.feasible_station_count),
                "new_profit_compliant_station_count": sum(int(row["profit_compliant"]) for row in new_financial.station_financials),
                "old_annual_government_subsidy": round(old_financial.annual_government_subsidy, 2),
                "new_annual_government_subsidy": round(new_financial.annual_government_subsidy, 2),
                "old_annual_net_profit": round(old_financial.annual_net_profit, 2),
                "new_annual_net_profit": round(new_financial.annual_net_profit, 2),
                "old_converged": old_financial.converged,
                "new_converged": new_financial.converged,
            }
        )
        progress_print(f"3_5 main scenario {scenario_code}: done.")
    write_csv(OUTPUT_DIR / f"{SERVICE_LEVEL_OUTPUT_PREFIX}_station_candidates.csv", all_station_candidate_rows)
    write_csv(OUTPUT_DIR / f"{SERVICE_LEVEL_OUTPUT_PREFIX}_global_candidates.csv", all_global_candidate_rows)
    write_csv(OUTPUT_DIR / f"{SERVICE_LEVEL_OUTPUT_PREFIX}_summary.csv", all_summary_rows)
    write_csv(OUTPUT_DIR / f"{SERVICE_LEVEL_OUTPUT_PREFIX}_by_station.csv", all_station_rows)
    write_csv(OUTPUT_DIR / f"{SERVICE_LEVEL_OUTPUT_PREFIX}_community_satisfaction.csv", all_community_rows)
    write_csv(OUTPUT_DIR / f"{SERVICE_LEVEL_OUTPUT_PREFIX}_model_comparison.csv", comparison_rows)
    write_service_level_notes(scenario_results)


def sort_price_evaluations(evaluations: List[PriceEvaluation]) -> List[PriceEvaluation]:
    assign_pareto_ranks(evaluations)
    return sorted(
        evaluations,
        key=lambda item: (
            -item.profit_compliant,
            -item.converged,
            -item.average_service_satisfaction,
            -item.minimum_service_satisfaction,
            item.pareto_rank,
            -item.feasible_station_count,
            -item.satisfaction_compliant,
            item.gini_access,
            item.max_min_gap,
            -item.vulnerable_service_satisfaction,
            -item.average_service_access_performance,
            item.annual_government_subsidy,
        ),
    )


def sort_financial_compliant_evaluations(evaluations: List[PriceEvaluation]) -> List[PriceEvaluation]:
    assign_pareto_ranks(evaluations)
    return sorted(
        evaluations,
        key=lambda item: (
            -item.profit_compliant,
            -item.converged,
            -item.average_service_satisfaction,
            -item.minimum_service_satisfaction,
            item.pareto_rank,
            -item.feasible_station_count,
            -item.satisfaction_compliant,
            -item.profit_rate,
            item.gini_access,
            -item.vulnerable_service_satisfaction,
            -item.average_service_access_performance,
            item.annual_government_subsidy,
        ),
    )


def sort_satisfaction_priority_evaluations(evaluations: List[PriceEvaluation]) -> List[PriceEvaluation]:
    assign_pareto_ranks(evaluations)
    return sorted(
        evaluations,
        key=lambda item: (
            -item.satisfaction_compliant,
            -item.average_service_satisfaction,
            -item.minimum_service_satisfaction,
            item.pareto_rank,
            item.gini_access,
            item.max_min_gap,
            -item.low_income_service_satisfaction,
            -item.vulnerable_service_satisfaction,
            -item.average_service_access_performance,
            -item.minimum_service_access_performance,
            -item.converged,
            -item.profit_compliant,
            item.annual_government_subsidy,
        ),
    )


def select_financial_best(evaluations: List[PriceEvaluation]) -> PriceEvaluation:
    return sort_financial_compliant_evaluations(evaluations)[0]


def select_satisfaction_best(evaluations: List[PriceEvaluation]) -> PriceEvaluation:
    converged = [item for item in evaluations if item.converged == 1]
    if converged:
        return sort_satisfaction_priority_evaluations(converged)[0]
    return sort_satisfaction_priority_evaluations(evaluations)[0]


def sort_fairness_priority_evaluations(evaluations: List[PriceEvaluation]) -> List[PriceEvaluation]:
    return sort_satisfaction_priority_evaluations(evaluations)


def select_fairness_best(evaluations: List[PriceEvaluation]) -> PriceEvaluation:
    return select_satisfaction_best(evaluations)


def evaluation_summary_row(item: PriceEvaluation) -> Dict[str, object]:
    if hasattr(item, "satisfaction_compliant"):
        satisfaction_compliant = int(getattr(item, "satisfaction_compliant"))
    else:
        satisfaction_compliant = int(getattr(item, "fair_satisfaction_compliant"))
    station_labels = []
    for station_name in sorted(item.station_prices):
        station_labels.append(
            f"{station_name}:"
            + ",".join(
                f"{service}={item.station_prices[station_name][service]:.2f}"
                for service in NON_EMERGENCY_SERVICES
            )
        )
    return {
        "price_scheme_detail": ";".join(station_labels),
        "pricing_model": "station_service_level_pricing",
        "pricing_formula": "p_{j,r} independent for r=1,...,5; p_{j,6}=0",
        "subsidy_policy": item.subsidy_policy_label,
        "pareto_rank": item.pareto_rank,
        "iteration_count": item.iteration_count,
        "iterations": item.iteration_count,
        "converged": item.converged,
        "damping_used": item.damping_used,
        "profit_compliant": item.profit_compliant,
        "satisfaction_compliant": satisfaction_compliant,
        "fair_satisfaction_compliant": satisfaction_compliant,
        "feasible_station_count": item.feasible_station_count,
        "average_service_satisfaction": round(item.average_service_satisfaction, 6),
        "minimum_service_satisfaction": round(item.minimum_service_satisfaction, 6),
        "average_service_access_performance": round(item.average_service_access_performance, 6),
        "minimum_service_access_performance": round(item.minimum_service_access_performance, 6),
        "vulnerable_service_satisfaction": round(item.vulnerable_service_satisfaction, 6),
        "low_income_service_satisfaction": round(item.low_income_service_satisfaction, 6),
        "low_income_served_coverage": round(item.low_income_served_coverage, 6),
        "served_population_coverage": round(item.served_population_coverage, 6),
        "weighted_served_population_coverage": round(item.weighted_served_population_coverage, 6),
        "served_demand_coverage": round(item.served_demand_coverage, 6),
        "gini_access": round(item.gini_access, 6),
        "theil_access": round(item.theil_access, 6),
        "max_min_gap": round(item.max_min_gap, 6),
        "annual_government_subsidy": round(item.annual_government_subsidy, 2),
        "annual_service_revenue": round(item.annual_service_revenue, 2),
        "annual_direct_cost": round(item.annual_direct_cost, 2),
        "annual_fixed_cost": round(item.annual_fixed_cost, 2),
        "annual_depreciation": round(item.annual_depreciation, 2),
        "annual_total_cost": round(item.annual_total_cost, 2),
        "annual_net_profit_before_subsidy": round(item.annual_net_profit_before_subsidy, 2),
        "annual_net_profit_after_subsidy": round(item.annual_net_profit_after_subsidy, 2),
        "annual_net_profit": round(item.annual_net_profit, 2),
        "profit_rate": round(item.profit_rate, 6),
        "financial_gap_to_break_even": round(financial_gap_to_break_even(item), 2),
    }


def write_price_evaluation_bundle(prefix: str, item: PriceEvaluation) -> None:
    write_csv(OUTPUT_DIR / f"{prefix}_summary.csv", [evaluation_summary_row(item)])
    write_csv(
        OUTPUT_DIR / f"{prefix}_stations.csv",
        [
            {
                **row,
                "annual_service_revenue": round(row["annual_service_revenue"], 2),
                "annual_direct_cost": round(row["annual_direct_cost"], 2),
                "annual_fixed_cost": round(row["annual_fixed_cost"], 2),
                "annual_depreciation": round(row["annual_depreciation"], 2),
                "annual_government_subsidy": round(row["annual_government_subsidy"], 2),
                "annual_subsidy": round(row["annual_subsidy"], 2),
                "annual_total_cost": round(row["annual_total_cost"], 2),
                "annual_net_profit_before_subsidy": round(row["annual_net_profit_before_subsidy"], 2),
                "annual_net_profit_after_subsidy": round(row["annual_net_profit_after_subsidy"], 2),
                "annual_net_profit": round(row["annual_net_profit"], 2),
                "profit_rate": round(row["profit_rate"], 6),
                "profit_compliant": row["profit_compliant"],
                "emergency_public_loss": round(row["emergency_public_loss"], 2),
            }
            for row in item.station_financials
        ],
    )
    write_csv(
        OUTPUT_DIR / f"{prefix}_communities.csv",
        [
            {
                **row,
                "distance_satisfaction": round(row["distance_satisfaction"], 6),
                "response_satisfaction": round(row["response_satisfaction"], 6),
                "service_satisfaction": round(row["service_satisfaction"], 6),
                "service_access_performance": round(row["service_access_performance"], 6),
                "price_satisfaction": round(row["price_satisfaction"], 6),
                "adjusted_demand_daily": round(row["adjusted_demand_daily"], 4),
                "raw_served_demand_daily": round(row["raw_served_demand_daily"], 4),
                "effective_person_times_daily": round(row["effective_person_times_daily"], 4),
                "demand_service_ratio": round(row["demand_service_ratio"], 6),
            }
            for row in item.community_results
        ],
    )
    write_csv(
        OUTPUT_DIR / f"{prefix}_iteration_trace.csv",
        [
            {
                "iteration": row.iteration,
                "max_satisfaction_delta": round(row.max_satisfaction_delta, 8),
                "average_service_satisfaction": round(row.average_service_satisfaction, 6),
                "feasible_station_count": row.feasible_station_count,
                "total_subsidy": round(row.total_subsidy, 2),
                "damping_used": row.damping_used,
            }
            for row in item.iteration_trace
        ],
    )
    write_csv(
        OUTPUT_DIR / f"{prefix}_accessibility_groups.csv",
        item.accessibility_groups,
    )


def scheme_comparison_row(
    scheme_label: str,
    item: PriceEvaluation,
) -> Dict[str, object]:
    return {
        "scheme_label": scheme_label,
        **evaluation_summary_row(item),
    }


def unique_frontier_rows(ranked_evaluations: List[PriceEvaluation]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    seen_metric_signatures: set[tuple[object, ...]] = set()
    for item in ranked_evaluations:
        if item.pareto_rank != 1:
            continue
        row = evaluation_summary_row(item)
        signature = (
            row["subsidy_policy"],
            row["profit_rate"],
            row["average_service_satisfaction"],
            row["minimum_service_satisfaction"],
            row["average_service_access_performance"],
            row["minimum_service_access_performance"],
            row["gini_access"],
            row["theil_access"],
            row["max_min_gap"],
            row["converged"],
            row["profit_compliant"],
            row["satisfaction_compliant"],
        )
        if signature in seen_metric_signatures:
            continue
        seen_metric_signatures.add(signature)
        rows.append(row)
    return rows


def evaluate_candidate_profiles(
    inputs: RQ3Inputs,
    candidate_profiles: List[Dict[str, Dict[str, float]]],
    initial_warm_start: Dict[str, float] | None = None,
) -> List[PriceEvaluation]:
    evaluations: List[PriceEvaluation] = []
    for subsidy_budget in subsidy_budget_candidates():
        warm_start_satisfaction = initial_warm_start
        for profile in candidate_profiles:
            subsidy_policy_label = "none" if subsidy_budget <= 1e-12 else f"targeted_subsidy_{subsidy_budget:.1f}"
            evaluation = evaluate_price_profile(
                inputs,
                profile,
                initial_satisfaction=warm_start_satisfaction,
                subsidy_budget_per_person=subsidy_budget,
                subsidy_policy_label=subsidy_policy_label,
            )
            evaluations.append(evaluation)
            warm_start_satisfaction = {
                row["community"]: row["service_satisfaction"]
                for row in evaluation.community_results
            }
    return evaluations


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Solve RQ3 pricing/subsidy model.")
    parser.add_argument(
        "--max-candidate-profiles",
        type=int,
        default=None,
        help="Optional cap on enumerated station price profiles for faster reproducible reruns.",
    )
    parser.add_argument(
        "--max-candidates-per-station",
        type=int,
        default=None,
        help="Maximum retained service-level candidates for each station.",
    )
    parser.add_argument(
        "--price-grid-level",
        choices=["basic", "full"],
        default="full",
        help="Price grid level for service-level pricing candidates.",
    )
    parser.add_argument(
        "--price-grid",
        choices=["basic", "full"],
        default=None,
        help="Alias of --price-grid-level for expanded search runs.",
    )
    parser.add_argument(
        "--run-expanded-search",
        action="store_true",
        help="Run controlled expanded search and write 3_5_expanded_search_* outputs without touching legacy model logic.",
    )
    parser.add_argument(
        "--expanded-search-only",
        action="store_true",
        help="Run only expanded search outputs and skip regenerating 3_5 main outputs.",
    )
    parser.add_argument(
        "--scenarios",
        default="S0,S4",
        help="Comma-separated scenarios for expanded search, e.g. S0,S4.",
    )
    parser.add_argument(
        "--search-levels",
        default="light,medium,heavy",
        help="Comma-separated expanded search levels, e.g. light,medium,heavy,extreme.",
    )
    parser.add_argument(
        "--search-level",
        choices=["light", "medium", "heavy", "extreme"],
        default=None,
        help="Single expanded search level alias.",
    )
    parser.add_argument(
        "--max-global-combinations",
        type=int,
        default=None,
        help="Optional override for expanded-search global combination cap.",
    )
    parser.add_argument(
        "--keep-near-boundary",
        action="store_true",
        help="Retain boundary-focused candidates/combinations in expanded search.",
    )
    parser.add_argument(
        "--no-keep-near-boundary",
        action="store_true",
        help="Disable boundary-focused candidate retention in expanded search.",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        help="Random seed for expanded-search sampled combinations.",
    )
    return parser.parse_args()


def main(
    max_candidate_profiles: int | None = None,
    max_candidates_per_station: int | None = None,
    price_grid_level: str = "full",
    run_expanded_search: bool = False,
    expanded_search_only: bool = False,
    scenarios: Tuple[str, ...] = SERVICE_LEVEL_SCENARIOS,
    search_levels: Tuple[str, ...] = ("light", "medium", "heavy"),
    max_global_combinations: int | None = None,
    keep_near_boundary: bool = False,
    random_seed: int = 42,
) -> None:
    if expanded_search_only:
        run_service_level_pricing_expanded_search(
            scenarios=scenarios,
            search_levels=search_levels,
            price_grid_level=price_grid_level,
            max_candidates_per_station=max_candidates_per_station,
            max_global_combinations=max_global_combinations,
            keep_near_boundary=keep_near_boundary,
            random_seed=random_seed,
            write_outputs=True,
        )
        print("Generated expanded search outputs without overwriting 3_5 main outputs.")
        return

    inputs = load_rq3_inputs()
    station_candidates, kept_by_station = generate_station_service_level_candidates(
        inputs,
        price_grid_level=price_grid_level,
        max_candidates_per_station=max_candidates_per_station or DEFAULT_MAX_CANDIDATES_PER_STATION,
    )
    candidate_profiles = compose_global_profiles_from_station_candidates(kept_by_station)
    if max_candidate_profiles is not None:
        candidate_profiles = candidate_profiles[:max_candidate_profiles]

    primary_evaluations = evaluate_candidate_profiles(inputs, candidate_profiles)
    ranked_primary = sort_price_evaluations(primary_evaluations)

    rescue_evaluations: List[PriceEvaluation] = []
    if ranked_primary and ranked_primary[0].profit_compliant == 0:
        rescue_candidates = generate_rescue_price_profiles(inputs, ranked_primary)
        for candidate in rescue_candidates:
            rescue_evaluations.append(
                evaluate_price_profile(
                    inputs,
                    candidate.station_prices,
                    initial_satisfaction=candidate.warm_start_satisfaction,
                    subsidy_budget_per_person=candidate.subsidy_budget_per_person,
                    subsidy_policy_label=candidate.subsidy_policy_label,
                )
            )

    all_evaluations = primary_evaluations + rescue_evaluations
    ranked = sort_price_evaluations(all_evaluations)
    financial_best = select_financial_best(all_evaluations)
    satisfaction_best = select_satisfaction_best(all_evaluations)
    joint_feasible = joint_feasible_solution_exists(all_evaluations)

    write_price_evaluation_bundle("3_1_best_price_scheme", financial_best)
    write_price_evaluation_bundle("3_1_aux_financial_best_price_scheme", financial_best)
    write_price_evaluation_bundle("3_1_aux_fairness_best_price_scheme", satisfaction_best)
    write_csv(
        OUTPUT_DIR / "3_1_aux_top_price_schemes.csv",
        [evaluation_summary_row(item) for item in ranked[:10]],
    )
    write_csv(
        OUTPUT_DIR / "3_1_aux_pareto_frontier.csv",
        unique_frontier_rows(ranked),
    )
    write_csv(
        OUTPUT_DIR / "3_1_aux_dual_scheme_comparison.csv",
        [
            {
                **scheme_comparison_row("financial_sustainable_scheme", financial_best),
                "summary": (
                    "财务优先方案；优先满足利润率合规。"
                    if financial_best.profit_compliant == 1
                    else "财务优先方案；当前仍未满足利润率合规。"
                ),
                "fiscal_gap": round(financial_gap_to_break_even(financial_best), 2),
                "joint_feasible_solution_exists": int(joint_feasible),
            },
            {
                **scheme_comparison_row("satisfaction_priority_scheme", satisfaction_best),
                "summary": (
                    "满意度优先方案；优先提高最低老人满意度/平均老人满意度。"
                ),
                "fiscal_gap": round(financial_gap_to_break_even(satisfaction_best), 2),
                "joint_feasible_solution_exists": int(joint_feasible),
            },
        ],
    )
    write_csv(
        OUTPUT_DIR / "3_1_aux_scheme_status_summary.csv",
        [
            {
                "financial_sustainable_scheme": "3_1_aux_financial_best_price_scheme",
                "satisfaction_priority_scheme": "3_1_aux_fairness_best_price_scheme",
                "joint_feasible_solution_exists": int(joint_feasible),
                "summary": (
                    "存在同时满足财务合规、满意度阈值与收敛要求的方案。"
                    if joint_feasible
                    else "在当前预算、补贴上限和服务需求下，调价无法同时实现财务合规与满意度阈值，需要追加补贴、扩容或专项公益服务补贴。"
                ),
            }
        ],
    )

    print(
        "Evaluated "
        f"{len(primary_evaluations)} primary candidates and "
        f"{len(rescue_evaluations)} rescue candidates."
    )
    print(
        "Financial sustainable scheme: "
        f"avg service satisfaction={financial_best.average_service_satisfaction:.6f}, "
        f"minimum service satisfaction={financial_best.minimum_service_satisfaction:.6f}, "
        f"profit compliant={financial_best.profit_compliant}, "
        f"satisfaction compliant={financial_best.satisfaction_compliant}, "
        f"iterations={financial_best.iteration_count}"
    )
    print(
        "Satisfaction priority scheme: "
        f"avg service satisfaction={satisfaction_best.average_service_satisfaction:.6f}, "
        f"minimum service satisfaction={satisfaction_best.minimum_service_satisfaction:.6f}, "
        f"profit compliant={satisfaction_best.profit_compliant}, "
        f"satisfaction compliant={satisfaction_best.satisfaction_compliant}, "
        f"iterations={satisfaction_best.iteration_count}"
    )
    print(
        "Current Q3 main model uses station-service-level pricing, "
        "re-evaluates each community's unique best station by satisfaction, "
        "and applies station-level proportional scaling when capacity is insufficient."
    )
    if not joint_feasible:
        print(
            "No jointly feasible solution found under current budget, subsidy cap, and demand: "
            "additional subsidy, capacity expansion, or dedicated public-service support is required."
        )
    run_service_level_pricing(
        max_candidates_per_station=max_candidates_per_station or DEFAULT_MAX_CANDIDATES_PER_STATION,
        price_grid_level=price_grid_level,
    )
    print(
        "Generated service-level pricing outputs for S0 and S4 with station-wise profit validation."
    )
    if run_expanded_search:
        run_service_level_pricing_expanded_search(
            scenarios=scenarios,
            search_levels=search_levels,
            price_grid_level=price_grid_level,
            max_candidates_per_station=max_candidates_per_station,
            max_global_combinations=max_global_combinations,
            keep_near_boundary=keep_near_boundary,
            random_seed=random_seed,
            write_outputs=True,
        )
        print("Generated expanded search outputs for controlled station-service pricing search.")


if __name__ == "__main__":
    args = parse_args()
    resolved_price_grid = args.price_grid or args.price_grid_level
    scenario_tokens = tuple(token.strip() for token in args.scenarios.split(",") if token.strip())
    level_tokens = (
        (args.search_level,)
        if args.search_level is not None
        else tuple(token.strip() for token in args.search_levels.split(",") if token.strip())
    )
    main(
        max_candidate_profiles=args.max_candidate_profiles,
        max_candidates_per_station=args.max_candidates_per_station,
        price_grid_level=resolved_price_grid,
        run_expanded_search=args.run_expanded_search,
        expanded_search_only=args.expanded_search_only,
        scenarios=scenario_tokens,
        search_levels=level_tokens,
        max_global_combinations=args.max_global_combinations,
        keep_near_boundary=(False if args.no_keep_near_boundary else args.keep_near_boundary),
        random_seed=args.random_seed,
    )
