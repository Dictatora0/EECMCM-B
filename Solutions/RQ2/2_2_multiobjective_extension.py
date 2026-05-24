from __future__ import annotations

from pathlib import Path

from common import (
    SAFE_CAPACITY_THRESHOLD,
    CommunityDemand,
    evaluate_scheme,
    enumerate_feasible_scheme_codes,
    load_adjusted_demand_summary,
    load_distance_matrix,
    load_satisfaction_rules,
    load_service_costs,
    load_station_scales,
    sort_scheme_evaluations,
    write_csv,
)


OUTPUT_DIR = Path(__file__).resolve().parent / "outputs"


def pareto_dominates(left, right) -> bool:
    no_worse = (
        left.served_population_coverage >= right.served_population_coverage - 1e-9
        and left.minimum_service_access_performance >= right.minimum_service_access_performance - 1e-9
        and left.capacity_safety_rate >= right.capacity_safety_rate - 1e-9
        and left.total_build_cost <= right.total_build_cost + 1e-9
    )
    strictly_better = (
        left.served_population_coverage > right.served_population_coverage + 1e-9
        or left.minimum_service_access_performance > right.minimum_service_access_performance + 1e-9
        or left.capacity_safety_rate > right.capacity_safety_rate + 1e-9
        or left.total_build_cost < right.total_build_cost - 1e-9
    )
    return no_worse and strictly_better


def with_total_build_cost(item):
    item.total_build_cost = sum(station.build_cost_wan for station in item.stations)
    return item


def evaluation_row(item, label: str) -> dict[str, float | str]:
    return {
        "scheme_label": label,
        "scheme_code": "".join(str(token) for token in item.scheme_code),
        "scheme_detail": ";".join(f"{station.community}-{station.scale}" for station in item.stations),
        "station_count": len(item.stations),
        "build_cost_wan": round(item.total_build_cost, 4),
        "served_population_coverage": round(item.served_population_coverage, 6),
        "weighted_served_population_coverage": round(item.weighted_served_population_coverage, 6),
        "served_demand_coverage": round(item.served_demand_coverage, 6),
        "average_service_access_performance": round(item.average_service_access_performance, 6),
        "minimum_service_access_performance": round(item.minimum_service_access_performance, 6),
        "capacity_safety_rate": round(item.capacity_safety_rate, 6),
        "max_station_utilization": round(item.max_station_utilization, 6),
        "annual_net_profit_after_policy_subsidy": round(item.annual_net_profit_after_policy_subsidy, 2),
        "profit_compliant": int(item.profit_compliant),
    }


def build_epsilon_rows(evaluations: list) -> list[dict[str, float | str]]:
    thresholds = [0.40, 0.45, 0.50, 0.55, 0.60]
    rows: list[dict[str, float | str]] = []
    for threshold in thresholds:
        feasible = [
            item for item in evaluations
            if item.minimum_service_access_performance >= threshold - 1e-9
        ]
        if feasible:
            best = sorted(
                feasible,
                key=lambda item: (
                    -item.served_population_coverage,
                    -item.average_service_access_performance,
                    -item.capacity_safety_rate,
                    item.total_build_cost,
                ),
            )[0]
            row = evaluation_row(best, f"epsilon_min_access_{threshold:.2f}")
            row["epsilon_min_access_threshold"] = threshold
            row["epsilon_feasible_count"] = len(feasible)
        else:
            row = {
                "scheme_label": f"epsilon_min_access_{threshold:.2f}",
                "epsilon_min_access_threshold": threshold,
                "epsilon_feasible_count": 0,
                "scheme_code": "",
                "scheme_detail": "",
                "station_count": 0,
                "build_cost_wan": 0.0,
                "served_population_coverage": 0.0,
                "weighted_served_population_coverage": 0.0,
                "served_demand_coverage": 0.0,
                "average_service_access_performance": 0.0,
                "minimum_service_access_performance": 0.0,
                "capacity_safety_rate": 0.0,
                "max_station_utilization": 0.0,
                "annual_net_profit_after_policy_subsidy": 0.0,
                "profit_compliant": 0,
            }
        rows.append(row)
    return rows


