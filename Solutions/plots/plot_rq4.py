from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import pandas as pd
import seaborn as sns

from alias_maps import add_canonical_metric_alias_columns, canonicalize_scheme_keys
from data_loader import MissingDataError, read_module_output
from label_maps import pretty_metric_label, short_metric_label
from layout_utils import load_distance_topology, parse_station_plan, station_size_value
from plot_config import ROOT, get_plot_style
from plot_utils import PlotResult, generated_result, save_figure, skipped_result


RQ4_OUTPUT = ROOT / "Solutions" / "RQ4" / "outputs"
DISTANCE_XLSX = ROOT / "data" / "附件4：小区间距离矩阵.xlsx"


def _skip_missing(
    figure_id: str,
    title_cn: str,
    reason: str,
    recommended_location: str,
    input_files: list[str] | None = None,
) -> PlotResult:
    if reason.strip() == "No existing input file found.":
        reason = "当前工作区缺少可读取的结果文件，未在 `Solutions/RQ4/outputs/` 中找到所需 CSV/Excel/JSON 输出。"
    return skipped_result(
        figure_id,
        title_cn,
        "RQ4",
        input_files or [],
        recommended_location,
        reason,
        "skipped_missing_data",
    )


def _load_scenario_summary() -> tuple[pd.DataFrame, list[str]]:
    required_columns = [
        "scenario",
        "q2_station_plan",
        "q2_served_demand_coverage",
        "q2_average_service_access_performance",
        "q2_max_station_utilization",
        "capacity_safety_rate",
        "fairness_average_service_access_performance",
        "fairness_minimum_service_access_performance",
        "financial_annual_net_profit",
        "financial_annual_government_subsidy",
        "financial_profit_rate",
        "fairness_profit_rate",
        "fairness_annual_net_profit",
    ]
    try:
        frame, path = read_module_output(
            "RQ4",
            candidate_keywords=[
                ["scenario", "unified", "summary"],
                ["4_1", "scenario", "unified", "summary"],
                ["unified", "summary"],
            ],
            required_columns=required_columns,
        )
        frame = add_canonical_metric_alias_columns(frame)
        frame = canonicalize_scheme_keys(frame, columns=("scheme_type",))
        return frame, [str(path)]
    except MissingDataError:
        pass

    q2_df, q2_path = read_module_output(
        "RQ4",
        candidate_keywords=[
            ["q2", "scenario", "summary"],
            ["4_1", "q2", "scenario", "summary"],
            ["scenario", "summary", "q2"],
        ],
        required_columns=[
            "scenario",
            "station_plan",
            "served_demand_coverage",
            "average_service_access_performance",
            "max_station_utilization",
            "capacity_safety_rate",
        ],
    )
    q3_df, q3_path = read_module_output(
        "RQ4",
        candidate_keywords=[
            ["q3", "scenario", "summary"],
            ["4_1", "q3", "scenario", "summary"],
            ["scenario", "summary", "q3"],
        ],
        required_columns=[
            "scenario",
            "scheme_type",
            "average_service_access_performance",
            "minimum_service_access_performance",
            "annual_government_subsidy",
            "annual_net_profit",
            "profit_rate",
        ],
    )

    q2_selected = q2_df[
        [
            "scenario",
            "station_plan",
            "served_demand_coverage",
            "average_service_access_performance",
            "max_station_utilization",
            "capacity_safety_rate",
        ]
    ].drop_duplicates(subset=["scenario"]).rename(
        columns={
            "station_plan": "q2_station_plan",
            "served_demand_coverage": "q2_served_demand_coverage",
            "average_service_access_performance": "q2_average_service_access_performance",
            "max_station_utilization": "q2_max_station_utilization",
        }
    )

    q3_df = add_canonical_metric_alias_columns(q3_df)
    q3_df = canonicalize_scheme_keys(q3_df, columns=("scheme_type",))
    financial = q3_df[q3_df["scheme_type"] == "financial_sustainable_scheme"].copy()
    satisfaction_priority = q3_df[q3_df["scheme_type"] == "satisfaction_priority_scheme"].copy()
    if financial.empty or satisfaction_priority.empty:
        raise MissingDataError("RQ4 q3 scenario summary exists, but financial/fairness scheme rows are incomplete.")

    financial_selected = financial[
        ["scenario", "annual_government_subsidy", "annual_net_profit", "profit_rate"]
    ].drop_duplicates(subset=["scenario"]).rename(
        columns={
            "annual_government_subsidy": "financial_annual_government_subsidy",
            "annual_net_profit": "financial_annual_net_profit",
            "profit_rate": "financial_profit_rate",
        }
    )
    satisfaction_selected = satisfaction_priority[
        ["scenario", "average_service_access_performance", "minimum_service_access_performance", "annual_net_profit", "profit_rate"]
    ].drop_duplicates(subset=["scenario"]).rename(
        columns={
            "average_service_access_performance": "satisfaction_average_service_access_performance",
            "minimum_service_access_performance": "satisfaction_minimum_service_access_performance",
            "annual_net_profit": "satisfaction_annual_net_profit",
            "profit_rate": "satisfaction_profit_rate",
        }
    )

    merged = q2_selected.merge(financial_selected, on="scenario", how="inner").merge(satisfaction_selected, on="scenario", how="inner")
    merged["fairness_average_service_access_performance"] = merged["satisfaction_average_service_access_performance"]
    merged["fairness_minimum_service_access_performance"] = merged["satisfaction_minimum_service_access_performance"]
    merged["fairness_annual_net_profit"] = merged["satisfaction_annual_net_profit"]
    merged["fairness_profit_rate"] = merged["satisfaction_profit_rate"]
    missing = [column for column in required_columns if column not in merged.columns]
    if missing:
        raise MissingDataError(f"Fallback scenario summary is missing required columns {missing}")
    return merged, [str(q2_path), str(q3_path)]


