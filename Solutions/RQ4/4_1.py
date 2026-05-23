from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from common import (
    BASELINE_PARAMETERS,
    CACHE_DIR,
    CACHE_VERSION,
    OUTPUT_DIR,
    RQ1_COMMON,
    RQ2_COMMON,
    RQ2_MAIN,
    RQ3_COMMON,
    RQ3_MAIN,
    ScenarioDefinition,
    build_station_plan_text,
    build_station_scale_map,
    compute_capacity_safety_rate,
    compute_financial_compliance_rate,
    compute_jaccard_location_stability,
    compute_layout_scale_consistency,
    q2_summary_row,
    q3_summary_row,
    read_json,
    robustness_row,
    scenario_definitions,
    scenario_execution_path,
    scenario_parameter_dict,
    scenario_requires_rerun_from_rq1,
    sensitivity_row,
    station_location_set,
    write_csv,
    write_json,
)


_BASELINE_SCHEME_CODES: list[tuple[int, ...]] | None = None


def load_baseline_rq1_inputs():
    return (
        RQ3_COMMON.load_year5_population(),
        RQ3_COMMON.load_adjusted_demand_summary(),
        RQ3_COMMON.load_adjusted_demand_detail(),
    )


def solve_rq1_under_scenario(
    scenario: ScenarioDefinition,
) -> tuple[list[dict[str, float]], list[dict[str, float]], list[dict[str, float]]]:
    communities = RQ1_COMMON.load_community_data()
    transition = RQ1_COMMON.load_transition_probabilities().copy()
    params = scenario_parameter_dict(scenario)

    transition["自理->半失能"] = params["p12"]
    transition["半失能->失能"] = params["p23"]
    projection = RQ1_COMMON.project_elderly_population(
        communities=communities,
        transition=transition,
        growth_rate=params["elderly_growth_rate"],
    )
    year5_population = [row for row in projection if int(row["year"]) == 5]
    service_demand = RQ1_COMMON.load_service_demand()
    service_costs = RQ1_COMMON.load_service_costs()
    adjusted_detail = RQ1_COMMON.affordability_adjusted_demand(
        communities=communities,
        year5_population=year5_population,
        service_demand=service_demand,
        service_costs=service_costs,
    )
    adjusted_summary = RQ1_COMMON.aggregate_adjusted_demand(adjusted_detail)
    return year5_population, adjusted_summary, adjusted_detail


def year5_population_records_to_rows(records) -> list[dict[str, float]]:
    return [
        {
            "community": row.community,
            "year": row.year,
            "self_care": row.self_care,
            "semi_disabled": row.semi_disabled,
            "disabled": row.disabled,
            "elderly_total": row.elderly_total,
            "new_entrants": row.new_entrants,
        }
        for row in records
    ]


def adjusted_summary_records_to_rows(records) -> list[dict[str, float]]:
    return [
        {
            "community": row.community,
            "service": row.service,
            "adjusted_monthly_demand": row.adjusted_monthly_demand,
        }
        for row in records
    ]


def adjusted_detail_records_to_rows(records) -> list[dict[str, float]]:
    return [
        {
            "community": row.community,
            "care_level": row.care_level,
            "service": row.service,
            "monthly_income": row.monthly_income,
            "budget_limit": row.budget_limit,
            "theoretical_per_person": row.theoretical_per_person,
            "adjusted_per_person": row.adjusted_per_person,
            "adjustment_scale": row.adjustment_scale,
            "population": row.population,
            "adjusted_monthly_demand": row.adjusted_monthly_demand,
        }
        for row in records
    ]


def enumerate_cached_scheme_codes(
    community_names: list[str],
    scales,
    budget_limit: float,
    reuse_baseline: bool,
) -> list[tuple[int, ...]]:
    global _BASELINE_SCHEME_CODES
    if reuse_baseline and _BASELINE_SCHEME_CODES is not None and abs(budget_limit - RQ2_COMMON.BUDGET_LIMIT) <= 1e-12:
        return _BASELINE_SCHEME_CODES
    scheme_codes = list(
        RQ2_COMMON.enumerate_feasible_scheme_codes(
            community_names,
            scales,
            budget_limit=budget_limit,
        )
    )
    if abs(budget_limit - RQ2_COMMON.BUDGET_LIMIT) <= 1e-12:
        _BASELINE_SCHEME_CODES = scheme_codes
    return scheme_codes


