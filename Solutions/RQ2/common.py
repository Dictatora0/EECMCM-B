from __future__ import annotations

from dataclasses import dataclass
from importlib.util import module_from_spec, spec_from_file_location
import json
import math
from pathlib import Path
from typing import Dict, Iterable, List, Tuple
import csv
import sys
import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp


RQ2_DIR = Path(__file__).resolve().parent
ROOT = RQ2_DIR.parents[1]
OUTPUT_DIR = RQ2_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

RQ1_DIR = ROOT / "Solutions" / "RQ1"
RQ1_COMMON_PATH = RQ1_DIR / "common.py"
RQ1_SPEC = spec_from_file_location("rq1_common_module", RQ1_COMMON_PATH)
if RQ1_SPEC is None or RQ1_SPEC.loader is None:
    raise RuntimeError(f"Failed to load RQ1 common module from {RQ1_COMMON_PATH}")
RQ1_COMMON = module_from_spec(RQ1_SPEC)
sys.modules[RQ1_SPEC.name] = RQ1_COMMON
RQ1_SPEC.loader.exec_module(RQ1_COMMON)

DATA_DIR = RQ1_COMMON.DATA_DIR
RQ1_OUTPUT_DIR = RQ1_COMMON.OUTPUT_DIR
SERVICE_ORDER = RQ1_COMMON.SERVICE_ORDER
load_community_data = RQ1_COMMON.load_community_data
read_xlsx_raw = RQ1_COMMON.read_xlsx_raw
write_csv = RQ1_COMMON.write_csv


BUDGET_LIMIT = 120.0
RADIUS_LIMIT = 1000.0
DAYS_PER_MONTH = 30.0
MONTHS_PER_YEAR = 12.0
DEPRECIATION_YEARS = 20.0
MIN_PROFIT_RATE = 0.0
MAX_PROFIT_RATE = 0.08
MAX_CANDIDATE_SCHEMES = 4 ** 10
SATISFACTION_WEIGHTS = {"distance": 0.2, "response": 0.3, "price": 0.5}
BASE_PRICE_SATISFACTION = 1.0
OVERFLOW_PENALTY = 0.08
MOVABLE_SERVICES = {"助餐", "日间照料", "上门护理", "康复理疗", "助浴"}
SAFE_CAPACITY_THRESHOLD = 0.50
SAFE_CAPACITY_THRESHOLD_GRID = [0.25, 0.50, 0.75, 1.00]
MILP_TOLERANCE = 1e-6


@dataclass(frozen=True)
class StationScale:
    name: str
    build_cost_wan: float
    daily_fixed_cost: float
    daily_capacity: float


@dataclass
class CommunityDemand:
    community: str
    elderly_population: float
    adjusted_monthly_demand: Dict[str, float]


@dataclass
class CandidateStation:
    community: str
    scale: str
    build_cost_wan: float
    daily_fixed_cost: float
    daily_capacity: float


@dataclass
class CommunityAllocation:
    community: str
    primary_station: str | None
    overflow_station: str | None
    geographic_reachable: int
    actually_served: int
    geographic_population_covered: float
    served_population_covered: float
    raw_served_demand_daily: float
    effective_person_times_daily: float
    primary_load: float
    overflow_load: float
    unmet_load: float
    geographic_satisfaction: float
    response_satisfaction: float
    price_satisfaction: float
    service_satisfaction: float
    adjusted_demand_daily: float = 0.0
    demand_service_ratio: float = 0.0
    service_access_performance: float = 0.0
    elderly_population: float = 0.0


@dataclass
class StationMetrics:
    community: str
    scale: str
    daily_capacity: float
    assigned_primary_load: float
    assigned_overflow_load: float
    total_load: float
    utilization: float
    annual_service_revenue: float
    annual_direct_cost: float
    annual_fixed_cost: float
    annual_depreciation: float
    annual_government_subsidy_baseline: float
    annual_net_profit_before_subsidy: float
    annual_net_profit_after_policy_subsidy: float
    annual_revenue: float = 0.0
    annual_subsidy: float = 0.0
    annual_total_cost: float = 0.0
    annual_net_profit: float = 0.0
    profit_rate: float = 0.0
    profit_compliant: int = 0


@dataclass
class SchemeEvaluation:
    scheme_code: Tuple[int, ...]
    stations: List[CandidateStation]
    allocations: List[CommunityAllocation]
    station_metrics: List[StationMetrics]
    geographic_population_coverage: float
    served_population_coverage: float
    served_demand_coverage: float
    average_service_satisfaction: float
    minimum_service_satisfaction: float
    total_raw_served_demand_daily: float
    total_effective_person_times_daily: float
    capacity_safety_rate: float
    max_station_utilization: float
    fully_safe: int
    utilization_variance: float
    annual_net_profit_before_subsidy: float
    annual_net_profit_after_policy_subsidy: float
    weighted_served_population_coverage: float = 0.0
    average_service_access_performance: float = 0.0
    minimum_service_access_performance: float = 0.0
    total_adjusted_demand_daily: float = 0.0
    annual_revenue: float = 0.0
    annual_subsidy: float = 0.0
    annual_direct_cost: float = 0.0
    annual_fixed_cost: float = 0.0
    annual_depreciation: float = 0.0
    annual_total_cost: float = 0.0
    annual_net_profit: float = 0.0
    profit_rate: float = 0.0
    profit_compliant: int = 0


SCALE_ORDER = {
    0: None,
    1: "小型",
    2: "中型",
    3: "大型",
}


