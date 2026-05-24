# 3.5 Satisfaction-Objective Pricing Notes

## 结论

问题3主目标现已统一为“最大化老人满意度”，具体落实为最大化社区平均满意度；`service_access_performance` 仅保留为辅助可及绩效指标，不再承担主目标含义。

站点级统一溢价要求同一站 5 项收费服务共用同一溢价系数，会压缩可行域；站点—服务项目级定价允许不同服务承担不同保本压力，因此理论上扩大可行域。

## S0
- joint_feasible_solution_exists = 0.
- financial_best: avg_satisfaction=0.860874, min_satisfaction=0.820548, station_profit_ok=1.
- satisfaction_priority_best: avg_satisfaction=0.955819, min_satisfaction=0.915741, station_profit_ok=0.
- auxiliary_access_metrics: avg_access=0.737329, min_access=0.682983.
- 未找到联合可行解。最接近方案仍受逐站利润率硬约束或满意度阈值限制，问题站点为：无。
- 区域统筹、站点间调剂或统收统支仅能作为扩展政策建议，未被用作主模型可行性判断。

## S4
- joint_feasible_solution_exists = 0.
- financial_best: avg_satisfaction=0.987357, min_satisfaction=0.978681, station_profit_ok=0.
- satisfaction_priority_best: avg_satisfaction=0.987357, min_satisfaction=0.978681, station_profit_ok=0.
- auxiliary_access_metrics: avg_access=0.718486, min_access=0.638213.
- 未找到联合可行解。最接近方案仍受逐站利润率硬约束或满意度阈值限制，问题站点为：A:-1.000000, C:-1.000000, G:0.146902, J:0.156767。
- 区域统筹、站点间调剂或统收统支仅能作为扩展政策建议，未被用作主模型可行性判断。
