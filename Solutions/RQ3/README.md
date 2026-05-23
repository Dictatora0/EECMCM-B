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
  仅对已服务对象定义，范围为 `[0.6, 1.0]`；未服务对象记为 `0`。
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
- `profit_compliant = 1[0 <= profit_rate <= 0.08]`

直接成本始终由原始服务量驱动，不允许改回有效人次口径。

## 5. 定价模型

当前代码实现的是站点级统一溢价候选，不是“站点-服务项目级独立定价”。

价格方案写为：

- `p_{j,r} = alpha_j * p_r^0, r = 1,...,5`
- `p_{j,6} = 0`

其中：

- `alpha_j ∈ {1.0, 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.8, 2.0}`

若后续扩展为服务项目独立定价，只能作为扩展模型另写。

## 6. 主站与协同分流解释

当前实现遵循：

1. 老人先按综合效用选择满意度最高的主服务站。
2. 若主站容量不足，仅允许可移动服务通过协同站点分流。
3. 该“分流”表示主站或街道平台派单协同，不表示老人主动改选其他站点。

这也是结果解释和论文表述必须保持的口径。

## 7. 固定点迭代口径

当前实现流程为：

1. 给定站点级价格方案 `alpha_j`。
2. 计算价格满意度并据此更新消费约束需求。
3. 按距离、响应、价格三类效用选择主站和备选协同站。
4. 在线性规划中处理容量约束下的协同分流。
5. 按站点利用率更新响应满意度。
6. 更新 `service_satisfaction` 与 `service_access_performance`。
7. 若 `max_abs_delta < 1e-4` 则停止。
8. 若检测到两周期振荡，则使用阻尼：
   `A_next = 0.5 * A_candidate + 0.5 * A_prev`

输出保留：

- `converged`
- `iterations`
- `max_satisfaction_delta`
- `damping_used`

## 8. 双方案输出

RQ3 至少输出两类方案：

- `financial_sustainable_scheme`
  优先满足利润率合规，报告平均/最低服务绩效、利润、利润率、补贴、收敛状态。
- `fairness_priority_scheme`
  优先提高最低或平均服务绩效，报告其利润率合规性、财政缺口、收敛状态。

若不存在同时满足：

- `profit_compliant = 1`
- `minimum_service_access_performance >= 阈值`
- `converged = 1`

的方案，则输出：

- `joint_feasible_solution_exists = false`

并在汇总中明确写出：

“在当前预算、补贴上限和服务需求下，调价无法同时实现财务合规与公平可及，需要追加补贴、扩容或专项公益服务补贴。”