def solve_rq2_under_scenario(
    scenario: ScenarioDefinition,
    year5_population_rows: list[dict[str, float]],
    adjusted_summary_rows: list[dict[str, float]],
) -> tuple[object, object, int]:
    scales = RQ2_COMMON.load_station_scales()
    distance_matrix = RQ2_COMMON.load_distance_matrix()
    satisfaction_rules = RQ2_COMMON.load_satisfaction_rules()
    service_costs = RQ2_COMMON.load_service_costs()
    params = scenario_parameter_dict(scenario)
    population_map = {row["community"]: float(row["elderly_total"]) for row in year5_population_rows}

    grouped = {}
    for row in adjusted_summary_rows:
        grouped.setdefault(row["community"], {})[row["service"]] = float(row["adjusted_monthly_demand"])
    communities = [
        RQ2_COMMON.CommunityDemand(
            community=community,
            elderly_population=population_map[community],
            adjusted_monthly_demand=demand,
        )
        for community, demand in sorted(grouped.items())
    ]

    fixed_cost_multiplier = params["fixed_cost_multiplier"]
    if abs(fixed_cost_multiplier - 1.0) > 1e-12:
        scales = {
            name: RQ2_COMMON.StationScale(
                name=scale.name,
                build_cost_wan=scale.build_cost_wan,
                daily_fixed_cost=scale.daily_fixed_cost * fixed_cost_multiplier,
                daily_capacity=scale.daily_capacity,
            )
            for name, scale in scales.items()
        }

    community_names = [item.community for item in communities]
    reuse_baseline_codes = scenario.code in {"S0", "S3"}
    scheme_codes = enumerate_cached_scheme_codes(
        community_names=community_names,
        scales=scales,
        budget_limit=params["budget_limit"],
        reuse_baseline=reuse_baseline_codes,
    )

    evaluations = []
    for scheme_code in scheme_codes:
        result = RQ2_COMMON.evaluate_scheme(
            scheme_code=scheme_code,
            communities=communities,
            distance_matrix=distance_matrix,
            scales=scales,
            satisfaction_rules=satisfaction_rules,
            service_costs=service_costs,
            budget_limit=params["budget_limit"],
        )
        if result is not None:
            evaluations.append(result)

    ranked = RQ2_COMMON.sort_scheme_evaluations(evaluations)
    best = ranked[0]
    safe_best, _ = RQ2_COMMON.select_safe_scheme(evaluations)
    best.scenario_budget_limit = params["budget_limit"]
    best.feasible_scheme_count = len(evaluations)
    safe_best.scenario_budget_limit = params["budget_limit"]
    safe_best.feasible_scheme_count = len(evaluations)
    return best, safe_best, len(evaluations)


