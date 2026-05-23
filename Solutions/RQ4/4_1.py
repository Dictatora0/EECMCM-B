from __future__ import annotations

from common import (
    CACHE_DIR,
    OUTPUT_DIR,
    RQ1_COMMON,
    RQ2_COMMON,
    RQ2_MAIN,
    RQ3_COMMON,
    RQ3_MAIN,
    ScenarioDefinition,
    ScenarioResult,
    q2_summary_row,
    q3_summary_row,
    read_json,
    robustness_row,
    scenario_definitions,
    scenario_requires_rerun_from_rq1,
    sensitivity_row,
    write_csv,
    write_json,
)


_BASELINE_SCHEME_CODES: list[tuple[int, ...]] | None = None


def solve_rq1_under_scenario(scenario: ScenarioDefinition) -> tuple[list[dict[str, float]], list[dict[str, float]], list[dict[str, float]]]:
    communities = RQ1_COMMON.load_community_data()
    transition = RQ1_COMMON.load_transition_probabilities().copy()
    growth_rate = RQ1_COMMON.ELDER_GROWTH_RATE

    if "self_to_semi" in scenario.parameter_changes:
        transition["自理->半失能"] = scenario.parameter_changes["self_to_semi"]
    if "semi_to_disabled" in scenario.parameter_changes:
        transition["半失能->失能"] = scenario.parameter_changes["semi_to_disabled"]
    if "elder_growth_rate" in scenario.parameter_changes:
        growth_rate = scenario.parameter_changes["elder_growth_rate"]

    projection = RQ1_COMMON.project_elderly_population(
        communities=communities,
        transition=transition,
        growth_rate=growth_rate,
    )
    year5_population = [row for row in projection if row["year"] == 5]
    service_demand = RQ1_COMMON.load_service_demand()
    service_costs = RQ1_COMMON.load_service_costs()
    theoretical = RQ1_COMMON.theoretical_monthly_demand(year5_population, service_demand)
    adjusted_detail = RQ1_COMMON.affordability_adjusted_demand(
        communities=communities,
        year5_population=year5_population,
        service_demand=service_demand,
        service_costs=service_costs,
    )
    adjusted_summary = RQ1_COMMON.aggregate_adjusted_demand(adjusted_detail)
    return year5_population, adjusted_summary, adjusted_detail


def solve_q2_only_scenario(
    scenario: ScenarioDefinition,
) -> tuple[object, object, list[dict[str, float]] | None, list[dict[str, float]] | None, list[dict[str, float]] | None]:
    if scenario_requires_rerun_from_rq1(scenario):
        year5_population, adjusted_summary, adjusted_detail = solve_rq1_under_scenario(scenario)
        q2_best, q2_safe = solve_rq2_under_scenario(
            scenario,
            year5_population_rows=year5_population,
            adjusted_summary_rows=adjusted_summary,
        )
        return q2_best, q2_safe, year5_population, adjusted_summary, adjusted_detail

    q2_best, q2_safe = solve_rq2_under_scenario(scenario, adjusted_summary_rows=None)
    return q2_best, q2_safe, None, None, None


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
    year5_population_rows: list[dict[str, float]] | None = None,
    adjusted_summary_rows: list[dict[str, float]] | None = None,
) -> tuple[object, object]:
    scales = RQ2_COMMON.load_station_scales()
    distance_matrix = RQ2_COMMON.load_distance_matrix()
    satisfaction_rules = RQ2_COMMON.load_satisfaction_rules()
    service_costs = RQ2_COMMON.load_service_costs()
    if adjusted_summary_rows is None:
        communities = RQ2_COMMON.load_adjusted_demand_summary()
    else:
        assert year5_population_rows is not None, "Scenario-adjusted population rows are required with adjusted demand rows"
        population_map = {row["community"]: row["elderly_total"] for row in year5_population_rows}
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

    community_names = [item.community for item in communities]
    budget_limit = scenario.parameter_changes.get("budget_limit", RQ2_COMMON.BUDGET_LIMIT)
    fixed_cost_multiplier = scenario.parameter_changes.get("fixed_cost_multiplier", 1.0)
    reuse_baseline_codes = scenario.code in {"S0", "S3"}
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

    evaluations = []
    scheme_codes = enumerate_cached_scheme_codes(
        community_names=community_names,
        scales=scales,
        budget_limit=budget_limit,
        reuse_baseline=reuse_baseline_codes,
    )
    for scheme_code in scheme_codes:
        result = RQ2_COMMON.evaluate_scheme(
            scheme_code=scheme_code,
            communities=communities,
            distance_matrix=distance_matrix,
            scales=scales,
            satisfaction_rules=satisfaction_rules,
            service_costs=service_costs,
        )
        if result is not None:
            evaluations.append(result)

    ranked = RQ2_COMMON.sort_scheme_evaluations(evaluations)
    best = ranked[0]
    safe_best, _safe_threshold = RQ2_COMMON.select_safe_scheme(evaluations)
    return best, safe_best


