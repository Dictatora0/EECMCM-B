from __future__ import annotations

import json
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

from common import OUTPUT_DIR, load_rq3_inputs, write_csv


RQ3_DIR = Path(__file__).resolve().parent
RQ3_MAIN_PATH = RQ3_DIR / "3_1.py"
RQ3_MAIN_SPEC = spec_from_file_location("rq3_joint_diag_main_module", RQ3_MAIN_PATH)
if RQ3_MAIN_SPEC is None or RQ3_MAIN_SPEC.loader is None:
    raise RuntimeError(f"Failed to load RQ3 main module from {RQ3_MAIN_PATH}")
RQ3_MAIN = module_from_spec(RQ3_MAIN_SPEC)
sys.modules[RQ3_MAIN_SPEC.name] = RQ3_MAIN
RQ3_MAIN_SPEC.loader.exec_module(RQ3_MAIN)

MAX_PROFIT_RATE = RQ3_MAIN.MAX_PROFIT_RATE
MIN_PROFIT_RATE = RQ3_MAIN.MIN_PROFIT_RATE
SERVICE_LEVEL_SCENARIOS = RQ3_MAIN.SERVICE_LEVEL_SCENARIOS
build_rq3_inputs_for_budget_scenario = RQ3_MAIN.build_rq3_inputs_for_budget_scenario
evaluate_price_profile = RQ3_MAIN.evaluate_price_profile
generate_station_service_level_candidates_expanded = RQ3_MAIN.generate_station_service_level_candidates_expanded
parse_price_vector_text = RQ3_MAIN.parse_price_vector_text
service_level_price_profile = RQ3_MAIN.service_level_price_profile


def station_direction(profit_rate: float) -> str:
    if profit_rate < MIN_PROFIT_RATE - 1e-9:
        return "raise_revenue_or_cut_cost"
    if profit_rate > MAX_PROFIT_RATE + 1e-9:
        return "lower_price_or_expand_public_service_mix"
    return "within_band"


def build_profile_from_station_rows(rows_by_station: dict[str, dict[str, object]]) -> dict[str, dict[str, float]]:
    station_names = sorted(rows_by_station)
    return service_level_price_profile(
        station_names=station_names,
        service_prices_by_station={
            station_name: parse_price_vector_text(str(rows_by_station[station_name]["selected_prices_by_service"]))
            for station_name in station_names
        },
    )


def closest_rows_per_station(kept_by_station: dict[str, list[dict[str, object]]]) -> dict[str, dict[str, object]]:
    selected = {}
    for station_name, rows in kept_by_station.items():
        selected[station_name] = sorted(
            rows,
            key=lambda row: (
                abs(float(row["profit_rate"]) - 0.0)
                if float(row["profit_rate"]) < 0.0
                else abs(float(row["profit_rate"]) - 0.08),
                float(row["break_even_gap"]),
                float(row["over_8pct_excess"]),
                -float(row["station_average_service_satisfaction"]),
            ),
        )[0]
    return selected


