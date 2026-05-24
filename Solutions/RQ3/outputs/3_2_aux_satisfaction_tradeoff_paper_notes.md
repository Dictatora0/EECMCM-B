# RQ3 Auxiliary Satisfaction-First Trade-off Notes

## 1. Frontier Definition

- Auxiliary frontier rank is assigned jointly by average service satisfaction, profit rate, and accessibility Gini coefficient.
- This auxiliary trade-off frontier is an extension analysis set; it is not the题面主结果命名口径.
- Current frontier size: 1 rank-1 candidate schemes.

## 2. Core Findings for the Main Text

- Frontier points by subsidy policy: none -> 1 points。
- Only 1 frontier point(s) converged, and 1 frontier point(s) satisfy station-level profit compliance.
- No frontier point reaches the minimum service satisfaction threshold 0.60; the count above threshold is 1.
- The profit-extreme frontier point is `A:助餐=10.00,日间照料=10.00,上门护理=10.00,康复理疗=10.00,助浴=10.00` under `none`. It reaches profit rate 0.040000 and annual net profit 1.00 万元, but its minimum service satisfaction is only 0.720000, while auxiliary minimum accessibility is 0.410000.
- The satisfaction-extreme frontier point is `A:助餐=10.00,日间照料=10.00,上门护理=10.00,康复理疗=10.00,助浴=10.00` under `none`. It raises average service satisfaction to 0.840000, minimum service satisfaction to 0.720000, and lowers Gini to 0.120000.
- The implementable financial sustainable scheme is `A:助餐=10.00,日间照料=10.00,上门护理=10.00,康复理疗=10.00,助浴=10.00`. It achieves station-level profit compliance with profit rate 0.040000 and annual net profit 1.00 万元, with average service satisfaction 0.840000 and minimum service satisfaction 0.720000.
- The satisfaction priority scheme is identical to the satisfaction-frontier representative: average service satisfaction 0.840000, minimum service satisfaction 0.720000, auxiliary average accessibility 0.660000, and Gini 0.120000; however, it still fails station-level profit compliance and does not cross the satisfaction threshold.

## 3. Interpretation for the Discussion Section

- Accessibility remains an auxiliary interpretation axis here; the report keeps satisfaction on the main axis and uses accessibility only to explain secondary trade-offs.
- If only `none` appears in `subsidy_policy`, this report should be read as a no-extra-subsidy auxiliary comparison among satisfaction-profit-equity trade-offs.
- A critical modeling conclusion is that aggregate profit rate alone is insufficient. Some candidate schemes show overall positive profit rates inside [0, 0.08], but still fail scheme-level compliance because at least one station violates the station-level profitability bound.
- Therefore, the Pareto frontier should be used in the paper as a trade-off reference set, while the operational recommendation should still distinguish between a financially implementable scheme and a satisfaction benchmark scheme.
- Since `joint_feasible_solution_exists = 0`, the paper should explicitly state that pricing alone cannot simultaneously satisfy station-level financial compliance, minimum service satisfaction threshold, and convergence under the current layout and subsidy cap. Additional construction budget, public-service subsidy, or targeted capacity expansion is still required.

## 4. Suggested Placement in the Paper

- Use the two Pareto figures in the正文 to visualize profit-satisfaction-equity trade-offs and the satisfaction-threshold gap; accessibility can be discussed as a secondary indicator.
- Use `3_2_aux_satisfaction_tradeoff_representative_schemes.csv` for extension comparison tables.
- Use `3_2_aux_satisfaction_tradeoff_policy_summary.csv` only as an auxiliary appendix artifact.

## 5. Generated Files

- `3_2_aux_satisfaction_tradeoff_profit_vs_avg_satisfaction.png/.pdf`
- `3_2_aux_satisfaction_tradeoff_min_satisfaction_vs_net_profit.png/.pdf`
- `3_2_aux_satisfaction_tradeoff_policy_summary.csv`
- `3_2_aux_satisfaction_tradeoff_representative_schemes.csv`
- `3_2_aux_satisfaction_tradeoff_paper_notes.md`

## 6. Representative Schemes Snapshot

- frontier_profit_peak: subsidy=none, profit_rate=0.040000, net_profit=1.00 万元, avg_satisfaction=0.840000, min_satisfaction=0.720000, avg_access=0.660000, min_access=0.410000, gini=0.120000。
- frontier_satisfaction_peak: subsidy=none, profit_rate=0.040000, net_profit=1.00 万元, avg_satisfaction=0.840000, min_satisfaction=0.720000, avg_access=0.660000, min_access=0.410000, gini=0.120000；duplicate_of=frontier_profit_peak。
- frontier_converged_reference: subsidy=none, profit_rate=0.040000, net_profit=1.00 万元, avg_satisfaction=0.840000, min_satisfaction=0.720000, avg_access=0.660000, min_access=0.410000, gini=0.120000；duplicate_of=frontier_profit_peak。
- financial_sustainable_scheme: subsidy=none, profit_rate=0.040000, net_profit=1.00 万元, avg_satisfaction=0.840000, min_satisfaction=0.720000, avg_access=0.660000, min_access=0.410000, gini=0.120000；duplicate_of=frontier_profit_peak。
- satisfaction_priority_scheme: subsidy=none, profit_rate=0.040000, net_profit=1.00 万元, avg_satisfaction=0.840000, min_satisfaction=0.720000, avg_access=0.660000, min_access=0.410000, gini=0.120000；duplicate_of=frontier_profit_peak。