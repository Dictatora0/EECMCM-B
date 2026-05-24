from __future__ import annotations

from pathlib import Path

from common import (
    DEATH_RATE,
    ELDER_GROWTH_RATE,
    OUTPUT_DIR,
    aggregate_adjusted_demand,
    aggregate_population_metrics,
    aggregate_service_metric,
    affordability_adjusted_demand,
    load_community_data,
    load_service_costs,
    load_service_demand,
    load_transition_probabilities,
    population_transition_matrix,
    project_elderly_population,
    project_elderly_population_matrix,
    round_rows,
    theoretical_monthly_demand,
    write_csv,
)


SENSITIVITY_CASES = [
    ("baseline", {"growth_rate": 0.07, "p12": None, "p23": None}),
    ("growth_minus_10pct", {"growth_rate": 0.07 * 0.9, "p12": None, "p23": None}),
    ("growth_plus_10pct", {"growth_rate": 0.07 * 1.1, "p12": None, "p23": None}),
    ("p12_minus_10pct", {"growth_rate": 0.07, "p12": 0.9, "p23": None}),
    ("p12_plus_10pct", {"growth_rate": 0.07, "p12": 1.1, "p23": None}),
    ("p23_minus_10pct", {"growth_rate": 0.07, "p12": None, "p23": 0.9}),
    ("p23_plus_10pct", {"growth_rate": 0.07, "p12": None, "p23": 1.1}),
]


def run_case(case_name: str, factors: dict[str, float | None]) -> dict[str, float | str]:
    communities = load_community_data()
    transition = load_transition_probabilities()
    service_demand = load_service_demand()
    service_costs = load_service_costs()

    if factors["p12"] is not None:
        transition["自理->半失能"] *= float(factors["p12"])
    if factors["p23"] is not None:
        transition["半失能->失能"] *= float(factors["p23"])

    growth_rate = float(factors["growth_rate"])
    recursive_rows = project_elderly_population(
        communities=communities,
        transition=transition,
        growth_rate=growth_rate,
    )
    matrix_rows = project_elderly_population_matrix(
        communities=communities,
        transition=transition,
        growth_rate=growth_rate,
    )
    year5_recursive = [row for row in recursive_rows if int(row["year"]) == 5]
    year5_matrix = [row for row in matrix_rows if int(row["year"]) == 5]
    max_abs_diff = max(
        max(
            abs(float(left[field]) - float(right[field]))
            for field in ("self_care", "semi_disabled", "disabled", "elderly_total")
        )
        for left, right in zip(year5_recursive, year5_matrix)
    )

    theoretical_rows = theoretical_monthly_demand(year5_recursive, service_demand)
    adjusted_rows = affordability_adjusted_demand(
        communities=communities,
        year5_population=year5_recursive,
        service_demand=service_demand,
        service_costs=service_costs,
    )
    year5_metrics = aggregate_population_metrics(recursive_rows, year=5)
    adjusted_summary = aggregate_adjusted_demand(adjusted_rows)
    return {
        "case": case_name,
        "death_rate": DEATH_RATE,
        "growth_rate": growth_rate,
        "p12": transition["自理->半失能"],
        "p23": transition["半失能->失能"],
        "year5_elderly_total": year5_metrics["elderly_total"],
        "year5_disabled_share": year5_metrics["disabled_share"],
        "theoretical_total_monthly_demand": aggregate_service_metric(theoretical_rows, "theoretical_monthly_demand"),
        "adjusted_total_monthly_demand": aggregate_service_metric(adjusted_summary, "adjusted_monthly_demand"),
        "matrix_equivalence_max_abs_diff": max_abs_diff,
    }


def write_markdown(summary_rows: list[dict[str, float | str]]) -> None:
    baseline = next(row for row in summary_rows if row["case"] == "baseline")
    lines = [
        "# RQ1 Validation Extension",
        "",
        "本扩展不改变问题1主结果，只补充三类论证：",
        "",
        "1. 递推式与状态转移矩阵形式等价；",
        "2. 第5年规模、失能占比与需求总量对关键参数的局部敏感性；",
        "3. 预测层与需求层、消费约束层之间的传导方向。",
        "",
        "## Matrix Form",
        "",
        "设状态向量为 `x_t = [自理, 半失能, 失能]^T`，则基准情景满足：",
        "",
        "```text",
        "x_(t+1) = A x_t",
        "```",
        "",
        "其中矩阵 `A` 由统一死亡率、单向转移概率与新增老人进入自理状态共同构成。",
        "",
        "## Sensitivity Summary",
        "",
        f"- 基准第5年老年总人数：{float(baseline['year5_elderly_total']):.6f}",
        f"- 基准第5年失能占比：{float(baseline['year5_disabled_share']):.6f}",
        f"- 基准理论月需求总量：{float(baseline['theoretical_total_monthly_demand']):.6f}",
        f"- 基准消费约束后月需求总量：{float(baseline['adjusted_total_monthly_demand']):.6f}",
        "",
        "## Interpretation",
        "",
        "- 若增长率上升，首先抬升总量，其次通过更多自理老人积累影响后续结构。",
        "- 若 `自理→半失能` 上升，半失能与失能服务需求会提前放大。",
        "- 若 `半失能→失能` 上升，失能占比与高成本服务压力会更明显增加。",
        "- 该扩展应写为“局部参数敏感性分析”，不能写成历史回测验证，因为题面未给出多期真实观测。",
        "",
    ]
    (OUTPUT_DIR / "1_4_validation_notes.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    summary_rows = [run_case(case_name, factors) for case_name, factors in SENSITIVITY_CASES]
    transition = load_transition_probabilities()
    matrix_rows = []
    matrix = population_transition_matrix(transition)
    labels = ["self_care_next", "semi_disabled_next", "disabled_next"]
    states = ["self_care", "semi_disabled", "disabled"]
    for row_label, row_values in zip(labels, matrix):
        row = {"target_state": row_label}
        for state, value in zip(states, row_values):
            row[state] = value
        matrix_rows.append(row)

    write_csv(OUTPUT_DIR / "1_4_transition_matrix.csv", round_rows(matrix_rows, digits=8))
    write_csv(OUTPUT_DIR / "1_4_validation_sensitivity_summary.csv", round_rows(summary_rows, digits=8))
    write_markdown(summary_rows)
    print(f"Saved {OUTPUT_DIR / '1_4_transition_matrix.csv'}")
    print(f"Saved {OUTPUT_DIR / '1_4_validation_sensitivity_summary.csv'}")
    print(f"Saved {OUTPUT_DIR / '1_4_validation_notes.md'}")


if __name__ == "__main__":
    main()