def build_rq3_inputs(
    scenario: ScenarioDefinition,
    q2_best,
    year5_population_rows: list[dict[str, float]],
    adjusted_summary_rows: list[dict[str, float]],
    adjusted_detail_rows: list[dict[str, float]],
):
    q2_summary_row_data = RQ2_MAIN.evaluation_to_summary_row(q2_best)
    q2_summary = RQ3_COMMON.SchemeSummaryRecord(
        scheme_type="coverage_priority",
        scheme_code=q2_summary_row_data["scheme_code"],
        scheme_detail=q2_summary_row_data["scheme_detail"],
        station_count=q2_summary_row_data["station_count"],
        build_cost_wan=q2_summary_row_data["build_cost_wan"],
        geographic_population_coverage=q2_summary_row_data["geographic_population_coverage"],
        served_population_coverage=q2_summary_row_data["served_population_coverage"],
        weighted_served_population_coverage=q2_summary_row_data["weighted_served_population_coverage"],
        served_demand_coverage=q2_summary_row_data["served_demand_coverage"],
        average_service_satisfaction=q2_summary_row_data["average_service_satisfaction"],
        minimum_service_satisfaction=q2_summary_row_data["minimum_service_satisfaction"],
        average_service_access_performance=q2_summary_row_data["average_service_access_performance"],
        minimum_service_access_performance=q2_summary_row_data["minimum_service_access_performance"],
        total_adjusted_demand_daily=q2_summary_row_data["total_adjusted_demand_daily"],
        total_raw_served_demand_daily=q2_summary_row_data["total_raw_served_demand_daily"],
        total_effective_person_times_daily=q2_summary_row_data["total_effective_person_times_daily"],
        capacity_safety_rate=q2_summary_row_data["capacity_safety_rate"],
        max_station_utilization=q2_summary_row_data["max_station_utilization"],
        fully_safe=q2_summary_row_data["fully_safe"],
        fully_served_community_count=q2_summary_row_data["fully_served_community_count"],
        total_unmet_daily_demand=q2_summary_row_data["total_unmet_daily_demand"],
        utilization_variance=q2_summary_row_data["utilization_variance"],
        annual_revenue=q2_summary_row_data["annual_revenue"],
        annual_subsidy=q2_summary_row_data["annual_subsidy"],
        annual_direct_cost=q2_summary_row_data["annual_direct_cost"],
        annual_fixed_cost=q2_summary_row_data["annual_fixed_cost"],
        annual_depreciation=q2_summary_row_data["annual_depreciation"],
        annual_total_cost=q2_summary_row_data["annual_total_cost"],
        annual_net_profit_before_subsidy=q2_summary_row_data["annual_net_profit_before_subsidy"],
        annual_net_profit_after_policy_subsidy=q2_summary_row_data["annual_net_profit_after_policy_subsidy"],
        annual_net_profit=q2_summary_row_data["annual_net_profit"],
        profit_rate=q2_summary_row_data["profit_rate"],
        profit_compliant=q2_summary_row_data["profit_compliant"],
    )
    q2_stations = [
        RQ3_COMMON.StationRecord(
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
        RQ3_COMMON.AllocationRecord(
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
    year5_population = [
        RQ3_COMMON.Year5PopulationRecord(
            community=row["community"],
            year=int(row["year"]),
            self_care=float(row["self_care"]),
            semi_disabled=float(row["semi_disabled"]),
            disabled=float(row["disabled"]),
            elderly_total=float(row["elderly_total"]),
            new_entrants=float(row["new_entrants"]),
        )
        for row in year5_population_rows
    ]
    adjusted_summary = [
        RQ3_COMMON.AdjustedDemandSummaryRecord(
            community=row["community"],
            service=row["service"],
            adjusted_monthly_demand=float(row["adjusted_monthly_demand"]),
        )
        for row in adjusted_summary_rows
    ]
    adjusted_detail = [
        RQ3_COMMON.AdjustedDemandDetailRecord(
            community=row["community"],
            care_level=row["care_level"],
            service=row["service"],
            monthly_income=float(row["monthly_income"]),
            budget_limit=float(row["budget_limit"]),
            theoretical_per_person=float(row["theoretical_per_person"]),
            adjusted_per_person=float(row["adjusted_per_person"]),
            adjustment_scale=float(row["adjustment_scale"]),
            population=float(row["population"]),
            adjusted_monthly_demand=float(row["adjusted_monthly_demand"]),
        )
        for row in adjusted_detail_rows
    ]
    return RQ3_COMMON.RQ3Inputs(
        metadata={
            "source": "RQ4",
            "scenario": scenario.code,
            "execution_path": scenario_execution_path(scenario),
            "coordination_note": "老人仍选择满意度最高的主服务站。容量不足时，协同站点分流表示由主站或街道平台进行派单协同，不表示老人自主改选其他站点。",
        },
        year5_population=year5_population,
        adjusted_demand_summary=adjusted_summary,
        adjusted_demand_detail=adjusted_detail,
        q2_summary=q2_summary,
        q2_stations=q2_stations,
        q2_allocations=q2_allocations,
    )


def solve_rq3_under_scenario(rq3_inputs) -> tuple[object, object, bool]:
    candidate_profiles = RQ3_MAIN.enumerate_station_price_profiles(rq3_inputs)
    warm_start = {row.community: row.service_satisfaction for row in rq3_inputs.q2_allocations}
    primary_evaluations = RQ3_MAIN.evaluate_candidate_profiles(
        rq3_inputs,
        candidate_profiles,
        initial_warm_start=warm_start,
    )
    ranked_primary = RQ3_MAIN.sort_price_evaluations(primary_evaluations)
    rescue_evaluations = []
    if ranked_primary and ranked_primary[0].profit_compliant == 0:
        rescue_candidates = RQ3_MAIN.generate_rescue_price_profiles(rq3_inputs, ranked_primary)
        for candidate in rescue_candidates:
            rescue_evaluations.append(
                RQ3_MAIN.evaluate_price_profile(
                    rq3_inputs,
                    candidate.station_prices,
                    initial_satisfaction=candidate.warm_start_satisfaction,
                )
            )
    all_evaluations = primary_evaluations + rescue_evaluations
    return (
        RQ3_MAIN.select_financial_best(all_evaluations),
        RQ3_MAIN.select_fairness_best(all_evaluations),
        RQ3_MAIN.joint_feasible_solution_exists(all_evaluations),
    )


def community_results_rows(evaluation) -> list[dict[str, object]]:
    return [
        {
            "community": row["community"],
            "primary_station": row.get("primary_station", ""),
            "overflow_station": row.get("overflow_station", ""),
            "adjusted_demand_daily": round(float(row["adjusted_demand_daily"]), 4),
            "raw_served_demand_daily": round(float(row["raw_served_demand_daily"]), 4),
            "effective_person_times_daily": round(float(row["effective_person_times_daily"]), 4),
            "demand_service_ratio": round(float(row["demand_service_ratio"]), 6),
            "service_satisfaction": round(float(row["service_satisfaction"]), 6),
            "service_access_performance": round(float(row["service_access_performance"]), 6),
            "served": int(row["served"]),
        }
        for row in evaluation.community_results
    ]


def solve_scenario(
    scenario: ScenarioDefinition,
    baseline_year5_rows: list[dict[str, float]],
    baseline_adjusted_summary_rows: list[dict[str, float]],
    baseline_adjusted_detail_rows: list[dict[str, float]],
) -> dict[str, object]:
    if scenario_requires_rerun_from_rq1(scenario):
        year5_rows, adjusted_summary_rows, adjusted_detail_rows = solve_rq1_under_scenario(scenario)
    else:
        year5_rows = [dict(row) for row in baseline_year5_rows]
        adjusted_summary_rows = [dict(row) for row in baseline_adjusted_summary_rows]
        adjusted_detail_rows = [dict(row) for row in baseline_adjusted_detail_rows]

    q2_best, q2_safe, feasible_scheme_count = solve_rq2_under_scenario(
        scenario,
        year5_population_rows=year5_rows,
        adjusted_summary_rows=adjusted_summary_rows,
    )
    rq3_inputs = build_rq3_inputs(
        scenario,
        q2_best=q2_best,
        year5_population_rows=year5_rows,
        adjusted_summary_rows=adjusted_summary_rows,
        adjusted_detail_rows=adjusted_detail_rows,
    )
    financial_best, fairness_best, joint_feasible = solve_rq3_under_scenario(rq3_inputs)
    params = scenario_parameter_dict(scenario)

    q2_best_summary = RQ2_MAIN.evaluation_to_summary_row(q2_best)
    q2_safe_summary = RQ2_MAIN.evaluation_to_summary_row(q2_safe)
    q2_best_station_plan = q2_best_summary["scheme_detail"]
    q2_safe_station_plan = q2_safe_summary["scheme_detail"]
    financial_summary = RQ3_MAIN.evaluation_summary_row(financial_best)
    fairness_summary = RQ3_MAIN.evaluation_summary_row(fairness_best)

    return {
        "cache_version": CACHE_VERSION,
        "scenario": scenario.code,
        "scenario_name": scenario.name,
        "scenario_parameters": params,
        "execution_path": scenario_execution_path(scenario),
        "reran_rq1": int(scenario_requires_rerun_from_rq1(scenario)),
        "feasible_scheme_count": feasible_scheme_count,
        "q2_best_summary": q2_best_summary,
        "q2_safe_summary": q2_safe_summary,
        "q2_best_station_plan": q2_best_station_plan,
        "q2_safe_station_plan": q2_safe_station_plan,
        "q2_best_station_locations": sorted(station_location_set(q2_best)),
        "q2_safe_station_locations": sorted(station_location_set(q2_safe)),
        "q2_best_station_utilizations": [float(item.utilization) for item in q2_best.station_metrics],
        "q2_safe_station_utilizations": [float(item.utilization) for item in q2_safe.station_metrics],
        "financial_best_summary": financial_summary,
        "fairness_best_summary": fairness_summary,
        "financial_best_station_financials": financial_best.station_financials,
        "fairness_best_station_financials": fairness_best.station_financials,
        "financial_best_community_results": community_results_rows(financial_best),
        "fairness_best_community_results": community_results_rows(fairness_best),
        "joint_feasible_solution_exists": bool(joint_feasible),
        "joint_feasible_summary": (
            "存在同时满足财务合规、公平可及阈值与收敛要求的方案。"
            if joint_feasible
            else "在当前预算、补贴上限和服务需求下，调价无法同时实现财务合规与公平可及，需要追加补贴、扩容或专项公益服务补贴。"
        ),
        "coordination_note": "老人仍选择满意度最高的主服务站。容量不足时，协同站点分流表示由主站或街道平台进行派单协同，不表示老人自主改选其他站点。",
    }


def cache_path_for_scenario(code: str) -> Path:
    return CACHE_DIR / f"{code}.json"


def cache_is_current(path: Path) -> bool:
    if not path.exists():
        return False
    try:
        payload = read_json(path)
    except Exception:
        return False
    return payload.get("cache_version") == CACHE_VERSION


def solve_and_cache_scenarios(scenarios: list[ScenarioDefinition]) -> dict[str, dict[str, object]]:
    baseline_year5, baseline_adjusted_summary, baseline_adjusted_detail = load_baseline_rq1_inputs()
    baseline_year5_rows = year5_population_records_to_rows(baseline_year5)
    baseline_adjusted_summary_rows = adjusted_summary_records_to_rows(baseline_adjusted_summary)
    baseline_adjusted_detail_rows = adjusted_detail_records_to_rows(baseline_adjusted_detail)

    result_map: dict[str, dict[str, object]] = {}
    for scenario in scenarios:
        path = cache_path_for_scenario(scenario.code)
        if cache_is_current(path):
            result_map[scenario.code] = read_json(path)
            print(f"Reused cached scenario {scenario.code}.")
            continue
        result = solve_scenario(
            scenario,
            baseline_year5_rows=baseline_year5_rows,
            baseline_adjusted_summary_rows=baseline_adjusted_summary_rows,
            baseline_adjusted_detail_rows=baseline_adjusted_detail_rows,
        )
        write_json(path, result)
        result_map[scenario.code] = result
        print(f"Solved scenario {scenario.code} and wrote cache.")
    return result_map


def build_q2_summary_rows(scenarios: list[ScenarioDefinition], result_map: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    rows = []
    for scenario in scenarios:
        result = result_map[scenario.code]
        rows.append(
            {
                "scenario": scenario.code,
                "budget_limit": result["scenario_parameters"]["budget_limit"],
                "fixed_cost_multiplier": result["scenario_parameters"]["fixed_cost_multiplier"],
                "p12": result["scenario_parameters"]["p12"],
                "p23": result["scenario_parameters"]["p23"],
                "elderly_growth_rate": result["scenario_parameters"]["elderly_growth_rate"],
                "station_plan": result["q2_best_station_plan"],
                "total_construction_cost": result["q2_best_summary"]["build_cost_wan"],
                "geographic_population_coverage": result["q2_best_summary"]["geographic_population_coverage"],
                "served_population_coverage": result["q2_best_summary"]["served_population_coverage"],
                "weighted_served_population_coverage": result["q2_best_summary"]["weighted_served_population_coverage"],
                "served_demand_coverage": result["q2_best_summary"]["served_demand_coverage"],
                "average_service_access_performance": result["q2_best_summary"]["average_service_access_performance"],
                "minimum_service_access_performance": result["q2_best_summary"]["minimum_service_access_performance"],
                "capacity_safety_rate": result["q2_best_summary"]["capacity_safety_rate"],
                "max_station_utilization": result["q2_best_summary"]["max_station_utilization"],
                "fully_safe": result["q2_best_summary"]["fully_safe"],
                "annual_net_profit_before_subsidy": result["q2_best_summary"]["annual_net_profit_before_subsidy"],
                "annual_net_profit_after_policy_subsidy": result["q2_best_summary"]["annual_net_profit_after_policy_subsidy"],
            }
        )
    return rows


def build_q3_summary_rows(scenarios: list[ScenarioDefinition], result_map: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    rows = []
    for scenario in scenarios:
        result = result_map[scenario.code]
        rows.append(
            {
                "scenario": scenario.code,
                "budget_limit": result["scenario_parameters"]["budget_limit"],
                "fixed_cost_multiplier": result["scenario_parameters"]["fixed_cost_multiplier"],
                "p12": result["scenario_parameters"]["p12"],
                "p23": result["scenario_parameters"]["p23"],
                "elderly_growth_rate": result["scenario_parameters"]["elderly_growth_rate"],
                "scheme_type": "financial_sustainable_scheme",
                "station_plan": result["q2_best_station_plan"],
                "average_service_access_performance": result["financial_best_summary"]["average_service_access_performance"],
                "minimum_service_access_performance": result["financial_best_summary"]["minimum_service_access_performance"],
                "annual_government_subsidy": result["financial_best_summary"]["annual_government_subsidy"],
                "annual_net_profit": result["financial_best_summary"]["annual_net_profit"],
                "profit_rate": result["financial_best_summary"]["profit_rate"],
                "profit_compliant": result["financial_best_summary"]["profit_compliant"],
                "converged": result["financial_best_summary"]["converged"],
                "iterations": result["financial_best_summary"]["iterations"],
                "fiscal_gap_if_any": round(RQ3_MAIN.financial_gap_to_break_even_from_summary(result["financial_best_summary"]) if hasattr(RQ3_MAIN, "financial_gap_to_break_even_from_summary") else max(0.0, -float(result["financial_best_summary"]["annual_net_profit"])), 2),
            }
        )
        rows.append(
            {
                "scenario": scenario.code,
                "budget_limit": result["scenario_parameters"]["budget_limit"],
                "fixed_cost_multiplier": result["scenario_parameters"]["fixed_cost_multiplier"],
                "p12": result["scenario_parameters"]["p12"],
                "p23": result["scenario_parameters"]["p23"],
                "elderly_growth_rate": result["scenario_parameters"]["elderly_growth_rate"],
                "scheme_type": "fairness_priority_scheme",
                "station_plan": result["q2_best_station_plan"],
                "average_service_access_performance": result["fairness_best_summary"]["average_service_access_performance"],
                "minimum_service_access_performance": result["fairness_best_summary"]["minimum_service_access_performance"],
                "annual_government_subsidy": result["fairness_best_summary"]["annual_government_subsidy"],
                "annual_net_profit": result["fairness_best_summary"]["annual_net_profit"],
                "profit_rate": result["fairness_best_summary"]["profit_rate"],
                "profit_compliant": result["fairness_best_summary"]["profit_compliant"],
                "converged": result["fairness_best_summary"]["converged"],
                "iterations": result["fairness_best_summary"]["iterations"],
                "fiscal_gap_if_any": round(max(0.0, -float(result["fairness_best_summary"]["annual_net_profit"])), 2),
            }
        )
    return rows


def build_sensitivity_rows(scenarios: list[ScenarioDefinition], result_map: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    baseline = result_map["S0"]
    rows = []
    metric_extractors = {
        "q2_served_demand_coverage": lambda item: float(item["q2_best_summary"]["served_demand_coverage"]),
        "q2_average_service_access_performance": lambda item: float(item["q2_best_summary"]["average_service_access_performance"]),
        "q3_financial_annual_net_profit": lambda item: float(item["financial_best_summary"]["annual_net_profit"]),
        "q3_financial_profit_rate": lambda item: float(item["financial_best_summary"]["profit_rate"]),
        "q3_fairness_minimum_service_access_performance": lambda item: float(item["fairness_best_summary"]["minimum_service_access_performance"]),
    }
    scenario_map = {item.code: item for item in scenarios}
    for code in sorted(result_map):
        if code == "S0":
            continue
        scenario = scenario_map[code]
        result = result_map[code]
        for metric_name, extractor in metric_extractors.items():
            rows.append(
                sensitivity_row(
                    scenario=scenario,
                    metric_name=metric_name,
                    baseline_value=extractor(baseline),
                    scenario_value=extractor(result),
                    baseline_parameters=BASELINE_PARAMETERS,
                )
            )
    return rows


def build_robustness_rows(scenarios: list[ScenarioDefinition], result_map: dict[str, dict[str, object]]) -> list[dict[str, object]]:
    baseline = result_map["S0"]
    baseline_station_plan = baseline["q2_best_station_plan"]
    baseline_q2_metric_map = {
        "geographic_population_coverage": float(baseline["q2_best_summary"]["geographic_population_coverage"]),
        "served_population_coverage": float(baseline["q2_best_summary"]["served_population_coverage"]),
        "weighted_served_population_coverage": float(baseline["q2_best_summary"]["weighted_served_population_coverage"]),
        "served_demand_coverage": float(baseline["q2_best_summary"]["served_demand_coverage"]),
        "average_service_access_performance": float(baseline["q2_best_summary"]["average_service_access_performance"]),
    }
    baseline_q3_financial_performance = float(baseline["financial_best_summary"]["average_service_access_performance"])
    baseline_q3_fairness_performance = float(baseline["fairness_best_summary"]["average_service_access_performance"])

    rows = []
    for scenario in scenarios:
        if scenario.code == "S0":
            continue
        result = result_map[scenario.code]
        rows.append(
            robustness_row(
                scenario=scenario,
                baseline_station_plan=baseline_station_plan,
                scenario_station_plan=result["q2_best_station_plan"],
                baseline_q2_metric_map=baseline_q2_metric_map,
                scenario_q2_metric_map={
                    "geographic_population_coverage": float(result["q2_best_summary"]["geographic_population_coverage"]),
                    "served_population_coverage": float(result["q2_best_summary"]["served_population_coverage"]),
                    "weighted_served_population_coverage": float(result["q2_best_summary"]["weighted_served_population_coverage"]),
                    "served_demand_coverage": float(result["q2_best_summary"]["served_demand_coverage"]),
                    "average_service_access_performance": float(result["q2_best_summary"]["average_service_access_performance"]),
                },
                baseline_q3_financial_performance=baseline_q3_financial_performance,
                scenario_q3_financial_performance=float(result["financial_best_summary"]["average_service_access_performance"]),
                baseline_q3_fairness_performance=baseline_q3_fairness_performance,
                scenario_q3_fairness_performance=float(result["fairness_best_summary"]["average_service_access_performance"]),
                station_profit_flags=[int(row["profit_compliant"]) for row in result["financial_best_station_financials"]],
                station_utilizations=[float(value) for value in result["q2_best_station_utilizations"]],
            )
        )
    return rows


def top_candidate_rows_for_budget(
    budget_limit: float,
    year5_rows: list[dict[str, float]],
    adjusted_summary_rows: list[dict[str, float]],
    fixed_cost_multiplier: float = 1.0,
    top_k: int = 10,
) -> tuple[int, list[dict[str, object]]]:
    scenario = ScenarioDefinition("TMP", "临时诊断", {"budget_limit": budget_limit, "fixed_cost_multiplier": fixed_cost_multiplier})
    scales = RQ2_COMMON.load_station_scales()
    if abs(fixed_cost_multiplier - 1.0) > 1e-12:
        scales = {
            name: RQ2_COMMON.StationScale(
                name=scale.name,
                build_cost_wan=scale.build_cost_wan,
                daily_fixed_cost=scale.daily_fixed_cost * fixed_cost_multiplier,
                daily_capacity=scale.daily_capacity,
            )
            for name, scale in scales.items()
        }
    population_map = {row["community"]: float(row["elderly_total"]) for row in year5_rows}
    grouped = {}
    for row in adjusted_summary_rows:
        grouped.setdefault(row["community"], {})[row["service"]] = float(row["adjusted_monthly_demand"])
    communities = [
        RQ2_COMMON.CommunityDemand(community=community, elderly_population=population_map[community], adjusted_monthly_demand=demand)
        for community, demand in sorted(grouped.items())
    ]
    distance_matrix = RQ2_COMMON.load_distance_matrix()
    satisfaction_rules = RQ2_COMMON.load_satisfaction_rules()
    service_costs = RQ2_COMMON.load_service_costs()
    community_names = [item.community for item in communities]
    scheme_codes = list(RQ2_COMMON.enumerate_feasible_scheme_codes(community_names, scales, budget_limit=budget_limit))
    evaluations = []
    for scheme_code in scheme_codes:
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
    ranked = RQ2_COMMON.sort_scheme_evaluations(evaluations)[:top_k]
    rows = []
    for item in ranked:
        summary = RQ2_MAIN.evaluation_to_summary_row(item)
        rows.append(
            {
                "station_plan": summary["scheme_detail"],
                "total_construction_cost": summary["build_cost_wan"],
                "served_demand_coverage": summary["served_demand_coverage"],
                "average_service_access_performance": summary["average_service_access_performance"],
                "max_station_utilization": summary["max_station_utilization"],
            }
        )
    return len(evaluations), rows


def build_s4_diagnostics(
    result_map: dict[str, dict[str, object]],
    baseline_year5_rows: list[dict[str, float]],
    baseline_adjusted_summary_rows: list[dict[str, float]],
) -> dict[str, object]:
    s0 = result_map["S0"]
    s4 = result_map["S4"]
    used_more_than_120 = float(s4["q2_best_summary"]["build_cost_wan"]) > 120.0 + 1e-12
    diagnostics = {
        "scenario": "S4",
        "station_count": int(s4["q2_best_summary"]["station_count"]),
        "station_plan": s4["q2_best_station_plan"],
        "total_construction_cost": float(s4["q2_best_summary"]["build_cost_wan"]),
        "uses_budget_above_120_and_not_above_140": bool(used_more_than_120 and float(s4["q2_best_summary"]["build_cost_wan"]) <= 140.0 + 1e-12),
        "served_demand_coverage_ge_s0": float(s4["q2_best_summary"]["served_demand_coverage"]) >= float(s0["q2_best_summary"]["served_demand_coverage"]) - 1e-12,
        "average_service_access_performance_ge_s0": float(s4["q2_best_summary"]["average_service_access_performance"]) >= float(s0["q2_best_summary"]["average_service_access_performance"]) - 1e-12,
    }
    if s4["q2_best_station_plan"] == s0["q2_best_station_plan"]:
        s4_count, s4_top10 = top_candidate_rows_for_budget(140.0, baseline_year5_rows, baseline_adjusted_summary_rows)
        s0_count, s0_top10 = top_candidate_rows_for_budget(120.0, baseline_year5_rows, baseline_adjusted_summary_rows)
        diagnostics["s4_feasible_scheme_count"] = s4_count
        diagnostics["s0_feasible_scheme_count"] = s0_count
        diagnostics["top_10_candidates_s4"] = s4_top10
        diagnostics["top_10_candidates_s0"] = s0_top10
        diagnostics["unchanged_reason"] = (
            "预算放宽后，新增预算内方案未在覆盖率、平均服务绩效和安全性排序上超过基准最优方案，因此最优解保持不变。"
        )
    else:
        diagnostics["unchanged_reason"] = ""
    return diagnostics


def write_interpretation_notes(
    scenarios: list[ScenarioDefinition],
    result_map: dict[str, dict[str, object]],
    s4_diagnostics: dict[str, object],
) -> None:
    s0_plan = result_map["S0"]["q2_best_station_plan"]
    layout_changed = [scenario.code for scenario in scenarios if result_map[scenario.code]["q2_best_station_plan"] != s0_plan]
    layout_unchanged = [scenario.code for scenario in scenarios if result_map[scenario.code]["q2_best_station_plan"] == s0_plan]

    lines = [
        "# RQ4 Interpretation Notes",
        "",
        "## 1. 哪些情景改变站点布局",
        "",
        f"- 改变布局的情景：{', '.join(layout_changed) if layout_changed else '无'}。",
        f"- 未改变布局的情景：{', '.join(layout_unchanged)}。",
        "",
        "## 2. 哪些情景主要影响定价和利润",
        "",
        "- `S3` 固定管理成本上升，直接推高年度固定管理成本，主要传导到利润率、财政缺口和调价结果。",
        "- `S4` 建设预算提高，先影响 Q2 站点布局，再通过新的容量与距离格局影响 Q3 定价和财务结果。",
        "- `S1` 和 `S2` 同时改变需求规模或结构，因此会联动影响布局、利用率、价格和补贴。",
        "",
        "## 3. 预算提高后的真实结论",
        "",
        f"- `S4` 最优站点方案为 `{s4_diagnostics['station_plan']}`，总建设成本 `{s4_diagnostics['total_construction_cost']}` 万元。",
        f"- 是否真正使用超过 120 万且不超过 140 万预算：`{str(s4_diagnostics['uses_budget_above_120_and_not_above_140']).lower()}`。",
        "- 若预算提高后覆盖率或平均服务绩效提高，应表述为预算放宽改善了服务配置；只有在新结果仍不改善时，才能解释为边际收益递减。",
        "",
        "## 4. 固定成本上升对价格、利润和满意度的传导",
        "",
        "- 固定管理成本上升不会改变 RQ1 需求，但会抬高 Q2/Q3 的年度固定成本。",
        "- 在 Q3 中，这会增加盈利压力，可能引致更高溢价、利润率下降或公平方案财政缺口扩大，并通过价格满意度影响服务绩效。",
        "",
        "## 5. 老人增长率提高但布局若稳定，应如何解释容量冗余",
        "",
        "- 若 `S1` 下布局未明显变化，可解释为基准方案存在容量冗余，增长后的需求仍主要在现有站点能力范围内消化。",
        "- 这类结论应结合 `max_station_utilization` 和 `capacity_safety_rate` 支撑，而不是仅看站点数量不变。",
        "",
        "## 6. 若转移概率变化主要改变服务结构，应如何解释",
        "",
        "- `S2` 主要改变老人健康状态结构，从而改变不同服务项目的需求组合。",
        "- 若布局变化有限但利润、补贴或价格方案变化明显，可解释为模型对服务结构而非空间分布更敏感。",
        "",
        "## 7. 不能写的结论",
        "",
        "- 不能再直接写“预算提高无效”，除非 `S4` 修复后的真实重算结果仍支持该结论。",
        "- 不能把 Q2 的服务绩效稳定性冒充 Q3 双方案的绩效稳定性。",
        "- 不能把 `financial_sustainable_scheme` 或 `fairness_priority_scheme` 强行描述为唯一最优方案；若 `joint_feasible_solution_exists = false`，必须明确财务合规与公平可及当前不可兼得。",
        "",
        "## 8. 协同分流口径说明",
        "",
        "- 老人仍选择满意度最高的主服务站。容量不足时，协同站点分流表示由主站或街道平台进行派单协同，不表示老人自主改选其他站点。",
    ]
    (OUTPUT_DIR / "4_interpretation_notes.md").write_text("\n".join(lines), encoding="utf-8")


def write_s4_diagnostics_file(diagnostics: dict[str, object]) -> None:
    write_json(OUTPUT_DIR / "4_1_s4_diagnostics.json", diagnostics)


def main() -> None:
    scenarios = scenario_definitions()
    result_map = solve_and_cache_scenarios(scenarios)

    baseline_year5, baseline_adjusted_summary, _baseline_adjusted_detail = load_baseline_rq1_inputs()
    baseline_year5_rows = year5_population_records_to_rows(baseline_year5)
    baseline_adjusted_summary_rows = adjusted_summary_records_to_rows(baseline_adjusted_summary)

    q2_rows = build_q2_summary_rows(scenarios, result_map)
    q3_rows = build_q3_summary_rows(scenarios, result_map)
    sensitivity_rows = build_sensitivity_rows(scenarios, result_map)
    robustness_rows = build_robustness_rows(scenarios, result_map)
    s4_diagnostics = build_s4_diagnostics(result_map, baseline_year5_rows, baseline_adjusted_summary_rows)

    write_csv(OUTPUT_DIR / "4_1_q2_scenario_summary.csv", q2_rows)
    write_csv(OUTPUT_DIR / "4_1_q3_scenario_summary.csv", q3_rows)
    write_csv(OUTPUT_DIR / "4_2_sensitivity_coefficients.csv", sensitivity_rows)
    write_csv(OUTPUT_DIR / "4_2_robustness_metrics.csv", robustness_rows)
    write_csv(OUTPUT_DIR / "4_1_sensitivity_coefficients.csv", sensitivity_rows)
    write_csv(OUTPUT_DIR / "4_1_robustness_metrics.csv", robustness_rows)
    write_s4_diagnostics_file(s4_diagnostics)
    write_interpretation_notes(scenarios, result_map, s4_diagnostics)

    print("Solved RQ4 scenarios and saved Q2/Q3 summaries, sensitivity table, robustness table, S4 diagnostics, and interpretation notes.")


if __name__ == "__main__":
    main()