def load_station_scales() -> Dict[str, StationScale]:
    sheets = read_xlsx_raw(DATA_DIR / "附件3：服务站建设与运营成本.xlsx")
    rows = sheets["服务站建设与运营成本"]
    result: Dict[str, StationScale] = {}
    for row in rows[2:5]:
        scale = str(row[0]).strip()
        result[scale] = StationScale(
            name=scale,
            build_cost_wan=float(row[1]),
            daily_fixed_cost=float(row[2]),
            daily_capacity=float(row[3]),
        )
    assert set(result) == {"小型", "中型", "大型"}, "Station scale sheet is incomplete"
    return result


def load_distance_matrix() -> Dict[str, Dict[str, float]]:
    sheets = read_xlsx_raw(DATA_DIR / "附件4：小区间距离矩阵.xlsx")
    rows = sheets["小区间距离矩阵"]
    header = [str(x).strip() for x in rows[1][1:11]]
    matrix: Dict[str, Dict[str, float]] = {}
    for row in rows[2:12]:
        community = str(row[0]).strip()
        matrix[community] = {header[idx - 1]: float(row[idx]) for idx in range(1, 11)}
    return matrix


def load_satisfaction_rules() -> Dict[str, List[Tuple[float, float]]]:
    sheets = read_xlsx_raw(DATA_DIR / "附件5：满意度评分规则.xlsx")
    rows = sheets["满意度评分规则"]
    distance_rules = [
        (300.0, 1.00),
        (500.0, 0.90),
        (650.0, 0.75),
        (1000.0, 0.60),
    ]
    response_rules = [
        (0.60, 1.00),
        (0.75, 0.93),
        (0.85, 0.85),
        (0.95, 0.72),
        (1.00, 0.60),
    ]
    assert rows[2][0].startswith("因素 1"), "Unexpected satisfaction rules layout"
    return {"distance": distance_rules, "response": response_rules}


def load_adjusted_demand_summary() -> List[CommunityDemand]:
    path = RQ1_OUTPUT_DIR / "1_3_high_precision_adjusted_demand.csv"
    validate_high_precision_input_path(path)
    validate_rq1_high_precision_metadata(expected_file=path.name, expected_years=None)
    with path.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    grouped: Dict[str, Dict[str, float]] = {}
    for row in rows:
        grouped.setdefault(row["community"], {})[row["service"]] = float(row["adjusted_monthly_demand"])
    year5_population = load_year5_population_totals()
    result = []
    for community, demand in grouped.items():
        result.append(
            CommunityDemand(
                community=community,
                elderly_population=year5_population[community],
                adjusted_monthly_demand=demand,
            )
        )
    assert len(result) == 10, "Expected adjusted demand for 10 communities"
    return sorted(result, key=lambda item: item.community)


def load_theoretical_demand_summary() -> Dict[str, Dict[str, float]]:
    path = RQ1_OUTPUT_DIR / "1_2_high_precision_theoretical_demand.csv"
    validate_high_precision_input_path(path)
    validate_rq1_high_precision_metadata(expected_file=path.name, expected_years=None)
    with path.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    grouped: Dict[str, Dict[str, float]] = {}
    for row in rows:
        grouped.setdefault(row["community"], {})[row["service"]] = float(row["theoretical_monthly_demand"])
    return grouped


