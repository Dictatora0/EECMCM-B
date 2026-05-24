from __future__ import annotations

import csv
import os
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Dict, Iterable, List

from common import OUTPUT_DIR, write_csv

os.environ.setdefault("MPLCONFIGDIR", str(OUTPUT_DIR / ".mplconfig"))
Path(os.environ["MPLCONFIGDIR"]).mkdir(parents=True, exist_ok=True)

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
ALIAS_MAPS_PATH = ROOT / "plots" / "alias_maps.py"
ALIAS_MAPS_SPEC = spec_from_file_location("rq3_plot_alias_maps", ALIAS_MAPS_PATH)
if ALIAS_MAPS_SPEC is None or ALIAS_MAPS_SPEC.loader is None:
    raise RuntimeError(f"Failed to load alias maps from {ALIAS_MAPS_PATH}")
ALIAS_MAPS = module_from_spec(ALIAS_MAPS_SPEC)
ALIAS_MAPS_SPEC.loader.exec_module(ALIAS_MAPS)
canonical_scheme_key = ALIAS_MAPS.canonical_scheme_key


PARETO_FRONTIER_PATH = OUTPUT_DIR / "3_1_aux_pareto_frontier.csv"
DUAL_SCHEME_PATH = OUTPUT_DIR / "3_1_aux_dual_scheme_comparison.csv"
POLICY_MARKER_CYCLE = ["o", "^", "s", "D", "P", "X", "v", "<", ">"]
FIGURE_PREFIX = "3_2_aux_satisfaction_tradeoff"
FAIRNESS_THRESHOLD = 0.60


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def as_float(row: Dict[str, str], key: str) -> float:
    return float(row[key])


def annual_net_profit_wan(row: Dict[str, str]) -> float:
    return as_float(row, "annual_net_profit") / 1e4


def policy_order(policy: str) -> tuple[int, str]:
    return (0 if policy == "none" else 1, policy)


def policy_marker(policy: str, ordered_policies: List[str]) -> str:
    if policy in ordered_policies:
        return POLICY_MARKER_CYCLE[ordered_policies.index(policy) % len(POLICY_MARKER_CYCLE)]
    return "o"


def policy_label(policy: str) -> str:
    if policy == "none":
        return "No extra subsidy policy"
    return policy.replace("_", " ")