def build_rq3_inputs_from_scenario(
    scenario: ScenarioDefinition,
    q2_best,
    year5_population_rows: list[dict[str, float]] | None = None,
    adjusted_summary_rows: list[dict[str, float]] | None = None,
    adjusted_detail_rows: list[dict[str, float]] | None = None,
):
    if year5_population_rows is None or adjusted_summary_rows is None or adjusted_detail_rows is None:
        return RQ3_COMMON.load_rq3_inputs()

    q2_summary_row_data = RQ2_MAIN.evaluation_to_summary_row(q2_best)
    q2_summary = RQ3_COMMON.SchemeSummaryRecord(
        scheme_type="coverage_priority",
        scheme_code=q2_summary_row_data["scheme_code"],
        scheme_detail=q2_summary_row_data["scheme_detail"],
        station_count=q2_summary_row_data["station_count"],
        build_cost_wan=q2_summary_row_data["build_cost_wan"],
        geographic_population_coverage=q2_summary_row_data["geographic_population_coverage"],
        served_population_coverage=q2_summary_row_data["served_population_coverage"],
        served_demand_coverage=q2_summary_row_data["served_demand_coverage"],
        average_service_satisfaction=q2_summary_row_data["average_service_satisfaction"],
        minimum_service_satisfaction=q2_summary_row_data["minimum_service_satisfaction"],
        total_raw_served_demand_daily=q2_summary_row_data["total_raw_served_demand_daily"],
        total_effective_person_times_daily=q2_summary_row_data["total_effective_person_times_daily"],
        capacity_safety_rate=q2_summary_row_data["capacity_safety_rate"],
        max_station_utilization=q2_summary_row_data["max_station_utilization"],
        fully_safe=q2_summary_row_data["fully_safe"],
        fully_served_community_count=q2_summary_row_data["fully_served_community_count"],
        total_unmet_daily_demand=q2_summary_row_data["total_unmet_daily_demand"],
        utilization_variance=q2_summary_row_data["utilization_variance"],
        annual_net_profit_before_subsidy=q2_summary_row_data["annual_net_profit_before_subsidy"],
        annual_net_profit_after_policy_subsidy=q2_summary_row_data["annual_net_profit_after_policy_subsidy"],
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
            annual_direct_cost=item.annual_direct_cost,
            annual_fixed_cost=item.annual_fixed_cost,
            annual_depreciation=item.annual_depreciation,
            annual_government_subsidy_baseline=item.annual_government_subsidy_baseline,
            annual_net_profit_before_subsidy=item.annual_net_profit_before_subsidy,
            annual_net_profit_after_policy_subsidy=item.annual_net_profit_after_policy_subsidy,
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
            raw_served_demand_daily=item.raw_served_demand_daily,
            effective_person_times_daily=item.effective_person_times_daily,
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
        metadata={"source": "RQ4", "scenario": scenario.code, "precision": "high"},
        year5_population=year5_population,
        adjusted_demand_summary=adjusted_summary,
        adjusted_demand_detail=adjusted_detail,
        q2_summary=q2_summary,
        q2_stations=q2_stations,
        q2_allocations=q2_allocations,
    )


def solve_rq3_under_scenario(scenario: ScenarioDefinition, q2_best, rq3_inputs) -> tuple[object, object]:
    candidate_profiles = RQ3_MAIN.enumerate_station_price_profiles(rq3_inputs)
    warm_start = {
        row.community: row.service_satisfaction
        for row in rq3_inputs.q2_allocations
    }
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
    )


def serialize_q2_result(
    scenario: ScenarioDefinition,
    q2_best,
    q2_safe,
) -> dict[str, object]:
    return {
        "scenario_code": scenario.code,
        "scenario_name": scenario.name,
        "q2_best_summary": RQ2_MAIN.evaluation_to_summary_row(q2_best),
        "q2_safe_summary": RQ2_MAIN.evaluation_to_summary_row(q2_safe),
        "q2_best_station_locations": sorted(station.community for station in q2_best.stations),
        "q2_safe_station_locations": sorted(station.community for station in q2_safe.stations),
        "q2_best_station_utilizations": [metric.utilization for metric in q2_best.station_metrics],
        "q2_safe_station_utilizations": [metric.utilization for metric in q2_safe.station_metrics],
    }


