# RQ3 Pareto Frontier Paper Notes

## 1. Frontier Definition

- Pareto rank is assigned jointly by three indicators: average service accessibility, profit rate, and accessibility Gini coefficient.
- The Pareto frontier therefore represents the efficiency envelope of the tri-objective model, not the final implementable policy set.
- Current frontier size: 11 rank-1 candidate schemes.

## 2. Core Findings for the Main Text

- Frontier points by subsidy policy: targeted_subsidy_0.0 -> 7 points；targeted_subsidy_1.0 -> 2 points；targeted_subsidy_2.0 -> 2 points。
- Only 1 frontier point(s) converged, and 0 frontier point(s) satisfy station-level profit compliance.
- No frontier point reaches the minimum accessibility threshold 0.60; the count above threshold is 0.
- The profit-extreme frontier point is `C:alpha=1.0;E:alpha=1.0;G:alpha=1.0;I:alpha=1.0;J:alpha=2.0` under `targeted_subsidy_2.0`. It reaches profit rate 0.224452 and annual net profit 725.42 万元, but its minimum accessibility is only 0.000000, and Gini rises to 0.512938.
- The fairness-extreme frontier point is `C:alpha=1.0;E:alpha=1.0;G:alpha=1.0;I:alpha=1.0;J:alpha=1.1` under `targeted_subsidy_0.0`. It raises average accessibility to 0.756593, minimum accessibility to 0.050372, and lowers Gini to 0.269215.
- The implementable financial sustainable scheme is `C:alpha=1.0;E:alpha=1.0;G:alpha=1.0;I:alpha=1.0;J:alpha=1.2`. It achieves station-level profit compliance with profit rate 0.026648 and annual net profit 90.35 万元, but its minimum accessibility remains 0.000000.
- The fairness priority scheme is identical to the fairness frontier representative: average accessibility 0.756593, minimum accessibility 0.050372, Gini 0.269215; however, it still fails station-level profit compliance and does not cross the fairness threshold.

## 3. Interpretation for the Discussion Section

- Raising targeted subsidy from 0.0 to 2.0 CNY/order shifts the frontier toward higher profit-rate upper bounds, but the best minimum accessibility on the frontier falls to 0, and inequality indicators worsen.
- This means the current targeted subsidy rule is more effective at supporting premium pricing and revenue capture than at repairing the weakest communities' service accessibility.
- A critical modeling conclusion is that aggregate profit rate alone is insufficient. Some candidate schemes show overall positive profit rates inside [0, 0.08], but still fail scheme-level compliance because at least one station violates the station-level profitability bound.
- Therefore, the Pareto frontier should be used in the paper as a trade-off reference set, while the operational recommendation should still distinguish between a financially implementable scheme and a fairness benchmark scheme.
- Since `joint_feasible_solution_exists = 0`, the paper should explicitly state that pricing alone cannot simultaneously satisfy station-level financial compliance, minimum accessibility threshold, and convergence under the current layout and subsidy cap. Additional construction budget, public-service subsidy, or targeted capacity expansion is still required.

## 4. Suggested Placement in the Paper

- Use the two Pareto figures in the正文 to visualize profit-accessibility-equity trade-offs and the fairness-threshold gap.
- Use `3_2_pareto_representative_schemes.csv` for the正文 comparison table.
- Use `3_2_pareto_policy_summary.csv` in the appendix to support the statement that higher subsidy shifts the frontier shape but does not eliminate the fairness bottleneck.

## 5. Generated Files

- `3_2_pareto_profit_vs_avg_access.png/.pdf`
- `3_2_pareto_min_access_vs_net_profit.png/.pdf`
- `3_2_pareto_policy_summary.csv`
- `3_2_pareto_representative_schemes.csv`
- `3_2_pareto_paper_notes.md`

## 6. Representative Schemes Snapshot

- frontier_profit_peak: subsidy=targeted_subsidy_2.0, profit_rate=0.224452, net_profit=725.42 万元, avg_access=0.616661, min_access=0.000000, gini=0.512938。
- frontier_fairness_peak: subsidy=targeted_subsidy_0.0, profit_rate=0.051008, net_profit=200.00 万元, avg_access=0.756593, min_access=0.050372, gini=0.269215。
- frontier_converged_reference: subsidy=targeted_subsidy_0.0, profit_rate=0.218002, net_profit=697.26 万元, avg_access=0.625730, min_access=0.000000, gini=0.501866。
- financial_sustainable_scheme: subsidy=targeted_subsidy_1.0, profit_rate=0.026648, net_profit=90.35 万元, avg_access=0.627746, min_access=0.000000, gini=0.507888。
- fairness_priority_scheme: subsidy=targeted_subsidy_0.0, profit_rate=0.051008, net_profit=200.00 万元, avg_access=0.756593, min_access=0.050372, gini=0.269215；duplicate_of=frontier_fairness_peak。