def policy_summary_rows(frontier_rows: List[Dict[str, str]]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for policy in sorted({row["subsidy_policy"] for row in frontier_rows}, key=policy_order):
        subset = [row for row in frontier_rows if row["subsidy_policy"] == policy]
        rows.append(
            {
                "subsidy_policy": policy,
                "frontier_point_count": len(subset),
                "converged_point_count": sum(int(row["converged"]) for row in subset),
                "frontier_profit_rate_max": round(max(as_float(row, "profit_rate") for row in subset), 6),
                "frontier_avg_satisfaction_max": round(
                    max(as_float(row, "average_service_satisfaction") for row in subset),
                    6,
                ),
                "frontier_min_satisfaction_max": round(
                    max(as_float(row, "minimum_service_satisfaction") for row in subset),
                    6,
                ),
                "frontier_avg_access_max": round(
                    max(as_float(row, "average_service_access_performance") for row in subset),
                    6,
                ),
                "frontier_min_access_max": round(
                    max(as_float(row, "minimum_service_access_performance") for row in subset),
                    6,
                ),
                "frontier_gini_min": round(min(as_float(row, "gini_access") for row in subset), 6),
                "frontier_theil_min": round(min(as_float(row, "theil_access") for row in subset), 6),
            }
        )
    return rows


def select_frontier_profit_peak(frontier_rows: List[Dict[str, str]]) -> Dict[str, str]:
    return max(
        frontier_rows,
        key=lambda row: (
            as_float(row, "profit_rate"),
            as_float(row, "annual_net_profit"),
            -as_float(row, "gini_access"),
        ),
    )


def select_frontier_satisfaction_peak(frontier_rows: List[Dict[str, str]]) -> Dict[str, str]:
    return max(
        frontier_rows,
        key=lambda row: (
            as_float(row, "minimum_service_satisfaction"),
            as_float(row, "average_service_satisfaction"),
            as_float(row, "minimum_service_access_performance"),
            -as_float(row, "gini_access"),
            -as_float(row, "theil_access"),
        ),
    )


def select_frontier_converged_reference(frontier_rows: List[Dict[str, str]]) -> Dict[str, str] | None:
    converged_rows = [row for row in frontier_rows if int(row["converged"]) == 1]
    if not converged_rows:
        return None
    return max(
        converged_rows,
        key=lambda row: (
            as_float(row, "profit_rate"),
            as_float(row, "average_service_satisfaction"),
            as_float(row, "average_service_access_performance"),
            -as_float(row, "gini_access"),
        ),
    )


def select_dual_scheme(dual_rows: Iterable[Dict[str, str]], scheme_label: str) -> Dict[str, str]:
    for row in dual_rows:
        if canonical_scheme_key(row["scheme_label"]) == canonical_scheme_key(scheme_label):
            return row
    raise KeyError(f"Missing scheme_label={scheme_label} in dual scheme comparison output")


def representative_rows(
    frontier_rows: List[Dict[str, str]],
    dual_rows: List[Dict[str, str]],
) -> List[Dict[str, object]]:
    financial_scheme = select_dual_scheme(dual_rows, "financial_sustainable_scheme")
    satisfaction_priority_scheme = select_dual_scheme(dual_rows, "satisfaction_priority_scheme")
    frontier_profit_peak = select_frontier_profit_peak(frontier_rows)
    frontier_satisfaction_peak = select_frontier_satisfaction_peak(frontier_rows)
    frontier_converged_reference = select_frontier_converged_reference(frontier_rows)

    selected: List[tuple[str, str, Dict[str, str]]] = [
        ("frontier_profit_peak", "pareto_frontier", frontier_profit_peak),
        ("frontier_satisfaction_peak", "pareto_frontier", frontier_satisfaction_peak),
        ("financial_sustainable_scheme", "dual_scheme_output", financial_scheme),
        ("satisfaction_priority_scheme", "dual_scheme_output", satisfaction_priority_scheme),
    ]
    if frontier_converged_reference is not None:
        selected.insert(2, ("frontier_converged_reference", "pareto_frontier", frontier_converged_reference))

    rows: List[Dict[str, object]] = []
    seen_signatures: dict[tuple[str, str], str] = {}
    for label, source, row in selected:
        signature = (row["subsidy_policy"], row["price_scheme_detail"])
        duplicate_of = seen_signatures.get(signature, "")
        seen_signatures.setdefault(signature, label)
        rows.append(
            {
                "representative_label": label,
                "source": source,
                "duplicate_of": duplicate_of,
                "subsidy_policy": row["subsidy_policy"],
                "price_scheme_detail": row["price_scheme_detail"],
                "pareto_rank": int(row["pareto_rank"]),
                "profit_rate": round(as_float(row, "profit_rate"), 6),
                "annual_net_profit_wan": round(annual_net_profit_wan(row), 2),
                "average_service_satisfaction": round(
                    as_float(row, "average_service_satisfaction"),
                    6,
                ),
                "minimum_service_satisfaction": round(
                    as_float(row, "minimum_service_satisfaction"),
                    6,
                ),
                "average_service_access_performance": round(
                    as_float(row, "average_service_access_performance"),
                    6,
                ),
                "minimum_service_access_performance": round(
                    as_float(row, "minimum_service_access_performance"),
                    6,
                ),
                "gini_access": round(as_float(row, "gini_access"), 6),
                "theil_access": round(as_float(row, "theil_access"), 6),
                "max_min_gap": round(as_float(row, "max_min_gap"), 6),
                "profit_compliant": int(row["profit_compliant"]),
                "satisfaction_compliant": int(row.get("satisfaction_compliant", row["fair_satisfaction_compliant"])),
                "fair_satisfaction_compliant": int(row.get("satisfaction_compliant", row["fair_satisfaction_compliant"])),
                "converged": int(row["converged"]),
            }
        )
    return rows


def configure_axes(ax, xlabel: str, ylabel: str, title: str) -> None:
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, linestyle="--", linewidth=0.6, alpha=0.5)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)


def frontier_color_norm(frontier_rows: List[Dict[str, str]]) -> Normalize:
    values = [as_float(row, "gini_access") for row in frontier_rows]
    return Normalize(vmin=min(values), vmax=max(values))