def solve_scenario(scenario: ScenarioDefinition) -> ScenarioResult:
    q2_best, q2_safe, year5_population, adjusted_summary, adjusted_detail = solve_q2_only_scenario(scenario)
    if year5_population is not None and adjusted_summary is not None and adjusted_detail is not None:
        rq3_inputs = build_rq3_inputs_from_scenario(
            scenario,
            q2_best=q2_best,
            year5_population_rows=year5_population,
            adjusted_summary_rows=adjusted_summary,
            adjusted_detail_rows=adjusted_detail,
        )
    else:
        rq3_inputs = RQ3_COMMON.load_rq3_inputs()
        q2_summary_row_data = RQ2_MAIN.evaluation_to_summary_row(q2_best)
        q2_summary = RQ3_COMMON.SchemeSummaryRecord(
            scheme_type="coverage_priority",
            scheme_code=q2_summary_row_data["scheme_code"],
            scheme_detail=q2_summary_row_data["scheme_detail"],
            station_count=q2_summary_row_data["station_count"],
            build_cost_wan=q2_summary_row_data["build_cost_wan"],
            geographic_population_coverage=q2_summary_row_data["geographic_population_coverage"],
            served_population_coverage=q2_summary_row_data["served_population_coverage"],
            served_demand_coverage=q2_summary_row_data["served_demand_coverage"],
            average_service_satisfaction=q2_summary_row_data["average_service_satisfaction"],
            minimum_service_satisfaction=q2_summary_row_data["minimum_service_satisfaction"],
            total_raw_served_demand_daily=q2_summary_row_data["total_raw_served_demand_daily"],
            total_effective_person_times_daily=q2_summary_row_data["total_effective_person_times_daily"],
            capacity_safety_rate=q2_summary_row_data["capacity_safety_rate"],
            max_station_utilization=q2_summary_row_data["max_station_utilization"],
            fully_safe=q2_summary_row_data["fully_safe"],
            fully_served_community_count=q2_summary_row_data["fully_served_community_count"],
            total_unmet_daily_demand=q2_summary_row_data["total_unmet_daily_demand"],
            utilization_variance=q2_summary_row_data["utilization_variance"],
            annual_net_profit_before_subsidy=q2_summary_row_data["annual_net_profit_before_subsidy"],
            annual_net_profit_after_policy_subsidy=q2_summary_row_data["annual_net_profit_after_policy_subsidy"],
        )
        rq3_inputs = RQ3_COMMON.RQ3Inputs(
            metadata={**rq3_inputs.metadata, "source": "RQ4", "scenario": scenario.code},
            year5_population=rq3_inputs.year5_population,
            adjusted_demand_summary=rq3_inputs.adjusted_demand_summary,
            adjusted_demand_detail=rq3_inputs.adjusted_demand_detail,
            q2_summary=q2_summary,
            q2_stations=[
                RQ3_COMMON.StationRecord(
                    station_community=item.community,
                    scale=item.scale,
                    daily_capacity=item.daily_capacity,
                    assigned_primary_load=item.assigned_primary_load,
                    assigned_overflow_load=item.assigned_overflow_load,
                    total_load=item.total_load,
                    utilization=item.utilization,
                    annual_service_revenue=item.annual_service_revenue,
                    annual_direct_cost=item.annual_direct_cost,
                    annual_fixed_cost=item.annual_fixed_cost,
                    annual_depreciation=item.annual_depreciation,
                    annual_government_subsidy_baseline=item.annual_government_subsidy_baseline,
                    annual_net_profit_before_subsidy=item.annual_net_profit_before_subsidy,
                    annual_net_profit_after_policy_subsidy=item.annual_net_profit_after_policy_subsidy,
                )
                for item in q2_best.station_metrics
            ],
            q2_allocations=[
                RQ3_COMMON.AllocationRecord(
                    community=item.community,
                    primary_station=item.primary_station,
                    overflow_station=item.overflow_station,
                    geographic_reachable=item.geographic_reachable,
                    actually_served=item.actually_served,
                    geographic_population_covered=item.geographic_population_covered,
                    served_population_covered=item.served_population_covered,
                    raw_served_demand_daily=item.raw_served_demand_daily,
                    effective_person_times_daily=item.effective_person_times_daily,
                    primary_load_daily=item.primary_load,
                    overflow_load_daily=item.overflow_load,
                    unmet_load_daily=item.unmet_load,
                    geographic_satisfaction=item.geographic_satisfaction,
                    response_satisfaction=item.response_satisfaction,
                    price_satisfaction=item.price_satisfaction,
                    service_satisfaction=item.service_satisfaction,
                )
                for item in q2_best.allocations
            ],
        )

    financial_best, fairness_best = solve_rq3_under_scenario(scenario, q2_best, rq3_inputs)
    return ScenarioResult(
        scenario_code=scenario.code,
        scenario_name=scenario.name,
        financial_best=financial_best,
        fairness_best=fairness_best,
        q2_best=q2_best,
        q2_safe=q2_safe,
    )


