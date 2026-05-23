from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product
from typing import Dict, List
from scipy.optimize import linprog

from common import (
    DAYS_PER_MONTH,
    NON_EMERGENCY_SERVICES,
    OUTPUT_DIR,
    RQ3Inputs,
    SERVICE_ORDER,
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
    load_rq3_inputs,
    population_by_community,
    recommended_price_candidates,
    stations_by_community,
    write_csv,
)


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
MAX_RESCUE_CANDIDATES = 480


@dataclass(frozen=True)
class IterationRecord:
    iteration: int
    max_satisfaction_delta: float
    average_service_satisfaction: float
    feasible_station_count: int
    total_subsidy: float
    damping_used: int = 0


@dataclass(frozen=True)
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
    fair_satisfaction_compliant: int
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
    weighted_served_population_coverage: float = 0.0
    served_demand_coverage: float = 0.0
    damping_used: int = 0


@dataclass(frozen=True)
class CommunityChoice:
    community: str
    primary_station: str
    backup_station: str | None
    utility_primary: float
    utility_backup: float
    demand_by_service: Dict[str, float]
    price_satisfaction_primary: float


@dataclass(frozen=True)
class RescueCandidate:
    station_prices: Dict[str, Dict[str, float]]
    warm_start_satisfaction: Dict[str, float]


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
        -item.fair_satisfaction_compliant,
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


def compute_price_satisfaction(base_price: float, actual_price: float) -> float:
    if base_price <= 0:
        return 1.0
    premium_ratio = actual_price / base_price - 1.0
    return max(0.6, 1.0 - 2.0 * premium_ratio)


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