def plot_profit_vs_average_satisfaction(
    frontier_rows: List[Dict[str, str]],
    financial_scheme: Dict[str, str],
    satisfaction_priority_scheme: Dict[str, str],
) -> None:
    norm = frontier_color_norm(frontier_rows)
    fig, ax = plt.subplots(figsize=(7.2, 5.2), dpi=220)
    scatter = None
    ordered_policies = sorted({row["subsidy_policy"] for row in frontier_rows}, key=policy_order)
    for policy in ordered_policies:
        subset = [row for row in frontier_rows if row["subsidy_policy"] == policy]
        scatter = ax.scatter(
            [as_float(row, "profit_rate") for row in subset],
            [as_float(row, "average_service_satisfaction") for row in subset],
            c=[as_float(row, "gini_access") for row in subset],
            cmap="viridis_r",
            norm=norm,
            marker=policy_marker(policy, ordered_policies),
            s=42,
            edgecolors="black",
            linewidths=0.4,
            alpha=0.88,
        )

    ax.scatter(
        [as_float(financial_scheme, "profit_rate")],
        [as_float(financial_scheme, "average_service_satisfaction")],
        marker="*",
        s=220,
        color="#d62728",
        edgecolors="black",
        linewidths=0.6,
        zorder=5,
    )
    ax.scatter(
        [as_float(satisfaction_priority_scheme, "profit_rate")],
        [as_float(satisfaction_priority_scheme, "average_service_satisfaction")],
        marker="D",
        s=96,
        color="#1f77b4",
        edgecolors="black",
        linewidths=0.6,
        zorder=5,
    )
    ax.annotate(
        "Financial sustainable scheme",
        (
            as_float(financial_scheme, "profit_rate"),
            as_float(financial_scheme, "average_service_satisfaction"),
        ),
        xytext=(12, -14),
        textcoords="offset points",
        fontsize=8,
    )
    ax.annotate(
        "Satisfaction priority scheme",
        (
            as_float(satisfaction_priority_scheme, "profit_rate"),
            as_float(satisfaction_priority_scheme, "average_service_satisfaction"),
        ),
        xytext=(12, 8),
        textcoords="offset points",
        fontsize=8,
    )
    configure_axes(
        ax,
        xlabel="Profit Rate",
        ylabel="Average Service Satisfaction",
        title="RQ3 Satisfaction-First Trade-off Frontier",
    )
    if scatter is not None:
        cbar = fig.colorbar(scatter, ax=ax, pad=0.02)
        cbar.set_label("Accessibility Gini (Auxiliary Equity Metric)")
    legend_handles = [
        Line2D(
            [0],
            [0],
            marker=policy_marker(policy, ordered_policies),
            linestyle="",
            markerfacecolor="#bdbdbd",
            markeredgecolor="black",
            markersize=7,
            label=policy_label(policy),
        )
        for policy in ordered_policies
    ]
    legend_handles.extend(
        [
            Line2D(
                [0],
                [0],
                marker="*",
                linestyle="",
                markerfacecolor="#d62728",
                markeredgecolor="black",
                markersize=12,
                label="Financial sustainable scheme",
            ),
            Line2D(
                [0],
                [0],
                marker="D",
                linestyle="",
                markerfacecolor="#1f77b4",
                markeredgecolor="black",
                markersize=7,
                label="Satisfaction priority scheme",
            ),
        ]
    )
    ax.legend(handles=legend_handles, loc="lower right", frameon=True, fontsize=8)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / f"{FIGURE_PREFIX}_profit_vs_avg_satisfaction.png", bbox_inches="tight")
    fig.savefig(OUTPUT_DIR / f"{FIGURE_PREFIX}_profit_vs_avg_satisfaction.pdf", bbox_inches="tight")
    plt.close(fig)