def load_year5_population_totals() -> Dict[str, float]:
    path = RQ1_OUTPUT_DIR / "1_1_high_precision_year5_population.csv"
    validate_high_precision_input_path(path)
    validate_rq1_high_precision_metadata(expected_file=path.name, expected_years=[5])
    with path.open(encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    assert all(int(row["year"]) == 5 for row in rows), "Year-5 high-precision population file must only contain year == 5 rows"
    result = {
        row["community"]: float(row["elderly_total"])
        for row in rows
    }
    assert len(result) == 10, "Expected year-5 population totals for 10 communities"
    return result


def validate_high_precision_input_path(path: Path) -> None:
    forbidden_keywords = ["rounded", "report", "summary_rounded"]
    lower_name = path.name.lower()
    assert all(keyword not in lower_name for keyword in forbidden_keywords), (
        f"RQ2 must not read rounded/report inputs: {path.name}"
    )


def validate_rq1_high_precision_metadata(expected_file: str, expected_years: List[int] | None) -> None:
    metadata_path = RQ1_OUTPUT_DIR / "rq1_high_precision_metadata.json"
    assert metadata_path.exists(), "Missing rq1_high_precision_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata.get("precision") == "high", "RQ2 requires high-precision RQ1 outputs"
    assert metadata.get("rounded_for_report") is False, "RQ2 inputs must not be rounded report tables"
    files = metadata.get("files", {})
    assert expected_file in files.values(), f"{expected_file} not declared in RQ1 metadata"
    if expected_years is not None:
        contains_years = metadata.get("contains_years", [])
        assert all(year in contains_years for year in expected_years), "Metadata year coverage mismatch"


def load_service_costs() -> Dict[str, Dict[str, float]]:
    return RQ1_COMMON.load_service_costs()


def distance_satisfaction(distance: float, rules: List[Tuple[float, float]]) -> float:
    if distance > RADIUS_LIMIT:
        return 0.0
    for threshold, score in rules:
        if distance <= threshold:
            return score
    return 0.0


def response_satisfaction(utilization: float, rules: List[Tuple[float, float]]) -> float:
    for threshold, score in rules:
        if utilization <= threshold + 1e-12:
            return score
    return 0.60


def average_price_per_visit(service_costs: Dict[str, Dict[str, float]], demand: Dict[str, float]) -> float:
    total_visits = sum(demand[service] for service in SERVICE_ORDER)
    if total_visits <= 0:
        return 0.0
    return sum(demand[service] * service_costs[service]["price"] for service in SERVICE_ORDER) / total_visits


def monthly_to_daily_load(demand: Dict[str, float]) -> float:
    return sum(demand.values()) / DAYS_PER_MONTH


def clamp_service_satisfaction(value: float) -> float:
    return min(1.0, max(0.6, value))


def compute_service_metrics(
    raw_served_demand_daily: float,
    adjusted_demand_daily: float,
    service_satisfaction: float,
) -> Dict[str, float]:
    if raw_served_demand_daily <= 1e-12:
        return {
            "effective_person_times_daily": 0.0,
            "demand_service_ratio": 0.0,
            "service_access_performance": 0.0,
        }
    demand_service_ratio = (
        min(1.0, raw_served_demand_daily / adjusted_demand_daily)
        if adjusted_demand_daily > 1e-12
        else 0.0
    )
    effective_person_times_daily = raw_served_demand_daily * service_satisfaction
    service_access_performance = (
        effective_person_times_daily / adjusted_demand_daily
        if adjusted_demand_daily > 1e-12
        else 0.0
    )
    return {
        "effective_person_times_daily": effective_person_times_daily,
        "demand_service_ratio": demand_service_ratio,
        "service_access_performance": service_access_performance,
    }


def subsidy_cap_per_day(scale: str) -> float:
    return {
        "小型": 1000.0,
        "中型": 1800.0,
        "大型": 2600.0,
    }[scale]


def compute_annual_financial_metrics(
    scale: str,
    build_cost_wan: float,
    daily_fixed_cost: float,
    raw_daily_by_service: Dict[str, float],
    effective_daily_by_service: Dict[str, float],
    service_costs: Dict[str, Dict[str, float]],
) -> Dict[str, float]:
    annual_revenue = sum(
        effective_daily_by_service[service] * service_costs[service]["price"] * 365.0
        for service in SERVICE_ORDER
    )
    annual_subsidy = min(
        2.0
        * sum(
            effective_daily_by_service[service] * 365.0
            for service in SERVICE_ORDER
            if service != "紧急救助"
        ),
        subsidy_cap_per_day(scale) * 365.0,
    )
    annual_direct_cost = sum(
        raw_daily_by_service[service] * service_costs[service]["direct_cost"] * 365.0
        for service in SERVICE_ORDER
    )
    annual_fixed_cost = daily_fixed_cost * 365.0
    annual_depreciation = build_cost_wan * 10000.0 / DEPRECIATION_YEARS
    annual_total_cost = annual_direct_cost + annual_fixed_cost + annual_depreciation
    annual_net_profit_before_subsidy = annual_revenue - annual_total_cost
    annual_net_profit = annual_revenue + annual_subsidy - annual_total_cost
    profit_rate = annual_net_profit / annual_total_cost if annual_total_cost > 0 else -1.0
    profit_compliant = int(MIN_PROFIT_RATE - 1e-9 <= profit_rate <= MAX_PROFIT_RATE + 1e-9)
    return {
        "annual_revenue": annual_revenue,
        "annual_subsidy": annual_subsidy,
        "annual_direct_cost": annual_direct_cost,
        "annual_fixed_cost": annual_fixed_cost,
        "annual_depreciation": annual_depreciation,
        "annual_total_cost": annual_total_cost,
        "annual_net_profit_before_subsidy": annual_net_profit_before_subsidy,
        "annual_net_profit": annual_net_profit,
        "profit_rate": profit_rate,
        "profit_compliant": profit_compliant,
    }


def compute_weighted_served_population_coverage(allocations: List[CommunityAllocation]) -> float:
    numerator = 0.0
    denominator = 0.0
    for item in allocations:
        population = item.elderly_population
        if population <= 1e-12:
            population = max(item.geographic_population_covered, item.served_population_covered)
        denominator += population
        numerator += population * item.demand_service_ratio
    return numerator / denominator if denominator > 1e-12 else 0.0


def annual_financials_for_load(
    demand: Dict[str, float],
    service_costs: Dict[str, Dict[str, float]],
    build_cost_wan: float,
    daily_fixed_cost: float,
) -> Dict[str, float]:
    daily_load = {service: demand[service] / DAYS_PER_MONTH for service in SERVICE_ORDER}
    result = compute_annual_financial_metrics(
        scale="小型",
        build_cost_wan=build_cost_wan,
        daily_fixed_cost=daily_fixed_cost,
        raw_daily_by_service=daily_load,
        effective_daily_by_service=daily_load,
        service_costs=service_costs,
    )
    return {
        "annual_service_revenue": result["annual_revenue"],
        "annual_direct_cost": result["annual_direct_cost"],
        "annual_fixed_cost": result["annual_fixed_cost"],
        "annual_depreciation_cost": result["annual_depreciation"],
        "annual_government_subsidy": result["annual_subsidy"],
        "annual_net_profit": result["annual_net_profit"],
    }


def scheme_from_code(
    communities: List[str],
    scheme_code: Tuple[int, ...],
    scales: Dict[str, StationScale],
) -> List[CandidateStation]:
    stations: List[CandidateStation] = []
    for community, token in zip(communities, scheme_code):
        scale_name = SCALE_ORDER[token]
        if scale_name is None:
            continue
        scale = scales[scale_name]
        stations.append(
            CandidateStation(
                community=community,
                scale=scale.name,
                build_cost_wan=scale.build_cost_wan,
                daily_fixed_cost=scale.daily_fixed_cost,
                daily_capacity=scale.daily_capacity,
            )
        )
    return stations


def total_build_cost(stations: List[CandidateStation]) -> float:
    return sum(station.build_cost_wan for station in stations)


def scheme_profit_compliance(station_metrics: List[StationMetrics]) -> int:
    if not station_metrics:
        return 0
    return int(all(metric.profit_compliant == 1 for metric in station_metrics))


def solve_location_milp(
    communities: List[CommunityDemand],
    distance_matrix: Dict[str, Dict[str, float]],
    scales: Dict[str, StationScale],
    budget_limit: float = BUDGET_LIMIT,
    fairness_weight: float = 0.2,
    safety_capacity_factor: float = 0.85,
) -> Tuple[int, ...] | None:
    community_names = [item.community for item in communities]
    scale_tokens = [1, 2, 3]
    scale_by_token = {1: scales["小型"], 2: scales["中型"], 3: scales["大型"]}
    daily_demand = {
        item.community: community_total_daily_demand(item)
        for item in communities
    }
    total_demand = sum(daily_demand.values())
    if total_demand <= MILP_TOLERANCE:
        return tuple(1 for _ in community_names)

    reachable_pairs: List[Tuple[str, str]] = []
    for demand_community in community_names:
        for station_community in community_names:
            if distance_matrix[demand_community][station_community] <= RADIUS_LIMIT + MILP_TOLERANCE:
                reachable_pairs.append((demand_community, station_community))

    build_indices: Dict[Tuple[str, int], int] = {}
    assignment_indices: Dict[Tuple[str, str], int] = {}
    idx = 0
    for station_community in community_names:
        for token in scale_tokens:
            build_indices[(station_community, token)] = idx
            idx += 1
    for pair in reachable_pairs:
        assignment_indices[pair] = idx
        idx += 1
    eta_idx = idx
    var_count = eta_idx + 1

    c = np.zeros(var_count, dtype=float)
    integrality = np.zeros(var_count, dtype=int)
    lb = np.zeros(var_count, dtype=float)
    ub = np.full(var_count, np.inf, dtype=float)

    for (station_community, token), var_idx in build_indices.items():
        del station_community
        integrality[var_idx] = 1
        ub[var_idx] = 1.0
        c[var_idx] = 1e-4 * scale_by_token[token].build_cost_wan

    fairness_weight = min(max(fairness_weight, 0.0), 1.0)
    served_weight = 1.0 - fairness_weight
    for demand_community, station_community in reachable_pairs:
        demand_value = daily_demand[demand_community]
        ub[assignment_indices[(demand_community, station_community)]] = demand_value
        distance = distance_matrix[demand_community][station_community]
        distance_bonus = max(0.0, 1.0 - distance / RADIUS_LIMIT)
        unit_benefit = served_weight / total_demand + 0.05 * distance_bonus / total_demand
        c[assignment_indices[(demand_community, station_community)]] = -unit_benefit
    ub[eta_idx] = 1.0
    c[eta_idx] = -fairness_weight

    rows = []
    lbs = []
    ubs = []

    budget_row = np.zeros(var_count, dtype=float)
    for (station_community, token), var_idx in build_indices.items():
        del station_community
        budget_row[var_idx] = scale_by_token[token].build_cost_wan
    rows.append(budget_row)
    lbs.append(-np.inf)
    ubs.append(budget_limit)

    at_least_one_row = np.zeros(var_count, dtype=float)
    for var_idx in build_indices.values():
        at_least_one_row[var_idx] = 1.0
    rows.append(at_least_one_row)
    lbs.append(1.0)
    ubs.append(np.inf)

    for station_community in community_names:
        row = np.zeros(var_count, dtype=float)
        for token in scale_tokens:
            row[build_indices[(station_community, token)]] = 1.0
        rows.append(row)
        lbs.append(-np.inf)
        ubs.append(1.0)

    for demand_community in community_names:
        row = np.zeros(var_count, dtype=float)
        for station_community in community_names:
            pair = (demand_community, station_community)
            if pair in assignment_indices:
                row[assignment_indices[pair]] = 1.0
        rows.append(row)
        lbs.append(-np.inf)
        ubs.append(daily_demand[demand_community])

        fairness_row = np.zeros(var_count, dtype=float)
        for station_community in community_names:
            pair = (demand_community, station_community)
            if pair in assignment_indices:
                fairness_row[assignment_indices[pair]] = 1.0
        fairness_row[eta_idx] = -daily_demand[demand_community]
        rows.append(fairness_row)
        lbs.append(0.0)
        ubs.append(np.inf)

    for station_community in community_names:
        cap_row = np.zeros(var_count, dtype=float)
        for demand_community in community_names:
            pair = (demand_community, station_community)
            if pair in assignment_indices:
                cap_row[assignment_indices[pair]] = 1.0
        for token in scale_tokens:
            cap_row[build_indices[(station_community, token)]] = (
                -safety_capacity_factor * scale_by_token[token].daily_capacity
            )
        rows.append(cap_row)
        lbs.append(-np.inf)
        ubs.append(0.0)

    for demand_community, station_community in reachable_pairs:
        row = np.zeros(var_count, dtype=float)
        row[assignment_indices[(demand_community, station_community)]] = 1.0
        for token in scale_tokens:
            row[build_indices[(station_community, token)]] = -daily_demand[demand_community]
        rows.append(row)
        lbs.append(-np.inf)
        ubs.append(0.0)

    constraints = [
        LinearConstraint(np.vstack(rows), np.array(lbs, dtype=float), np.array(ubs, dtype=float))
    ]
    result = milp(
        c=c,
        integrality=integrality,
        bounds=Bounds(lb, ub),
        constraints=constraints,
        options={"mip_rel_gap": 1e-8},
    )
    if not result.success or result.x is None:
        return None

    scheme_code: List[int] = []
    for station_community in community_names:
        chosen_token = 0
        chosen_value = 0.0
        for token in scale_tokens:
            value = float(result.x[build_indices[(station_community, token)]])
            if value > chosen_value + 0.5:
                chosen_token = token
                chosen_value = value
        scheme_code.append(chosen_token)
    return tuple(scheme_code)


def enumerate_scheme_codes(n: int) -> Iterable[Tuple[int, ...]]:
    raise NotImplementedError("Use enumerate_feasible_scheme_codes instead")


def enumerate_feasible_scheme_codes(
    communities: List[str],
    scales: Dict[str, StationScale],
    budget_limit: float = BUDGET_LIMIT,
) -> Iterable[Tuple[int, ...]]:
    scale_costs = {
        0: 0.0,
        1: scales["小型"].build_cost_wan,
        2: scales["中型"].build_cost_wan,
        3: scales["大型"].build_cost_wan,
    }

    def dfs(idx: int, spent: float, current: List[int]) -> Iterable[Tuple[int, ...]]:
        if spent > budget_limit + 1e-9:
            return
        if idx == len(communities):
            if any(token > 0 for token in current):
                yield tuple(current)
            return
        for token in (0, 1, 2, 3):
            current.append(token)
            yield from dfs(idx + 1, spent + scale_costs[token], current)
            current.pop()

    yield from dfs(0, 0.0, [])


def community_total_monthly_demand(item: CommunityDemand) -> float:
    return sum(item.adjusted_monthly_demand.values())


def community_total_daily_demand(item: CommunityDemand) -> float:
    return community_total_monthly_demand(item) / DAYS_PER_MONTH


def evaluate_scheme(
    scheme_code: Tuple[int, ...],
    communities: List[CommunityDemand],
    distance_matrix: Dict[str, Dict[str, float]],
    scales: Dict[str, StationScale],
    satisfaction_rules: Dict[str, List[Tuple[float, float]]],
    service_costs: Dict[str, Dict[str, float]],
    budget_limit: float = BUDGET_LIMIT,
) -> SchemeEvaluation | None:
    station_names = [item.community for item in communities]
    stations = scheme_from_code(station_names, scheme_code, scales)
    if not stations:
        return None
    if total_build_cost(stations) > budget_limit + 1e-9:
        return None

    response_by_station = {station.community: 1.0 for station in stations}
    allocations: List[CommunityAllocation] = []
    station_metrics: List[StationMetrics] = []
    for _ in range(20):
        allocations, station_metrics, next_response = allocate_with_response_scores(
            stations=stations,
            communities=communities,
            distance_matrix=distance_matrix,
            distance_rules=satisfaction_rules["distance"],
            response_rules=satisfaction_rules["response"],
            response_by_station=response_by_station,
            service_costs=service_costs,
        )
        diff = max(
            abs(next_response[name] - response_by_station[name])
            for name in response_by_station
        )
        response_by_station = next_response
        if diff < 1e-6:
            break

    allocations, station_metrics, response_by_station = allocate_with_response_scores(
        stations=stations,
        communities=communities,
        distance_matrix=distance_matrix,
        distance_rules=satisfaction_rules["distance"],
        response_rules=satisfaction_rules["response"],
        response_by_station=response_by_station,
        service_costs=service_costs,
    )

    total_population = sum(item.elderly_population for item in communities)
    total_daily_demand = sum(community_total_daily_demand(item) for item in communities)
    geographic_population = sum(item.geographic_population_covered for item in allocations)
    served_population = sum(item.served_population_covered for item in allocations)
    served_demand = sum(item.raw_served_demand_daily for item in allocations)
    effective_person_times = sum(item.effective_person_times_daily for item in allocations)
    served_allocations = [item for item in allocations if item.actually_served]
    average_service_satisfaction = effective_person_times / served_demand if served_demand > 1e-12 else 0.0
    minimum_service_satisfaction = min(
        (item.service_satisfaction for item in served_allocations),
        default=0.0,
    )
    average_service_access_performance = (
        effective_person_times / total_daily_demand
        if total_daily_demand > 1e-12
        else 0.0
    )
    minimum_service_access_performance = min(
        (item.service_access_performance for item in allocations),
        default=0.0,
    )
    weighted_served_population_coverage = compute_weighted_served_population_coverage(allocations)
    capacity_safety_rate = (
        sum(1 for item in station_metrics if item.utilization <= 0.85 + 1e-12) / len(station_metrics)
        if station_metrics
        else 0.0
    )
    utilizations = [item.utilization for item in station_metrics]
    max_station_utilization = max(utilizations) if utilizations else 0.0
    fully_safe = int(max_station_utilization <= 0.85 + 1e-12)
    utilization_variance = (
        sum((value - sum(utilizations) / len(utilizations)) ** 2 for value in utilizations) / len(utilizations)
        if utilizations
        else 0.0
    )
    annual_net_profit_before_subsidy = sum(item.annual_net_profit_before_subsidy for item in station_metrics)
    annual_net_profit_after_policy_subsidy = sum(
        item.annual_net_profit_after_policy_subsidy for item in station_metrics
    )
    annual_revenue = sum(item.annual_revenue for item in station_metrics)
    annual_subsidy = sum(item.annual_subsidy for item in station_metrics)
    annual_direct_cost = sum(item.annual_direct_cost for item in station_metrics)
    annual_fixed_cost = sum(item.annual_fixed_cost for item in station_metrics)
    annual_depreciation = sum(item.annual_depreciation for item in station_metrics)
    annual_total_cost = sum(item.annual_total_cost for item in station_metrics)
    annual_net_profit = sum(item.annual_net_profit for item in station_metrics)
    profit_rate = annual_net_profit / annual_total_cost if annual_total_cost > 1e-12 else -1.0
    profit_compliant = scheme_profit_compliance(station_metrics)
    return SchemeEvaluation(
        scheme_code=scheme_code,
        stations=stations,
        allocations=allocations,
        station_metrics=station_metrics,
        geographic_population_coverage=geographic_population / total_population if total_population > 0 else 0.0,
        served_population_coverage=served_population / total_population if total_population > 0 else 0.0,
        served_demand_coverage=served_demand / total_daily_demand if total_daily_demand > 0 else 0.0,
        average_service_satisfaction=average_service_satisfaction,
        minimum_service_satisfaction=minimum_service_satisfaction,
        total_raw_served_demand_daily=served_demand,
        total_effective_person_times_daily=effective_person_times,
        capacity_safety_rate=capacity_safety_rate,
        max_station_utilization=max_station_utilization,
        fully_safe=fully_safe,
        utilization_variance=utilization_variance,
        annual_net_profit_before_subsidy=annual_net_profit_before_subsidy,
        annual_net_profit_after_policy_subsidy=annual_net_profit_after_policy_subsidy,
        weighted_served_population_coverage=weighted_served_population_coverage,
        average_service_access_performance=average_service_access_performance,
        minimum_service_access_performance=minimum_service_access_performance,
        total_adjusted_demand_daily=total_daily_demand,
        annual_revenue=annual_revenue,
        annual_subsidy=annual_subsidy,
        annual_direct_cost=annual_direct_cost,
        annual_fixed_cost=annual_fixed_cost,
        annual_depreciation=annual_depreciation,
        annual_total_cost=annual_total_cost,
        annual_net_profit=annual_net_profit,
        profit_rate=profit_rate,
        profit_compliant=profit_compliant,
    )


def allocate_with_response_scores(
    stations: List[CandidateStation],
    communities: List[CommunityDemand],
    distance_matrix: Dict[str, Dict[str, float]],
    distance_rules: List[Tuple[float, float]],
    response_rules: List[Tuple[float, float]],
    response_by_station: Dict[str, float],
    service_costs: Dict[str, Dict[str, float]],
) -> Tuple[List[CommunityAllocation], List[StationMetrics], Dict[str, float]]:
    station_map = {station.community: station for station in stations}
    remaining_capacity = {station.community: station.daily_capacity for station in stations}
    primary_monthly_by_station = {
        station.community: {service: 0.0 for service in SERVICE_ORDER}
        for station in stations
    }
    overflow_monthly_by_station = {
        station.community: {service: 0.0 for service in SERVICE_ORDER}
        for station in stations
    }
    effective_monthly_by_station = {
        station.community: {service: 0.0 for service in SERVICE_ORDER}
        for station in stations
    }
    raw_monthly_by_station = {
        station.community: {service: 0.0 for service in SERVICE_ORDER}
        for station in stations
    }

    allocations: List[CommunityAllocation] = []
    ordered_communities = sorted(
        communities,
        key=lambda item: (-community_total_daily_demand(item), -item.elderly_population, item.community),
    )

    for item in ordered_communities:
        monthly_demand = item.adjusted_monthly_demand
        daily_demand = {service: monthly_demand[service] / DAYS_PER_MONTH for service in SERVICE_ORDER}
        total_daily = sum(daily_demand.values())
        emergency_daily = daily_demand["紧急救助"]

        reachable = rank_reachable_stations(
            community=item.community,
            stations=stations,
            distance_matrix=distance_matrix,
            distance_rules=distance_rules,
            response_by_station=response_by_station,
        )
        if not reachable:
            allocations.append(
                CommunityAllocation(
                    community=item.community,
                    primary_station=None,
                    overflow_station=None,
                    geographic_reachable=0,
                    actually_served=0,
                    geographic_population_covered=0.0,
                    served_population_covered=0.0,
                    raw_served_demand_daily=0.0,
                    effective_person_times_daily=0.0,
                    primary_load=0.0,
                    overflow_load=0.0,
                    unmet_load=community_total_daily_demand(item),
                    geographic_satisfaction=0.0,
                    response_satisfaction=0.0,
                    price_satisfaction=0.0,
                    service_satisfaction=0.0,
                    adjusted_demand_daily=community_total_daily_demand(item),
                    demand_service_ratio=0.0,
                    service_access_performance=0.0,
                    elderly_population=item.elderly_population,
                )
            )
            continue

        primary_name = choose_primary_station(
            reachable=reachable,
            remaining_capacity=remaining_capacity,
            total_daily_demand=total_daily,
            emergency_daily_demand=emergency_daily,
        )
        primary_record = next(item for item in reachable if item[0] == primary_name)
        _, primary_distance, primary_distance_sat, base_primary_score = primary_record
        overflow_name = choose_overflow_station(
            reachable=reachable,
            primary_name=primary_name,
            remaining_capacity=remaining_capacity,
        )

        primary_assigned_daily = 0.0
        overflow_assigned_daily = 0.0
        unmet_daily = 0.0

        remaining_primary = remaining_capacity[primary_name]
        emergency_primary_daily = min(emergency_daily, remaining_primary)
        remaining_primary -= emergency_primary_daily
        primary_assigned_daily += emergency_primary_daily
        unmet_daily += emergency_daily - emergency_primary_daily
        primary_monthly_by_station[primary_name]["紧急救助"] += emergency_primary_daily * DAYS_PER_MONTH

        movable_total_daily = sum(daily_demand[service] for service in MOVABLE_SERVICES)
        movable_primary_ratio = min(1.0, remaining_primary / movable_total_daily) if movable_total_daily > 0 else 0.0
        movable_primary_daily = movable_total_daily * movable_primary_ratio
        remaining_primary -= movable_primary_daily
        primary_assigned_daily += movable_primary_daily

        movable_overflow_needed_daily = movable_total_daily - movable_primary_daily
        movable_overflow_ratio = 0.0
        if overflow_name is not None and movable_overflow_needed_daily > 0:
            remaining_overflow = remaining_capacity[overflow_name]
            movable_overflow_ratio = min(1.0, remaining_overflow / movable_overflow_needed_daily)
            movable_overflow_daily = movable_overflow_needed_daily * movable_overflow_ratio
            remaining_capacity[overflow_name] = remaining_overflow - movable_overflow_daily
            overflow_assigned_daily += movable_overflow_daily
            unmet_daily += movable_overflow_needed_daily - movable_overflow_daily
        else:
            unmet_daily += movable_overflow_needed_daily

        remaining_capacity[primary_name] = remaining_primary

        for service in MOVABLE_SERVICES:
            service_daily = daily_demand[service]
            primary_service_daily = service_daily * movable_primary_ratio
            primary_monthly_by_station[primary_name][service] += primary_service_daily * DAYS_PER_MONTH

            leftover_daily = service_daily - primary_service_daily
            overflow_service_daily = leftover_daily * movable_overflow_ratio
            if overflow_name is not None:
                overflow_monthly_by_station[overflow_name][service] += overflow_service_daily * DAYS_PER_MONTH

        response_score = response_by_station[primary_name]
        raw_served_daily = primary_assigned_daily + overflow_assigned_daily
        actually_served = int(raw_served_daily > 1e-12)
        primary_service_satisfaction = clamp_service_satisfaction(base_primary_score)
        overflow_service_satisfaction = clamp_service_satisfaction(base_primary_score - OVERFLOW_PENALTY)
        service_satisfaction = 0.0
        if actually_served:
            service_satisfaction = (
                primary_assigned_daily * primary_service_satisfaction
                + overflow_assigned_daily * overflow_service_satisfaction
            ) / raw_served_daily
        service_metrics = compute_service_metrics(
            raw_served_demand_daily=raw_served_daily,
            adjusted_demand_daily=total_daily,
            service_satisfaction=service_satisfaction,
        )

        primary_increment = {
            service: daily_demand[service] * DAYS_PER_MONTH * (
                movable_primary_ratio if service in MOVABLE_SERVICES else emergency_primary_daily / emergency_daily if service == "紧急救助" and emergency_daily > 0 else 0.0
            )
            for service in SERVICE_ORDER
        }
        for service, value in primary_increment.items():
            raw_monthly_by_station[primary_name][service] += value
            effective_monthly_by_station[primary_name][service] += value * primary_service_satisfaction
        if overflow_name is not None:
            overflow_increment = {
                service: (daily_demand[service] - daily_demand[service] * movable_primary_ratio) * DAYS_PER_MONTH * movable_overflow_ratio
                if service in MOVABLE_SERVICES
                else 0.0
                for service in SERVICE_ORDER
            }
            for service, value in overflow_increment.items():
                raw_monthly_by_station[overflow_name][service] += value
                effective_monthly_by_station[overflow_name][service] += value * overflow_service_satisfaction

        allocations.append(
            CommunityAllocation(
                community=item.community,
                primary_station=primary_name,
                overflow_station=overflow_name if overflow_assigned_daily > 0 else None,
                geographic_reachable=1,
                actually_served=actually_served,
                geographic_population_covered=item.elderly_population,
                served_population_covered=item.elderly_population if actually_served else 0.0,
                raw_served_demand_daily=raw_served_daily,
                effective_person_times_daily=service_metrics["effective_person_times_daily"],
                primary_load=primary_assigned_daily,
                overflow_load=overflow_assigned_daily,
                unmet_load=unmet_daily,
                geographic_satisfaction=primary_distance_sat,
                response_satisfaction=response_score,
                price_satisfaction=BASE_PRICE_SATISFACTION,
                service_satisfaction=service_satisfaction,
                adjusted_demand_daily=total_daily,
                demand_service_ratio=service_metrics["demand_service_ratio"],
                service_access_performance=service_metrics["service_access_performance"],
                elderly_population=item.elderly_population,
            )
        )

    station_metrics: List[StationMetrics] = []
    next_response: Dict[str, float] = {}
    for station in stations:
        primary_load = sum(primary_monthly_by_station[station.community].values()) / DAYS_PER_MONTH
        overflow_load = sum(overflow_monthly_by_station[station.community].values()) / DAYS_PER_MONTH
        total_load = primary_load + overflow_load
        utilization = total_load / station.daily_capacity if station.daily_capacity > 0 else 0.0
        next_response[station.community] = response_satisfaction(utilization, response_rules)

        raw_daily_by_service = {
            service: raw_monthly_by_station[station.community][service] / DAYS_PER_MONTH
            for service in SERVICE_ORDER
        }
        effective_daily_by_service = {
            service: effective_monthly_by_station[station.community][service] / DAYS_PER_MONTH
            for service in SERVICE_ORDER
        }
        financials = compute_annual_financial_metrics(
            scale=station.scale,
            build_cost_wan=station.build_cost_wan,
            daily_fixed_cost=station.daily_fixed_cost,
            raw_daily_by_service=raw_daily_by_service,
            effective_daily_by_service=effective_daily_by_service,
            service_costs=service_costs,
        )
        station_metrics.append(
            StationMetrics(
                community=station.community,
                scale=station.scale,
                daily_capacity=station.daily_capacity,
                assigned_primary_load=primary_load,
                assigned_overflow_load=overflow_load,
                total_load=total_load,
                utilization=utilization,
                annual_service_revenue=financials["annual_revenue"],
                annual_direct_cost=financials["annual_direct_cost"],
                annual_fixed_cost=financials["annual_fixed_cost"],
                annual_depreciation=financials["annual_depreciation"],
                annual_government_subsidy_baseline=financials["annual_subsidy"],
                annual_net_profit_before_subsidy=financials["annual_net_profit_before_subsidy"],
                annual_net_profit_after_policy_subsidy=financials["annual_net_profit"],
                annual_revenue=financials["annual_revenue"],
                annual_subsidy=financials["annual_subsidy"],
                annual_total_cost=financials["annual_total_cost"],
                annual_net_profit=financials["annual_net_profit"],
                profit_rate=financials["profit_rate"],
                profit_compliant=financials["profit_compliant"],
            )
        )

    allocations.sort(key=lambda item: item.community)
    station_metrics.sort(key=lambda item: item.community)
    return allocations, station_metrics, next_response


def choose_primary_station(
    reachable: List[Tuple[str, float, float, float]],
    remaining_capacity: Dict[str, float],
    total_daily_demand: float,
    emergency_daily_demand: float,
) -> str:
    del remaining_capacity, total_daily_demand, emergency_daily_demand
    return reachable[0][0]


def choose_overflow_station(
    reachable: List[Tuple[str, float, float, float]],
    primary_name: str,
    remaining_capacity: Dict[str, float],
) -> str | None:
    candidates = [item for item in reachable if item[0] != primary_name and remaining_capacity[item[0]] > 1e-12]
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: (-item[3], item[1], item[0]))[0][0]


