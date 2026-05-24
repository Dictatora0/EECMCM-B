from __future__ import annotations

import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from alias_maps import canonicalize_scheme_keys
from data_loader import MissingDataError, get_module_output_dir, load_csv_if_exists, read_module_output
from label_maps import pretty_metric_label, pretty_scheme_label
from plot_config import ensure_matplotlib_configured
from plot_utils import PlotResult, generated_result, save_figure, skipped_result


def _skip_missing(
    figure_id: str,
    title_cn: str,
    reason: str,
    input_files: list[str] | None = None,
    recommended_location: str = "appendix",
) -> PlotResult:
    if reason.strip() == "No existing input file found.":
        reason = "当前工作区缺少可读取的结果文件，未在 `Solutions/RQ3/outputs/` 中找到所需 CSV/Excel/JSON 输出。"
    return skipped_result(
        figure_id,
        title_cn,
        "RQ3",
        input_files or [],
        recommended_location,
        reason,
        "skipped_missing_data",
    )


def _load_dual_scheme_rows() -> tuple[pd.DataFrame, list[str]]:
    dual_df, dual_path = read_module_output(
        "RQ3",
        candidate_keywords=[
            ["3_1", "dual", "scheme", "comparison"],
            ["dual", "scheme", "comparison"],
        ],
        required_columns=[
            "scheme_label",
            "average_service_access_performance",
            "minimum_service_access_performance",
            "annual_net_profit",
            "profit_rate",
            "profit_compliant",
        ],
    )
    dual_df = canonicalize_scheme_keys(dual_df, columns=("scheme_label",))
    rows = dual_df[
        [
            "scheme_label",
            "average_service_access_performance",
            "minimum_service_access_performance",
            "annual_net_profit",
            "profit_rate",
            "profit_compliant",
        ]
    ].copy()
    rows["scheme_label_cn"] = rows["scheme_label"].map(pretty_scheme_label)
    return rows, [str(dual_path)]


def _representative_offsets(labels: list[str]) -> dict[str, tuple[float, float, str]]:
    defaults = {
        "财务可持续方案": (10, 8, "left"),
        "满意度优先方案": (10, 10, "left"),
        "利润峰值点": (-12, 10, "right"),
        "满意度峰值点": (12, 10, "left"),
        "收敛参考点": (12, 2, "left"),
    }
    return {label: defaults.get(label, (10, 8, "left")) for label in labels}


def _build_representative_from_frontier(frontier_df: pd.DataFrame) -> pd.DataFrame:
    frame = frontier_df.copy()
    required_satisfaction_columns = [
        "average_service_satisfaction",
        "minimum_service_satisfaction",
    ]
    missing_satisfaction_columns = [column for column in required_satisfaction_columns if column not in frame.columns]
    if missing_satisfaction_columns:
        raise ValueError(
            "Missing required satisfaction columns for representative frontier construction: "
            + ", ".join(missing_satisfaction_columns)
        )
    frame["annual_net_profit_wan"] = pd.to_numeric(frame["annual_net_profit"], errors="coerce") / 10000.0
    frame["average_service_satisfaction"] = pd.to_numeric(frame["average_service_satisfaction"], errors="coerce")
    frame["minimum_service_satisfaction"] = pd.to_numeric(frame["minimum_service_satisfaction"], errors="coerce")
    frame["minimum_service_access_performance"] = pd.to_numeric(frame["minimum_service_access_performance"], errors="coerce")
    frame["average_service_access_performance"] = pd.to_numeric(frame["average_service_access_performance"], errors="coerce")
    frame["profit_rate"] = pd.to_numeric(frame["profit_rate"], errors="coerce")
    frame["converged"] = pd.to_numeric(frame["converged"], errors="coerce")
    frame["profit_compliant"] = pd.to_numeric(frame["profit_compliant"], errors="coerce")

    representatives: list[dict[str, float | str]] = []
    profit_peak = frame.sort_values(
        ["annual_net_profit_wan", "average_service_satisfaction"],
        ascending=[False, False],
    ).iloc[0]
    satisfaction_peak = frame.sort_values(
        ["minimum_service_satisfaction", "average_service_satisfaction", "annual_net_profit_wan"],
        ascending=[False, False, False],
    ).iloc[0]
    converged_reference_candidates = frame[
        (frame["converged"] == 1) & (frame["profit_compliant"] == 1)
    ].copy()
    if converged_reference_candidates.empty:
        converged_reference_candidates = frame[frame["converged"] == 1].copy()
    if converged_reference_candidates.empty:
        converged_reference = frame.sort_values(
            ["average_service_satisfaction", "annual_net_profit_wan"],
            ascending=[False, False],
        ).iloc[0]
    else:
        median_profit = converged_reference_candidates["annual_net_profit_wan"].median()
        median_satisfaction = converged_reference_candidates["average_service_satisfaction"].median()
        converged_reference_candidates["distance"] = (
            (converged_reference_candidates["annual_net_profit_wan"] - median_profit).abs()
            + (converged_reference_candidates["average_service_satisfaction"] - median_satisfaction).abs()
        )
        converged_reference = converged_reference_candidates.sort_values("distance").iloc[0]

    for label, row in [
        ("frontier_profit_peak", profit_peak),
        ("frontier_satisfaction_peak", satisfaction_peak),
        ("frontier_converged_reference", converged_reference),
    ]:
        representatives.append(
            {
                "representative_label": label,
                "annual_net_profit_wan": float(row["annual_net_profit_wan"]),
                "average_service_satisfaction": float(row["average_service_satisfaction"]),
                "minimum_service_satisfaction": float(row["minimum_service_satisfaction"]),
                "minimum_service_access_performance": float(row["minimum_service_access_performance"]),
                "profit_rate": float(row["profit_rate"]),
                "converged": int(row["converged"]) if pd.notna(row["converged"]) else 0,
            }
        )
    return pd.DataFrame(representatives).drop_duplicates(subset=["representative_label"])


