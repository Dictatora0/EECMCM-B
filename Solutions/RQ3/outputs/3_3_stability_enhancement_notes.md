# 3.3 Stability Enhancement Notes

## 1. 为什么固定点可能不收敛

- 当前迭代不是连续光滑映射，而是受到响应满意度分段函数、主站离散改选和容量分流线性规划共同影响。
- 当若干社区在两个候选主站之间来回切换时，站点负载与响应满意度会形成跳变，导致 ABAB 型振荡。

## 2. 阻尼是否改善收敛

### S0_baseline
- lambda=0.2: convergence_rate=0.6389.
- lambda=0.3: convergence_rate=0.6389.
- lambda=0.5: convergence_rate=0.6389.
- lambda=0.7: convergence_rate=0.6389.
- lambda=1.0: convergence_rate=0.6389.
- aggregate_profit_band_count=53, station_profit_compliant_count=3, access_threshold_count@0.6=0, converged_count=115.
- aggregate_joint_feasible_count=0, station_joint_feasible_count=0.

### S4_budget_140
- lambda=0.2: convergence_rate=0.1556.
- lambda=0.3: convergence_rate=0.1556.
- lambda=0.5: convergence_rate=0.1444.
- lambda=0.7: convergence_rate=0.1444.
- lambda=1.0: convergence_rate=0.1444.
- aggregate_profit_band_count=113, station_profit_compliant_count=3, access_threshold_count@0.6=108, converged_count=26.
- aggregate_joint_feasible_count=4, station_joint_feasible_count=0.

## 3. 不同公平阈值下财务可持续性变化

- 采用 epsilon-constraint 后，可以直接读取达到不同最低可及性阈值所需的最小财政缺口。
- 若 fiscal_gap=0 且 aggregate_profit_rate_compliant=1，但 station_profit_compliant=0，说明方案总利润率已落入 [0,0.08]，但仍有至少一个站点未满足主模型的逐站利润率约束，因此 joint_feasible_solution_exists 仍为 false。
- 如果某个 epsilon 下 feasible_count=0，表示在当前候选空间和定价口径下不存在达到该阈值的候选方案；这时不能把财政缺口解释为 0，而应解释为“当前候选空间内不可达”。

## 4. S4 扩容是否降低公平达标财政缺口

- epsilon=0.7: S0 feasible_count=0, fiscal_gap=NA; S4 feasible_count=73, fiscal_gap=0.0, aggregate_profit_rate_compliant=1, station_profit_compliant=0, converged=1.
- epsilon=0.8: S0 feasible_count=0, fiscal_gap=NA; S4 feasible_count=12, fiscal_gap=0.0, aggregate_profit_rate_compliant=1, station_profit_compliant=0, converged=1.

## 5. 适合写进正文的结论

- 可以强调：Pareto 前沿中多数点不收敛，主要来自离散选站与容量分流导致的结构性振荡，而不是程序计算错误。
- 可以强调：阻尼在 S0 基本无改善，在 S4 仅对少量边界候选点有效，因此阻尼是数值稳定化手段，不是可行性创造手段。
- 可以强调：S0 在当前布局下连 epsilon=0.4 都无法达到，说明高公平阈值不是简单追加补贴即可解决，而需要预算扩容或站点布局升级。
- 可以强调：S4 扩容后，epsilon=0.7 与 0.8 均已有候选方案，且存在 fiscal_gap=0 的方案；但由于逐站利润率尚未全部合规，joint_feasible_solution_exists 仍然为 false。

## 6. 适合放附录的结果

- 全部 lambda x 候选点的明细表。
- 全部 epsilon x 选择规则的对照表。
- 站点级利润率未达标但方案总利润率达标的诊断明细。

## 7. 不得夸大的结论

- 不能写成“阻尼后模型全部收敛”。
- 不能写成“当前政策已实现财务与公平双达标”；S4 只能写成“总利润率与公平阈值可同时达到，但逐站利润率约束仍未全部满足”。
- 不能把 epsilon-constraint 下的财政缺口理解为现实中唯一所需财政投入，只能解释为在当前候选空间下的模型内最小补足量。