def rank_reachable_stations(
    community: str,
    stations: List[CandidateStation],
    distance_matrix: Dict[str, Dict[str, float]],
    distance_rules: List[Tuple[float, float]],
    response_by_station: Dict[str, float],
) -> List[Tuple[str, float, float, float]]:
    result: List[Tuple[str, float, float, float]] = []
    for station in stations:
        distance = distance_matrix[community][station.community]
        distance_score = distance_satisfaction(distance, distance_rules)
        if distance_score <= 0:
            continue
        score = (
            SATISFACTION_WEIGHTS["distance"] * distance_score
            + SATISFACTION_WEIGHTS["response"] * response_by_station[station.community]
            + SATISFACTION_WEIGHTS["price"] * BASE_PRICE_SATISFACTION
        )
        result.append((station.community, distance, distance_score, score))
    return sorted(result, key=lambda item: (-item[3], item[1], item[0]))


def evaluation_key(item: SchemeEvaluation) -> Tuple[float, float, float, float, float]:
    return (
        item.served_population_coverage,
        item.served_demand_coverage,
        item.average_service_satisfaction,
        item.capacity_safety_rate,
        item.minimum_service_satisfaction,
    )


def tie_break_key(item: SchemeEvaluation) -> Tuple[float, float]:
    return (
        item.utilization_variance,
        item.annual_net_profit_after_policy_subsidy,
    )