def service_satisfaction_from_effective_ratio(effective_ratio: float) -> float:
    if effective_ratio <= 1e-12:
        return 0.0
    return min(1.0, max(0.6, effective_ratio))


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
        and item.minimum_service_access_performance >= min_service_access_threshold - 1e-9
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
) -> Dict[str, float]:
    result = {service: 0.0 for service in SERVICE_ORDER}
    community_details = detail_map[community]
    for care_level in CARE_LEVEL_ORDER:
        rows_by_service = community_details[care_level]
        budget_limit = rows_by_service["助餐"].budget_limit
        theoretical_fee = sum(
            rows_by_service[service].theoretical_per_person * station_price_vector[service]
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

    variable_specs: List[tuple[int, str, str]] = []
    objective: List[float] = []
    bounds: List[tuple[float, float]] = []

    for choice_idx, choice in enumerate(choices):
        for service in SERVICE_ORDER:
            demand = choice.demand_by_service.get(service, 0.0)
            variable_specs.append((choice_idx, "primary", service))
            objective.append(-choice.utility_primary)
            bounds.append((0.0, demand))
            if service in NON_EMERGENCY_SERVICES and choice.backup_station is not None:
                variable_specs.append((choice_idx, "backup", service))
                objective.append(-(choice.utility_backup - OVERFLOW_UTILITY_PENALTY))
                bounds.append((0.0, demand))

    a_ub: List[List[float]] = []
    b_ub: List[float] = []

    for choice_idx, choice in enumerate(choices):
        for service in SERVICE_ORDER:
            row = [0.0] * len(variable_specs)
            for var_idx, (var_choice_idx, leg, var_service) in enumerate(variable_specs):
                if var_choice_idx == choice_idx and var_service == service:
                    row[var_idx] = 1.0
            a_ub.append(row)
            b_ub.append(choice.demand_by_service.get(service, 0.0))

    for station_name in station_names:
        row = [0.0] * len(variable_specs)
        for var_idx, (choice_idx, leg, _service) in enumerate(variable_specs):
            choice = choices[choice_idx]
            served_station = choice.primary_station if leg == "primary" else choice.backup_station
            if served_station == station_name:
                row[var_idx] = 1.0
        a_ub.append(row)
        b_ub.append(station_capacities[station_name])

    result = linprog(
        c=objective,
        A_ub=a_ub if a_ub else None,
        b_ub=b_ub if b_ub else None,
        bounds=bounds,
        method="highs",
    )
    assert result.success, f"Collaboration LP failed: {result.message}"

    per_choice_service: Dict[tuple[int, str], Dict[str, float]] = {}
    for value, (choice_idx, leg, service) in zip(result.x, variable_specs):
        per_choice_service.setdefault((choice_idx, leg), {}).setdefault(service, 0.0)
        per_choice_service[(choice_idx, leg)][service] += float(value)

    for choice_idx, choice in enumerate(choices):
        primary_load = sum(per_choice_service.get((choice_idx, "primary"), {}).values())
        overflow_load = sum(per_choice_service.get((choice_idx, "backup"), {}).values())
        total_demand = sum(choice.demand_by_service.values())
        unmet = total_demand - primary_load - overflow_load

        primary_effective = primary_load * choice.utility_primary
        backup_effective = overflow_load * max(choice.utility_backup - OVERFLOW_UTILITY_PENALTY, 0.0)
        effective_total = primary_effective + backup_effective
        served_ratio = (primary_load + overflow_load) / total_demand if total_demand > 1e-12 else 0.0
        effective_ratio = effective_total / total_demand if total_demand > 1e-12 else 0.0
        service_satisfaction = (
            service_satisfaction_from_effective_ratio(effective_total / max(primary_load + overflow_load, 1e-12))
            if primary_load + overflow_load > 1e-12
            else 0.0
        )
        access_performance = service_access_performance(effective_total, total_demand)

        for service, amount in per_choice_service.get((choice_idx, "primary"), {}).items():
            station_raw[choice.primary_station][service] += amount
            station_effective[choice.primary_station][service] += amount * choice.utility_primary
        if choice.backup_station is not None:
            for service, amount in per_choice_service.get((choice_idx, "backup"), {}).items():
                station_raw[choice.backup_station][service] += amount
                station_effective[choice.backup_station][service] += amount * max(choice.utility_backup - OVERFLOW_UTILITY_PENALTY, 0.0)

        community_rows.append(
            {
                "community": choice.community,
                "primary_station": choice.primary_station,
                "overflow_station": choice.backup_station or "",
                "primary_load_daily": primary_load,
                "overflow_load_daily": overflow_load,
                "unmet_load_daily": unmet,
                "raw_served_demand_daily": primary_load + overflow_load,
                "effective_person_times_daily": effective_total,
                "adjusted_demand_daily": total_demand,
                "demand_service_ratio": min(1.0, served_ratio),
                "service_satisfaction": service_satisfaction,
                "service_access_performance": access_performance,
                "served": int(primary_load + overflow_load > 1e-9),
                "price_satisfaction": choice.price_satisfaction_primary,
            }
        )

    return community_rows, station_raw, station_effective


def build_community_choices(
    inputs: RQ3Inputs,
    station_prices: Dict[str, Dict[str, float]],
    response_by_station: Dict[str, float],
) -> List[CommunityChoice]:
    distance_matrix = load_distance_matrix()
    satisfaction_rules = load_satisfaction_rules()
    detail_map = adjusted_demand_detail_map(inputs.adjusted_demand_detail)
    station_names = [station.station_community for station in inputs.q2_stations]
    base_prices = base_price_by_service()

    choices: List[CommunityChoice] = []
    for community in sorted(detail_map):
        utility_by_station: Dict[str, float] = {}
        demand_by_station: Dict[str, Dict[str, float]] = {}
        price_satisfaction_by_station: Dict[str, float] = {}
        for station_name in station_names:
            distance = distance_matrix[community][station_name]
            s1 = distance_satisfaction(distance, satisfaction_rules["distance"])
            if s1 <= 0:
                continue
            demand_by_service = compute_price_adjusted_monthly_demand_for_station(
                community=community,
                station_price_vector=station_prices[station_name],
                detail_map=detail_map,
            )
            s3 = compute_weighted_price_satisfaction_for_community(
                demand_by_service=demand_by_service,
                station_price_vector=station_prices[station_name],
                base_prices=base_prices,
            )
            demand_by_station[station_name] = demand_by_service
            price_satisfaction_by_station[station_name] = s3
            utility_by_station[station_name] = (
                SATISFACTION_WEIGHTS["distance"] * s1
                + SATISFACTION_WEIGHTS["response"] * response_by_station[station_name]
                + SATISFACTION_WEIGHTS["price"] * s3
            )

        primary, backup = select_primary_and_backup(utility_by_station)
        if primary is None:
            continue
        choices.append(
            CommunityChoice(
                community=community,
                primary_station=primary,
                backup_station=backup,
                utility_primary=utility_by_station[primary],
                utility_backup=utility_by_station[backup] if backup is not None else 0.0,
                demand_by_service={
                    service: demand_by_station[primary][service] / DAYS_PER_MONTH
                    for service in SERVICE_ORDER
                },
                price_satisfaction_primary=price_satisfaction_by_station[primary],
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
) -> PriceEvaluation:
    populations = population_by_community(inputs.year5_population)
    stations = stations_by_community(inputs.q2_stations)
    direct_costs = direct_cost_by_service()
    satisfaction_rules = load_satisfaction_rules()
    low_income_set = low_income_communities()
    baseline_adjusted_summary = adjusted_demand_summary_map(inputs.adjusted_demand_summary)

    old_satisfaction = initial_satisfaction or initial_service_satisfaction_by_community(inputs.q2_allocations)
    satisfaction_history: List[Dict[str, float]] = [old_satisfaction.copy()]
    iteration_trace: List[IterationRecord] = []
    station_financials: List[Dict[str, float]] = []
    community_results: List[Dict[str, float]] = []
    final_station_net_profits: Dict[str, float] = {}
    final_station_total_costs: Dict[str, float] = {}
    damping_used = 0

    for iteration in range(1, max_iterations + 1):
        response_by_station = {}
        for station_name, station in stations.items():
            if iteration == 1:
                utilization = station.utilization
            else:
                prev_raw = sum(station_raw_demand[station_name].values())
                utilization = prev_raw / station.daily_capacity if station.daily_capacity > 0 else 1.0
            response_by_station[station_name] = response_satisfaction_from_utilization(
                utilization,
                satisfaction_rules["response"],
            )

        choices = build_community_choices(
            inputs=inputs,
            station_prices=station_prices,
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
        if detect_two_cycle_oscillation(satisfaction_history + [candidate_satisfaction]):
            new_satisfaction = apply_damping(
                previous=old_satisfaction,
                candidate=candidate_satisfaction,
                damping_lambda=damping_lambda,
            )
            damping_used = 1
        else:
            new_satisfaction = candidate_satisfaction

        community_choice_map = {choice.community: choice for choice in choices}
        for row in community_results:
            if row["served"] == 0:
                row["price_satisfaction"] = 0.0
                continue
            row["price_satisfaction"] = community_choice_map[row["community"]].price_satisfaction_primary

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
        total_effective_current = sum(row["effective_person_times_daily"] for row in community_results)
        total_raw_current = sum(row["raw_served_demand_daily"] for row in community_results)
        average_service_satisfaction = (
            total_effective_current / total_raw_current
            if total_raw_current > 1e-12
            else 0.0
        )
        iteration_trace.append(
            IterationRecord(
                iteration=iteration,
                max_satisfaction_delta=max_delta,
                average_service_satisfaction=average_service_satisfaction,
                feasible_station_count=feasible_station_count,
                total_subsidy=total_subsidy,
                damping_used=damping_used,
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
        total_effective_person_times / total_raw_served_demand_daily
        if total_raw_served_demand_daily > 1e-12
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
        populations[row["community"]].elderly_total
        for row in low_income_rows
        if row["served"] == 1
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
    fair_satisfaction_compliant = int(
        minimum_service_access_performance >= DEFAULT_MIN_SERVICE_ACCESS_THRESHOLD - 1e-9
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
        fair_satisfaction_compliant=fair_satisfaction_compliant,
        low_income_service_satisfaction=low_income_service_satisfaction,
        low_income_served_coverage=low_income_served_coverage,
        weighted_served_population_coverage=weighted_served_population_coverage,
        served_demand_coverage=served_demand_coverage,
        damping_used=damping_used,
        iteration_trace=iteration_trace,
        station_financials=station_financials,
        community_results=community_results,
        accessibility_groups=accessibility_groups,
    )


def sort_price_evaluations(evaluations: List[PriceEvaluation]) -> List[PriceEvaluation]:
    return sorted(
        evaluations,
        key=lambda item: (
            item.profit_compliant,
            item.feasible_station_count,
            item.fair_satisfaction_compliant,
            item.vulnerable_service_satisfaction,
            item.average_service_satisfaction,
            -item.annual_government_subsidy,
        ),
        reverse=True,
    )


def sort_financial_compliant_evaluations(evaluations: List[PriceEvaluation]) -> List[PriceEvaluation]:
    return sorted(
        evaluations,
        key=lambda item: (
            item.profit_compliant,
            item.feasible_station_count,
            item.fair_satisfaction_compliant,
            item.vulnerable_service_satisfaction,
            item.average_service_satisfaction,
            item.minimum_service_satisfaction,
            -item.annual_government_subsidy,
        ),
        reverse=True,
    )


def sort_fairness_priority_evaluations(evaluations: List[PriceEvaluation]) -> List[PriceEvaluation]:
    return sorted(
        evaluations,
        key=lambda item: (
            item.fair_satisfaction_compliant,
            item.minimum_service_satisfaction,
            item.vulnerable_service_satisfaction,
            item.average_service_satisfaction,
            item.low_income_service_satisfaction,
            item.profit_compliant,
            item.feasible_station_count,
            -item.annual_government_subsidy,
        ),
        reverse=True,
    )


def select_financial_best(evaluations: List[PriceEvaluation]) -> PriceEvaluation:
    return sort_financial_compliant_evaluations(evaluations)[0]


def select_fairness_best(evaluations: List[PriceEvaluation]) -> PriceEvaluation:
    return sort_fairness_priority_evaluations(evaluations)[0]


def evaluation_summary_row(item: PriceEvaluation) -> Dict[str, object]:
    station_labels = []
    for station_name in sorted(item.station_prices):
        multipliers = [
            item.station_prices[station_name][service] / base_price_by_service()[service]
            for service in NON_EMERGENCY_SERVICES
            if base_price_by_service()[service] > 0
        ]
        alpha = multipliers[0] if multipliers else 1.0
        station_labels.append(f"{station_name}:alpha={alpha:.1f}")
    return {
        "price_scheme_detail": ";".join(station_labels),
        "pricing_model": "station_level_uniform_premium",
        "pricing_formula": "p_{j,r}=alpha_j*p_r^0,r=1,...,5; p_{j,6}=0",
        "iteration_count": item.iteration_count,
        "iterations": item.iteration_count,
        "converged": item.converged,
        "damping_used": item.damping_used,
        "profit_compliant": item.profit_compliant,
        "fair_satisfaction_compliant": item.fair_satisfaction_compliant,
        "feasible_station_count": item.feasible_station_count,
        "average_service_satisfaction": round(item.average_service_satisfaction, 6),
        "minimum_service_satisfaction": round(item.minimum_service_satisfaction, 6),
        "average_service_access_performance": round(item.average_service_access_performance, 6),
        "minimum_service_access_performance": round(item.minimum_service_access_performance, 6),
        "vulnerable_service_satisfaction": round(item.vulnerable_service_satisfaction, 6),
        "low_income_service_satisfaction": round(item.low_income_service_satisfaction, 6),
        "low_income_served_coverage": round(item.low_income_served_coverage, 6),
        "weighted_served_population_coverage": round(item.weighted_served_population_coverage, 6),
        "served_demand_coverage": round(item.served_demand_coverage, 6),
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


def evaluate_candidate_profiles(
    inputs: RQ3Inputs,
    candidate_profiles: List[Dict[str, Dict[str, float]]],
    initial_warm_start: Dict[str, float] | None = None,
) -> List[PriceEvaluation]:
    evaluations: List[PriceEvaluation] = []
    warm_start_satisfaction = initial_warm_start
    for profile in candidate_profiles:
        evaluation = evaluate_price_profile(
            inputs,
            profile,
            initial_satisfaction=warm_start_satisfaction,
        )
        evaluations.append(evaluation)
        warm_start_satisfaction = {
            row["community"]: row["service_satisfaction"]
            for row in evaluation.community_results
        }
    return evaluations


def main(max_candidate_profiles: int | None = None) -> None:
    inputs = load_rq3_inputs()
    candidate_profiles = enumerate_station_price_profiles(inputs)
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
                )
            )

    all_evaluations = primary_evaluations + rescue_evaluations
    ranked = sort_price_evaluations(all_evaluations)
    financial_best = select_financial_best(all_evaluations)
    fairness_best = select_fairness_best(all_evaluations)
    joint_feasible = joint_feasible_solution_exists(all_evaluations)

    write_price_evaluation_bundle("3_1_best_price_scheme", financial_best)
    write_price_evaluation_bundle("3_1_financial_best_price_scheme", financial_best)
    write_price_evaluation_bundle("3_1_fairness_best_price_scheme", fairness_best)
    write_csv(
        OUTPUT_DIR / "3_1_top_price_schemes.csv",
        [evaluation_summary_row(item) for item in ranked[:10]],
    )
    write_csv(
        OUTPUT_DIR / "3_1_dual_scheme_comparison.csv",
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
                **scheme_comparison_row("fairness_priority_scheme", fairness_best),
                "summary": (
                    "公平优先方案；优先提高最低服务绩效/平均服务绩效。"
                ),
                "fiscal_gap": round(financial_gap_to_break_even(fairness_best), 2),
                "joint_feasible_solution_exists": int(joint_feasible),
            },
        ],
    )
    write_csv(
        OUTPUT_DIR / "3_1_scheme_status_summary.csv",
        [
            {
                "financial_sustainable_scheme": "3_1_financial_best_price_scheme",
                "fairness_priority_scheme": "3_1_fairness_best_price_scheme",
                "joint_feasible_solution_exists": int(joint_feasible),
                "summary": (
                    "存在同时满足财务合规、公平可及阈值与收敛要求的方案。"
                    if joint_feasible
                    else "在当前预算、补贴上限和服务需求下，调价无法同时实现财务合规与公平可及，需要追加补贴、扩容或专项公益服务补贴。"
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
        f"avg service access performance={financial_best.average_service_access_performance:.6f}, "
        f"minimum access performance={financial_best.minimum_service_access_performance:.6f}, "
        f"profit compliant={financial_best.profit_compliant}, "
        f"fairness compliant={financial_best.fair_satisfaction_compliant}, "
        f"iterations={financial_best.iteration_count}"
    )
    print(
        "Fairness priority scheme: "
        f"avg service access performance={fairness_best.average_service_access_performance:.6f}, "
        f"minimum access performance={fairness_best.minimum_service_access_performance:.6f}, "
        f"profit compliant={fairness_best.profit_compliant}, "
        f"fairness compliant={fairness_best.fair_satisfaction_compliant}, "
        f"iterations={fairness_best.iteration_count}"
    )
    print(
        "Current Q3 model uses station-level uniform premium candidates, "
        "re-evaluates primary stations by utility, and treats collaboration overflow as platform dispatch from the primary station."
    )
    if not joint_feasible:
        print(
            "No jointly feasible solution found under current budget, subsidy cap, and demand: "
            "additional subsidy, capacity expansion, or dedicated public-service support is required."
        )


if __name__ == "__main__":
    main()