def write_notes(frontier_rows: list[dict[str, float | str]], epsilon_rows: list[dict[str, float | str]]) -> None:
    lines = [
        "# RQ2 Multiobjective Extension",
        "",
        "本扩展不改变问题2主结果，只将现有离散可行方案集重写为多目标设施选址分析。",
        "",
        "## Why This Upgrade Matters",
        "",
        "- 当前问题2本质上是有限离散候选站点、离散规模、预算与半径约束下的容量设施选址问题。",
        "- 因候选站点仅有 10 个，小中大型三档规模离散，因此可将穷举解释为“有限离散精确搜索”，而非简单暴力枚举。",
        "- 在论文中，应把 MILP 结果写为对精确搜索结论的规范化建模与交叉验证，而不是另一个互相矛盾的模型。",
        "",
        "## Suggested Main-text Use",
        "",
        "- 正文主模型：离散设施选址 + 容量约束 + 满意度驱动分配。",
        "- 正文强化：展示 Pareto 前沿代表方案与 epsilon-constraint 公平阈值对最优布局的影响。",
        "- 附录补充：枚举规模、剪枝思想和 MILP 验证结果。",
        "",
        f"- Pareto frontier point count = {len(frontier_rows)}",
        f"- epsilon rows = {len(epsilon_rows)}",
        "",
        "## Paper Wording",
        "",
        "- 推荐写法：在有限离散候选空间内先进行预算可行性剪枝，再对可行方案集进行精确评价，并基于 Pareto 优势关系筛选代表布局。",
        "- 避免写法：采用复杂智能算法搜索最优站点。当前数据规模下，这种表述既不必要，也降低可信度。",
        "",
    ]
    (OUTPUT_DIR / "2_2_multiobjective_notes.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    communities: list[CommunityDemand] = load_adjusted_demand_summary()
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
            evaluations.append(with_total_build_cost(result))

    ranked = sort_scheme_evaluations(evaluations)
    frontier = []
    for item in ranked:
        if any(pareto_dominates(other, item) for other in frontier):
            continue
        frontier = [other for other in frontier if not pareto_dominates(item, other)]
        frontier.append(item)
    frontier_rows = [evaluation_row(item, f"pareto_{idx + 1}") for idx, item in enumerate(frontier)]

    epsilon_rows = build_epsilon_rows(evaluations)
    bottleneck_rows = []
    for item in ranked[:20]:
        bottleneck_rows.append(
            {
                "scheme_code": "".join(str(token) for token in item.scheme_code),
                "scheme_detail": ";".join(f"{station.community}-{station.scale}" for station in item.stations),
                "build_cost_wan": round(item.total_build_cost, 4),
                "served_population_coverage": round(item.served_population_coverage, 6),
                "minimum_service_access_performance": round(item.minimum_service_access_performance, 6),
                "capacity_safety_rate": round(item.capacity_safety_rate, 6),
                "max_station_utilization": round(item.max_station_utilization, 6),
                "binding_capacity_risk": int(item.max_station_utilization > SAFE_CAPACITY_THRESHOLD + 1e-9),
                "full_profit_compliance": int(item.profit_compliant),
            }
        )

    write_csv(OUTPUT_DIR / "2_2_pareto_frontier.csv", frontier_rows)
    write_csv(OUTPUT_DIR / "2_2_epsilon_constraint_summary.csv", epsilon_rows)
    write_csv(OUTPUT_DIR / "2_2_capacity_bottleneck_top20.csv", bottleneck_rows)
    write_notes(frontier_rows, epsilon_rows)
    print(f"Saved {OUTPUT_DIR / '2_2_pareto_frontier.csv'}")
    print(f"Saved {OUTPUT_DIR / '2_2_epsilon_constraint_summary.csv'}")
    print(f"Saved {OUTPUT_DIR / '2_2_capacity_bottleneck_top20.csv'}")
    print(f"Saved {OUTPUT_DIR / '2_2_multiobjective_notes.md'}")


if __name__ == "__main__":
    main()