def serialize_scenario_result(result: ScenarioResult) -> dict[str, object]:
    return {
        "scenario_code": result.scenario_code,
        "scenario_name": result.scenario_name,
        "q2_best_summary": RQ2_MAIN.evaluation_to_summary_row(result.q2_best),
        "q2_safe_summary": RQ2_MAIN.evaluation_to_summary_row(result.q2_safe),
        "q2_best_station_locations": sorted(station.community for station in result.q2_best.stations),
        "q2_safe_station_locations": sorted(station.community for station in result.q2_safe.stations),
        "q2_best_station_utilizations": [metric.utilization for metric in result.q2_best.station_metrics],
        "q2_safe_station_utilizations": [metric.utilization for metric in result.q2_safe.station_metrics],
        "financial_best_summary": RQ3_MAIN.evaluation_summary_row(result.financial_best),
        "fairness_best_summary": RQ3_MAIN.evaluation_summary_row(result.fairness_best),
        "financial_best_station_financials": result.financial_best.station_financials,
        "fairness_best_station_financials": result.fairness_best.station_financials,
    }


def solve_and_cache_q2_scenarios(scenarios: list[ScenarioDefinition]) -> None:
    for scenario in scenarios:
        cache_path = CACHE_DIR / f"{scenario.code}_q2.json"
        if cache_path.exists():
            continue
        q2_best, q2_safe, _year5, _adjusted_summary, _adjusted_detail = solve_q2_only_scenario(scenario)
        write_json(cache_path, serialize_q2_result(scenario, q2_best, q2_safe))


def build_q2_summary_table_from_cache(output_codes: set[str]) -> None:
    scenario_map = {item.code: item for item in scenario_definitions()}
    q2_rows = []
    for code in sorted(output_codes):
        scenario = scenario_map[code]
        result = read_json(CACHE_DIR / f"{code}_q2.json")
        q2_rows.append(
            {
                "scenario_code": scenario.code,
                "scenario_name": scenario.name,
                "scheme_label": "coverage_priority",
                "station_count": result["q2_best_summary"]["station_count"],
                "station_locations": ";".join(result["q2_best_station_locations"]),
                "build_cost_wan": result["q2_best_summary"]["build_cost_wan"],
                "geographic_population_coverage": result["q2_best_summary"]["geographic_population_coverage"],
                "served_population_coverage": result["q2_best_summary"]["served_population_coverage"],
                "served_demand_coverage": result["q2_best_summary"]["served_demand_coverage"],
                "average_service_satisfaction": result["q2_best_summary"]["average_service_satisfaction"],
                "minimum_service_satisfaction": result["q2_best_summary"]["minimum_service_satisfaction"],
                "annual_net_profit_before_subsidy": result["q2_best_summary"]["annual_net_profit_before_subsidy"],
                "annual_net_profit_after_policy_subsidy": result["q2_best_summary"]["annual_net_profit_after_policy_subsidy"],
                "capacity_safety_rate": result["q2_best_summary"]["capacity_safety_rate"],
                "max_station_utilization": result["q2_best_summary"]["max_station_utilization"],
                "fully_safe": result["q2_best_summary"]["fully_safe"],
            }
        )
        q2_rows.append(
            {
                "scenario_code": scenario.code,
                "scenario_name": scenario.name,
                "scheme_label": "safety_priority",
                "station_count": result["q2_safe_summary"]["station_count"],
                "station_locations": ";".join(result["q2_safe_station_locations"]),
                "build_cost_wan": result["q2_safe_summary"]["build_cost_wan"],
                "geographic_population_coverage": result["q2_safe_summary"]["geographic_population_coverage"],
                "served_population_coverage": result["q2_safe_summary"]["served_population_coverage"],
                "served_demand_coverage": result["q2_safe_summary"]["served_demand_coverage"],
                "average_service_satisfaction": result["q2_safe_summary"]["average_service_satisfaction"],
                "minimum_service_satisfaction": result["q2_safe_summary"]["minimum_service_satisfaction"],
                "annual_net_profit_before_subsidy": result["q2_safe_summary"]["annual_net_profit_before_subsidy"],
                "annual_net_profit_after_policy_subsidy": result["q2_safe_summary"]["annual_net_profit_after_policy_subsidy"],
                "capacity_safety_rate": result["q2_safe_summary"]["capacity_safety_rate"],
                "max_station_utilization": result["q2_safe_summary"]["max_station_utilization"],
                "fully_safe": result["q2_safe_summary"]["fully_safe"],
            }
        )
    write_csv(OUTPUT_DIR / "4_1_q2_scenario_summary.csv", q2_rows)


def build_q3_summary_table_from_cache(output_codes: set[str]) -> None:
    scenario_map = {item.code: item for item in scenario_definitions()}
    q3_rows = []
    for code in sorted(output_codes):
        scenario = scenario_map[code]
        result = read_json(CACHE_DIR / f"{code}.json")
        q3_rows.append(
            {
                "scenario_code": scenario.code,
                "scenario_name": scenario.name,
                "scheme_label": "financial_best",
                **result["financial_best_summary"],
            }
        )
        q3_rows.append(
            {
                "scenario_code": scenario.code,
                "scenario_name": scenario.name,
                "scheme_label": "fairness_best",
                **result["fairness_best_summary"],
            }
        )
    write_csv(OUTPUT_DIR / "4_1_q3_dual_scheme_summary.csv", q3_rows)