def station_diagnostic_rows(
    scenario: str,
    search_label: str,
    evaluation,
) -> list[dict[str, object]]:
    rows = []
    for station_row in evaluation.station_financials:
        profit_rate = float(station_row["profit_rate"])
        rows.append(
            {
                "scenario": scenario,
                "search_label": search_label,
                "station": station_row["station_community"],
                "scale": station_row["scale"],
                "selected_prices_by_service": json.dumps(
                    evaluation.station_prices[station_row["station_community"]],
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                "annual_service_revenue": round(float(station_row["annual_service_revenue"]), 2),
                "annual_government_subsidy": round(float(station_row["annual_government_subsidy"]), 2),
                "annual_direct_cost": round(float(station_row["annual_direct_cost"]), 2),
                "annual_fixed_cost": round(float(station_row["annual_fixed_cost"]), 2),
                "annual_depreciation": round(float(station_row["annual_depreciation"]), 2),
                "annual_total_cost": round(float(station_row["annual_total_cost"]), 2),
                "annual_net_profit": round(float(station_row["annual_net_profit"]), 2),
                "profit_rate": round(profit_rate, 6),
                "profit_compliant": int(station_row["profit_compliant"]),
                "break_even_gap": round(max(0.0, -float(station_row["annual_net_profit"])), 2),
                "over_8pct_excess": round(max(0.0, profit_rate - MAX_PROFIT_RATE), 6),
                "binding_direction": station_direction(profit_rate),
            }
        )
    return rows


def write_notes(rows: list[dict[str, object]], summary_rows: list[dict[str, object]]) -> None:
    lines = [
        "# RQ3 Joint Feasibility Diagnostics",
        "",
        "本扩展不改变问题3主模型，只将“联合可行性”失败拆解到逐站利润率边界上。",
        "",
        "## Interpretation Rules",
        "",
        "- `profit_rate < 0`：该站点在当前承接结构下无法保本，需提高相关收费服务收入或降低固定/直接成本压力。",
        "- `profit_rate > 0.08`：该站点超过“微利”上界，需降价、提高公益承接占比，或通过布局调整分担需求。",
        "- `joint feasible` 只能在所有站点都满足 `0 <= profit_rate <= 0.08` 且全局固定点收敛时成立。",
        "",
    ]
    for summary in summary_rows:
        lines.append(f"## {summary['scenario']} / {summary['search_label']}")
        lines.append(f"- converged = {summary['converged']}")
        lines.append(f"- average_service_access_performance = {summary['average_service_access_performance']}")
        lines.append(f"- minimum_service_access_performance = {summary['minimum_service_access_performance']}")
        lines.append(f"- joint_feasible = {summary['joint_feasible']}")
        scenario_rows = [row for row in rows if row["scenario"] == summary["scenario"] and row["search_label"] == summary["search_label"]]
        failing = [row for row in scenario_rows if int(row["profit_compliant"]) == 0]
        if failing:
            lines.append("- 卡点站点：")
            for row in failing:
                lines.append(
                    f"  - {row['station']} ({row['scale']}): profit_rate={row['profit_rate']}, "
                    f"break_even_gap={row['break_even_gap']}, over_8pct_excess={row['over_8pct_excess']}, "
                    f"direction={row['binding_direction']}"
                )
        else:
            lines.append("- 所有站点逐站利润率均已进入约束区间。")
        lines.append("")
    (OUTPUT_DIR / "3_4_joint_feasibility_notes.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    summary_rows = []
    station_rows = []
    for scenario in SERVICE_LEVEL_SCENARIOS:
        budget_limit = 120.0 if scenario == "S0" else 140.0
        inputs = load_rq3_inputs() if scenario == "S0" else build_rq3_inputs_for_budget_scenario(scenario, budget_limit)
        _candidate_rows, kept_by_station = generate_station_service_level_candidates_expanded(
            inputs=inputs,
            scenario_code=scenario,
            price_grid_level="full",
            max_candidates_per_station=30,
            keep_near_boundary=True,
        )
        closest_profile = build_profile_from_station_rows(closest_rows_per_station(kept_by_station))
        closest_eval = evaluate_price_profile(inputs, closest_profile)
        summary_rows.append(
            {
                "scenario": scenario,
                "search_label": "station_boundary_proxy",
                "converged": int(closest_eval.converged),
                "average_service_access_performance": round(float(closest_eval.average_service_access_performance), 6),
                "minimum_service_access_performance": round(float(closest_eval.minimum_service_access_performance), 6),
                "annual_government_subsidy": round(float(closest_eval.annual_government_subsidy), 2),
                "annual_net_profit": round(float(closest_eval.annual_net_profit), 2),
                "joint_feasible": int(
                    closest_eval.converged == 1 and all(int(row["profit_compliant"]) == 1 for row in closest_eval.station_financials)
                ),
            }
        )
        station_rows.extend(station_diagnostic_rows(scenario, "station_boundary_proxy", closest_eval))

    write_csv(OUTPUT_DIR / "3_4_joint_feasibility_summary.csv", summary_rows)
    write_csv(OUTPUT_DIR / "3_4_joint_feasibility_by_station.csv", station_rows)
    write_notes(station_rows, summary_rows)
    print("Saved Solutions/RQ3/outputs/3_4_joint_feasibility_summary.csv")
    print("Saved Solutions/RQ3/outputs/3_4_joint_feasibility_by_station.csv")
    print("Saved Solutions/RQ3/outputs/3_4_joint_feasibility_notes.md")


if __name__ == "__main__":
    main()
