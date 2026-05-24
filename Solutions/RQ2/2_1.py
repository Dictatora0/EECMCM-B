from __future__ import annotations

from common import (
    OUTPUT_DIR,
    SAFE_CAPACITY_THRESHOLD,
    SAFE_CAPACITY_THRESHOLD_GRID,
    enumerate_feasible_scheme_codes,
    evaluate_scheme,
    load_adjusted_demand_summary,
    load_distance_matrix,
    load_satisfaction_rules,
    load_service_costs,
    load_station_scales,
    solve_location_milp,
    select_safe_scheme,
    sort_scheme_evaluations_safe,
    sort_scheme_evaluations,
    write_csv,
)


def evaluation_to_summary_row(item):
    nonzero_scales = [
        f"{station.community}-{station.scale}"
        for station in item.stations
    ]
    fully_served_count = sum(1 for allocation in item.allocations if allocation.unmet_load <= 1e-8)
    total_unmet_daily = sum(allocation.unmet_load for allocation in item.allocations)
    return {
        "scheme_code": "".join(str(token) for token in item.scheme_code),
        "scheme_detail": ";".join(nonzero_scales),
        "station_count": len(item.stations),
        "build_cost_wan": round(sum(station.build_cost_wan for station in item.stations), 4),
        "geographic_population_coverage": round(item.geographic_population_coverage, 6),
        "served_population_coverage": round(item.served_population_coverage, 6),
        "weighted_served_population_coverage": round(item.weighted_served_population_coverage, 6),
        "served_demand_coverage": round(item.served_demand_coverage, 6),
        "average_service_satisfaction": round(item.average_service_satisfaction, 6),
        "minimum_service_satisfaction": round(item.minimum_service_satisfaction, 6),
        "average_service_access_performance": round(item.average_service_access_performance, 6),
        "minimum_service_access_performance": round(item.minimum_service_access_performance, 6),
        "total_adjusted_demand_daily": round(item.total_adjusted_demand_daily, 4),
        "total_raw_served_demand_daily": round(item.total_raw_served_demand_daily, 4),
        "total_effective_person_times_daily": round(item.total_effective_person_times_daily, 4),
        "capacity_safety_rate": round(item.capacity_safety_rate, 6),
        "max_station_utilization": round(item.max_station_utilization, 6),
        "fully_safe": item.fully_safe,
        "fully_served_community_count": fully_served_count,
        "total_unmet_daily_demand": round(total_unmet_daily, 4),
        "utilization_variance": round(item.utilization_variance, 6),
        "annual_revenue": round(item.annual_revenue, 2),
        "annual_subsidy": round(item.annual_subsidy, 2),
        "annual_direct_cost": round(item.annual_direct_cost, 2),
        "annual_fixed_cost": round(item.annual_fixed_cost, 2),
        "annual_depreciation": round(item.annual_depreciation, 2),
        "annual_total_cost": round(item.annual_total_cost, 2),
        "annual_net_profit_before_subsidy": round(item.annual_net_profit_before_subsidy, 2),
        "annual_net_profit_after_policy_subsidy": round(item.annual_net_profit_after_policy_subsidy, 2),
        "annual_net_profit": round(item.annual_net_profit, 2),
        "profit_rate": round(item.profit_rate, 6),
        "profit_compliant": item.profit_compliant,
    }


