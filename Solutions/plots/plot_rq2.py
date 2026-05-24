from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import pandas as pd
import seaborn as sns
import math

from data_loader import MissingDataError, read_first_existing
from label_maps import pretty_metric_label, pretty_scheme_label
from layout_utils import load_distance_topology, parse_station_plan, station_size_value
from plot_config import ROOT, ensure_matplotlib_configured
from plot_utils import PlotResult, generated_result, is_low_information_series, save_figure, save_plotly_figure, skipped_result


RQ2_OUTPUT = ROOT / "Solutions" / "RQ2" / "outputs"
DISTANCE_XLSX = ROOT / "data" / "附件4：小区间距离矩阵.xlsx"


def _load_best_summary() -> tuple[pd.DataFrame, list[str]]:
    frame, path = read_first_existing([RQ2_OUTPUT / "2_1_best_scheme_summary.csv"])
    return frame, [str(path)]


def _load_best_stations() -> tuple[pd.DataFrame, list[str]]:
    frame, path = read_first_existing(
        [RQ2_OUTPUT / "2_1_best_scheme_stations.csv"],
        required_columns=[
            "station_community",
            "utilization",
            "scale",
            "daily_capacity",
            "assigned_primary_load",
            "total_load",
            "annual_revenue",
            "annual_subsidy",
            "annual_direct_cost",
            "annual_fixed_cost",
            "annual_depreciation",
            "annual_net_profit",
        ],
    )
    return frame, [str(path)]


def _load_best_allocations() -> tuple[pd.DataFrame, list[str]]:
    frame, path = read_first_existing(
        [RQ2_OUTPUT / "2_1_best_scheme_allocations.csv"],
        required_columns=[
            "community",
            "primary_station",
            "service_access_performance",
            "demand_service_ratio",
            "primary_load_daily",
            "unmet_load_daily",
        ],
    )
    return frame, [str(path)]


def _build_service_flow_sankey(top_links: pd.DataFrame, style) -> object:
    import plotly.graph_objects as go

    communities = top_links["community"].tolist()
    primary_nodes = sorted({value for value in top_links["primary_station"].dropna().tolist() if value})
    station_nodes = []
    for station in primary_nodes:
        if station not in station_nodes:
            station_nodes.append(station)

    labels = [f"小区 {community}" for community in communities] + [f"服务站 {station}" for station in station_nodes]
    colors = [style.colors[0]] * len(communities) + [style.colors[1]] * len(station_nodes)
    node_index = {label: idx for idx, label in enumerate(labels)}

    sources: list[int] = []
    targets: list[int] = []
    values: list[float] = []
    link_colors: list[str] = []
    customdata: list[str] = []

    for _, row in top_links.iterrows():
        community_label = f"小区 {row['community']}"
        primary_station = str(row["primary_station"]) if pd.notna(row["primary_station"]) else ""

        primary_value = float(row.get("primary_load_daily", 0.0))
        if primary_station and primary_value > 0:
            sources.append(node_index[community_label])
            targets.append(node_index[f"服务站 {primary_station}"])
            values.append(primary_value)
            link_colors.append("rgba(91,124,153,0.55)")
            customdata.append("唯一主站承接")

    return go.Figure(
        data=[
            go.Sankey(
                arrangement="snap",
                node=dict(
                    pad=16,
                    thickness=18,
                    line=dict(color="rgba(55,65,81,0.45)", width=0.8),
                    label=labels,
                    color=colors,
                ),
                link=dict(
                    source=sources,
                    target=targets,
                    value=values,
                    color=link_colors,
                    customdata=customdata,
                    hovertemplate="%{customdata}<br>%{source.label} → %{target.label}<br>日承接量: %{value:.0f} 次<extra></extra>",
                ),
            )
        ]
    ).update_layout(
        title="小区—服务站唯一主站服务承接图",
        font=dict(family=style.font_cn, size=12, color="#222222"),
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=20, r=20, t=60, b=20),
    )