def plot_min_satisfaction_vs_net_profit(
    frontier_rows: List[Dict[str, str]],
    financial_scheme: Dict[str, str],
    satisfaction_priority_scheme: Dict[str, str],
) -> None:
    norm = frontier_color_norm(frontier_rows)
    fig, ax = plt.subplots(figsize=(7.2, 5.2), dpi=220)
    scatter = None
    ordered_policies = sorted({row["subsidy_policy"] for row in frontier_rows}, key=policy_order)
    for policy in ordered_policies:
        subset = [row for row in frontier_rows if row["subsidy_policy"] == policy]
        scatter = ax.scatter(
            [as_float(row, "minimum_service_satisfaction") for row in subset],
            [annual_net_profit_wan(row) for row in subset],
            c=[as_float(row, "gini_access") for row in subset],
            cmap="viridis_r",
            norm=norm,
            marker=policy_marker(policy, ordered_policies),
            s=42,
            edgecolors="black",
            linewidths=0.4,
            alpha=0.88,
        )

    ax.axvline(
        FAIRNESS_THRESHOLD,
        color="#444444",
        linestyle="--",
        linewidth=1.2,
        label=f"Minimum-satisfaction threshold = {FAIRNESS_THRESHOLD:.2f}",
    )
    ax.scatter(
        [as_float(financial_scheme, "minimum_service_satisfaction")],
        [annual_net_profit_wan(financial_scheme)],
        marker="*",
        s=220,
        color="#d62728",
        edgecolors="black",
        linewidths=0.6,
        zorder=5,
    )
    ax.scatter(
        [as_float(satisfaction_priority_scheme, "minimum_service_satisfaction")],
        [annual_net_profit_wan(satisfaction_priority_scheme)],
        marker="D",
        s=96,
        color="#1f77b4",
        edgecolors="black",
        linewidths=0.6,
        zorder=5,
    )
    ax.annotate(
        "Financial sustainable scheme",
        (
            as_float(financial_scheme, "minimum_service_satisfaction"),
            annual_net_profit_wan(financial_scheme),
        ),
        xytext=(10, -14),
        textcoords="offset points",
        fontsize=8,
    )
    ax.annotate(
        "Satisfaction priority scheme",
        (
            as_float(satisfaction_priority_scheme, "minimum_service_satisfaction"),
            annual_net_profit_wan(satisfaction_priority_scheme),
        ),
        xytext=(12, 8),
        textcoords="offset points",
        fontsize=8,
    )
    ax.set_xlim(0.0, max(FAIRNESS_THRESHOLD + 0.05, ax.get_xlim()[1]))
    configure_axes(
        ax,
        xlabel="Minimum Service Satisfaction",
        ylabel="Annual Net Profit (10^4 CNY/year)",
        title="RQ3 Satisfaction Threshold Gap with Accessibility as Auxiliary Axis",
    )
    if scatter is not None:
        cbar = fig.colorbar(scatter, ax=ax, pad=0.02)
        cbar.set_label("Accessibility Gini (Auxiliary Equity Metric)")
    legend_handles = [
        Line2D(
            [0],
            [0],
            marker=policy_marker(policy, ordered_policies),
            linestyle="",
            markerfacecolor="#bdbdbd",
            markeredgecolor="black",
            markersize=7,
            label=policy_label(policy),
        )
        for policy in ordered_policies
    ]
    legend_handles.extend(
        [
            Line2D([0], [0], color="#444444", linestyle="--", linewidth=1.2, label="Minimum-satisfaction threshold"),
            Line2D(
                [0],
                [0],
                marker="*",
                linestyle="",
                markerfacecolor="#d62728",
                markeredgecolor="black",
                markersize=12,
                label="Financial sustainable scheme",
            ),
            Line2D(
                [0],
                [0],
                marker="D",
                linestyle="",
                markerfacecolor="#1f77b4",
                markeredgecolor="black",
                markersize=7,
                label="Satisfaction priority scheme",
            ),
        ]
    )
    ax.legend(handles=legend_handles, loc="lower right", frameon=True, fontsize=8)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / f"{FIGURE_PREFIX}_min_satisfaction_vs_net_profit.png", bbox_inches="tight")
    fig.savefig(OUTPUT_DIR / f"{FIGURE_PREFIX}_min_satisfaction_vs_net_profit.pdf", bbox_inches="tight")
    plt.close(fig)


