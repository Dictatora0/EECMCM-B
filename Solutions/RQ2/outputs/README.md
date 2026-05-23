# RQ2 Outputs

本目录保存问题2的选址、规模、分配与基准价财务评价输出。生成脚本为 `Solutions/RQ2/2_1.py`，也可通过 `Solutions/RQ2/run_all.py` 调用。

## 用途

- 输出问题2主方案与安全优先备选方案。
- 为问题3提供布局、站点规模和小区分配基线。
- 为论文提供覆盖率、服务绩效、容量安全和基准价财务评价表。

## 主文件

- `2_1_best_scheme_summary.csv`
- `2_1_best_scheme_stations.csv`
- `2_1_best_scheme_allocations.csv`

其中 `best_scheme` 是当前问题3默认读取的正式输入。

## 文件说明

### 主方案

- `2_1_best_scheme_summary.csv`
  - 含义：问题2主方案汇总表。
  - 关键字段：
    - 覆盖率：`geographic_population_coverage`, `served_population_coverage`, `weighted_served_population_coverage`, `served_demand_coverage`
    - 满意度与绩效：`average_service_satisfaction`, `minimum_service_satisfaction`, `average_service_access_performance`, `minimum_service_access_performance`
    - 服务量：`total_adjusted_demand_daily`, `total_raw_served_demand_daily`, `total_effective_person_times_daily`
    - 安全性：`capacity_safety_rate`, `max_station_utilization`, `fully_safe`
    - 财务：`annual_revenue`, `annual_subsidy`, `annual_direct_cost`, `annual_fixed_cost`, `annual_depreciation`, `annual_total_cost`, `annual_net_profit_before_subsidy`, `annual_net_profit_after_policy_subsidy`, `profit_rate`, `profit_compliant`

- `2_1_best_scheme_stations.csv`
  - 含义：主方案站点级明细。
  - 关键字段：
    - 负荷：`assigned_primary_load`, `assigned_overflow_load`, `total_load`, `utilization`
    - 财务：`annual_service_revenue`, `annual_subsidy`, `annual_direct_cost`, `annual_fixed_cost`, `annual_depreciation`, `annual_total_cost`, `annual_net_profit_before_subsidy`, `annual_net_profit_after_policy_subsidy`, `profit_rate`, `profit_compliant`

- `2_1_best_scheme_allocations.csv`
  - 含义：主方案小区级分配结果。
  - 关键字段：
    - 站点分配：`primary_station`, `overflow_station`
    - 覆盖与服务：`geographic_reachable`, `actually_served`, `geographic_population_covered`, `served_population_covered`
    - 服务量：`adjusted_demand_daily`, `raw_served_demand_daily`, `effective_person_times_daily`, `demand_service_ratio`
    - 绩效：`service_satisfaction`, `service_access_performance`
    - 分解满意度：`geographic_satisfaction`, `response_satisfaction`, `price_satisfaction`

### 安全优先备选方案

- `2_1_safe_scheme_summary.csv`
- `2_1_safe_scheme_stations.csv`
- `2_1_safe_scheme_allocations.csv`

这些文件对应安全优先备选方案，不是问题3默认读取输入。若要用于问题3，需显式切换。

### 对比与诊断输出

- `2_1_dual_scheme_compare.csv`
  - 含义：主方案与安全优先方案对比。

- `2_1_top10_schemes.csv`
  - 含义：候选方案前10名，用于解释排序和方案稳定性。

- `2_1_safety_threshold_tradeoff.csv`
  - 含义：不同容量安全阈值请求下的折中结果。

## 结果口径说明

- `raw_served_demand_daily` 用于容量占用和直接成本。
- `effective_person_times_daily = raw_served_demand_daily * service_satisfaction`，用于收入、补贴和绩效。
- `service_satisfaction` 是已服务对象满意度，非零时应位于 `0.6` 到 `1.0`。
- `service_access_performance` 是考虑服务承接比例后的绩效，允许位于 `0` 到 `1`。
- 零服务小区应满足：
  - `raw_served_demand_daily = 0`
  - `effective_person_times_daily = 0`
  - `service_satisfaction = 0`
  - `service_access_performance = 0`
- 直接成本由原始服务量驱动，收入和补贴由有效服务人次驱动。

## 与问题3的关系

- 问题3默认读取：
  - `2_1_best_scheme_summary.csv`
  - `2_1_best_scheme_stations.csv`
  - `2_1_best_scheme_allocations.csv`
- 若要用安全优先方案做压力测试，需要修改问题3输入源，不能只改文档说明。

## 重跑建议

- 若 RQ1 的高精度人口或消费约束需求变化，应重跑 `python Solutions/RQ2/2_1.py`。
- 若预算、容量安全阈值、财务参数或分配口径变化，也应重跑本题并同步重跑问题3与问题4。
