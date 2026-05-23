# 3.3 Damping Notes

## Main Findings

- RQ3 主 Pareto 前沿共 11 个点，其中收敛 1 个，未收敛 10 个。
- 这说明论文展示的候选点中，大部分点本身就位于离散跳变更强的高收益/高公平边界，因此非收敛并不是程序错误，而是固定点映射的结构性现象。

### S0_baseline
- evaluated_candidates=180, aggregate_profit_band_count=53, station_profit_compliant_count=3.
- lambda=0.2: convergence_rate=0.6389, mean_iterations=12.75.
- lambda=0.3: convergence_rate=0.6389, mean_iterations=12.75.
- lambda=0.5: convergence_rate=0.6389, mean_iterations=12.75.
- lambda=0.7: convergence_rate=0.6389, mean_iterations=12.75.
- lambda=1.0: convergence_rate=0.6389, mean_iterations=12.75.
- originally non-convergent but converged after damping: 0 candidate-lambda pairs.
- if candidates still do not converge, the likely reason is the joint effect of piecewise response satisfaction, discrete primary-station switching, and capacity-driven overflow jumps.

### S4_budget_140
- evaluated_candidates=180, aggregate_profit_band_count=113, station_profit_compliant_count=3.
- lambda=0.2: convergence_rate=0.1556, mean_iterations=25.87.
- lambda=0.3: convergence_rate=0.1556, mean_iterations=25.87.
- lambda=0.5: convergence_rate=0.1444, mean_iterations=26.11.
- lambda=0.7: convergence_rate=0.1444, mean_iterations=26.11.
- lambda=1.0: convergence_rate=0.1444, mean_iterations=26.11.
- originally non-convergent but converged after damping: 4 candidate-lambda pairs.
- representative improved candidates:
  - S4_budget_140_P018_SB1.0 | lambda=0.2 | targeted_subsidy_1.0 | min_access=0.790029 | net_profit=885333.77.
  - S4_budget_140_P018_SB1.0 | lambda=0.3 | targeted_subsidy_1.0 | min_access=0.790029 | net_profit=885333.77.
  - S4_budget_140_P018_SB2.0 | lambda=0.2 | targeted_subsidy_2.0 | min_access=0.783639 | net_profit=930867.53.
- if candidates still do not converge, the likely reason is the joint effect of piecewise response satisfaction, discrete primary-station switching, and capacity-driven overflow jumps.