def build_sensitivity_table_from_cache(output_codes: set[str]) -> None:
    scenario_map = {item.code: item for item in scenario_definitions()}
    result_map = {
        code: read_json(CACHE_DIR / f"{code}.json")
        for code in sorted(output_codes | {"S0"})
    }
    baseline = result_map["S0"]
    baseline_parameters = {
        "elder_growth_rate": RQ1_COMMON.ELDER_GROWTH_RATE,
        "self_to_semi": RQ1_COMMON.load_transition_probabilities()["自理->半失能"],
        "semi_to_disabled": RQ1_COMMON.load_transition_probabilities()["半失能->失能"],
        "fixed_cost_multiplier": 1.0,
        "budget_limit": RQ2_COMMON.BUDGET_LIMIT,
    }
    sensitivity_rows = []
    for code in sorted(output_codes):
        if code == "S0":
            continue
        scenario = scenario_map[code]
        result = result_map[code]
        scenario_parameters = {**baseline_parameters, **scenario.parameter_changes}
        sensitivity_rows.append(
            sensitivity_row(
                scenario,
                "financial_best",
                "served_demand_coverage",
                float(baseline["q2_best_summary"]["served_demand_coverage"]),
                float(result["q2_best_summary"]["served_demand_coverage"]),
                baseline_parameters=baseline_parameters,
                scenario_parameters=scenario_parameters,
            )
        )
        sensitivity_rows.append(
            sensitivity_row(
                scenario,
                "financial_best",
                "average_service_satisfaction",
                float(baseline["financial_best_summary"]["average_service_satisfaction"]),
                float(result["financial_best_summary"]["average_service_satisfaction"]),
                baseline_parameters=baseline_parameters,
                scenario_parameters=scenario_parameters,
            )
        )
        sensitivity_rows.append(
            sensitivity_row(
                scenario,
                "financial_best",
                "annual_government_subsidy",
                float(baseline["financial_best_summary"]["annual_government_subsidy"]),
                float(result["financial_best_summary"]["annual_government_subsidy"]),
                baseline_parameters=baseline_parameters,
                scenario_parameters=scenario_parameters,
            )
        )
        sensitivity_rows.append(
            sensitivity_row(
                scenario,
                "financial_best",
                "annual_net_profit_after_subsidy",
                float(baseline["financial_best_summary"]["annual_net_profit_after_subsidy"]),
                float(result["financial_best_summary"]["annual_net_profit_after_subsidy"]),
                baseline_parameters=baseline_parameters,
                scenario_parameters=scenario_parameters,
            )
        )
    write_csv(OUTPUT_DIR / "4_1_sensitivity_coefficients.csv", sensitivity_rows)


def build_robustness_table_from_cache(output_codes: set[str]) -> None:
    scenario_map = {item.code: item for item in scenario_definitions()}
    result_map = {
        code: read_json(CACHE_DIR / f"{code}.json")
        for code in sorted(output_codes | {"S0"})
    }
    baseline = result_map["S0"]
    robustness_rows = []
    baseline_locations = set(baseline["q2_best_station_locations"])
    baseline_cov = float(baseline["q2_best_summary"]["served_demand_coverage"])
    baseline_sat = float(baseline["q2_best_summary"]["average_service_satisfaction"])
    for code in sorted(output_codes):
        if code == "S0":
            continue
        scenario = scenario_map[code]
        result = result_map[code]
        scenario_locations = set(result["q2_best_station_locations"])
        scenario_cov = float(result["q2_best_summary"]["served_demand_coverage"])
        scenario_sat = float(result["q2_best_summary"]["average_service_satisfaction"])

        for scheme_label, summary_key, station_fin_key in [
            ("financial_best", "financial_best_summary", "financial_best_station_financials"),
            ("fairness_best", "fairness_best_summary", "fairness_best_station_financials"),
        ]:
            station_financials = result[station_fin_key]
            robustness_rows.append(
                {
                    "scenario_code": scenario.code,
                    "scenario_name": scenario.name,
                    "scheme_label": scheme_label,
                    "RS_loc": round(
                        len(baseline_locations & scenario_locations) / max(len(baseline_locations), 1),
                        6,
                    ),
                    "RS_cov": round(1.0 - abs(scenario_cov - baseline_cov), 6),
                    "RS_sat": round(1.0 - abs(scenario_sat - baseline_sat), 6),
                    "RS_fin": round(
                        sum(1 for row in station_financials if row["profit_compliant"] == 1)
                        / max(len(station_financials), 1),
                        6,
                    ),
                    "RS_cap": round(
                        sum(1 for value in result["q2_best_station_utilizations"] if value <= 0.85 + 1e-12)
                        / max(len(result["q2_best_station_utilizations"]), 1),
                        6,
                    ),
                    "profit_compliant": result[summary_key]["profit_compliant"],
                    "fair_satisfaction_compliant": result[summary_key]["fair_satisfaction_compliant"],
                    "minimum_service_satisfaction": result[summary_key]["minimum_service_satisfaction"],
                    "max_station_utilization": result["q2_best_summary"]["max_station_utilization"],
                    "capacity_safety_rate": result["q2_best_summary"]["capacity_safety_rate"],
                    "avg_station_profit_rate": round(
                        sum(float(row["profit_rate"]) for row in station_financials)
                        / max(len(station_financials), 1),
                        6,
                    ),
                }
            )
    write_csv(OUTPUT_DIR / "4_1_robustness_metrics.csv", robustness_rows)