def _load_multi_scheme_summaries() -> tuple[pd.DataFrame, list[str]]:
    files = [
        RQ2_OUTPUT / "2_1_best_scheme_summary.csv",
        RQ2_OUTPUT / "2_1_safe_scheme_summary.csv",
        RQ2_OUTPUT / "2_1_robust_scheme_summary.csv",
        RQ2_OUTPUT / "2_1_optimized_scheme_summary.csv",
    ]
    frames = []
    used = []
    for path in files:
        if path.exists():
            frames.append(pd.read_csv(path, encoding="utf-8-sig"))
            used.append(str(path))
    if not frames:
        raise MissingDataError("RQ2 summary files are missing.")
    merged = pd.concat(frames, ignore_index=True)
    label_map = {
        "coverage_fairness_capacity_milp": "最优方案",
        "safety_priority": "安全优先方案",
        "robust_capacity_priority": "鲁棒方案",
        "milp_multiobjective": "优化方案",
    }
    merged["scheme_label_cn"] = merged["scheme_type"].map(label_map).fillna(merged["scheme_type"])
    return merged, used


def _load_pareto_frontier() -> tuple[pd.DataFrame, list[str]]:
    frame, path = read_first_existing(
        [RQ2_OUTPUT / "2_2_pareto_frontier.csv"],
        required_columns=[
            "scheme_label",
            "served_population_coverage",
            "weighted_served_population_coverage",
            "served_demand_coverage",
            "average_service_access_performance",
            "minimum_service_access_performance",
            "capacity_safety_rate",
            "max_station_utilization",
            "annual_net_profit_after_policy_subsidy",
            "profit_compliant",
        ],
    )
    return frame, [str(path)]


def _load_epsilon_summary() -> tuple[pd.DataFrame, list[str]]:
    frame, path = read_first_existing(
        [RQ2_OUTPUT / "2_2_epsilon_constraint_summary.csv"],
        required_columns=[
            "epsilon_min_access_threshold",
            "epsilon_feasible_count",
            "average_service_access_performance",
            "minimum_service_access_performance",
            "annual_net_profit_after_policy_subsidy",
        ],
    )
    return frame, [str(path)]


def _load_capacity_bottleneck() -> tuple[pd.DataFrame, list[str]]:
    frame, path = read_first_existing(
        [RQ2_OUTPUT / "2_2_capacity_bottleneck_top20.csv"],
        required_columns=[
            "scheme_detail",
            "minimum_service_access_performance",
            "max_station_utilization",
            "binding_capacity_risk",
            "full_profit_compliance",
        ],
    )
    return frame, [str(path)]


