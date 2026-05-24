from __future__ import annotations

from alias_maps import canonical_metric_key, canonical_scheme_key


METRIC_LABELS = {
    "q2_served_demand_coverage": "服务需求覆盖率",
    "q2_average_service_access_performance": "平均服务可及绩效",
    "q2_max_station_utilization": "最大站点利用率",
    "q2_service_access_performance_stability": "问题2可及绩效稳定性",
    "q3_financial_annual_net_profit": "财务方案年净利润",
    "q3_financial_profit_rate": "财务方案利润率",
    "q3_satisfaction_minimum_service_access_performance": "满意度方案最低可及绩效",
    "q3_fairness_minimum_service_access_performance": "满意度方案最低可及绩效",
    "satisfaction_average_service_access_performance": "满意度方案平均可及绩效",
    "fairness_average_service_access_performance": "满意度方案平均可及绩效",
    "satisfaction_minimum_service_access_performance": "满意度方案最低可及绩效",
    "fairness_minimum_service_access_performance": "满意度方案最低可及绩效",
    "financial_annual_net_profit": "年净利润",
    "financial_profit_rate": "利润率",
    "financial_annual_government_subsidy": "政府补贴",
    "financial_compliance_rate": "财务合规率",
    "capacity_safety_rate": "容量安全率",
    "served_population_coverage": "实际服务人口覆盖率",
    "weighted_served_population_coverage": "加权服务人口覆盖率",
    "served_demand_coverage": "服务需求覆盖率",
    "average_service_access_performance": "平均服务可及绩效",
    "minimum_service_access_performance": "最低服务可及绩效",
    "profit_rate": "利润率",
    "annual_net_profit": "年净利润",
    "profit_compliant": "利润率达标",
    "all_station_profit_compliant": "全站利润率达标",
    "price_satisfaction": "价格满意度",
    "service_access_performance": "服务可及绩效",
    "service_satisfaction": "服务满意度",
    "demand_service_ratio": "需求服务比",
    "RS_loc": "选址稳定性",
    "RS_layout": "规模布局稳定性",
    "geographic_population_coverage_stability": "地理覆盖稳定性",
    "served_population_coverage_stability": "服务人口稳定性",
    "weighted_served_population_coverage_stability": "加权覆盖稳定性",
    "served_demand_coverage_stability": "需求覆盖稳定性",
    "q3_financial_scheme_performance_stability": "财务方案稳定性",
    "q3_satisfaction_scheme_performance_stability": "满意度方案稳定性",
    "q3_fairness_scheme_performance_stability": "满意度方案稳定性",
    "max_station_utilization": "最大站点利用率",
    "fully_safe": "完全安全",
    "financial_profit_rate": "财务方案利润率",
    "satisfaction_profit_rate": "满意度方案利润率",
    "fairness_profit_rate": "满意度方案利润率",
    "satisfaction_annual_net_profit": "满意度方案年净利润",
    "fairness_annual_net_profit": "满意度方案年净利润",
    "year5_elderly_total": "第5年老年总人数",
    "year5_disabled_share": "第5年失能占比",
    "theoretical_total_monthly_demand": "理论月需求总量",
    "adjusted_total_monthly_demand": "消费约束后月需求总量",
    "matrix_equivalence_max_abs_diff": "矩阵等价最大绝对误差",
    "epsilon_min_access_threshold": "最低可及绩效阈值",
    "epsilon_feasible_count": "可行方案数量",
    "binding_capacity_risk": "容量瓶颈风险",
    "full_profit_compliance": "全局利润合规",
    "joint_feasible": "联合可行",
    "break_even_gap": "保本缺口",
    "over_8pct_excess": "超出8%上界幅度",
    "binding_direction": "约束方向",
    "annual_government_subsidy": "政府补贴",
    "annual_net_profit_after_policy_subsidy": "政策补贴后年净利润",
    "annual_net_profit_after_subsidy": "补贴后年净利润",
    "station_count": "站点数量",
    "build_cost_wan": "建设成本",
    "converged": "是否收敛",
    "scenario": "情景",
}


SCHEME_LABELS = {
    "financial_sustainable_scheme": "财务可持续方案",
    "satisfaction_priority_scheme": "满意度优先方案",
    "fairness_priority_scheme": "满意度优先方案",
    "coverage_fairness_capacity_milp": "最优方案",
    "safety_priority": "安全优先方案",
    "robust_capacity_priority": "鲁棒方案",
    "milp_multiobjective": "优化方案",
    "frontier_profit_peak": "利润峰值点",
    "frontier_satisfaction_peak": "满意度峰值点",
    "frontier_fairness_peak": "满意度峰值点",
    "frontier_converged_reference": "收敛参考点",
    "joint_feasible_best_satisfaction": "联合可行满意度最优",
    "financial_best": "财务最优方案",
    "satisfaction_best": "满意度最优方案",
    "fairness_best": "满意度最优方案",
}


def pretty_metric_label(name: str) -> str:
    canonical = canonical_metric_key(name)
    return METRIC_LABELS.get(canonical, METRIC_LABELS.get(name, name.replace("_", " ")))


def pretty_scheme_label(name: str) -> str:
    canonical = canonical_scheme_key(name)
    return SCHEME_LABELS.get(canonical, SCHEME_LABELS.get(name, name))


def short_metric_label(name: str) -> str:
    mapping = {
        "财务方案年净利润": "财务净利润",
        "财务方案利润率": "财务利润率",
        "满意度方案最低可及绩效": "满意度最低可及",
        "满意度方案年净利润": "满意度净利润",
        "实际服务人口覆盖率": "服务人口覆盖",
        "平均服务可及绩效": "平均可及绩效",
        "最大站点利用率": "最大利用率",
        "政府补贴": "政府补贴",
        "服务人口稳定性": "服务人口稳定",
        "地理覆盖稳定性": "地理覆盖稳定",
        "加权覆盖稳定性": "加权覆盖稳定",
        "需求覆盖稳定性": "需求覆盖稳定",
        "问题2可及绩效稳定性": "问题2绩效稳定",
        "财务方案稳定性": "财务方案稳定",
        "满意度方案稳定性": "满意度方案稳定",
        "财务合规率": "财务合规率",
        "容量安全率": "容量安全率",
        "完全安全": "完全安全",
        "第5年老年总人数": "第5年总人数",
        "第5年失能占比": "第5年失能占比",
        "理论月需求总量": "理论月需求",
        "消费约束后月需求总量": "修正后月需求",
        "矩阵等价最大绝对误差": "矩阵误差",
        "最低满意度阈值": "满意度阈值",
        "可行方案数量": "可行方案数",
        "容量瓶颈风险": "瓶颈风险",
        "联合可行": "联合可行",
        "保本缺口": "保本缺口",
        "超出8%上界幅度": "超8%幅度",
        "政府补贴": "政府补贴",
    }
    return mapping.get(name, name)