def solve_and_cache_scenarios(scenarios: list[ScenarioDefinition]) -> None:
    for scenario in scenarios:
        cache_path = CACHE_DIR / f"{scenario.code}.json"
        if cache_path.exists():
            continue
        result = solve_scenario(scenario)
        write_json(cache_path, serialize_scenario_result(result))


def build_summary_tables_from_cache(output_codes: set[str]) -> None:
    scenario_map = {item.code: item for item in scenario_definitions()}
    result_map = {
        code: read_json(CACHE_DIR / f"{code}.json")
        for code in sorted(output_codes | {"S0"})
    }
    baseline = result_map["S0"]

    all_scenarios = scenario_definitions()
    q2_rows = []
    q3_rows = []
    sensitivity_rows = []
    robustness_rows = []

    baseline_parameters = {
        "elder_growth_rate": RQ1_COMMON.ELDER_GROWTH_RATE,
        "self_to_semi": RQ1_COMMON.load_transition_probabilities()["自理->半失能"],
        "semi_to_disabled": RQ1_COMMON.load_transition_probabilities()["半失能->失能"],
        "fixed_cost_multiplier": 1.0,
        "budget_limit": RQ2_COMMON.BUDGET_LIMIT,
    }

    for code in sorted(output_codes):
        result = result_map[code]
        scenario = scenario_map[code]
        q2_rows.append(
            {
                "scenario_code": scenario.code,
                "scenario_name": scenario.name,
                "scheme_label": "coverage_priority",
                "station_count": result["q2_best_summary"]["station_count"],
                "station_locations": ";".join(result["q2_best_station_locations"]),
                "build_cost_wan": result["q2_best_summary"]["build_cost_wan"],
                "geographic_population_coverage": result["q2_best_summary"]["geographic_population_coverage"],
                "served_population_coverage": result["q2_best_summary"]["served_population_coverage"],
                "served_demand_coverage": result["q2_best_summary"]["served_demand_coverage"],
                "average_service_satisfaction": result["q2_best_summary"]["average_service_satisfaction"],
                "minimum_service_satisfaction": result["q2_best_summary"]["minimum_service_satisfaction"],
                "annual_net_profit_before_subsidy": result["q2_best_summary"]["annual_net_profit_before_subsidy"],
                "annual_net_profit_after_policy_subsidy": result["q2_best_summary"]["annual_net_profit_after_policy_subsidy"],
                "capacity_safety_rate": result["q2_best_summary"]["capacity_safety_rate"],
                "max_station_utilization": result["q2_best_summary"]["max_station_utilization"],
                "fully_safe": result["q2_best_summary"]["fully_safe"],
            }
        )
        q2_rows.append(
            {
                "scenario_code": scenario.code,
                "scenario_name": scenario.name,
                "scheme_label": "safety_priority",
                "station_count": result["q2_safe_summary"]["station_count"],
                "station_locations": ";".join(result["q2_safe_station_locations"]),
                "build_cost_wan": result["q2_safe_summary"]["build_cost_wan"],
                "geographic_population_coverage": result["q2_safe_summary"]["geographic_population_coverage"],
                "served_population_coverage": result["q2_safe_summary"]["served_population_coverage"],
                "served_demand_coverage": result["q2_safe_summary"]["served_demand_coverage"],
                "average_service_satisfaction": result["q2_safe_summary"]["average_service_satisfaction"],
                "minimum_service_satisfaction": result["q2_safe_summary"]["minimum_service_satisfaction"],
                "annual_net_profit_before_subsidy": result["q2_safe_summary"]["annual_net_profit_before_subsidy"],
                "annual_net_profit_after_policy_subsidy": result["q2_safe_summary"]["annual_net_profit_after_policy_subsidy"],
                "capacity_safety_rate": result["q2_safe_summary"]["capacity_safety_rate"],
                "max_station_utilization": result["q2_safe_summary"]["max_station_utilization"],
                "fully_safe": result["q2_safe_summary"]["fully_safe"],
            }
        )
        q3_rows.append(
            {
                "scenario_code": scenario.code,
                "scenario_name": scenario.name,
                "scheme_label": "financial_best",
                **result["financial_best_summary"],
            }
        )
        q3_rows.append(
            {
                "scenario_code": scenario.code,
                "scenario_name": scenario.name,
                "scheme_label": "fairness_best",
                **result["fairness_best_summary"],
            }
        )

        if code == "S0":
            continue

        scenario_parameters = {**baseline_parameters, **scenario.parameter_changes}
        sensitivity_rows.append(
            sensitivity_row(
                scenario,
                "financial_best",
                "served_demand_coverage",
                float(baseline["q2_best_summary"]["served_demand_coverage"]),
                float(result["q2_best_summary"]["served_demand_coverage"]),
                baseline_parameters=baseline_parameters,
                scenario_parameters=scenario_parameters,
            )
        )
        sensitivity_rows.append(
            sensitivity_row(
                scenario,
                "financial_best",
                "average_service_satisfaction",
                float(baseline["financial_best_summary"]["average_service_satisfaction"]),
                float(result["financial_best_summary"]["average_service_satisfaction"]),
                baseline_parameters=baseline_parameters,
                scenario_parameters=scenario_parameters,
            )
        )
        sensitivity_rows.append(
            sensitivity_row(
                scenario,
                "financial_best",
                "annual_government_subsidy",
                float(baseline["financial_best_summary"]["annual_government_subsidy"]),
                float(result["financial_best_summary"]["annual_government_subsidy"]),
                baseline_parameters=baseline_parameters,
                scenario_parameters=scenario_parameters,
            )
        )
        sensitivity_rows.append(
            sensitivity_row(
                scenario,
                "financial_best",
                "annual_net_profit_after_subsidy",
                float(baseline["financial_best_summary"]["annual_net_profit_after_subsidy"]),
                float(result["financial_best_summary"]["annual_net_profit_after_subsidy"]),
                baseline_parameters=baseline_parameters,
                scenario_parameters=scenario_parameters,
            )
        )

        robustness_rows.append(
            {
                "scenario_code": scenario.code,
                "scenario_name": scenario.name,
                "scheme_label": "financial_best",
                "RS_loc": round(
                    len(set(baseline["q2_best_station_locations"]) & set(result["q2_best_station_locations"]))
                    / max(len(set(baseline["q2_best_station_locations"])), 1),
                    6,
                ),
                "RS_cov": round(
                    1.0 - abs(
                        float(result["q2_best_summary"]["served_demand_coverage"])
                        - float(baseline["q2_best_summary"]["served_demand_coverage"])
                    ),
                    6,
                ),
                "RS_sat": round(
                    1.0 - abs(
                        float(result["q2_best_summary"]["average_service_satisfaction"])
                        - float(baseline["q2_best_summary"]["average_service_satisfaction"])
                    ),
                    6,
                ),
                "RS_fin": round(
                    sum(1 for row in result["financial_best_station_financials"] if row["profit_compliant"] == 1)
                    / max(len(result["financial_best_station_financials"]), 1),
                    6,
                ),
                "RS_cap": round(
                    sum(1 for value in result["q2_best_station_utilizations"] if value <= 0.85 + 1e-12)
                    / max(len(result["q2_best_station_utilizations"]), 1),
                    6,
                ),
                "profit_compliant": result["financial_best_summary"]["profit_compliant"],
                "fair_satisfaction_compliant": result["financial_best_summary"]["fair_satisfaction_compliant"],
                "minimum_service_satisfaction": result["financial_best_summary"]["minimum_service_satisfaction"],
                "max_station_utilization": result["q2_best_summary"]["max_station_utilization"],
                "capacity_safety_rate": result["q2_best_summary"]["capacity_safety_rate"],
                "avg_station_profit_rate": round(
                    sum(float(row["profit_rate"]) for row in result["financial_best_station_financials"])
                    / max(len(result["financial_best_station_financials"]), 1),
                    6,
                ),
            }
        )
        robustness_rows.append(
            {
                "scenario_code": scenario.code,
                "scenario_name": scenario.name,
                "scheme_label": "fairness_best",
                "RS_loc": round(
                    len(set(baseline["q2_best_station_locations"]) & set(result["q2_best_station_locations"]))
                    / max(len(set(baseline["q2_best_station_locations"])), 1),
                    6,
                ),
                "RS_cov": round(
                    1.0 - abs(
                        float(result["q2_best_summary"]["served_demand_coverage"])
                        - float(baseline["q2_best_summary"]["served_demand_coverage"])
                    ),
                    6,
                ),
                "RS_sat": round(
                    1.0 - abs(
                        float(result["q2_best_summary"]["average_service_satisfaction"])
                        - float(baseline["q2_best_summary"]["average_service_satisfaction"])
                    ),
                    6,
                ),
                "RS_fin": round(
                    sum(1 for row in result["fairness_best_station_financials"] if row["profit_compliant"] == 1)
                    / max(len(result["fairness_best_station_financials"]), 1),
                    6,
                ),
                "RS_cap": round(
                    sum(1 for value in result["q2_best_station_utilizations"] if value <= 0.85 + 1e-12)
                    / max(len(result["q2_best_station_utilizations"]), 1),
                    6,
                ),
                "profit_compliant": result["fairness_best_summary"]["profit_compliant"],
                "fair_satisfaction_compliant": result["fairness_best_summary"]["fair_satisfaction_compliant"],
                "minimum_service_satisfaction": result["fairness_best_summary"]["minimum_service_satisfaction"],
                "max_station_utilization": result["q2_best_summary"]["max_station_utilization"],
                "capacity_safety_rate": result["q2_best_summary"]["capacity_safety_rate"],
                "avg_station_profit_rate": round(
                    sum(float(row["profit_rate"]) for row in result["fairness_best_station_financials"])
                    / max(len(result["fairness_best_station_financials"]), 1),
                    6,
                ),
            }
        )

    write_csv(OUTPUT_DIR / "4_1_q2_scenario_summary.csv", q2_rows)
    write_csv(OUTPUT_DIR / "4_1_q3_dual_scheme_summary.csv", q3_rows)
    write_csv(OUTPUT_DIR / "4_1_sensitivity_coefficients.csv", sensitivity_rows)
    write_csv(OUTPUT_DIR / "4_1_robustness_metrics.csv", robustness_rows)


