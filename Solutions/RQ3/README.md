# RQ3 接口与口径说明

本文档与 `Solutions/RQ3/3_1.py` 当前实现保持一致，用于统一问题3的输入、定价、固定点迭代、服务绩效与财务口径。

## 1. 上游输入

RQ3 默认读取问题2主方案：

- `Solutions/RQ2/outputs/2_1_best_scheme_summary.csv`
- `Solutions/RQ2/outputs/2_1_best_scheme_stations.csv`
- `Solutions/RQ2/outputs/2_1_best_scheme_allocations.csv`

安全优先方案只能作为备选输入显式切换，不能在文档或结果中静默替代主方案。

RQ3 只允许读取 RQ1 高精度文件：

- `rq1_high_precision_metadata.json`
- `1_1_high_precision_year5_population.csv`
- `1_3_high_precision_adjusted_demand.csv`
- `1_3_high_precision_adjusted_demand_detail.csv`

## 2. 四类核心量

问题2和问题3统一使用以下四类量：

- `raw_served_demand`
  表示站点实际承接的原始服务需求人次，用于容量占用和直接成本。
- `effective_person_times`
  定义为 `raw_served_demand * service_satisfaction`，用于收入、补贴和绩效评价。
- `service_satisfaction`
  表示题目满意度规则下的社区综合满意度，按 `S = 0.2S1 + 0.3S2 + 0.5S3` 计算；仅对已服务对象定义，范围为 `[0.6, 1.0]`；未服务对象记为 `0`。
- `service_access_performance`
  定义为 `service_satisfaction * min(1, raw_served_demand / adjusted_demand)`，范围为 `[0, 1]`；零服务时记为 `0`。

输出层面不再把 `service_access_performance` 叫作“满意度”。

## 3. 覆盖率口径

问题2和问题3同时保留以下覆盖率：

- `geographic_population_coverage`
- `served_population_coverage`
- `weighted_served_population_coverage`
- `served_demand_coverage`

其中：

`weighted_served_population_coverage = sum_i P_i * min(1, q_i / d_i) / sum_i P_i`

这里 `P_i` 为第5年高精度老年人口，`q_i` 为小区实际承接服务量，`d_i` 为消费约束后的总需求。

## 4. 财务口径

问题2和问题3统一采用：

- `annual_revenue = effective_person_times * price`
- `annual_subsidy = min(2 * effective_person_times_excluding_emergency, subsidy_cap)`
- `annual_direct_cost = raw_served_demand * direct_cost`
- `annual_fixed_cost = 365 * daily_fixed_cost`
- `annual_depreciation = construction_cost_yuan / 20`
- `annual_total_cost = annual_direct_cost + annual_fixed_cost + annual_depreciation`
- `annual_net_profit = annual_revenue + annual_subsidy - annual_total_cost`
- `profit_rate = annual_net_profit / annual_total_cost`
- 对站点级财务表，`profit_compliant = 1[0 <= profit_rate <= 0.08]`
- 对方案汇总表，`profit_compliant = 1` 表示全部已建站点均满足上述利润率约束，而不是只看汇总 `profit_rate`

直接成本始终由原始服务量驱动，不允许改回有效人次口径。

## 5. 定价模型

当前主实现已经采用逐站逐服务定价，而不是“每站一个统一溢价系数”。

主结果口径写为：

- `p_{j,r}` 对 `r = 1,...,5` 独立取值
- `p_{j,6} = 0`

汇总输出中的规范说明为：

- `pricing_model = station_service_level_pricing`
- `pricing_formula = p_{j,r} independent for r=1,...,5; p_{j,6}=0`

求解时仍通过有限离散候选集合搜索，以保证可复现与可解释；但结果含义上已经是“每个站点每项收费服务可独立定价”。

## 6. 主站选择与容量承接口径

当前实现严格遵循：

1. 老人只在 `d_ij <= 1000` 的站点中比较综合效用。
2. 每个小区只选择满意度最高的唯一主服务站。
3. 这一步不看剩余容量；若先看容量，就不再是题面的“选择满意度最高站”。
4. 若主站容量不足，不再转到第二站，而是对所有选择该站的小区按统一承接比例 `rho_j` 服务。
5. 未承接部分直接记为 `unmet`。

这也是结果解释和论文表述必须保持的口径。