def sort_scheme_evaluations(evaluations: List[SchemeEvaluation]) -> List[SchemeEvaluation]:
    return sorted(
        evaluations,
        key=lambda item: (
            -item.served_population_coverage,
            -item.served_demand_coverage,
            -item.average_service_satisfaction,
            -item.capacity_safety_rate,
            -item.minimum_service_satisfaction,
            item.utilization_variance,
            -item.annual_net_profit_after_policy_subsidy,
        ),
    )


def sort_scheme_evaluations_safe(evaluations: List[SchemeEvaluation]) -> List[SchemeEvaluation]:
    return sorted(
        evaluations,
        key=lambda item: (
            -item.served_population_coverage,
            -item.capacity_safety_rate,
            -item.minimum_service_satisfaction,
            -item.served_demand_coverage,
            -item.average_service_satisfaction,
            item.utilization_variance,
            -item.annual_net_profit_after_policy_subsidy,
        ),
    )


def select_safe_scheme(
    evaluations: List[SchemeEvaluation],
    capacity_safety_threshold: float = SAFE_CAPACITY_THRESHOLD,
) -> Tuple[SchemeEvaluation, float]:
    filtered = [
        item for item in evaluations if item.capacity_safety_rate >= capacity_safety_threshold - 1e-12
    ]
    if filtered:
        return sort_scheme_evaluations_safe(filtered)[0], capacity_safety_threshold

    best_available_threshold = max(item.capacity_safety_rate for item in evaluations)
    fallback = [
        item for item in evaluations if abs(item.capacity_safety_rate - best_available_threshold) <= 1e-12
    ]
    return sort_scheme_evaluations_safe(fallback)[0], best_available_threshold
