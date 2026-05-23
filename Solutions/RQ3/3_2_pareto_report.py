from __future__ import annotations

import csv
import os
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


PARETO_FRONTIER_PATH = OUTPUT_DIR / "3_1_pareto_frontier.csv"
DUAL_SCHEME_PATH = OUTPUT_DIR / "3_1_dual_scheme_comparison.csv"
POLICY_MARKERS = {
    "targeted_subsidy_0.0": "o",
    "targeted_subsidy_1.0": "^",
    "targeted_subsidy_2.0": "s",
}
POLICY_LABELS = {
    "targeted_subsidy_0.0": "Targeted subsidy = 0.0 CNY/order",
    "targeted_subsidy_1.0": "Targeted subsidy = 1.0 CNY/order",
    "targeted_subsidy_2.0": "Targeted subsidy = 2.0 CNY/order",
}
FIGURE_PREFIX = "3_2_pareto"
FAIRNESS_THRESHOLD = 0.60


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def as_float(row: Dict[str, str], key: str) -> float:
    return float(row[key])


def annual_net_profit_wan(row: Dict[str, str]) -> float:
    return as_float(row, "annual_net_profit") / 1e4


def policy_order(policy: str) -> tuple[int, str]:
    ordered = list(POLICY_MARKERS)
    return (ordered.index(policy), policy) if policy in ordered else (len(ordered), policy)


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


def select_frontier_fairness_peak(frontier_rows: List[Dict[str, str]]) -> Dict[str, str]:
    return max(
        frontier_rows,
        key=lambda row: (
            as_float(row, "minimum_service_access_performance"),
            as_float(row, "average_service_access_performance"),
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
            as_float(row, "average_service_access_performance"),
            -as_float(row, "gini_access"),
        ),
    )


def select_dual_scheme(dual_rows: Iterable[Dict[str, str]], scheme_label: str) -> Dict[str, str]:
    for row in dual_rows:
        if row["scheme_label"] == scheme_label:
            return row
    raise KeyError(f"Missing scheme_label={scheme_label} in dual scheme comparison output")


def representative_rows(
    frontier_rows: List[Dict[str, str]],
    dual_rows: List[Dict[str, str]],
) -> List[Dict[str, object]]:
    financial_scheme = select_dual_scheme(dual_rows, "financial_sustainable_scheme")
    fairness_scheme = select_dual_scheme(dual_rows, "fairness_priority_scheme")
    frontier_profit_peak = select_frontier_profit_peak(frontier_rows)
    frontier_fairness_peak = select_frontier_fairness_peak(frontier_rows)
    frontier_converged_reference = select_frontier_converged_reference(frontier_rows)

    selected: List[tuple[str, str, Dict[str, str]]] = [
        ("frontier_profit_peak", "pareto_frontier", frontier_profit_peak),
        ("frontier_fairness_peak", "pareto_frontier", frontier_fairness_peak),
        ("financial_sustainable_scheme", "dual_scheme_output", financial_scheme),
        ("fairness_priority_scheme", "dual_scheme_output", fairness_scheme),
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
                "fair_satisfaction_compliant": int(row["fair_satisfaction_compliant"]),
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


def plot_profit_vs_average_access(
    frontier_rows: List[Dict[str, str]],
    financial_scheme: Dict[str, str],
    fairness_scheme: Dict[str, str],
) -> None:
    norm = frontier_color_norm(frontier_rows)
    fig, ax = plt.subplots(figsize=(7.2, 5.2), dpi=220)
    scatter = None
    for policy in sorted({row["subsidy_policy"] for row in frontier_rows}, key=policy_order):
        subset = [row for row in frontier_rows if row["subsidy_policy"] == policy]
        scatter = ax.scatter(
            [as_float(row, "profit_rate") for row in subset],
            [as_float(row, "average_service_access_performance") for row in subset],
            c=[as_float(row, "gini_access") for row in subset],
            cmap="viridis_r",
            norm=norm,
            marker=POLICY_MARKERS.get(policy, "o"),
            s=42,
            edgecolors="black",
            linewidths=0.4,
            alpha=0.88,
        )

    ax.scatter(
        [as_float(financial_scheme, "profit_rate")],
        [as_float(financial_scheme, "average_service_access_performance")],
        marker="*",
        s=220,
        color="#d62728",
        edgecolors="black",
        linewidths=0.6,
        zorder=5,
    )
    ax.scatter(
        [as_float(fairness_scheme, "profit_rate")],
        [as_float(fairness_scheme, "average_service_access_performance")],
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
            as_float(financial_scheme, "average_service_access_performance"),
        ),
        xytext=(12, -14),
        textcoords="offset points",
        fontsize=8,
    )
    ax.annotate(
        "Fairness priority scheme",
        (
            as_float(fairness_scheme, "profit_rate"),
            as_float(fairness_scheme, "average_service_access_performance"),
        ),
        xytext=(12, 8),
        textcoords="offset points",
        fontsize=8,
    )
    configure_axes(
        ax,
        xlabel="Profit Rate",
        ylabel="Average Service Accessibility",
        title="RQ3 Pareto Frontier in Profit-Accessibility Space",
    )
    if scatter is not None:
        cbar = fig.colorbar(scatter, ax=ax, pad=0.02)
        cbar.set_label("Accessibility Gini")
    legend_handles = [
        Line2D(
            [0],
            [0],
            marker=POLICY_MARKERS[policy],
            linestyle="",
            markerfacecolor="#bdbdbd",
            markeredgecolor="black",
            markersize=7,
            label=POLICY_LABELS[policy],
        )
        for policy in POLICY_MARKERS
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
                label="Fairness priority scheme",
            ),
        ]
    )
    ax.legend(handles=legend_handles, loc="lower right", frameon=True, fontsize=8)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / f"{FIGURE_PREFIX}_profit_vs_avg_access.png", bbox_inches="tight")
    fig.savefig(OUTPUT_DIR / f"{FIGURE_PREFIX}_profit_vs_avg_access.pdf", bbox_inches="tight")
    plt.close(fig)