def build_rq4_plots(export_formats: list[str]) -> list[PlotResult]:
    results: list[PlotResult] = []
    style = get_plot_style()

    try:
        scenario_df, scenario_files = _load_scenario_summary()
    except MissingDataError as exc:
        shared_reason = str(exc)
        results.extend(
            [
                _skip_missing("rq4_01", "S0-S4 情景核心指标总对比", shared_reason, "main_text"),
                _skip_missing("rq4_02", "多情景服务站拓扑布局对照图", shared_reason, "appendix"),
                _skip_missing("rq4_05", "S0 与 S4 情景关键指标对比", shared_reason, "main_text"),
                _skip_missing("rq4_06", "S0 与 S3 情景下成本上升对利润指标的影响", shared_reason, "appendix"),
            ]
        )
        scenario_df = None
        scenario_files = []

    if scenario_df is not None:
        fig, axes = plt.subplots(2, 2, figsize=(style.figure_width + 4.2, style.figure_height + 3.0), constrained_layout=True)
        served_cols = ["scenario", "q2_served_demand_coverage", "q2_average_service_access_performance"]
        safety_cols = ["scenario", "q2_max_station_utilization", "capacity_safety_rate"]
        scenario_df = add_canonical_metric_alias_columns(scenario_df)
        satisfaction_cols = ["scenario", "satisfaction_average_service_access_performance", "satisfaction_minimum_service_access_performance"]
        money_cols = ["scenario", "financial_annual_net_profit", "financial_annual_government_subsidy"]
        served_long = scenario_df[served_cols].melt(id_vars="scenario", var_name="metric", value_name="value")
        safety_long = scenario_df[safety_cols].melt(id_vars="scenario", var_name="metric", value_name="value")
        satisfaction_long = scenario_df[satisfaction_cols].melt(id_vars="scenario", var_name="metric", value_name="value")
        money_long = scenario_df[money_cols].melt(id_vars="scenario", var_name="metric", value_name="value")
        for frame in (served_long, safety_long, satisfaction_long, money_long):
            frame["metric"] = frame["metric"].map(pretty_metric_label)
        sns.barplot(data=served_long, x="scenario", y="value", hue="metric", palette=style.colors[:2], ax=axes[0, 0])
        sns.barplot(data=safety_long, x="scenario", y="value", hue="metric", palette=style.colors[2:4], ax=axes[0, 1])
        sns.barplot(data=satisfaction_long, x="scenario", y="value", hue="metric", palette=style.colors[1:3], ax=axes[1, 0])
        money_wan = money_long.copy()
        money_wan["value"] = money_wan["value"] / 10000.0
        sns.barplot(data=money_wan, x="scenario", y="value", hue="metric", palette=style.colors[3:5], ax=axes[1, 1])
        axes[0, 0].set_title("覆盖与平均可及性")
        axes[0, 1].set_title("容量安全与最大利用率")
        axes[1, 0].set_title("满意度优先方案绩效")
        axes[1, 1].set_title("财务量级指标")
        axes[1, 1].set_ylabel("金额 / 万元")
        for ax in axes.ravel():
            ax.set_xlabel("情景")
            ax.set_ylabel(ax.get_ylabel() or "指标值")
            ax.legend(frameon=False, title="", fontsize=8)
        outputs = save_figure(fig, "rq4_01_scenario_overview", export_formats)
        results.append(
            generated_result(
                "rq4_01",
                "S0-S4 情景核心指标总对比",
                "RQ4",
                scenario_files,
                "main_text",
                "按覆盖、容量、公平、财务四组拆开，避免利润金额与比例指标同轴失真。",
                pd.concat([served_long, safety_long, satisfaction_long, money_wan], ignore_index=True),
                outputs,
            )
        )

        topology = load_distance_topology(DISTANCE_XLSX)
        fig, axes = plt.subplots(1, 5, figsize=(style.figure_width + 6.4, style.figure_height - 0.3), constrained_layout=True)
        for ax, (_, row) in zip(axes, scenario_df.iterrows()):
            plan = parse_station_plan(row["q2_station_plan"])
            ax.scatter(topology["x"], topology["y"], s=30, c="#e5e7eb", edgecolors="#cbd5e1", linewidth=0.6)
            for _, node in topology.iterrows():
                community = node["community"]
                if community in plan:
                    ax.scatter(node["x"], node["y"], s=station_size_value(plan[community]), c=style.colors[0], edgecolors="#374151", linewidth=1.0)
                    ax.text(node["x"], node["y"], community, ha="center", va="center", fontsize=10, weight="bold")
            ax.set_title(row["scenario"])
            ax.set_xticks([])
            ax.set_yticks([])
        outputs = save_figure(fig, "rq4_02_layout_small_multiples", export_formats)
        results.append(
            generated_result(
                "rq4_02",
                "多情景服务站拓扑布局对照图",
                "RQ4",
                scenario_files,
                "appendix",
                "通过小 multiples 观察情景扰动下站点位置与规模的稳定性。",
                scenario_df[["scenario", "q2_station_plan"]],
                outputs,
                note="注：拓扑布局仅用于展示距离关系，不代表真实地图坐标。",
            )
        )

        s0s4 = scenario_df[scenario_df["scenario"].isin(["S0", "S4"])].copy()
        if len(s0s4) < 2:
            results.append(
                skipped_result(
                    "rq4_05",
                    "S0 与 S4 情景关键指标对比",
                    "RQ4",
                    scenario_files,
                    "main_text",
                    "缺少 S0 或 S4 情景数据。",
                    "skipped_missing_data",
                    s0s4,
                )
            )
        else:
            s0s4_coverage = s0s4[
                ["scenario", "q2_served_demand_coverage", "q2_average_service_access_performance"]
            ].melt(id_vars="scenario", var_name="metric", value_name="value")
            s0s4_safety = s0s4[
                ["scenario", "capacity_safety_rate", "satisfaction_minimum_service_access_performance"]
            ].melt(id_vars="scenario", var_name="metric", value_name="value")
            s0s4_money = s0s4[["scenario", "financial_annual_net_profit"]].copy()
            s0s4_coverage["metric"] = s0s4_coverage["metric"].map(pretty_metric_label).map(short_metric_label)
            s0s4_safety["metric"] = s0s4_safety["metric"].map(pretty_metric_label).map(short_metric_label)
            s0s4_money["financial_annual_net_profit"] = s0s4_money["financial_annual_net_profit"] / 10000.0
            fig, axes = plt.subplots(1, 3, figsize=(style.figure_width + 5.0, style.figure_height), constrained_layout=True)
            sns.barplot(data=s0s4_coverage, x="metric", y="value", hue="scenario", palette=style.colors[:2], ax=axes[0])
            sns.barplot(data=s0s4_safety, x="metric", y="value", hue="scenario", palette=style.colors[:2], ax=axes[1])
            sns.barplot(
                data=s0s4_money,
                x="scenario",
                y="financial_annual_net_profit",
                hue="scenario",
                palette=style.colors[:2],
                dodge=False,
                legend=False,
                ax=axes[2],
            )
            axes[0].set_title("覆盖与平均可及性")
            axes[1].set_title("安全率与公平底线")
            axes[2].set_title("年净利润")
            axes[2].set_ylabel("年净利润 / 万元")
            for ax in axes[:2]:
                ax.set_xlabel("")
                ax.set_ylabel("指标值")
                ax.tick_params(axis="x", rotation=10)
                ax.legend(frameon=False, title="")
            axes[2].set_xlabel("情景")
            outputs = save_figure(fig, "rq4_05_s0_vs_s4", export_formats)
            results.append(
                generated_result(
                    "rq4_05",
                    "S0 与 S4 情景关键指标对比",
                    "RQ4",
                    scenario_files,
                    "main_text",
                    "将预算提高前后的覆盖、底线公平和净利润拆开呈现，避免异质量纲挤在同一子图。",
                    pd.concat([s0s4_coverage, s0s4_safety, s0s4_money], ignore_index=True, sort=False),
                    outputs,
                )
            )

        s0s3 = scenario_df[scenario_df["scenario"].isin(["S0", "S3"])].copy()
        if len(s0s3) < 2:
            results.append(
                skipped_result(
                    "rq4_06",
                    "S0 与 S3 情景下成本上升对利润指标的影响",
                    "RQ4",
                    scenario_files,
                    "appendix",
                    "缺少 S0 或 S3 情景数据。",
                    "skipped_missing_data",
                    s0s3,
                )
            )
        else:
            s0s3 = add_canonical_metric_alias_columns(s0s3)
            rate_long = s0s3[["scenario", "financial_profit_rate", "satisfaction_profit_rate"]].melt(
                id_vars="scenario",
                var_name="metric",
                value_name="value",
            )
            money_long = s0s3[["scenario", "financial_annual_net_profit", "satisfaction_annual_net_profit"]].melt(
                id_vars="scenario",
                var_name="metric",
                value_name="value",
            )
            rate_long["metric"] = rate_long["metric"].map(pretty_metric_label).map(short_metric_label)
            money_long["metric"] = money_long["metric"].map(pretty_metric_label).map(short_metric_label)
            money_long["value"] = money_long["value"] / 10000.0
            fig, axes = plt.subplots(1, 2, figsize=(style.figure_width + 3.2, style.figure_height), constrained_layout=True)
            sns.barplot(data=rate_long, x="metric", y="value", hue="scenario", palette=style.colors[:2], ax=axes[0])
            sns.barplot(data=money_long, x="metric", y="value", hue="scenario", palette=style.colors[2:4], ax=axes[1])
            axes[0].axhline(0.0, color="#666666", linewidth=1.0)
            axes[0].axhline(0.08, color=style.colors[3], linestyle="--", linewidth=1.2, label="0.08 上限")
            axes[0].set_title("成本上升对利润率的影响")
            axes[1].set_title("成本上升对净利润的影响")
            axes[1].set_ylabel("年净利润 / 万元")
            for ax in axes:
                ax.set_xlabel("")
                if ax is axes[0]:
                    ax.set_ylabel("利润率")
                ax.tick_params(axis="x", rotation=10)
                ax.legend(frameon=False, title="")
            outputs = save_figure(fig, "rq4_06_s0_vs_s3_cost_impact", export_formats)
            results.append(
                generated_result(
                    "rq4_06",
                    "S0 与 S3 情景下成本上升对利润指标的影响",
                    "RQ4",
                    scenario_files,
                    "appendix",
                    "将利润率与净利润拆开，解释固定成本上升的传导方向和量级。",
                    pd.concat([rate_long, money_long], ignore_index=True),
                    outputs,
                )
            )

    try:
        sensitivity_df, sensitivity_path = read_module_output(
            "RQ4",
            candidate_keywords=[
                ["4_2", "sensitivity", "coefficient"],
                ["sensitivity", "coefficient"],
                ["4_1", "sensitivity", "coefficient"],
            ],
            required_columns=["scenario", "metric", "sensitivity_coefficient"],
        )
    except MissingDataError as exc:
        results.append(
            _skip_missing(
                "rq4_03",
                "关键指标敏感性系数对比",
                str(exc),
                "main_text",
            )
        )
    else:
        sensitivity_files = [str(sensitivity_path)]
        sensitivity_plot = sensitivity_df.copy()
        sensitivity_plot["metric_label"] = sensitivity_plot["metric"].map(pretty_metric_label).map(short_metric_label)
        fig, axes = plt.subplots(2, 2, figsize=(style.figure_width + 3.4, style.figure_height + 2.6), constrained_layout=True)
        scenario_order = ["S1", "S2", "S3", "S4"]
        for ax, scenario in zip(axes.ravel(), scenario_order):
            subset = sensitivity_plot[sensitivity_plot["scenario"] == scenario].copy()
            subset["abs_coef"] = subset["sensitivity_coefficient"].abs()
            subset = subset.sort_values("abs_coef", ascending=True)
            sns.barplot(data=subset, x="sensitivity_coefficient", y="metric_label", color=style.colors[scenario_order.index(scenario)], ax=ax)
            ax.set_title(f"{scenario} 情景")
            ax.set_xlabel("敏感性系数")
            ax.set_ylabel("指标")
        outputs = save_figure(fig, "rq4_03_sensitivity_coefficients", export_formats)
        results.append(
            generated_result(
                "rq4_03",
                "关键指标敏感性系数对比",
                "RQ4",
                sensitivity_files,
                "main_text",
                "按情景分面后，极端敏感项不再压扁其它指标，强弱关系更可读。",
                sensitivity_plot,
                outputs,
            )
        )

    try:
        robustness_df, robustness_path = read_module_output(
            "RQ4",
            candidate_keywords=[
                ["4_2", "robustness", "metric"],
                ["robustness", "metric"],
                ["4_1", "robustness", "metric"],
            ],
            required_columns=["scenario"],
        )
    except MissingDataError as exc:
        results.append(
            _skip_missing(
                "rq4_04",
                "各情景鲁棒性指标热力图",
                str(exc),
                "appendix",
            )
        )
    else:
        robustness_files = [str(robustness_path)]
        robustness_heatmap = robustness_df.set_index("scenario").rename(columns=pretty_metric_label).rename(columns=short_metric_label)
        fig, ax = plt.subplots(figsize=(style.figure_width + 0.8, style.figure_height + 0.6))
        sns.heatmap(robustness_heatmap, cmap="YlGnBu", annot=True, fmt=".2f", linewidths=0.5, cbar_kws={"label": "鲁棒性指标值"}, ax=ax)
        ax.set_title("各情景鲁棒性指标热力图")
        ax.set_xlabel("鲁棒性指标")
        ax.set_ylabel("情景")
        ax.tick_params(axis="x", labelsize=9)
        outputs = save_figure(fig, "rq4_04_robustness_heatmap", export_formats)
        results.append(
            generated_result(
                "rq4_04",
                "各情景鲁棒性指标热力图",
                "RQ4",
                robustness_files,
                "appendix",
                "适合附录集中展示鲁棒性评价全貌。",
                robustness_heatmap.reset_index(),
                outputs,
            )
        )

    return results