def _parse_station_service_prices(price_scheme_detail: str) -> pd.DataFrame:
    parsed = json.loads(price_scheme_detail)
    rows: list[dict[str, object]] = []
    for station, service_map in parsed.items():
        for service, price in service_map.items():
            rows.append(
                {
                    "station": station,
                    "service": service,
                    "price": float(price),
                }
            )
    return pd.DataFrame(rows)


def _select_service_level_scheme(summary_df: pd.DataFrame, scenario: str | None = None) -> pd.Series:
    frame = summary_df.copy()
    if scenario is not None and "scenario" in frame.columns:
        scenario_rows = frame[frame["scenario"] == scenario].copy()
        if not scenario_rows.empty:
            frame = scenario_rows
    preferred = [
        "joint_feasible_best_satisfaction",
        "satisfaction_best",
        "financial_best",
    ]
    if "scheme_label" in frame.columns:
        frame = canonicalize_scheme_keys(frame, columns=("scheme_label",))
        for label in preferred:
            matched = frame[frame["scheme_label"] == label]
            if not matched.empty:
                return matched.iloc[0]
    return frame.iloc[0]


def build_rq3_plots(export_formats: list[str]) -> list[PlotResult]:
    results: list[PlotResult] = []
    style = ensure_matplotlib_configured()
    rq3_output_dir = get_module_output_dir("RQ3")

    try:
        dual_metrics, dual_files = _load_dual_scheme_rows()
    except MissingDataError as exc:
        results.append(
            _skip_missing(
                "rq3_01",
                "问题3两类代表性定价方案对比",
                str(exc),
                recommended_location="main_text",
            )
        )
    else:
        fig, axes = plt.subplots(1, 3, figsize=(style.figure_width + 4.0, style.figure_height), constrained_layout=True)
        x_positions = list(range(len(dual_metrics)))
        colors = [style.colors[0], style.colors[1]]

        axes[0].bar(
            [x - 0.16 for x in x_positions],
            dual_metrics["average_service_access_performance"],
            width=0.32,
            color=colors[0],
            label="平均服务可及绩效",
        )
        axes[0].bar(
            [x + 0.16 for x in x_positions],
            dual_metrics["minimum_service_access_performance"],
            width=0.32,
            color=style.colors[2],
            label="最低服务可及绩效",
        )
        axes[0].set_ylim(0, 1.0)
        axes[0].set_title("辅助可及绩效对比")
        axes[0].set_ylabel("指标值")
        axes[0].legend(frameon=False, loc="upper left")

        bars = axes[1].bar(
            dual_metrics["scheme_label_cn"],
            dual_metrics["profit_rate"],
            color=colors,
            width=0.58,
        )
        axes[1].axhline(0.0, color="#666666", linewidth=1.0)
        axes[1].axhline(0.08, color=style.colors[3], linestyle="--", linewidth=1.2, label="0.08 上限")
        axes[1].set_ylim(min(-0.01, dual_metrics["profit_rate"].min() - 0.01), max(0.09, dual_metrics["profit_rate"].max() + 0.015))
        axes[1].set_title("逐站利润率约束表现")
        axes[1].set_ylabel("利润率")
        axes[1].legend(frameon=False, loc="upper right")
        for bar, compliant in zip(bars, dual_metrics["profit_compliant"]):
            label = "达标" if compliant == 1 else "未达标"
            y = bar.get_height()
            offset = 0.003 if y >= 0 else -0.003
            va = "bottom" if y >= 0 else "top"
            axes[1].text(
                bar.get_x() + bar.get_width() / 2,
                y + offset,
                label,
                ha="center",
                va=va,
                fontsize=9,
                color="#333333",
            )

        net_profit_wan = dual_metrics.copy()
        net_profit_wan["annual_net_profit_wan"] = net_profit_wan["annual_net_profit"] / 10000.0
        axes[2].bar(
            net_profit_wan["scheme_label_cn"],
            net_profit_wan["annual_net_profit_wan"],
            color=colors,
            width=0.58,
        )
        axes[2].axhline(0.0, color="#666666", linewidth=1.0)
        axes[2].set_title("年净利润对比")
        axes[2].set_ylabel("年净利润 / 万元")

        for ax in axes:
            ax.set_xlabel("")
            ax.tick_params(axis="x", rotation=10)

        outputs = save_figure(fig, "rq3_01_dual_scheme_compare", export_formats)
        results.append(
            generated_result(
                "rq3_01",
                "问题3两类代表性定价方案对比",
                "RQ3",
                dual_files,
                "main_text",
                "并列展示满意度主目标下的两类代表性定价方案，突出辅助可及绩效、逐站利润率约束与净利润之间的差异。",
                dual_metrics,
                outputs,
            )
        )

    try:
        frontier_df, frontier_path = read_module_output(
            "RQ3",
            candidate_keywords=[
                ["pareto", "frontier"],
                ["3_1", "pareto"],
                ["frontier"],
            ],
            required_columns=[
                "annual_net_profit",
                "average_service_satisfaction",
                "minimum_service_satisfaction",
                "profit_compliant",
                "converged",
            ],
        )
    except MissingDataError as exc:
        results.append(
            _skip_missing(
                "rq3_02",
                "问题3社区平均老人满意度前沿图",
                str(exc),
                recommended_location="main_text",
            )
        )
        frontier_df = None
        frontier_path = None
    else:
        frontier_df = frontier_df.copy()
        required_frontier_columns = {
            "annual_net_profit",
            "average_service_satisfaction",
            "minimum_service_satisfaction",
            "profit_compliant",
            "converged",
        }
        missing_frontier_columns = sorted(required_frontier_columns - set(frontier_df.columns))
        if missing_frontier_columns:
            results.append(
                _skip_missing(
                    "rq3_02",
                    "问题3社区平均老人满意度前沿图",
                    "Pareto 前沿结果缺少满意度主图所需字段："
                    + ", ".join(missing_frontier_columns)
                    + "。不能用辅助可及绩效字段替代满意度字段。",
                    [str(frontier_path)],
                    "main_text",
                )
            )
            frontier_df = None
            frontier_path = None
        else:
            for column in [
                "annual_net_profit",
                "average_service_satisfaction",
                "minimum_service_satisfaction",
                "average_service_access_performance",
                "minimum_service_access_performance",
                "profit_compliant",
                "converged",
                "profit_rate",
            ]:
                if column in frontier_df.columns:
                    frontier_df[column] = pd.to_numeric(frontier_df[column], errors="coerce")
            fig, ax = plt.subplots(figsize=(style.figure_width, style.figure_height))
            sns.scatterplot(
                data=frontier_df,
                x="annual_net_profit",
                y="average_service_satisfaction",
                hue="profit_compliant",
                style="converged",
                palette={0: style.colors[3], 1: style.colors[2]},
                s=90,
                ax=ax,
            )
            ax.set_title("问题3社区平均老人满意度前沿图")
            ax.set_xlabel("年净利润 / 元")
            ax.set_ylabel("社区平均老人满意度")
            handles, labels = ax.get_legend_handles_labels()
            label_map = {"profit_compliant": "利润率达标", "converged": "是否收敛", "0": "否", "1": "是"}
            ax.legend(handles, [label_map.get(label, label) for label in labels], frameon=False, title="")
            outputs = save_figure(fig, "rq3_02_pareto_profit_avg_satisfaction", export_formats)
            results.append(
                generated_result(
                    "rq3_02",
                    "问题3社区平均老人满意度前沿图",
                    "RQ3",
                    [str(frontier_path)],
                    "main_text",
                    "展示满意度主目标下定价方案在利润与社区平均老人满意度之间的权衡关系，可作为问题3正文核心前沿图。",
                    frontier_df,
                    outputs,
                )
            )

    representative_df = None
    representative_path_strs: list[str] = []
    try:
        representative_df, representative_path = read_module_output(
            "RQ3",
            candidate_keywords=[
                ["pareto", "representative", "scheme"],
                ["3_2", "pareto", "representative"],
                ["representative", "scheme"],
            ],
            required_columns=[
                "representative_label",
                "annual_net_profit_wan",
                "minimum_service_satisfaction",
                "converged",
            ],
        )
        representative_path_strs = [str(representative_path)]
    except MissingDataError:
        if frontier_df is not None and frontier_path is not None:
            try:
                representative_df = _build_representative_from_frontier(frontier_df)
                representative_path_strs = [str(frontier_path)]
            except ValueError:
                representative_df = None
                representative_path_strs = []

    if representative_df is None:
        results.append(
            _skip_missing(
                "rq3_03",
                "问题3最低老人满意度边界图",
                "当前未生成代表方案汇总，也无法由现有 Pareto 前沿结果构造可用于正文比较的代表性方案。",
                recommended_location="main_text",
            )
        )
    else:
        representative_df = representative_df.copy()
        for column in ["annual_net_profit_wan", "average_service_satisfaction", "minimum_service_satisfaction", "minimum_service_access_performance", "profit_rate"]:
            if column in representative_df.columns:
                representative_df[column] = pd.to_numeric(representative_df[column], errors="coerce")
        representative_df = canonicalize_scheme_keys(representative_df, columns=("representative_label",))
        representative_df["representative_label_cn"] = representative_df["representative_label"].map(pretty_scheme_label)
        if "minimum_service_satisfaction" not in representative_df.columns:
            results.append(
                _skip_missing(
                    "rq3_03",
                    "问题3最低老人满意度边界图",
                    "代表方案汇总缺少 `minimum_service_satisfaction` 字段，不能用辅助可及绩效替代最低老人满意度。",
                    representative_path_strs,
                    "main_text",
                )
            )
            representative_df = None
        else:
            y_col = "minimum_service_satisfaction"
            fig, ax = plt.subplots(figsize=(style.figure_width + 0.8, style.figure_height))
            palette = dict(zip(representative_df["representative_label_cn"], style.colors[: len(representative_df)]))
            sns.scatterplot(
                data=representative_df,
                x="annual_net_profit_wan",
                y=y_col,
                hue="representative_label_cn",
                palette=palette,
                s=140,
                legend=False,
                ax=ax,
            )
            offsets = _representative_offsets(representative_df["representative_label_cn"].tolist())
            for _, row in representative_df.iterrows():
                dx, dy, ha = offsets[row["representative_label_cn"]]
                ax.annotate(
                    row["representative_label_cn"],
                    xy=(row["annual_net_profit_wan"], row[y_col]),
                    xytext=(dx, dy),
                    textcoords="offset points",
                    fontsize=9,
                    ha=ha,
                    va="bottom",
                )
            ax.set_title("问题3最低老人满意度边界图")
            ax.set_xlabel("年净利润 / 万元")
            ax.set_ylabel("最低老人满意度")
            ax.set_ylim(max(0.59, representative_df[y_col].min() - 0.02), min(1.01, representative_df[y_col].max() + 0.02))
            outputs = save_figure(fig, "rq3_03_pareto_min_satisfaction", export_formats)
            reason = "聚焦少量代表性定价方案而非全部点云，更适合在正文直接解释最低老人满意度边界与财务代价。"
            if representative_path_strs and representative_path_strs[0].endswith("3_1_pareto_frontier.csv"):
                reason = "当前缺少 3_2 代表方案汇总，已根据现有 Pareto 前沿自动构造利润峰值、满意度峰值和收敛参考方案，用于近似刻画最低老人满意度边界。"
            results.append(
                generated_result(
                    "rq3_03",
                    "问题3最低老人满意度边界图",
                    "RQ3",
                    representative_path_strs,
                    "main_text",
                    reason,
                    representative_df,
                    outputs,
                )
            )

    try:
        satisfaction_community_df, satisfaction_community_path = read_module_output(
            "RQ3",
            candidate_keywords=[
                ["3_5", "service", "level", "pricing", "community", "satisfaction"],
                ["3_1", "satisfaction", "community"],
                ["3_1", "satisfaction", "communities"],
                ["3_1", "fairness", "community"],
                ["3_1", "fairness", "communities"],
                ["fairness", "community"],
            ],
            required_columns=["community", "price_satisfaction", "service_access_performance"],
        )
    except MissingDataError as exc:
        results.append(
            _skip_missing(
                "rq3_04",
                "价格满意度与辅助可及绩效对比",
                str(exc),
            )
        )
    else:
        community_compare = satisfaction_community_df[["community", "price_satisfaction", "service_access_performance"]].copy()
        if "scenario" in satisfaction_community_df.columns:
            scenarios = satisfaction_community_df["scenario"].dropna().unique().tolist()
            if scenarios:
                preferred_scenario = "S4" if "S4" in scenarios else scenarios[0]
                community_compare = satisfaction_community_df[
                    satisfaction_community_df["scenario"] == preferred_scenario
                ][["community", "price_satisfaction", "service_access_performance"]].copy()
                title = f"{preferred_scenario} 情景下价格满意度与辅助可及绩效对比"
                reason = "基于社区级结果对比价格满意度与辅助可及绩效，用于说明价格接受度变化如何传导到服务结果。"
            else:
                title = "价格满意度与辅助可及绩效对比"
                reason = "用于拆解价格因素与服务结果之间的关系，适合作为正文之外的机制解释图。"
        else:
            title = "满意度优先方案下价格满意度与辅助可及绩效"
            reason = "用于拆解价格因素与服务结果之间的关系，适合作为正文之外的机制解释图。"
        fig, ax = plt.subplots(figsize=(style.figure_width + 0.8, style.figure_height))
        width = 0.36
        x = range(len(community_compare))
        ax.bar([i - width / 2 for i in x], community_compare["price_satisfaction"], width=width, color=style.colors[1], label="价格满意度")
        ax.bar([i + width / 2 for i in x], community_compare["service_access_performance"], width=width, color=style.colors[2], label="辅助可及绩效")
        ax.set_xticks(list(x))
        ax.set_xticklabels(community_compare["community"])
        ax.set_ylim(0, 1.05)
        ax.set_title(title)
        ax.set_xlabel("小区")
        ax.set_ylabel("指标值")
        ax.legend(frameon=False)
        outputs = save_figure(fig, "rq3_04_price_vs_access", export_formats)
        results.append(
            generated_result(
                "rq3_04",
                title,
                "RQ3",
                [str(satisfaction_community_path)],
                "appendix",
                reason,
                community_compare,
                outputs,
            )
        )

    try:
        station_financial_df, station_financial_path = read_module_output(
            "RQ3",
            candidate_keywords=[
                ["3_1", "financial", "station"],
                ["3_1", "financial", "stations"],
                ["financial", "station"],
            ],
            required_columns=["station_community", "emergency_public_loss"],
        )
    except MissingDataError as exc:
        results.append(
            _skip_missing(
                "rq3_05",
                "各服务站紧急救助公益服务亏损",
                str(exc),
            )
        )
    else:
        emergency_loss = station_financial_df[["station_community", "emergency_public_loss"]].copy()
        if emergency_loss["emergency_public_loss"].abs().sum() <= 1e-9:
            results.append(
                skipped_result(
                    "rq3_05",
                    "各服务站紧急救助公益服务亏损",
                    "RQ3",
                    [str(station_financial_path)],
                    "appendix",
                    "紧急救助公益亏损接近 0，绘图解释价值有限。",
                    "skipped_table_better",
                    emergency_loss,
                )
            )
        else:
            fig, ax = plt.subplots(figsize=(style.figure_width, style.figure_height))
            ax.bar(emergency_loss["station_community"], emergency_loss["emergency_public_loss"] / 10000, color=style.colors[3], width=0.65)
            ax.axhline(0.0, color="#666666", linewidth=1.0)
            ax.set_title("各服务站紧急救助公益服务亏损")
            ax.set_xlabel("服务站")
            ax.set_ylabel("亏损 / 万元")
            outputs = save_figure(fig, "rq3_05_emergency_loss", export_formats)
            results.append(
                generated_result(
                    "rq3_05",
                    "各服务站紧急救助公益服务亏损",
                    "RQ3",
                    [str(station_financial_path)],
                    "appendix",
                    "用于说明公益服务为什么需要政策补偿，是较强的政策解释图。",
                    emergency_loss,
                    outputs,
                )
            )

    try:
        damping_df, damping_path = read_module_output(
            "RQ3",
            candidate_keywords=[
                ["3_3", "damping", "sensitivity"],
                ["damping", "sensitivity"],
                ["damping"],
            ],
            required_columns=["lambda", "converged"],
        )
        epsilon_df, epsilon_path = read_module_output(
            "RQ3",
            candidate_keywords=[
                ["3_3", "epsilon", "constraint", "summary"],
                ["epsilon", "constraint", "summary"],
                ["epsilon", "summary"],
            ],
            required_columns=["epsilon", "feasible_count", "fiscal_gap", "minimum_service_access_performance", "average_service_access_performance"],
        )
    except MissingDataError as exc:
        results.append(
            _skip_missing(
                "rq3_06",
                "RQ3 稳定性增强诊断图",
                str(exc),
            )
        )
    else:
        stability_files = [str(damping_path), str(epsilon_path)]
        fig, axes = plt.subplots(1, 3, figsize=(style.figure_width + 4.0, style.figure_height), constrained_layout=True)
        sns.lineplot(data=damping_df, x="lambda", y="converged", estimator="mean", marker="o", color=style.colors[0], ax=axes[0])
        axes[0].set_title("阻尼系数与收敛率")
        axes[0].set_xlabel("阻尼系数 λ")
        axes[0].set_ylabel("收敛率")
        epsilon_valid = epsilon_df[epsilon_df["feasible_count"] > 0].copy()
        sns.lineplot(data=epsilon_valid, x="epsilon", y="fiscal_gap", marker="o", color=style.colors[3], ax=axes[1])
        axes[1].set_title("可及绩效阈值与财政缺口")
        axes[1].set_xlabel("最低可及绩效阈值 ε")
        axes[1].set_ylabel("财政缺口 / 元")
        sns.lineplot(data=epsilon_valid, x="epsilon", y="minimum_service_access_performance", marker="o", color=style.colors[2], label="最低可及绩效", ax=axes[2])
        sns.lineplot(data=epsilon_valid, x="epsilon", y="average_service_access_performance", marker="s", color=style.colors[1], label="平均可及绩效", ax=axes[2])
        axes[2].set_title("可及绩效阈值与服务可及绩效")
        axes[2].set_xlabel("最低可及绩效阈值 ε")
        axes[2].set_ylabel("绩效值")
        axes[2].legend(frameon=False)
        outputs = save_figure(fig, "rq3_06_stability_suite", export_formats)
        results.append(
            generated_result(
                "rq3_06",
                "RQ3 稳定性增强诊断图",
                "RQ3",
                stability_files,
                "appendix",
                "统一重绘阻尼与可及绩效阈值诊断图，便于在附录说明算法稳定性。",
                pd.concat([damping_df.head(20), epsilon_valid.head(20)], ignore_index=True, sort=False),
                outputs,
            )
        )

    summary_path = rq3_output_dir / "3_5_satisfaction_objective_summary.csv"
    station_path = rq3_output_dir / "3_5_satisfaction_objective_by_station.csv"
    summary_df, actual_summary_path = load_csv_if_exists(summary_path)
    station_df, actual_station_path = load_csv_if_exists(station_path)
    if summary_df is None:
        results.append(
            skipped_result(
                "rq3_07",
                "站点—服务项目级定价热力图",
                "RQ3",
                [str(summary_path)],
                "appendix",
                "缺少 3_5_satisfaction_objective_summary.csv，无法生成满意度主目标下的站点—服务项目级定价图。",
                "skipped_missing_data",
            )
        )
    else:
        selected_row = _select_service_level_scheme(summary_df, scenario="S4" if "S4" in summary_df.get("scenario", pd.Series(dtype=str)).astype(str).tolist() else None)
        if "price_scheme_detail" not in selected_row or pd.isna(selected_row["price_scheme_detail"]):
            results.append(
                skipped_result(
                    "rq3_07",
                    "站点—服务项目级定价热力图",
                    "RQ3",
                    [str(actual_summary_path)],
                    "appendix",
                    "服务级定价汇总文件存在，但未提供可解析的 price_scheme_detail 定价明细。",
                    "skipped_missing_data",
                    summary_df,
                )
            )
        else:
            price_rows = _parse_station_service_prices(str(selected_row["price_scheme_detail"]))
            price_heatmap = price_rows.pivot(index="station", columns="service", values="price").sort_index()
            fig, ax = plt.subplots(figsize=(style.figure_width + 1.0, style.figure_height))
            sns.heatmap(price_heatmap, cmap="YlOrRd", annot=True, fmt=".1f", linewidths=0.5, cbar_kws={"label": "价格 / 元"}, ax=ax)
            scenario_label = str(selected_row.get("scenario", ""))
            if scenario_label:
                ax.set_title(f"{scenario_label} 情景站点—服务项目级定价热力图")
            else:
                ax.set_title("站点—服务项目级定价热力图")
            ax.set_xlabel("服务类型")
            ax.set_ylabel("服务站")
            outputs = save_figure(fig, "rq3_07_service_level_pricing", export_formats)
            results.append(
                generated_result(
                    "rq3_07",
                    ax.get_title(),
                    "RQ3",
                    [str(actual_summary_path)],
                    "appendix",
                    f"从 3_5 满意度主目标汇总文件解析代表方案 `{selected_row.get('scheme_label', '')}` 的站点-服务价格矩阵，用于展示差异化定价结构。",
                    price_heatmap.reset_index(),
                    outputs,
                )
            )

    if station_df is None:
        results.append(
            skipped_result(
                "rq3_08",
                "服务级定价方案下各站点利润率",
                "RQ3",
                [str(station_path)],
                "appendix",
                "缺少 3_5_satisfaction_objective_by_station.csv，无法生成满意度主目标方案下的站点利润率图。",
                "skipped_missing_data",
            )
        )
    else:
        station_plot = station_df.copy()
        if "scenario" in station_plot.columns:
            scenarios = station_plot["scenario"].dropna().unique().tolist()
            preferred_scenario = "S4" if "S4" in scenarios else scenarios[0]
            station_plot = station_plot[station_plot["scenario"] == preferred_scenario].copy()
            title = f"{preferred_scenario} 情景服务级定价站点利润率"
        else:
            title = "服务级定价站点利润率"
        station_plot["profit_rate"] = pd.to_numeric(station_plot["profit_rate"], errors="coerce")
        fig, ax = plt.subplots(figsize=(style.figure_width, style.figure_height))
        bars = ax.bar(station_plot["station"], station_plot["profit_rate"], color=style.colors[0], width=0.62)
        ax.axhline(0.0, color="#666666", linewidth=1.0)
        ax.axhline(0.08, color=style.colors[3], linestyle="--", linewidth=1.2, label="0.08 上限")
        for bar, compliant in zip(bars, station_plot["profit_compliant"]):
            label = "达标" if int(compliant) == 1 else "未达标"
            y = bar.get_height()
            offset = 0.003 if y >= 0 else -0.003
            va = "bottom" if y >= 0 else "top"
            ax.text(bar.get_x() + bar.get_width() / 2, y + offset, label, ha="center", va=va, fontsize=9)
        ax.set_title(title)
        ax.set_xlabel("服务站")
        ax.set_ylabel("利润率")
        ax.legend(frameon=False)
        outputs = save_figure(fig, "rq3_08_service_level_station_profit", export_formats)
        results.append(
            generated_result(
                "rq3_08",
                title,
                "RQ3",
                [str(actual_station_path)],
                "appendix",
                "与服务级定价热力图配套，展示代表方案下各站点是否进入微利约束区间。",
                station_plot,
                outputs,
            )
        )

    joint_summary_path = rq3_output_dir / "3_4_joint_feasibility_summary.csv"
    joint_station_path = rq3_output_dir / "3_4_joint_feasibility_by_station.csv"
    joint_summary_df, actual_joint_summary_path = load_csv_if_exists(joint_summary_path)
    joint_station_df, actual_joint_station_path = load_csv_if_exists(joint_station_path)
    if joint_summary_df is None:
        results.append(
            skipped_result(
                "rq3_09",
                "联合可行性情景对比",
                "RQ3",
                [str(joint_summary_path)],
                "appendix",
                "缺少 3_4_joint_feasibility_summary.csv，无法生成联合可行性情景对比图。",
                "skipped_missing_data",
            )
        )
    else:
        summary_plot = joint_summary_df.copy()
        metric_long = summary_plot[
            [
                "scenario",
                "average_service_access_performance",
                "minimum_service_access_performance",
                "annual_net_profit",
            ]
        ].melt(id_vars="scenario", var_name="metric", value_name="value")
        metric_long["metric"] = metric_long["metric"].map(pretty_metric_label)
        fig, axes = plt.subplots(1, 2, figsize=(style.figure_width + 3.8, style.figure_height), constrained_layout=True)
        access_long = metric_long[metric_long["metric"].isin(["平均服务可及绩效", "最低服务可及绩效"])].copy()
        money_long = metric_long[metric_long["metric"] == "年净利润"].copy()
        money_long["value"] = pd.to_numeric(money_long["value"], errors="coerce") / 10000.0
        sns.barplot(data=access_long, x="scenario", y="value", hue="metric", palette=style.colors[:2], ax=axes[0])
        sns.barplot(data=money_long, x="scenario", y="value", color=style.colors[3], ax=axes[1])
        axes[0].set_title("联合可行性方案的辅助可及绩效")
        axes[0].set_xlabel("情景")
        axes[0].set_ylabel("指标值")
        axes[0].legend(frameon=False, title="")
        axes[1].set_title("联合可行性方案年净利润")
        axes[1].set_xlabel("情景")
        axes[1].set_ylabel("年净利润 / 万元")
        outputs = save_figure(fig, "rq3_09_joint_feasibility_summary", export_formats)
        results.append(
            generated_result(
                "rq3_09",
                "联合可行性情景对比",
                "RQ3",
                [str(actual_joint_summary_path)],
                "appendix",
                "用于补充比较 S0 与 S4 情景下联合可行性搜索的辅助可及绩效与利润表现。",
                summary_plot,
                outputs,
            )
        )

    if joint_station_df is None:
        results.append(
            skipped_result(
                "rq3_10",
                "联合可行性逐站利润率诊断",
                "RQ3",
                [str(joint_station_path)],
                "appendix",
                "缺少 3_4_joint_feasibility_by_station.csv，无法生成逐站联合可行性诊断图。",
                "skipped_missing_data",
            )
        )
    else:
        station_diag = joint_station_df.copy()
        station_diag["profit_rate"] = pd.to_numeric(station_diag["profit_rate"], errors="coerce")
        fig, axes = plt.subplots(1, max(1, station_diag["scenario"].nunique()), figsize=(style.figure_width + 2.8, style.figure_height), constrained_layout=True)
        axes = np.atleast_1d(axes).ravel().tolist()
        unique_scenarios = sorted(station_diag["scenario"].dropna().unique().tolist())
        for ax, scenario in zip(axes, unique_scenarios):
            subset = station_diag[station_diag["scenario"] == scenario].copy()
            bars = ax.bar(subset["station"], subset["profit_rate"], color=style.colors[0], width=0.62)
            ax.axhline(0.0, color="#666666", linewidth=1.0)
            ax.axhline(0.08, color=style.colors[3], linestyle="--", linewidth=1.2)
            for bar, direction in zip(bars, subset["binding_direction"]):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + (0.003 if bar.get_height() >= 0 else -0.003),
                    str(direction),
                    ha="center",
                    va="bottom" if bar.get_height() >= 0 else "top",
                    fontsize=8,
                    rotation=90,
                )
            ax.set_title(f"{scenario} 逐站利润率")
            ax.set_xlabel("服务站")
            ax.set_ylabel("利润率")
        outputs = save_figure(fig, "rq3_10_joint_station_profit", export_formats)
        results.append(
            generated_result(
                "rq3_10",
                "联合可行性逐站利润率诊断",
                "RQ3",
                [str(actual_joint_station_path)],
                "appendix",
                "逐站标出利润率偏离方向，可直接解释联合可行性为何未成立以及卡点站点位置。",
                station_diag,
                outputs,
            )
        )

    return results