def plot_min_access_vs_net_profit(
    frontier_rows: List[Dict[str, str]],
    financial_scheme: Dict[str, str],
    fairness_scheme: Dict[str, str],
) -> None:
    norm = frontier_color_norm(frontier_rows)
    fig, ax = plt.subplots(figsize=(7.2, 5.2), dpi=220)
    scatter = None
    for policy in sorted({row["subsidy_policy"] for row in frontier_rows}, key=policy_order):
        subset = [row for row in frontier_rows if row["subsidy_policy"] == policy]
        scatter = ax.scatter(
            [as_float(row, "minimum_service_access_performance") for row in subset],
            [annual_net_profit_wan(row) for row in subset],
            c=[as_float(row, "gini_access") for row in subset],
            cmap="viridis_r",
            norm=norm,
            marker=POLICY_MARKERS.get(policy, "o"),
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
        label=f"Minimum-access threshold = {FAIRNESS_THRESHOLD:.2f}",
    )
    ax.scatter(
        [as_float(financial_scheme, "minimum_service_access_performance")],
        [annual_net_profit_wan(financial_scheme)],
        marker="*",
        s=220,
        color="#d62728",
        edgecolors="black",
        linewidths=0.6,
        zorder=5,
    )
    ax.scatter(
        [as_float(fairness_scheme, "minimum_service_access_performance")],
        [annual_net_profit_wan(fairness_scheme)],
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
            as_float(financial_scheme, "minimum_service_access_performance"),
            annual_net_profit_wan(financial_scheme),
        ),
        xytext=(10, -14),
        textcoords="offset points",
        fontsize=8,
    )
    ax.annotate(
        "Fairness priority scheme",
        (
            as_float(fairness_scheme, "minimum_service_access_performance"),
            annual_net_profit_wan(fairness_scheme),
        ),
        xytext=(12, 8),
        textcoords="offset points",
        fontsize=8,
    )
    ax.set_xlim(0.0, max(FAIRNESS_THRESHOLD + 0.05, ax.get_xlim()[1]))
    configure_axes(
        ax,
        xlabel="Minimum Service Accessibility",
        ylabel="Annual Net Profit (10^4 CNY/year)",
        title="RQ3 Fairness Threshold Gap on the Pareto Frontier",
    )
    if scatter is not None:
        cbar = fig.colorbar(scatter, ax=ax, pad=0.02)
        cbar.set_label("Accessibility Gini")
    legend_handles = [
        Line2D(
            [0],
            [0],
            marker=POLICY_MARKERS[policy],
            linestyle="",
            markerfacecolor="#bdbdbd",
            markeredgecolor="black",
            markersize=7,
            label=POLICY_LABELS[policy],
        )
        for policy in POLICY_MARKERS
    ]
    legend_handles.extend(
        [
            Line2D([0], [0], color="#444444", linestyle="--", linewidth=1.2, label="Minimum-access threshold"),
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
                label="Fairness priority scheme",
            ),
        ]
    )
    ax.legend(handles=legend_handles, loc="lower right", frameon=True, fontsize=8)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / f"{FIGURE_PREFIX}_min_access_vs_net_profit.png", bbox_inches="tight")
    fig.savefig(OUTPUT_DIR / f"{FIGURE_PREFIX}_min_access_vs_net_profit.pdf", bbox_inches="tight")
    plt.close(fig)