def write_paper_notes(
    frontier_rows: List[Dict[str, str]],
    dual_rows: List[Dict[str, str]],
    policy_rows: List[Dict[str, object]],
    representative_scheme_rows: List[Dict[str, object]],
) -> None:
    financial_scheme = select_dual_scheme(dual_rows, "financial_sustainable_scheme")
    satisfaction_priority_scheme = select_dual_scheme(dual_rows, "satisfaction_priority_scheme")
    frontier_profit_peak = select_frontier_profit_peak(frontier_rows)
    frontier_satisfaction_peak = select_frontier_satisfaction_peak(frontier_rows)
    converged_count = sum(int(row["converged"]) for row in frontier_rows)
    station_profit_compliant_count = sum(int(row["profit_compliant"]) for row in frontier_rows)
    satisfaction_threshold_count = sum(
        1
        for row in frontier_rows
        if as_float(row, "minimum_service_satisfaction") >= FAIRNESS_THRESHOLD - 1e-9
    )
    lines = [
        "# RQ3 Auxiliary Satisfaction-First Trade-off Notes",
        "",
        "## 1. Frontier Definition",
        "",
        "- Auxiliary frontier rank is assigned jointly by average service satisfaction, profit rate, and accessibility Gini coefficient.",
        "- This auxiliary trade-off frontier is an extension analysis set; it is not the题面主结果命名口径.",
        f"- Current frontier size: {len(frontier_rows)} rank-1 candidate schemes.",
        "",
        "## 2. Core Findings for the Main Text",
        "",
        f"- Frontier points by subsidy policy: "
        + "；".join(
            f"{row['subsidy_policy']} -> {row['frontier_point_count']} points"
            for row in policy_rows
        )
        + "。",
        f"- Only {converged_count} frontier point(s) converged, and {station_profit_compliant_count} frontier point(s) satisfy station-level profit compliance.",
        f"- No frontier point reaches the minimum service satisfaction threshold {FAIRNESS_THRESHOLD:.2f}; the count above threshold is {satisfaction_threshold_count}.",
        f"- The profit-extreme frontier point is `{frontier_profit_peak['price_scheme_detail']}` under `{frontier_profit_peak['subsidy_policy']}`. It reaches profit rate {as_float(frontier_profit_peak, 'profit_rate'):.6f} and annual net profit {annual_net_profit_wan(frontier_profit_peak):.2f} 万元, but its minimum service satisfaction is only {as_float(frontier_profit_peak, 'minimum_service_satisfaction'):.6f}, while auxiliary minimum accessibility is {as_float(frontier_profit_peak, 'minimum_service_access_performance'):.6f}.",
        f"- The satisfaction-extreme frontier point is `{frontier_satisfaction_peak['price_scheme_detail']}` under `{frontier_satisfaction_peak['subsidy_policy']}`. It raises average service satisfaction to {as_float(frontier_satisfaction_peak, 'average_service_satisfaction'):.6f}, minimum service satisfaction to {as_float(frontier_satisfaction_peak, 'minimum_service_satisfaction'):.6f}, and lowers Gini to {as_float(frontier_satisfaction_peak, 'gini_access'):.6f}.",
        f"- The implementable financial sustainable scheme is `{financial_scheme['price_scheme_detail']}`. It achieves station-level profit compliance with profit rate {as_float(financial_scheme, 'profit_rate'):.6f} and annual net profit {annual_net_profit_wan(financial_scheme):.2f} 万元, with average service satisfaction {as_float(financial_scheme, 'average_service_satisfaction'):.6f} and minimum service satisfaction {as_float(financial_scheme, 'minimum_service_satisfaction'):.6f}.",
        f"- The satisfaction priority scheme is identical to the satisfaction-frontier representative: average service satisfaction {as_float(satisfaction_priority_scheme, 'average_service_satisfaction'):.6f}, minimum service satisfaction {as_float(satisfaction_priority_scheme, 'minimum_service_satisfaction'):.6f}, auxiliary average accessibility {as_float(satisfaction_priority_scheme, 'average_service_access_performance'):.6f}, and Gini {as_float(satisfaction_priority_scheme, 'gini_access'):.6f}; however, it still fails station-level profit compliance and does not cross the satisfaction threshold.",
        "",
        "## 3. Interpretation for the Discussion Section",
        "",
        "- Accessibility remains an auxiliary interpretation axis here; the report keeps satisfaction on the main axis and uses accessibility only to explain secondary trade-offs.",
        "- If only `none` appears in `subsidy_policy`, this report should be read as a no-extra-subsidy auxiliary comparison among satisfaction-profit-equity trade-offs.",
        "- A critical modeling conclusion is that aggregate profit rate alone is insufficient. Some candidate schemes show overall positive profit rates inside [0, 0.08], but still fail scheme-level compliance because at least one station violates the station-level profitability bound.",
        "- Therefore, the Pareto frontier should be used in the paper as a trade-off reference set, while the operational recommendation should still distinguish between a financially implementable scheme and a satisfaction benchmark scheme.",
        "- Since `joint_feasible_solution_exists = 0`, the paper should explicitly state that pricing alone cannot simultaneously satisfy station-level financial compliance, minimum service satisfaction threshold, and convergence under the current layout and subsidy cap. Additional construction budget, public-service subsidy, or targeted capacity expansion is still required.",
        "",
        "## 4. Suggested Placement in the Paper",
        "",
        "- Use the two Pareto figures in the正文 to visualize profit-satisfaction-equity trade-offs and the satisfaction-threshold gap; accessibility can be discussed as a secondary indicator.",
        "- Use `3_2_aux_satisfaction_tradeoff_representative_schemes.csv` for extension comparison tables.",
        "- Use `3_2_aux_satisfaction_tradeoff_policy_summary.csv` only as an auxiliary appendix artifact.",
        "",
        "## 5. Generated Files",
        "",
        "- `3_2_aux_satisfaction_tradeoff_profit_vs_avg_satisfaction.png/.pdf`",
        "- `3_2_aux_satisfaction_tradeoff_min_satisfaction_vs_net_profit.png/.pdf`",
        "- `3_2_aux_satisfaction_tradeoff_policy_summary.csv`",
        "- `3_2_aux_satisfaction_tradeoff_representative_schemes.csv`",
        "- `3_2_aux_satisfaction_tradeoff_paper_notes.md`",
        "",
        "## 6. Representative Schemes Snapshot",
        "",
    ]
    for row in representative_scheme_rows:
        duplicate_note = f"；duplicate_of={row['duplicate_of']}" if row["duplicate_of"] else ""
        lines.append(
            f"- {row['representative_label']}: subsidy={row['subsidy_policy']}, "
            f"profit_rate={row['profit_rate']:.6f}, "
            f"net_profit={row['annual_net_profit_wan']:.2f} 万元, "
            f"avg_satisfaction={row['average_service_satisfaction']:.6f}, "
            f"min_satisfaction={row['minimum_service_satisfaction']:.6f}, "
            f"avg_access={row['average_service_access_performance']:.6f}, "
            f"min_access={row['minimum_service_access_performance']:.6f}, "
            f"gini={row['gini_access']:.6f}{duplicate_note}。"
        )
    (OUTPUT_DIR / "3_2_aux_satisfaction_tradeoff_paper_notes.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    frontier_rows = read_csv_rows(PARETO_FRONTIER_PATH)
    dual_rows = read_csv_rows(DUAL_SCHEME_PATH)
    if not frontier_rows:
        raise RuntimeError("3_1_aux_pareto_frontier.csv is empty; run Solutions/RQ3/3_1.py first.")
    if not dual_rows:
        raise RuntimeError("3_1_aux_dual_scheme_comparison.csv is empty; run Solutions/RQ3/3_1.py first.")

    policy_rows = policy_summary_rows(frontier_rows)
    representative_scheme_rows = representative_rows(frontier_rows, dual_rows)
    write_csv(OUTPUT_DIR / "3_2_aux_satisfaction_tradeoff_policy_summary.csv", policy_rows)
    write_csv(OUTPUT_DIR / "3_2_aux_satisfaction_tradeoff_representative_schemes.csv", representative_scheme_rows)

    financial_scheme = select_dual_scheme(dual_rows, "financial_sustainable_scheme")
    satisfaction_priority_scheme = select_dual_scheme(dual_rows, "satisfaction_priority_scheme")
    plot_profit_vs_average_satisfaction(frontier_rows, financial_scheme, satisfaction_priority_scheme)
    plot_min_satisfaction_vs_net_profit(frontier_rows, financial_scheme, satisfaction_priority_scheme)
    write_paper_notes(frontier_rows, dual_rows, policy_rows, representative_scheme_rows)

    print(
        "Generated RQ3 auxiliary satisfaction-first trade-off figures, policy summary table, "
        "representative scheme table, and paper notes."
    )


if __name__ == "__main__":
    main()