def main_q2_stage(
    scenario_codes: list[str] | None = None,
    summary_codes: list[str] | None = None,
) -> None:
    all_scenarios = scenario_definitions()
    scenario_map = {item.code: item for item in all_scenarios}
    if scenario_codes is not None:
        requested = set(scenario_codes)
        assert requested, "Scenario code filter must not be empty"
        assert requested <= set(scenario_map), f"Unknown scenario codes: {sorted(requested - set(scenario_map))}"
        solve_codes = {"S0"} | requested
        scenarios = [item for item in all_scenarios if item.code in solve_codes]
        output_codes = set(summary_codes) if summary_codes is not None else requested
    else:
        scenarios = all_scenarios
        output_codes = set(summary_codes) if summary_codes is not None else {item.code for item in all_scenarios}

    assert output_codes <= set(scenario_map), f"Unknown summary codes: {sorted(output_codes - set(scenario_map))}"

    solve_and_cache_q2_scenarios(scenarios)
    build_q2_summary_table_from_cache(output_codes)

    print(f"Solved Q2 stage for {len(scenarios)} scenarios including baseline cache when required.")
    print("Saved Q2 scenario summary.")


def main_q3_summary_only(summary_codes: list[str]) -> None:
    scenario_map = {item.code: item for item in scenario_definitions()}
    requested = set(summary_codes)
    assert requested, "Summary code filter must not be empty"
    assert requested <= set(scenario_map), f"Unknown summary codes: {sorted(requested - set(scenario_map))}"
    build_q3_summary_table_from_cache(requested)
    print(f"Saved Q3 dual-scheme summary for {len(requested)} scenarios from cache.")