def write_paper_notes(
    frontier_rows: List[Dict[str, str]],
    dual_rows: List[Dict[str, str]],
    policy_rows: List[Dict[str, object]],
    representative_scheme_rows: List[Dict[str, object]],
) -> None:
    financial_scheme = select_dual_scheme(dual_rows, "financial_sustainable_scheme")
    fairness_scheme = select_dual_scheme(dual_rows, "fairness_priority_scheme")
    frontier_profit_peak = select_frontier_profit_peak(frontier_rows)
    frontier_fairness_peak = select_frontier_fairness_peak(frontier_rows)
    converged_count = sum(int(row["converged"]) for row in frontier_rows)
    station_profit_compliant_count = sum(int(row["profit_compliant"]) for row in frontier_rows)
    fairness_threshold_count = sum(
        1
        for row in frontier_rows
        if as_float(row, "minimum_service_access_performance") >= FAIRNESS_THRESHOLD - 1e-9
    )
    lines = [
        "# RQ3 Pareto Frontier Paper Notes",
        "",
        "## 1. Frontier Definition",
        "",
        "- Pareto rank is assigned jointly by three indicators: average service accessibility, profit rate, and accessibility Gini coefficient.",
        "- The Pareto frontier therefore represents the efficiency envelope of the tri-objective model, not the final implementable policy set.",
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
        f"- No frontier point reaches the minimum accessibility threshold {FAIRNESS_THRESHOLD:.2f}; the count above threshold is {fairness_threshold_count}.",
        f"- The profit-extreme frontier point is `{frontier_profit_peak['price_scheme_detail']}` under `{frontier_profit_peak['subsidy_policy']}`. It reaches profit rate {as_float(frontier_profit_peak, 'profit_rate'):.6f} and annual net profit {annual_net_profit_wan(frontier_profit_peak):.2f} 万元, but its minimum accessibility is only {as_float(frontier_profit_peak, 'minimum_service_access_performance'):.6f}, and Gini rises to {as_float(frontier_profit_peak, 'gini_access'):.6f}.",
        f"- The fairness-extreme frontier point is `{frontier_fairness_peak['price_scheme_detail']}` under `{frontier_fairness_peak['subsidy_policy']}`. It raises average accessibility to {as_float(frontier_fairness_peak, 'average_service_access_performance'):.6f}, minimum accessibility to {as_float(frontier_fairness_peak, 'minimum_service_access_performance'):.6f}, and lowers Gini to {as_float(frontier_fairness_peak, 'gini_access'):.6f}.",
        f"- The implementable financial sustainable scheme is `{financial_scheme['price_scheme_detail']}`. It achieves station-level profit compliance with profit rate {as_float(financial_scheme, 'profit_rate'):.6f} and annual net profit {annual_net_profit_wan(financial_scheme):.2f} 万元, but its minimum accessibility remains {as_float(financial_scheme, 'minimum_service_access_performance'):.6f}.",
        f"- The fairness priority scheme is identical to the fairness frontier representative: average accessibility {as_float(fairness_scheme, 'average_service_access_performance'):.6f}, minimum accessibility {as_float(fairness_scheme, 'minimum_service_access_performance'):.6f}, Gini {as_float(fairness_scheme, 'gini_access'):.6f}; however, it still fails station-level profit compliance and does not cross the fairness threshold.",
        "",
        "## 3. Interpretation for the Discussion Section",
        "",
        "- Raising targeted subsidy from 0.0 to 2.0 CNY/order shifts the frontier toward higher profit-rate upper bounds, but the best minimum accessibility on the frontier falls to 0, and inequality indicators worsen.",
        "- This means the current targeted subsidy rule is more effective at supporting premium pricing and revenue capture than at repairing the weakest communities' service accessibility.",
        "- A critical modeling conclusion is that aggregate profit rate alone is insufficient. Some candidate schemes show overall positive profit rates inside [0, 0.08], but still fail scheme-level compliance because at least one station violates the station-level profitability bound.",
        "- Therefore, the Pareto frontier should be used in the paper as a trade-off reference set, while the operational recommendation should still distinguish between a financially implementable scheme and a fairness benchmark scheme.",
        "- Since `joint_feasible_solution_exists = 0`, the paper should explicitly state that pricing alone cannot simultaneously satisfy station-level financial compliance, minimum accessibility threshold, and convergence under the current layout and subsidy cap. Additional construction budget, public-service subsidy, or targeted capacity expansion is still required.",
        "",
        "## 4. Suggested Placement in the Paper",
        "",
        "- Use the two Pareto figures in the正文 to visualize profit-accessibility-equity trade-offs and the fairness-threshold gap.",
        "- Use `3_2_pareto_representative_schemes.csv` for the正文 comparison table.",
        "- Use `3_2_pareto_policy_summary.csv` in the appendix to support the statement that higher subsidy shifts the frontier shape but does not eliminate the fairness bottleneck.",
        "",
        "## 5. Generated Files",
        "",
        "- `3_2_pareto_profit_vs_avg_access.png/.pdf`",
        "- `3_2_pareto_min_access_vs_net_profit.png/.pdf`",
        "- `3_2_pareto_policy_summary.csv`",
        "- `3_2_pareto_representative_schemes.csv`",
        "- `3_2_pareto_paper_notes.md`",
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
            f"avg_access={row['average_service_access_performance']:.6f}, "
            f"min_access={row['minimum_service_access_performance']:.6f}, "
            f"gini={row['gini_access']:.6f}{duplicate_note}。"
        )
    (OUTPUT_DIR / "3_2_pareto_paper_notes.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    frontier_rows = read_csv_rows(PARETO_FRONTIER_PATH)
    dual_rows = read_csv_rows(DUAL_SCHEME_PATH)
    if not frontier_rows:
        raise RuntimeError("3_1_pareto_frontier.csv is empty; run Solutions/RQ3/3_1.py first.")
    if not dual_rows:
        raise RuntimeError("3_1_dual_scheme_comparison.csv is empty; run Solutions/RQ3/3_1.py first.")

    policy_rows = policy_summary_rows(frontier_rows)
    representative_scheme_rows = representative_rows(frontier_rows, dual_rows)
    write_csv(OUTPUT_DIR / "3_2_pareto_policy_summary.csv", policy_rows)
    write_csv(OUTPUT_DIR / "3_2_pareto_representative_schemes.csv", representative_scheme_rows)

    financial_scheme = select_dual_scheme(dual_rows, "financial_sustainable_scheme")
    fairness_scheme = select_dual_scheme(dual_rows, "fairness_priority_scheme")
    plot_profit_vs_average_access(frontier_rows, financial_scheme, fairness_scheme)
    plot_min_access_vs_net_profit(frontier_rows, financial_scheme, fairness_scheme)
    write_paper_notes(frontier_rows, dual_rows, policy_rows, representative_scheme_rows)

    print(
        "Generated RQ3 Pareto paper figures, policy summary table, "
        "representative scheme table, and paper notes."
    )


if __name__ == "__main__":
    main()
