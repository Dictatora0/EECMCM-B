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
        "served_demand_coverage": round(item.served_demand_coverage, 6),
        "average_service_satisfaction": round(item.average_service_satisfaction, 6),
        "minimum_service_satisfaction": round(item.minimum_service_satisfaction, 6),
        "total_raw_served_demand_daily": round(item.total_raw_served_demand_daily, 4),
        "total_effective_person_times_daily": round(item.total_effective_person_times_daily, 4),
        "capacity_safety_rate": round(item.capacity_safety_rate, 6),
        "max_station_utilization": round(item.max_station_utilization, 6),
        "fully_safe": item.fully_safe,
        "fully_served_community_count": fully_served_count,
        "total_unmet_daily_demand": round(total_unmet_daily, 4),
        "utilization_variance": round(item.utilization_variance, 6),
        "annual_net_profit_before_subsidy": round(item.annual_net_profit_before_subsidy, 2),
        "annual_net_profit_after_policy_subsidy": round(item.annual_net_profit_after_policy_subsidy, 2),
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
                "assigned_overflow_load": round(metric.assigned_overflow_load, 4),
                "total_load": round(metric.total_load, 4),
                "utilization": round(metric.utilization, 6),
                "annual_service_revenue": round(metric.annual_service_revenue, 2),
                "annual_direct_cost": round(metric.annual_direct_cost, 2),
                "annual_fixed_cost": round(metric.annual_fixed_cost, 2),
                "annual_depreciation": round(metric.annual_depreciation, 2),
                "annual_government_subsidy_baseline": round(metric.annual_government_subsidy_baseline, 2),
                "annual_net_profit_before_subsidy": round(metric.annual_net_profit_before_subsidy, 2),
                "annual_net_profit_after_policy_subsidy": round(metric.annual_net_profit_after_policy_subsidy, 2),
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
                "overflow_station": allocation.overflow_station or "",
                "geographic_reachable": allocation.geographic_reachable,
                "actually_served": allocation.actually_served,
                "geographic_population_covered": round(allocation.geographic_population_covered, 4),
                "served_population_covered": round(allocation.served_population_covered, 4),
                "raw_served_demand_daily": round(allocation.raw_served_demand_daily, 4),
                "effective_person_times_daily": round(allocation.effective_person_times_daily, 4),
                "primary_load_daily": round(allocation.primary_load, 4),
                "overflow_load_daily": round(allocation.overflow_load, 4),
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
    best = ranked[0]
    safe_best, safe_threshold_used = select_safe_scheme(
        evaluations,
        capacity_safety_threshold=capacity_safety_threshold,
    )

    top_output = OUTPUT_DIR / "2_1_top10_schemes.csv"
    compare_output = OUTPUT_DIR / "2_1_dual_scheme_compare.csv"
    tradeoff_output = OUTPUT_DIR / "2_1_safety_threshold_tradeoff.csv"

    write_scheme_bundle("2_1_best_scheme", best, {"scheme_type": "coverage_priority"})
    write_scheme_bundle(
        "2_1_safe_scheme",
        safe_best,
        {
            "scheme_type": "safety_priority",
            "capacity_safety_threshold_used": round(safe_threshold_used, 6),
        },
    )
    write_csv(top_output, [evaluation_to_summary_row(item) for item in ranked[:10]])
    write_csv(
        compare_output,
        [
            {
                "scheme_type": "coverage_priority",
                "capacity_safety_threshold_used": "",
                **evaluation_to_summary_row(best),
            },
            {
                "scheme_type": "safety_priority",
                "capacity_safety_threshold_used": round(safe_threshold_used, 6),
                **evaluation_to_summary_row(safe_best),
            },
        ],
    )
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
        f"served coverage(pop)={best.served_population_coverage:.6f}, "
        f"served coverage(demand)={best.served_demand_coverage:.6f}, "
        f"avg service satisfaction={best.average_service_satisfaction:.6f}; "
        f"safe capacity rate={safe_best.capacity_safety_rate:.6f}"
    )


if __name__ == "__main__":
    main()
