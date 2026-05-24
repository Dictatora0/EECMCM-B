from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from data_loader import MissingDataError, read_first_existing
from label_maps import pretty_metric_label
from plot_config import ROOT, ensure_matplotlib_configured
from plot_utils import PlotResult, generated_result, is_low_information_series, save_figure, skipped_result


RQ1_OUTPUT = ROOT / "Solutions" / "RQ1" / "outputs"


def _load_population_by_year() -> tuple[pd.DataFrame, list[str]]:
    frame, path = read_first_existing(
        [RQ1_OUTPUT / "1_1_high_precision_population_by_year.csv"],
        required_columns=["year", "community", "self_care", "semi_disabled", "disabled"],
    )
    return frame, [str(path)]


def _load_adjusted_demand_detail() -> tuple[pd.DataFrame, list[str]]:
    frame, path = read_first_existing(
        [RQ1_OUTPUT / "1_3_high_precision_adjusted_demand_detail.csv"],
        required_columns=["community", "care_level", "service", "adjustment_scale", "adjusted_monthly_demand"],
    )
    return frame, [str(path)]


def _load_adjusted_summary() -> tuple[pd.DataFrame, list[str]]:
    frame, path = read_first_existing(
        [RQ1_OUTPUT / "1_3_high_precision_adjusted_demand.csv"],
        required_columns=["community", "service", "adjusted_monthly_demand"],
    )
    return frame, [str(path)]


def _load_theoretical_summary() -> tuple[pd.DataFrame, list[str]]:
    frame, path = read_first_existing(
        [RQ1_OUTPUT / "1_2_high_precision_theoretical_demand.csv"],
        required_columns=["community", "service", "theoretical_monthly_demand"],
    )
    return frame, [str(path)]


def _load_transition_matrix() -> tuple[pd.DataFrame, list[str]]:
    frame, path = read_first_existing(
        [RQ1_OUTPUT / "1_4_transition_matrix.csv"],
        required_columns=["target_state", "self_care", "semi_disabled", "disabled"],
    )
    return frame, [str(path)]


def _load_validation_sensitivity() -> tuple[pd.DataFrame, list[str]]:
    frame, path = read_first_existing(
        [RQ1_OUTPUT / "1_4_validation_sensitivity_summary.csv"],
        required_columns=[
            "case",
            "year5_elderly_total",
            "year5_disabled_share",
            "theoretical_total_monthly_demand",
            "adjusted_total_monthly_demand",
            "matrix_equivalence_max_abs_diff",
        ],
    )
    return frame, [str(path)]


def _case_label(case_name: str) -> str:
    mapping = {
        "baseline": "基准",
        "growth_minus_10pct": "增长率 -10%",
        "growth_plus_10pct": "增长率 +10%",
        "p12_minus_10pct": "自理转半失能 -10%",
        "p12_plus_10pct": "自理转半失能 +10%",
        "p23_minus_10pct": "半失能转失能 -10%",
        "p23_plus_10pct": "半失能转失能 +10%",
    }
    return mapping.get(case_name, case_name)