def write_scheme_bundle(prefix: str, item, extra_fields: dict | None = None) -> None:
    summary_output = OUTPUT_DIR / f"{prefix}_summary.csv"
    station_output = OUTPUT_DIR / f"{prefix}_stations.csv"
    allocation_output = OUTPUT_DIR / f"{prefix}_allocations.csv"

    row = evaluation_to_summary_row(item)
    if extra_fields:
        row = {**extra_fields, **row}
    write_csv(summary_output, [row])
    write_csv(
        station_output,
        [
            {
                "station_community": metric.community,
                "scale": metric.scale,
                "daily_capacity": round(metric.daily_capacity, 4),
                "assigned_primary_load": round(metric.assigned_primary_load, 4),
                "total_load": round(metric.total_load, 4),
                "utilization": round(metric.utilization, 6),
                "annual_service_revenue": round(metric.annual_service_revenue, 2),
                "annual_revenue": round(metric.annual_revenue, 2),
                "annual_subsidy": round(metric.annual_subsidy, 2),
                "annual_direct_cost": round(metric.annual_direct_cost, 2),
                "annual_fixed_cost": round(metric.annual_fixed_cost, 2),
                "annual_depreciation": round(metric.annual_depreciation, 2),
                "annual_government_subsidy_baseline": round(metric.annual_government_subsidy_baseline, 2),
                "annual_total_cost": round(metric.annual_total_cost, 2),
                "annual_net_profit_before_subsidy": round(metric.annual_net_profit_before_subsidy, 2),
                "annual_net_profit_after_policy_subsidy": round(metric.annual_net_profit_after_policy_subsidy, 2),
                "annual_net_profit": round(metric.annual_net_profit, 2),
                "profit_rate": round(metric.profit_rate, 6),
                "profit_compliant": metric.profit_compliant,
            }
            for metric in item.station_metrics
        ],
    )
    write_csv(
        allocation_output,
        [
            {
                "community": allocation.community,
                "primary_station": allocation.primary_station or "",
                "geographic_reachable": allocation.geographic_reachable,
                "actually_served": allocation.actually_served,
                "geographic_population_covered": round(allocation.geographic_population_covered, 4),
                "served_population_covered": round(allocation.served_population_covered, 4),
                "adjusted_demand_daily": round(allocation.adjusted_demand_daily, 4),
                "raw_served_demand_daily": round(allocation.raw_served_demand_daily, 4),
                "effective_person_times_daily": round(allocation.effective_person_times_daily, 4),
                "demand_service_ratio": round(allocation.demand_service_ratio, 6),
                "service_access_performance": round(allocation.service_access_performance, 6),
                "primary_load_daily": round(allocation.primary_load, 4),
                "unmet_load_daily": round(allocation.unmet_load, 4),
                "geographic_satisfaction": round(allocation.geographic_satisfaction, 6),
                "response_satisfaction": round(allocation.response_satisfaction, 6),
                "price_satisfaction": round(allocation.price_satisfaction, 6),
                "service_satisfaction": round(allocation.service_satisfaction, 6),
            }
            for allocation in item.allocations
        ],
    )


