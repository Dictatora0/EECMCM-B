# RQ3 Outputs

本目录保存问题3的站点级统一溢价定价结果、双方案比较、固定点迭代记录和群体可及性分析。生成脚本为 `Solutions/RQ3/3_1.py`。

## 用途

- 输出财务可持续方案与公平优先方案的权衡结果。
- 供问题4读取情景下的定价、收敛和利润表现。
- 为论文提供双方案总表、站点财务表、小区服务绩效表和迭代收敛证据。

## 当前实现边界

- 当前实现是站点级统一溢价，不是站点-服务项目级独立定价。
- 定价形式：
  - `p_{j,r} = alpha_j * p_r^0, r = 1,...,5`
  - `p_{j,6} = 0`
- `3_1_best_price_scheme_*` 与 `3_1_financial_best_price_scheme_*` 内容一致，属于兼容别名输出。

## 主文件

- `3_1_dual_scheme_comparison.csv`
- `3_1_financial_best_price_scheme_summary.csv`
- `3_1_fairness_best_price_scheme_summary.csv`
- `3_1_scheme_status_summary.csv`

## 文件说明

### 双方案总表

- `3_1_dual_scheme_comparison.csv`
  - 含义：双方案总对照表。
  - 关键字段：
    - 方案标签：`scheme_label`
    - 收敛：`iteration_count`, `iterations`, `converged`, `damping_used`
    - 约束状态：`profit_compliant`, `fair_satisfaction_compliant`, `feasible_station_count`
    - 绩效：`average_service_satisfaction`, `minimum_service_satisfaction`, `average_service_access_performance`, `minimum_service_access_performance`
    - 群体指标：`vulnerable_service_satisfaction`, `low_income_service_satisfaction`, `low_income_served_coverage`
    - 覆盖：`weighted_served_population_coverage`, `served_demand_coverage`
    - 财务：`annual_government_subsidy`, `annual_service_revenue`, `annual_direct_cost`, `annual_fixed_cost`, `annual_depreciation`, `annual_total_cost`, `annual_net_profit_before_subsidy`, `annual_net_profit_after_subsidy`, `annual_net_profit`, `profit_rate`
    - 缺口与结论：`financial_gap_to_break_even`, `fiscal_gap`, `joint_feasible_solution_exists`, `summary`

- `3_1_scheme_status_summary.csv`
  - 含义：仅保留双方案名称、联合可行性和摘要文字，适合快速引用。

### 财务可持续方案

- `3_1_financial_best_price_scheme_summary.csv`
- `3_1_financial_best_price_scheme_stations.csv`
- `3_1_financial_best_price_scheme_communities.csv`
- `3_1_financial_best_price_scheme_iteration_trace.csv`
- `3_1_financial_best_price_scheme_accessibility_groups.csv`

说明：

- `summary`：财务可持续方案汇总。
- `stations`：站点级财务表，包含 `raw_served_demand_daily`, `effective_person_times_daily`, `profit_rate`, `profit_compliant`, `emergency_public_loss` 等字段。
- `communities`：小区级服务结果，包含 `service_satisfaction`, `service_access_performance`, `demand_service_ratio`, `price_satisfaction` 等字段。
- `iteration_trace`：固定点迭代轨迹，包含 `max_satisfaction_delta`, `average_service_satisfaction`, `feasible_station_count`, `total_subsidy`, `damping_used`。
- `accessibility_groups`：按群体汇总的可及性解释表。

### 公平优先方案

- `3_1_fairness_best_price_scheme_summary.csv`
- `3_1_fairness_best_price_scheme_stations.csv`
- `3_1_fairness_best_price_scheme_communities.csv`
- `3_1_fairness_best_price_scheme_iteration_trace.csv`
- `3_1_fairness_best_price_scheme_accessibility_groups.csv`

结构与财务可持续方案相同，但排序优先级不同，且可能出现：

- `converged = 0`
- `profit_compliant = 0`

因此该方案只能作为公平取向参考，不应被写成唯一最优。

### 兼容别名文件

- `3_1_best_price_scheme_summary.csv`
- `3_1_best_price_scheme_stations.csv`
- `3_1_best_price_scheme_communities.csv`
- `3_1_best_price_scheme_iteration_trace.csv`
- `3_1_best_price_scheme_accessibility_groups.csv`

这些文件与 `3_1_financial_best_price_scheme_*` 内容完全一致，用于兼容既有调用链。

### 候选方案

- `3_1_top_price_schemes.csv`
  - 含义：代表性候选价格方案排序表，可用于解释“为什么选中当前双方案”。

## 结果口径说明

- `service_satisfaction` 是已服务对象满意度，非零时应在 `0.6` 到 `1.0`。
- `service_access_performance` 是考虑服务承接比例后的绩效，允许在 `0` 到 `1`。
- `raw_served_demand_daily` 驱动容量与直接成本。
- `effective_person_times_daily` 驱动收入、补贴和绩效。
- 方案汇总层的 `profit_compliant = 1` 表示全部站点均满足利润率约束，而不是只看汇总 `profit_rate`。
- 若 `joint_feasible_solution_exists = false`，应解释为当前预算、补贴和需求条件下公平与财务不可兼得。

## 重跑建议

- 若问题2主方案变化，应重跑 `python Solutions/RQ3/3_1.py`。
- 若价格候选集、补贴上限、利润率约束、公平阈值或固定点迭代参数变化，也应重跑本题。