def build_rq1_plots(export_formats: list[str]) -> list[PlotResult]:
    results: list[PlotResult] = []
    style = ensure_matplotlib_configured()

    try:
        population_df, population_files = _load_population_by_year()
    except MissingDataError as exc:
        population_df = None
        population_files = []
        results.append(
            skipped_result(
                "rq1_01",
                "三类老人五年变化趋势图",
                "RQ1",
                population_files,
                "main_text",
                str(exc),
                "skipped_missing_data",
            )
        )
    if population_df is not None:
        trend = (
            population_df.groupby("year")[["self_care", "semi_disabled", "disabled"]]
            .sum()
            .reset_index()
            .sort_values("year")
        )
        fig, ax = plt.subplots(figsize=(style.figure_width, style.figure_height))
        ax.plot(trend["year"], trend["self_care"], label="自理", linewidth=style.line_width, color=style.colors[0])
        ax.plot(trend["year"], trend["semi_disabled"], label="半失能", linewidth=style.line_width, color=style.colors[1])
        ax.plot(trend["year"], trend["disabled"], label="失能", linewidth=style.line_width, color=style.colors[3])
        ax.set_title("未来五年三类老人数量变化趋势")
        ax.set_xlabel("年份")
        ax.set_ylabel("人数 / 人")
        ax.legend(frameon=False)
        outputs = save_figure(fig, "rq1_01_population_trend", export_formats)
        results.append(
            generated_result(
                "rq1_01",
                "未来五年三类老人数量变化趋势",
                "RQ1",
                population_files,
                "main_text",
                "展示老龄规模增长与失能化趋势，适合作为问题1核心结果图。",
                trend,
                outputs,
            )
        )

        year5 = population_df[population_df["year"] == population_df["year"].max()].copy()
        if len(year5) < 2:
            results.append(
                skipped_result(
                    "rq1_02",
                    "第5年末各小区老人结构堆叠柱状图",
                    "RQ1",
                    population_files,
                    "table_better",
                    "有效小区数量不足，建议直接列表展示。",
                    "skipped_table_better",
                    year5,
                )
            )
        else:
            year5 = year5.sort_values("community")
            fig, ax = plt.subplots(figsize=(style.figure_width + 0.8, style.figure_height))
            bottom = pd.Series([0.0] * len(year5), index=year5.index)
            for label, column, color in [
                ("自理", "self_care", style.colors[0]),
                ("半失能", "semi_disabled", style.colors[1]),
                ("失能", "disabled", style.colors[3]),
            ]:
                ax.bar(year5["community"], year5[column], bottom=bottom, label=label, color=color, width=0.72)
                bottom = bottom + year5[column]
            ax.set_title("第5年末各小区老人结构对比")
            ax.set_xlabel("小区")
            ax.set_ylabel("人数 / 人")
            ax.legend(frameon=False, ncol=3)
            outputs = save_figure(fig, "rq1_02_year5_structure", export_formats)
            results.append(
                generated_result(
                    "rq1_02",
                    "第5年末各小区老人结构对比",
                    "RQ1",
                    population_files,
                    "main_text",
                    "反映空间差异，可支撑后续服务站选址解释。",
                    year5,
                    outputs,
                )
            )

    try:
        theoretical_summary_df, theoretical_summary_files = _load_theoretical_summary()
    except MissingDataError as exc:
        theoretical_summary_df = None
        theoretical_summary_files = []
        results.append(
            skipped_result(
                "rq1_03a",
                "第5年末理论服务需求热力图",
                "RQ1",
                theoretical_summary_files,
                "main_text",
                str(exc),
                "skipped_missing_data",
            )
        )
    if theoretical_summary_df is not None:
        heatmap = theoretical_summary_df.pivot(index="community", columns="service", values="theoretical_monthly_demand").sort_index()
        fig, ax = plt.subplots(figsize=(style.figure_width + 1.2, style.figure_height + 0.6))
        sns.heatmap(heatmap, cmap=style.cmap, annot=True, fmt=".0f", linewidths=0.5, cbar_kws={"label": "月需求次数 / 次"}, ax=ax)
        ax.set_title("第5年末理论服务需求热力图")
        ax.set_xlabel("服务类型")
        ax.set_ylabel("小区")
        outputs = save_figure(fig, "rq1_03a_theoretical_demand_heatmap", export_formats)
        results.append(
            generated_result(
                "rq1_03a",
                "第5年末理论服务需求热力图",
                "RQ1",
                theoretical_summary_files,
                "main_text",
                "与消费约束后需求图并排展示，可直接对比预算约束前后的理论需求与实现需求差异。",
                heatmap.reset_index(),
                outputs,
            )
        )

    try:
        adjusted_summary_df, adjusted_summary_files = _load_adjusted_summary()
    except MissingDataError as exc:
        adjusted_summary_df = None
        adjusted_summary_files = []
        results.append(
            skipped_result(
                "rq1_03",
                "第5年末消费约束后服务需求热力图",
                "RQ1",
                adjusted_summary_files,
                "main_text",
                str(exc),
                "skipped_missing_data",
            )
        )
    if adjusted_summary_df is not None:
        heatmap = adjusted_summary_df.pivot(index="community", columns="service", values="adjusted_monthly_demand").sort_index()
        fig, ax = plt.subplots(figsize=(style.figure_width + 1.2, style.figure_height + 0.6))
        sns.heatmap(heatmap, cmap=style.cmap, annot=True, fmt=".0f", linewidths=0.5, cbar_kws={"label": "月需求次数 / 次"}, ax=ax)
        ax.set_title("第5年末消费约束后服务需求热力图")
        ax.set_xlabel("服务类型")
        ax.set_ylabel("小区")
        outputs = save_figure(fig, "rq1_03_adjusted_demand_heatmap", export_formats)
        results.append(
            generated_result(
                "rq1_03",
                "第5年末消费约束后服务需求热力图",
                "RQ1",
                adjusted_summary_files,
                "main_text",
                "同时呈现空间与服务维度差异，信息密度高，适合正文。",
                heatmap.reset_index(),
                outputs,
            )
        )

    try:
        adjusted_detail_df, adjusted_detail_files = _load_adjusted_demand_detail()
    except MissingDataError as exc:
        adjusted_detail_df = None
        adjusted_detail_files = []
        results.append(
            skipped_result(
                "rq1_04",
                "消费修正系数热力图",
                "RQ1",
                adjusted_detail_files,
                "appendix",
                str(exc),
                "skipped_missing_data",
            )
        )
    if adjusted_detail_df is not None:
        lambda_df = (
            adjusted_detail_df.groupby(["community", "care_level"], as_index=False)["adjustment_scale"]
            .mean()
            .pivot(index="community", columns="care_level", values="adjustment_scale")
            .sort_index()
        )
        flat_values = lambda_df.to_numpy().ravel().tolist()
        if is_low_information_series(flat_values):
            results.append(
                skipped_result(
                    "rq1_04",
                    "消费修正系数热力图",
                    "RQ1",
                    adjusted_detail_files,
                    "table_better",
                    "修正系数几乎不变，单独绘图信息量不足，建议以表格呈现。",
                    "skipped_table_better",
                    lambda_df.reset_index(),
                    note="该指标建议用表格呈现，不建议单独绘图。",
                )
            )
        else:
            fig, ax = plt.subplots(figsize=(style.figure_width - 0.4, style.figure_height))
            sns.heatmap(lambda_df, cmap="YlGnBu", annot=True, fmt=".2f", linewidths=0.5, cbar_kws={"label": "消费修正系数 λ"}, ax=ax)
            ax.set_title("各小区老人类型消费修正系数热力图")
            ax.set_xlabel("老人类型")
            ax.set_ylabel("小区")
            outputs = save_figure(fig, "rq1_04_lambda_heatmap", export_formats)
            results.append(
                generated_result(
                    "rq1_04",
                    "各小区老人类型消费修正系数热力图",
                    "RQ1",
                    adjusted_detail_files,
                    "appendix",
                    "可用于解释预算约束对不同群体服务需求的压缩程度。",
                    lambda_df.reset_index(),
                    outputs,
                )
            )

    try:
        transition_df, transition_files = _load_transition_matrix()
    except MissingDataError as exc:
        transition_df = None
        transition_files = []
        results.append(
            skipped_result(
                "rq1_05",
                "老人状态转移矩阵热力图",
                "RQ1",
                transition_files,
                "appendix",
                str(exc),
                "skipped_missing_data",
            )
        )
    if transition_df is not None:
        matrix = transition_df.set_index("target_state").rename(
            index={
                "self_care_next": "下一期自理",
                "semi_disabled_next": "下一期半失能",
                "disabled_next": "下一期失能",
            },
            columns={
                "self_care": "本期自理",
                "semi_disabled": "本期半失能",
                "disabled": "本期失能",
            },
        )
        fig, ax = plt.subplots(figsize=(style.figure_width - 0.6, style.figure_height - 0.2))
        sns.heatmap(
            matrix,
            cmap="YlGnBu",
            annot=True,
            fmt=".3f",
            linewidths=0.5,
            cbar_kws={"label": "转移概率"},
            ax=ax,
        )
        ax.set_title("老年状态转移矩阵热力图")
        ax.set_xlabel("本期状态")
        ax.set_ylabel("下一期状态")
        outputs = save_figure(fig, "rq1_05_transition_matrix", export_formats)
        results.append(
            generated_result(
                "rq1_05",
                "老年状态转移矩阵热力图",
                "RQ1",
                transition_files,
                "appendix",
                "用于补充说明递推预测的状态转移结构，适合作为附录方法图。",
                matrix.reset_index(),
                outputs,
            )
        )

    try:
        sensitivity_df, sensitivity_files = _load_validation_sensitivity()
    except MissingDataError as exc:
        sensitivity_df = None
        sensitivity_files = []
        results.append(
            skipped_result(
                "rq1_06",
                "关键参数敏感性热力图",
                "RQ1",
                sensitivity_files,
                "appendix",
                str(exc),
                "skipped_missing_data",
            )
        )
    if sensitivity_df is not None:
        metric_columns = [
            "year5_elderly_total",
            "year5_disabled_share",
            "theoretical_total_monthly_demand",
            "adjusted_total_monthly_demand",
        ]
        baseline_rows = sensitivity_df[sensitivity_df["case"] == "baseline"]
        baseline = baseline_rows.iloc[0] if not baseline_rows.empty else sensitivity_df.iloc[0]
        relative_change = sensitivity_df[["case"] + metric_columns].copy()
        for column in metric_columns:
            base_value = float(baseline[column])
            if abs(base_value) <= 1e-12:
                relative_change[column] = 0.0
            else:
                relative_change[column] = (pd.to_numeric(relative_change[column], errors="coerce") / base_value - 1.0) * 100.0
        relative_change["case_label"] = relative_change["case"].map(_case_label)
        heatmap = relative_change.set_index("case_label")[metric_columns].rename(columns=pretty_metric_label)
        non_baseline = heatmap.drop(index="基准", errors="ignore")
        if len(non_baseline) < 1 or is_low_information_series(non_baseline.to_numpy().ravel().tolist()):
            results.append(
                skipped_result(
                    "rq1_06",
                    "关键参数敏感性热力图",
                    "RQ1",
                    sensitivity_files,
                    "table_better",
                    "敏感性结果相对基准变化过小，建议直接在表格中列示参数扰动影响。",
                    "skipped_table_better",
                    heatmap.reset_index(),
                    note="该指标建议用表格呈现，不建议单独绘图。",
                )
            )
        else:
            fig, ax = plt.subplots(figsize=(style.figure_width + 1.0, style.figure_height - 0.1))
            sns.heatmap(
                heatmap,
                cmap="RdYlBu_r",
                center=0.0,
                annot=True,
                fmt=".1f",
                linewidths=0.5,
                cbar_kws={"label": "相对基准变化 / %"},
                ax=ax,
            )
            ax.set_title("关键参数扰动对第5年规模与需求的敏感性")
            ax.set_xlabel("指标")
            ax.set_ylabel("扰动情形")
            outputs = save_figure(fig, "rq1_06_validation_sensitivity", export_formats)
            equivalence_error = pd.to_numeric(sensitivity_df["matrix_equivalence_max_abs_diff"], errors="coerce").fillna(0.0).max()
            results.append(
                generated_result(
                    "rq1_06",
                    "关键参数扰动对第5年规模与需求的敏感性",
                    "RQ1",
                    sensitivity_files,
                    "appendix",
                    f"以相对基准变化率集中展示规模与需求的局部敏感性；矩阵等价误差最大值为 {equivalence_error:.2e}。",
                    heatmap.reset_index(),
                    outputs,
                )
            )

    return results