## 7. 固定点迭代口径

当前实现流程为：

1. 给定逐站逐服务价格方案 `p_{j,r}`。
2. 计算价格满意度并据此更新消费约束需求。
3. 按距离、响应、价格三类效用为每个小区选择唯一主站。
4. 对每个站点按总需求与容量计算统一承接比例 `rho_j`。
5. 按站点利用率更新响应满意度。
6. 更新 `service_satisfaction` 与 `service_access_performance`。
7. 若 `max_abs_delta < 1e-4` 则停止。
8. 若检测到两周期振荡，则使用阻尼：
   `A_next = 0.5 * A_candidate + 0.5 * A_prev`

输出保留：

- `converged`
- `iterations`
- `max_satisfaction_delta`
  代码中该字段承担 `max_abs_delta` 的兼容输出角色。
- `damping_used`

## 8. 价格满意度分段

当前实现按题目分段规则计算 `S3`：

- `actual_price <= base_price` 时，`S3 = 1.00`
- `0 < premium <= 10%` 时，`S3 = 0.90`
- `10% < premium <= 20%` 时，`S3 = 0.75`
- `premium > 20%` 时，`S3 = 0.60`

## 9. 题面外个人补贴机制

当前主实现不启用额外的面向个人或群体的定向补贴。问题3只保留题目给定的站点级政府补贴：

- 除紧急救助外，按实际有效服务人次补贴 `2 元/人次`
- 单站每日补贴上限按规模分别为 `1000/1800/2600 元`

若后续研究要加入低收入或脆弱群体定向补贴，只能作为扩展模型单列说明，不能与题目主方案混写。
## 10. 主结果与辅助扩展输出

RQ3 当前输出分成两层：

- 主结果：`3_1_best_price_scheme_*`
  这是题面主模型的标准输出，正文应优先引用这一组文件。
- 辅助扩展：`3_1_aux_financial_best_price_scheme_*`、`3_1_aux_fairness_best_price_scheme_*`、`3_1_aux_pareto_frontier.csv`、`3_1_aux_dual_scheme_comparison.csv`
  这些文件只用于扩展比较、附录或补充分析，不覆盖主结果。

辅助扩展中的满意度优先方案若未收敛或不满足利润率约束，只能作为参考方案解释，不能写成“题目唯一最优方案”。

若不存在同时满足：

- `profit_compliant = 1`
- `minimum_service_satisfaction >= 阈值`
- `converged = 1`

的方案，则输出：

- `joint_feasible_solution_exists = false`

并在汇总中明确写出：

“在当前预算、补贴上限和服务需求下，调价无法同时实现财务合规与满意度阈值，需要追加补贴、扩容或专项公益服务补贴。”

## 11. 辅助图表输出文件名前缀

满意度主轴、可及性辅轴的辅助图表文件现统一采用：

- `3_2_aux_satisfaction_tradeoff_*`

主结果定价文件则统一采用：

- `3_1_best_price_scheme_*`
- `3_1_aux_*`

## 12. 兼容字段名说明

为兼容既有缓存、审计脚本和旧版图表链路，当前仓库仍保留少量 legacy 字段名。它们只作为兼容输出存在，内部主逻辑与论文表述统一使用 satisfaction 口径。

- 方案标签兼容：
  - canonical：`satisfaction_priority_scheme`
  - legacy：`fairness_priority_scheme`
- 合规字段兼容：
  - canonical：`satisfaction_compliant`
  - legacy：`fair_satisfaction_compliant`
- 问题4统计字段兼容：
  - canonical：`q3_satisfaction_minimum_service_access_performance`
  - legacy：`q3_fairness_minimum_service_access_performance`
  - canonical：`q3_satisfaction_scheme_performance_stability`
  - legacy：`q3_fairness_scheme_performance_stability`

论文正文、图题和结果讨论应优先使用 canonical satisfaction 命名，不建议再使用 fairness 口径描述满意度主目标方案。

若需要完整对照表，请直接查看：

- [兼容字段矩阵](../compatibility_matrix.md)
- `3_2_aux_satisfaction_tradeoff_paper_notes.md`

是论文和复核时最常用的四个文件；`service_access_performance` 仍会保留在这些文件中，但仅作为辅助可及绩效指标解释。