def main(capacity_safety_threshold: float = SAFE_CAPACITY_THRESHOLD) -> None:
    communities = load_adjusted_demand_summary()
    community_names = [item.community for item in communities]
    scales = load_station_scales()
    distance_matrix = load_distance_matrix()
    satisfaction_rules = load_satisfaction_rules()
    service_costs = load_service_costs()

    evaluations = []
    for scheme_code in enumerate_feasible_scheme_codes(community_names, scales):
        result = evaluate_scheme(
            scheme_code=scheme_code,
            communities=communities,
            distance_matrix=distance_matrix,
            scales=scales,
            satisfaction_rules=satisfaction_rules,
            service_costs=service_costs,
        )
        if result is not None:
            evaluations.append(result)

    ranked = sort_scheme_evaluations(evaluations)
    baseline_best = ranked[0]
    safe_best, safe_threshold_used = select_safe_scheme(
        evaluations,
        capacity_safety_threshold=capacity_safety_threshold,
    )
    optimized_scheme_code = solve_location_milp(
        communities=communities,
        distance_matrix=distance_matrix,
        scales=scales,
        budget_limit=120.0,
        fairness_weight=0.25,
        safety_capacity_factor=0.85,
    )
    optimized_best = (
        evaluate_scheme(
            scheme_code=optimized_scheme_code,
            communities=communities,
            distance_matrix=distance_matrix,
            scales=scales,
            satisfaction_rules=satisfaction_rules,
            service_costs=service_costs,
        )
        if optimized_scheme_code is not None
        else None
    )
    robust_scheme_code = solve_location_milp(
        communities=communities,
        distance_matrix=distance_matrix,
        scales=scales,
        budget_limit=120.0,
        fairness_weight=0.35,
        safety_capacity_factor=0.75,
    )
    robust_best = (
        evaluate_scheme(
            scheme_code=robust_scheme_code,
            communities=communities,
            distance_matrix=distance_matrix,
            scales=scales,
            satisfaction_rules=satisfaction_rules,
            service_costs=service_costs,
        )
        if robust_scheme_code is not None
        else None
    )

    top_output = OUTPUT_DIR / "2_1_top10_schemes.csv"
    compare_output = OUTPUT_DIR / "2_1_dual_scheme_compare.csv"
    tradeoff_output = OUTPUT_DIR / "2_1_safety_threshold_tradeoff.csv"
    model_compare_output = OUTPUT_DIR / "2_1_extension_model_upgrade_compare.csv"

    write_scheme_bundle("2_1_best_scheme", baseline_best, {"scheme_type": "coverage_priority_baseline"})
    write_scheme_bundle(
        "2_1_safe_scheme",
        safe_best,
        {
            "scheme_type": "safety_priority",
            "capacity_safety_threshold_used": round(safe_threshold_used, 6),
        },
    )
    if optimized_best is not None:
        write_scheme_bundle(
            "2_1_extension_optimized_scheme",
            optimized_best,
            {
                "scheme_type": "milp_multiobjective",
                "model_name": "coverage_fairness_capacity_milp",
            },
        )
    if robust_best is not None:
        write_scheme_bundle(
            "2_1_extension_robust_scheme",
            robust_best,
            {
                "scheme_type": "robust_capacity_priority",
                "model_name": "robust_milp",
            },
        )
    write_csv(top_output, [evaluation_to_summary_row(item) for item in ranked[:10]])
    write_csv(
        compare_output,
        [
            {
                "scheme_type": "coverage_priority_baseline",
                "capacity_safety_threshold_used": "",
                **evaluation_to_summary_row(baseline_best),
            },
            {
                "scheme_type": "safety_priority",
                "capacity_safety_threshold_used": round(safe_threshold_used, 6),
                **evaluation_to_summary_row(safe_best),
            },
        ],
    )
    model_compare_rows = [
        {
            "model_variant": "baseline_enumeration",
            **evaluation_to_summary_row(baseline_best),
        },
        {
            "model_variant": "safe_baseline",
            **evaluation_to_summary_row(safe_best),
        },
    ]
    if optimized_best is not None:
        model_compare_rows.append(
            {
                "model_variant": "milp_multiobjective",
                **evaluation_to_summary_row(optimized_best),
            }
        )
    if robust_best is not None:
        model_compare_rows.append(
            {
                "model_variant": "robust_milp",
                **evaluation_to_summary_row(robust_best),
            }
        )
    write_csv(model_compare_output, model_compare_rows)
    tradeoff_rows = []
    for threshold in SAFE_CAPACITY_THRESHOLD_GRID:
        picked, used = select_safe_scheme(evaluations, capacity_safety_threshold=threshold)
        tradeoff_rows.append(
            {
                "requested_capacity_safety_threshold": round(threshold, 6),
                "actual_threshold_used": round(used, 6),
                **evaluation_to_summary_row(picked),
            }
        )
    write_csv(tradeoff_output, tradeoff_rows)

    print(f"Enumerated {len(evaluations)} feasible schemes.")
    print("Saved coverage-priority and safety-priority scheme bundles.")
    print(f"Saved top-10 schemes to {top_output}")
    print(f"Saved dual-scheme comparison to {compare_output}")
    print(f"Saved safety-threshold tradeoff table to {tradeoff_output}")
    print(
        "Validation: "
        f"served coverage(pop)={baseline_best.served_population_coverage:.6f}, "
        f"served coverage(demand)={baseline_best.served_demand_coverage:.6f}, "
        f"avg service satisfaction={baseline_best.average_service_satisfaction:.6f}; "
        f"safe capacity rate={safe_best.capacity_safety_rate:.6f}"
    )


if __name__ == "__main__":
    main()