def main_metrics_summary_only(summary_codes: list[str]) -> None:
    scenario_map = {item.code: item for item in scenario_definitions()}
    requested = set(summary_codes)
    assert requested, "Summary code filter must not be empty"
    assert requested <= set(scenario_map), f"Unknown summary codes: {sorted(requested - set(scenario_map))}"
    build_sensitivity_table_from_cache(requested)
    build_robustness_table_from_cache(requested)
    print(f"Saved sensitivity and robustness summaries for {len(requested)} scenarios from cache.")


def main(scenario_codes: list[str] | None = None) -> None:
    all_scenarios = scenario_definitions()
    scenario_map = {item.code: item for item in all_scenarios}
    if scenario_codes is not None:
        requested = set(scenario_codes)
        assert requested, "Scenario code filter must not be empty"
        assert requested <= set(scenario_map), f"Unknown scenario codes: {sorted(requested - set(scenario_map))}"
        solve_codes = {"S0"} | requested
        scenarios = [item for item in all_scenarios if item.code in solve_codes]
        output_codes = requested
    else:
        scenarios = all_scenarios
        output_codes = {item.code for item in all_scenarios}

    solve_and_cache_scenarios(scenarios)
    build_summary_tables_from_cache(output_codes)

    print(f"Solved {len(scenarios)} scenarios including baseline cache when required.")
    print("Saved Q2 summary, Q3 dual-scheme summary, sensitivity coefficients, and robustness metrics.")


if __name__ == "__main__":
    main()
