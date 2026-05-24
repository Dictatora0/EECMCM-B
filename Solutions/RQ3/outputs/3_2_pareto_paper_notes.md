# RQ3 Pareto Frontier Paper Notes

## 1. Frontier Definition

- Pareto rank is assigned jointly by three indicators: average service satisfaction, profit rate, and accessibility Gini coefficient.
- The Pareto frontier therefore represents the efficiency envelope of the satisfaction-first tri-objective model, not the final implementable policy set.
- Current frontier size: 1 rank-1 candidate schemes.

## 2. Core Findings for the Main Text

- Frontier points by subsidy policy: none -> 1 points。
- Only 1 frontier point(s) converged, and 1 frontier point(s) satisfy station-level profit compliance.
- No frontier point reaches the minimum service satisfaction threshold 0.60; the count above threshold is 1.
- The profit-extreme frontier point is `A:alpha=1.0` under `none`. It reaches profit rate 0.040000 and annual net profit 1.00 万元, but its minimum service satisfaction is only 0.720000, while auxiliary minimum accessibility is 0.410000.
- The satisfaction-extreme frontier point is `A:alpha=1.0` under `none`. It raises average service satisfaction to 0.840000, minimum service satisfaction to 0.720000, and lowers Gini to 0.120000.
- The implementable financial sustainable scheme is `A:alpha=1.0`. It achieves station-level profit compliance with profit rate 0.040000 and annual net profit 1.00 万元, with average service satisfaction 0.840000 and minimum service satisfaction 0.720000.
- The satisfaction priority scheme is identical to the satisfaction-frontier representative: average service satisfaction 0.840000, minimum service satisfaction 0.720000, auxiliary average accessibility 0.660000, and Gini 0.120000; however, it still fails station-level profit compliance and does not cross the satisfaction threshold.

## 3. Interpretation for the Discussion Section

- Raising targeted subsidy from 0.0 to 2.0 CNY/order shifts the frontier toward higher profit-rate upper bounds, but the best minimum service satisfaction on the frontier still remains constrained, and inequality indicators worsen.
- This means the current targeted subsidy rule is more effective at supporting premium pricing and revenue capture than at repairing the weakest communities' service satisfaction.
- A critical modeling conclusion is that aggregate profit rate alone is insufficient. Some candidate schemes show overall positive profit rates inside [0, 0.08], but still fail scheme-level compliance because at least one station violates the station-level profitability bound.
- Therefore, the Pareto frontier should be used in the paper as a trade-off reference set, while the operational recommendation should still distinguish between a financially implementable scheme and a satisfaction benchmark scheme.
- Since `joint_feasible_solution_exists = 0`, the paper should explicitly state that pricing alone cannot simultaneously satisfy station-level financial compliance, minimum service satisfaction threshold, and convergence under the current layout and subsidy cap. Additional construction budget, public-service subsidy, or targeted capacity expansion is still required.

## 4. Suggested Placement in the Paper

- Use the two Pareto figures in the正文 to visualize profit-satisfaction-equity trade-offs and the satisfaction-threshold gap; accessibility can be discussed as a secondary indicator.
- Use `3_2_pareto_representative_schemes.csv` for the正文 comparison table.
- Use `3_2_pareto_policy_summary.csv` in the appendix to support the statement that higher subsidy shifts the frontier shape but does not eliminate the fairness bottleneck.

## 5. Generated Files

- `3_2_pareto_profit_vs_avg_satisfaction.png/.pdf`
- `3_2_pareto_min_satisfaction_vs_net_profit.png/.pdf`
- `3_2_pareto_policy_summary.csv`
- `3_2_pareto_representative_schemes.csv`
- `3_2_pareto_paper_notes.md`

## 6. Representative Schemes Snapshot

- frontier_profit_peak: subsidy=none, profit_rate=0.040000, net_profit=1.00 万元, avg_satisfaction=0.840000, min_satisfaction=0.720000, avg_access=0.660000, min_access=0.410000, gini=0.120000。
- frontier_satisfaction_peak: subsidy=none, profit_rate=0.040000, net_profit=1.00 万元, avg_satisfaction=0.840000, min_satisfaction=0.720000, avg_access=0.660000, min_access=0.410000, gini=0.120000；duplicate_of=frontier_profit_peak。
- frontier_converged_reference: subsidy=none, profit_rate=0.040000, net_profit=1.00 万元, avg_satisfaction=0.840000, min_satisfaction=0.720000, avg_access=0.660000, min_access=0.410000, gini=0.120000；duplicate_of=frontier_profit_peak。
- financial_sustainable_scheme: subsidy=none, profit_rate=0.040000, net_profit=1.00 万元, avg_satisfaction=0.840000, min_satisfaction=0.720000, avg_access=0.660000, min_access=0.410000, gini=0.120000；duplicate_of=frontier_profit_peak。
- satisfaction_priority_scheme: subsidy=none, profit_rate=0.040000, net_profit=1.00 万元, avg_satisfaction=0.840000, min_satisfaction=0.720000, avg_access=0.660000, min_access=0.410000, gini=0.120000；duplicate_of=frontier_profit_peak。