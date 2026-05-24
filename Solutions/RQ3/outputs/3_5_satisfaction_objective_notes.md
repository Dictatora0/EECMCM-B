# 3.5 Satisfaction-Objective Pricing Notes

## 结论

问题3主目标现已统一为“最大化老人满意度”，具体落实为最大化社区平均满意度；`service_access_performance` 仅保留为辅助可及绩效指标，不再承担主目标含义。

站点级统一溢价要求同一站 5 项收费服务共用同一溢价系数，会压缩可行域；站点—服务项目级定价允许不同服务承担不同保本压力，因此理论上扩大可行域。

## S0
- joint_feasible_solution_exists = 1.
- financial_best: avg_satisfaction=0.876073, min_satisfaction=0.850840, station_profit_ok=1.
- satisfaction_priority_best: avg_satisfaction=0.955819, min_satisfaction=0.915741, station_profit_ok=0.
- auxiliary_access_metrics: avg_access=0.747010, min_access=0.705122.
- 找到逐站利润率合规、收敛且满足满意度阈值的联合可行解，可将其作为严格满足题目硬约束的主推荐方案。
- 区域统筹、站点间调剂或统收统支仅能作为扩展政策建议，未被用作主模型可行性判断。

## S4
- joint_feasible_solution_exists = 0.
- financial_best: avg_satisfaction=0.988000, min_satisfaction=0.980000, station_profit_ok=0.
- satisfaction_priority_best: avg_satisfaction=0.988000, min_satisfaction=0.980000, station_profit_ok=0.
- auxiliary_access_metrics: avg_access=0.473103, min_access=0.303843.
- 未找到联合可行解。最接近方案仍受逐站利润率硬约束或满意度阈值限制，问题站点为：A:0.094456, C:-1.000000, G:0.142138, J:-1.000000。
- 区域统筹、站点间调剂或统收统支仅能作为扩展政策建议，未被用作主模型可行性判断。