def build_rq2_plots(export_formats: list[str]) -> list[PlotResult]:
    results: list[PlotResult] = []
    style = ensure_matplotlib_configured()

    try:
        summary_df, summary_files = _load_best_summary()
        stations_df, station_files = _load_best_stations()
        allocations_df, allocation_files = _load_best_allocations()
    except MissingDataError as exc:
        results.append(
            skipped_result(
                "rq2_01",
                "服务站空间布局与覆盖图",
                "RQ2",
                [],
                "main_text",
                str(exc),
                "skipped_missing_data",
            )
        )
        return results

    topology = load_distance_topology(DISTANCE_XLSX)
    plan = parse_station_plan(summary_df.loc[0, "scheme_detail"])
    x_span = max(float(topology["x"].max()) - float(topology["x"].min()), 1.0)
    y_span = max(float(topology["y"].max()) - float(topology["y"].min()), 1.0)
    coverage_radius = 0.16 * math.hypot(x_span, y_span)
    fig, ax = plt.subplots(figsize=(style.figure_width + 0.6, style.figure_height + 0.8))
    ax.scatter(topology["x"], topology["y"], s=120, c="#cfd7de", edgecolors="#6b7280", linewidth=0.8, zorder=2)
    for _, row in topology.iterrows():
        community = row["community"]
        if community in plan:
            ax.add_patch(
                Circle(
                    (row["x"], row["y"]),
                    radius=coverage_radius,
                    fill=False,
                    linestyle="--",
                    linewidth=1.0,
                    edgecolor=style.colors[1],
                    alpha=0.45,
                )
            )
            ax.scatter(row["x"], row["y"], s=station_size_value(plan[community]), c=style.colors[0], edgecolors="#374151", linewidth=1.0, zorder=4)
            ax.text(row["x"], row["y"], community, ha="center", va="center", fontsize=10, color="white", weight="bold", zorder=5)
        else:
            ax.text(row["x"], row["y"], community, ha="center", va="center", fontsize=10, color="#111827", zorder=3)
    ax.set_title("服务站拓扑布局与覆盖关系图")
    ax.set_xlabel("拓扑坐标 X")
    ax.set_ylabel("拓扑坐标 Y")
    ax.set_xticks([])
    ax.set_yticks([])
    outputs = save_figure(fig, "rq2_01_topology_layout", export_formats)
    results.append(
        generated_result(
            "rq2_01",
            "服务站拓扑布局与覆盖关系图",
            "RQ2",
            summary_files + station_files + [str(DISTANCE_XLSX)],
            "main_text",
            "展示服务站选址和规模配置；图注明确说明为拓扑布局而非真实地图。",
            topology,
            outputs,
            note="注：拓扑布局仅用于展示距离关系，不代表真实地图坐标。",
        )
    )

    nonzero_links = allocations_df[allocations_df["primary_load_daily"] > 0].copy()
    if len(nonzero_links) > 18:
        results.append(
            skipped_result(
                "rq2_02",
                "小区—服务站服务流图",
                "RQ2",
                allocation_files,
                "table_better",
                "服务流连线过密，静态图阅读成本高，建议用服务覆盖表或文字说明替代。",
                "skipped_table_better",
                nonzero_links,
                note="该指标建议用表格呈现，不建议单独绘图。",
            )
        )
    else:
        top_links = nonzero_links.copy()
        top_links["station_pair"] = top_links["primary_station"].fillna("")
        top_links = top_links.sort_values(["primary_load_daily"], ascending=False)
        if len(top_links) <= 12:
            try:
                sankey = _build_service_flow_sankey(top_links, style)
                outputs = save_plotly_figure(sankey, "rq2_02_service_flow", export_formats)
                results.append(
                    generated_result(
                        "rq2_02",
                        "小区—服务站唯一主站服务承接图",
                        "RQ2",
                        allocation_files,
                        "main_text",
                        "展示各小区需求仅流向满意度最高的唯一主服务站，符合题目单站选择口径。",
                        top_links,
                        outputs,
                    )
                )
            except Exception:
                fig, ax = plt.subplots(figsize=(style.figure_width + 0.8, style.figure_height + 0.4))
                ax.barh(top_links["community"], top_links["primary_load_daily"], color=style.colors[0], label="唯一主站承接")
                for _, row in top_links.iterrows():
                    ax.text(row["primary_load_daily"] + 10, row["community"], row["station_pair"], va="center", fontsize=9)
                ax.set_title("小区—服务站唯一主站服务承接图")
                ax.set_xlabel("日服务承接量 / 次")
                ax.set_ylabel("小区")
                ax.legend(frameon=False)
                outputs = save_figure(fig, "rq2_02_service_flow", export_formats)
                results.append(
                    generated_result(
                        "rq2_02",
                        "小区—服务站唯一主站服务承接图",
                        "RQ2",
                        allocation_files,
                        "main_text",
                        "Plotly 静态导出失败时自动回退为 Matplotlib 条形图，仍保持唯一主站承接口径。",
                        top_links,
                        outputs,
                    )
                )
        else:
            fig, ax = plt.subplots(figsize=(style.figure_width + 0.8, style.figure_height + 0.4))
            ax.barh(top_links["community"], top_links["primary_load_daily"], color=style.colors[0], label="唯一主站承接")
            for _, row in top_links.iterrows():
                ax.text(row["primary_load_daily"] + 10, row["community"], row["station_pair"], va="center", fontsize=9)
            ax.set_title("小区—服务站唯一主站服务承接图")
            ax.set_xlabel("日服务承接量 / 次")
            ax.set_ylabel("小区")
            ax.legend(frameon=False)
            outputs = save_figure(fig, "rq2_02_service_flow", export_formats)
            results.append(
                generated_result(
                    "rq2_02",
                    "小区—服务站唯一主站服务承接图",
                    "RQ2",
                    allocation_files,
                    "main_text",
                    "链路数适中时可直接用条形图展示唯一主站承接量，避免旧协同站口径混入正文。",
                    top_links,
                    outputs,
                )
            )

    try:
        multi_summary_df, multi_summary_files = _load_multi_scheme_summaries()
    except MissingDataError as exc:
        results.append(
            skipped_result(
                "rq2_03",
                "覆盖率指标对比图",
                "RQ2",
                [],
                "main_text",
                str(exc),
                "skipped_missing_data",
            )
        )
    else:
        coverage = multi_summary_df[
            [
                "scheme_label_cn",
                "geographic_population_coverage",
                "served_population_coverage",
                "weighted_served_population_coverage",
                "served_demand_coverage",
            ]
        ].drop_duplicates()
        coverage = coverage.drop_duplicates(
            subset=[
                "geographic_population_coverage",
                "served_population_coverage",
                "weighted_served_population_coverage",
                "served_demand_coverage",
            ]
        )
        coverage_long = coverage.melt(id_vars="scheme_label_cn", var_name="metric", value_name="value")
        metric_label = {
            "geographic_population_coverage": "地理人口覆盖率",
            "served_population_coverage": "实际服务人口覆盖率",
            "weighted_served_population_coverage": "加权服务人口覆盖率",
            "served_demand_coverage": "服务需求覆盖率",
        }
        coverage_long["metric"] = coverage_long["metric"].map(metric_label)
        fig, ax = plt.subplots(figsize=(style.figure_width + 1.0, style.figure_height))
        sns.barplot(data=coverage_long, x="metric", y="value", hue="scheme_label_cn", palette=style.colors[:4], ax=ax)
        ax.set_title("RQ2 不同方案覆盖率指标对比")
        ax.set_xlabel("")
        ax.set_ylabel("指标值")
        ax.tick_params(axis="x", rotation=12)
        ax.legend(frameon=False, title="")
        outputs = save_figure(fig, "rq2_03_coverage_compare", export_formats)
        results.append(
            generated_result(
                "rq2_03",
                "RQ2 不同方案覆盖率指标对比",
                "RQ2",
                multi_summary_files,
                "main_text",
                "自动剔除数值完全重复的方案，仅保留有区分度的覆盖率比较。",
                coverage_long,
                outputs,
            )
        )

    util = stations_df.sort_values("station_community").copy()
    if is_low_information_series(util["utilization"].tolist()):
        results.append(
            skipped_result(
                "rq2_04",
                "各服务站容量利用率与安全阈值",
                "RQ2",
                station_files,
                "table_better",
                "全部站点利用率几乎一致，单独柱状图信息量不足，建议在正文文字或表格中直接说明。",
                "skipped_table_better",
                util,
                note="该指标建议用表格呈现，不建议单独绘图。",
            )
        )
    else:
        fig, ax = plt.subplots(figsize=(style.figure_width, style.figure_height))
        bars = ax.bar(util["station_community"], util["utilization"], color=style.colors[0], width=0.65)
        for bar, scale in zip(bars, util["scale"]):
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.02, scale, ha="center", va="bottom", fontsize=9)
        ax.axhline(0.85, color=style.colors[3], linestyle="--", linewidth=1.4, label="0.85 安全线")
        ax.axhline(1.0, color="#444444", linestyle=":", linewidth=1.4, label="1.0 容量上限")
        ax.set_ylim(0, max(1.1, util["utilization"].max() + 0.12))
        ax.set_title("各服务站容量利用率与安全阈值")
        ax.set_xlabel("服务站")
        ax.set_ylabel("利用率")
        ax.legend(frameon=False)
        outputs = save_figure(fig, "rq2_04_station_utilization", export_formats)
        results.append(
            generated_result(
                "rq2_04",
                "各服务站容量利用率与安全阈值",
                "RQ2",
                station_files,
                "main_text",
                "直接判断是否存在过载站点，并通过标注规模说明容量结构。",
                util,
                outputs,
            )
        )

    access = allocations_df.sort_values("community").copy()
    fig, ax = plt.subplots(figsize=(style.figure_width + 0.8, style.figure_height))
    ax.bar(access["community"], access["service_access_performance"], color=style.colors[2], width=0.65, label="服务可及绩效")
    if "service_satisfaction" in access.columns:
        ax.plot(access["community"], access["service_satisfaction"], color=style.colors[1], marker="o", linewidth=1.8, label="服务满意度")
        reason = "用于展示社区层面的服务可及差异，并叠加满意度辅助解释。"
        title = "各小区服务可及绩效与满意度"
    else:
        reason = "用于展示社区层面的服务可及差异；当前结果缺少满意度列，因此仅保留可及绩效主指标。"
        title = "各小区服务可及绩效对比"
    ax.set_ylim(0, 1.05)
    ax.set_title(title)
    ax.set_xlabel("小区")
    ax.set_ylabel("指标值")
    ax.legend(frameon=False)
    outputs = save_figure(fig, "rq2_05_access_performance", export_formats)
    results.append(
        generated_result(
            "rq2_05",
            title,
            "RQ2",
            allocation_files,
            "appendix",
            reason,
            access,
            outputs,
        )
    )

    station_financial = stations_df[
        [
            "station_community",
            "annual_revenue",
            "annual_subsidy",
            "annual_direct_cost",
            "annual_fixed_cost",
            "annual_depreciation",
            "annual_net_profit",
        ]
    ].copy()
    if len(station_financial) <= 1:
        results.append(
            skipped_result(
                "rq2_06",
                "Q2 年度收支结构图",
                "RQ2",
                station_files,
                "table_better",
                "站点数量过少，表格比图更直观。",
                "skipped_table_better",
                station_financial,
            )
        )
    else:
        fig, ax = plt.subplots(figsize=(style.figure_width + 0.8, style.figure_height + 0.3))
        ax.bar(station_financial["station_community"], station_financial["annual_revenue"] / 10000, color=style.colors[0], label="营业收入")
        ax.bar(station_financial["station_community"], station_financial["annual_subsidy"] / 10000, bottom=station_financial["annual_revenue"] / 10000, color=style.colors[2], label="补贴收入")
        costs = (station_financial["annual_direct_cost"] + station_financial["annual_fixed_cost"] + station_financial["annual_depreciation"]) / 10000
        ax.plot(station_financial["station_community"], costs, color=style.colors[3], marker="s", linewidth=1.8, label="总成本")
        ax.plot(station_financial["station_community"], station_financial["annual_net_profit"] / 10000, color="#333333", marker="o", linewidth=1.6, label="净利润")
        ax.set_title("各服务站年度收支结构与净利润")
        ax.set_xlabel("服务站")
        ax.set_ylabel("金额 / 万元")
        ax.legend(frameon=False, ncol=2)
        outputs = save_figure(fig, "rq2_06_financial_structure", export_formats)
        results.append(
            generated_result(
                "rq2_06",
                "各服务站年度收支结构与净利润",
                "RQ2",
                station_files,
                "appendix",
                "用于补充站点级财务差异；若正文版面紧张，建议置于附录。",
                station_financial,
                outputs,
            )
        )

    try:
        pareto_df, pareto_files = _load_pareto_frontier()
    except MissingDataError as exc:
        results.append(
            skipped_result(
                "rq2_07",
                "RQ2 Pareto 前沿：净利润与平均服务可及绩效",
                "RQ2",
                [],
                "appendix",
                str(exc),
                "skipped_missing_data",
            )
        )
    else:
        frontier = pareto_df.copy()
        frontier["annual_net_profit_wan"] = pd.to_numeric(frontier["annual_net_profit_after_policy_subsidy"], errors="coerce") / 10000.0
        frontier["average_service_access_performance"] = pd.to_numeric(frontier["average_service_access_performance"], errors="coerce")
        frontier["profit_compliant"] = pd.to_numeric(frontier["profit_compliant"], errors="coerce").fillna(0).astype(int)
        fig, ax = plt.subplots(figsize=(style.figure_width + 0.5, style.figure_height))
        sns.scatterplot(
            data=frontier,
            x="annual_net_profit_wan",
            y="average_service_access_performance",
            hue="profit_compliant",
            style="capacity_safety_rate",
            palette={0: style.colors[3], 1: style.colors[2]},
            s=70,
            ax=ax,
        )
        ax.axvline(0.0, color="#666666", linewidth=1.0)
        ax.set_title("RQ2 Pareto 前沿：净利润与平均服务可及绩效")
        ax.set_xlabel("政策补贴后年净利润 / 万元")
        ax.set_ylabel("平均服务可及绩效")
        handles, labels = ax.get_legend_handles_labels()
        label_map = {"profit_compliant": "利润率达标", "capacity_safety_rate": "容量安全率", "0": "否", "1": "是"}
        ax.legend(handles, [label_map.get(label, label) for label in labels], frameon=False, title="")
        outputs = save_figure(fig, "rq2_07_pareto_profit_vs_access", export_formats)
        results.append(
            generated_result(
                "rq2_07",
                "RQ2 Pareto 前沿：净利润与平均服务可及绩效",
                "RQ2",
                pareto_files,
                "appendix",
                "用于补充说明问题2在容量安全、利润合规约束下的布局权衡，属于扩展分析图，不替代主结论图。",
                frontier,
                outputs,
            )
        )

    try:
        epsilon_df, epsilon_files = _load_epsilon_summary()
    except MissingDataError as exc:
        results.append(
            skipped_result(
                "rq2_08",
                "最低可及绩效阈值变化下的可行方案与绩效",
                "RQ2",
                [],
                "appendix",
                str(exc),
                "skipped_missing_data",
            )
        )
    else:
        epsilon_plot = epsilon_df.copy().sort_values("epsilon_min_access_threshold")
        fig, axes = plt.subplots(1, 2, figsize=(style.figure_width + 3.2, style.figure_height), constrained_layout=True)
        sns.barplot(
            data=epsilon_plot,
            x="epsilon_min_access_threshold",
            y="epsilon_feasible_count",
            color=style.colors[0],
            ax=axes[0],
        )
        axes[0].set_title("最低可及绩效阈值与可行方案数量")
        axes[0].set_xlabel("最低可及性阈值 ε")
        axes[0].set_ylabel("可行方案数量")
        epsilon_valid = epsilon_plot[epsilon_plot["epsilon_feasible_count"] > 0].copy()
        epsilon_long = epsilon_valid[
            [
                "epsilon_min_access_threshold",
                "minimum_service_access_performance",
                "average_service_access_performance",
            ]
        ].melt(id_vars="epsilon_min_access_threshold", var_name="metric", value_name="value")
        epsilon_long["metric"] = epsilon_long["metric"].map(pretty_metric_label)
        sns.lineplot(
            data=epsilon_long,
            x="epsilon_min_access_threshold",
            y="value",
            hue="metric",
            marker="o",
            palette=style.colors[1:3],
            ax=axes[1],
        )
        axes[1].set_title("最低可及绩效阈值与代表方案绩效")
        axes[1].set_xlabel("最低可及性阈值 ε")
        axes[1].set_ylabel("指标值")
        axes[1].legend(frameon=False, title="")
        outputs = save_figure(fig, "rq2_08_epsilon_constraint", export_formats)
        results.append(
            generated_result(
                "rq2_08",
                "最低可及绩效阈值变化下的可行方案与绩效",
                "RQ2",
                epsilon_files,
                "appendix",
                "将最低可及绩效阈值提高后可行空间快速缩小，同时可直观看到最低可及性门槛对代表方案绩效的牵引，属于扩展分析图，不替代主结论图。",
                epsilon_plot,
                outputs,
            )
        )

    try:
        bottleneck_df, bottleneck_files = _load_capacity_bottleneck()
    except MissingDataError as exc:
        results.append(
            skipped_result(
                "rq2_09",
                "容量瓶颈方案最低可及绩效对比",
                "RQ2",
                [],
                "appendix",
                str(exc),
                "skipped_missing_data",
            )
        )
    else:
        bottleneck_plot = bottleneck_df.copy().head(10)
        if len(bottleneck_plot) < 2:
            results.append(
                skipped_result(
                    "rq2_09",
                    "容量瓶颈方案最低可及绩效对比",
                    "RQ2",
                    bottleneck_files,
                    "table_better",
                    "容量瓶颈候选方案数量不足，建议直接列表说明。",
                    "skipped_table_better",
                    bottleneck_plot,
                )
            )
        else:
            bottleneck_plot["scheme_label_short"] = [f"方案{i + 1}" for i in range(len(bottleneck_plot))]
            fig, ax = plt.subplots(figsize=(style.figure_width + 0.8, style.figure_height + 0.5))
            sns.barplot(
                data=bottleneck_plot,
                x="scheme_label_short",
                y="minimum_service_access_performance",
                hue="full_profit_compliance",
                palette={0: style.colors[3], 1: style.colors[2]},
                ax=ax,
            )
            ax.set_title("容量瓶颈候选方案最低可及绩效对比")
            ax.set_xlabel("容量瓶颈候选方案")
            ax.set_ylabel("最低服务可及绩效")
            ax.legend(frameon=False, title="利润合规", labels=["未达标", "达标"])
            outputs = save_figure(fig, "rq2_09_capacity_bottleneck", export_formats)
            results.append(
                generated_result(
                    "rq2_09",
                    "容量瓶颈候选方案最低可及绩效对比",
                    "RQ2",
                    bottleneck_files,
                    "appendix",
                    "从容量约束最紧的候选方案中筛出代表样本，辅助解释为什么部分布局在最低可及绩效底线下仍受容量卡住。",
                    bottleneck_plot,
                    outputs,
                )
            )

    return results
