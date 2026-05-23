# RQ3 接口说明

本文档用于在实现问题3前固定上游输入接口与指标口径，避免后续代码阶段重新解释 RQ1、RQ2 的输出字段。

## 1. 默认上游入口

RQ3 默认接入问题2主方案，不直接读取安全优先方案。

- 默认方案文件：
  - `Solutions/RQ2/outputs/2_1_best_scheme_summary.csv`
  - `Solutions/RQ2/outputs/2_1_best_scheme_stations.csv`
  - `Solutions/RQ2/outputs/2_1_best_scheme_allocations.csv`
- 备选稳健性方案：
  - `Solutions/RQ2/outputs/2_1_safe_scheme_summary.csv`
  - `Solutions/RQ2/outputs/2_1_safe_scheme_stations.csv`
  - `Solutions/RQ2/outputs/2_1_safe_scheme_allocations.csv`

若切换到安全优先方案，必须在输出文件名、日志和论文表述中显式标注，不能静默替换默认主方案。

## 2. RQ1 必读高精度文件

RQ3 只允许使用高精度输入，不允许回退到取整展示表。

### 2.1 必需文件

- `Solutions/RQ1/outputs/rq1_high_precision_metadata.json`
- `Solutions/RQ1/outputs/1_1_high_precision_year5_population.csv`
- `Solutions/RQ1/outputs/1_3_high_precision_adjusted_demand.csv`
- `Solutions/RQ1/outputs/1_3_high_precision_adjusted_demand_detail.csv`

### 2.2 可选文件

- `Solutions/RQ1/outputs/1_2_high_precision_theoretical_demand.csv`
  - 仅用于“理论需求 vs 可支付需求 vs 实际有效服务”对比分析，不作为主优化约束输入。
- `Solutions/RQ1/outputs/1_1_high_precision_population_by_year.csv`
  - 仅用于趋势图或问题4联动分析；若被调用，必须显式筛选 `year == 5` 后再传给 RQ3。

### 2.3 字段要求

`1_1_high_precision_year5_population.csv`

- 必含字段：`year, community, self_care, semi_disabled, disabled, elderly_total, new_entrants`
- 断言要求：
  - 全部记录满足 `year == 5`
  - 恰好覆盖 10 个小区

`1_3_high_precision_adjusted_demand.csv`

- 必含字段：`community, service, adjusted_monthly_demand`
- 断言要求：
  - 恰好覆盖 `10 × 6 = 60` 条小区-服务记录

`1_3_high_precision_adjusted_demand_detail.csv`

- 必含字段：
  - `community`
  - `care_level`
  - `service`
  - `monthly_income`
  - `budget_limit`
  - `theoretical_per_person`
  - `adjusted_per_person`
  - `adjustment_scale`
  - `population`
  - `adjusted_monthly_demand`
- 断言要求：
  - 恰好覆盖 `10 × 3 × 6 = 180` 条小区-老人类型-服务记录
  - 至少部分 `population` 或 `adjusted_monthly_demand` 为非整数小数，用于防止误读取整表

## 3. RQ2 必读文件与字段

### 3.1 方案总表

`2_1_best_scheme_summary.csv` 必含字段：

- `scheme_type`
- `scheme_code`
- `scheme_detail`
- `station_count`
- `build_cost_wan`
- `geographic_population_coverage`
- `served_population_coverage`
- `served_demand_coverage`
- `average_service_satisfaction`
- `minimum_service_satisfaction`
- `total_raw_served_demand_daily`
- `total_effective_person_times_daily`
- `capacity_safety_rate`
- `max_station_utilization`
- `fully_safe`
- `fully_served_community_count`
- `total_unmet_daily_demand`
- `utilization_variance`
- `annual_net_profit_before_subsidy`
- `annual_net_profit_after_policy_subsidy`

用途说明：

- `summary` 主要用于读取方案编码、站点数量、基线覆盖指标与问题2级别的汇总校验。
- `annual_net_profit_*` 只作为问题2基准运营评价，不直接作为问题3约束输入。

### 3.2 站点表

`2_1_best_scheme_stations.csv` 必含字段：

- `station_community`
- `scale`
- `daily_capacity`
- `assigned_primary_load`
- `assigned_overflow_load`
- `total_load`
- `utilization`
- `annual_service_revenue`
- `annual_direct_cost`
- `annual_fixed_cost`
- `annual_depreciation`
- `annual_government_subsidy_baseline`
- `annual_net_profit_before_subsidy`
- `annual_net_profit_after_policy_subsidy`

用途说明：

- `station_community` 与 `scale` 用于构造 RQ3 的既定站点集合与站点规模。
- `daily_capacity` 是问题3容量约束的直接上游输入。
- 问题3重新定价后需重算收入、补贴和利润率，不能直接复用这些财务值。

### 3.3 小区分配表

`2_1_best_scheme_allocations.csv` 必含字段：

- `community`
- `primary_station`
- `overflow_station`
- `geographic_reachable`
- `actually_served`
- `geographic_population_covered`
- `served_population_covered`
- `raw_served_demand_daily`
- `effective_person_times_daily`
- `primary_load_daily`
- `overflow_load_daily`
- `unmet_load_daily`
- `geographic_satisfaction`
- `response_satisfaction`
- `price_satisfaction`
- `service_satisfaction`

用途说明：

- `primary_station` 和 `overflow_station` 作为问题3初始主站/协同站基线，不代表定价后必须固定不变。
- `service_satisfaction` 仅对 `actually_served = 1` 的小区有效，用作固定点迭代初值。
- 若 `actually_served = 0` 或 `raw_served_demand_daily <= 0`，则 RQ3 中该小区满意度初值必须按 0 处理。

## 4. 统一口径

RQ3 必须沿用 RQ2 已经固定的四层概念，不能混用。

- 地理可达：1000 米内存在可达站点。
- 实际服务：需求被主站或协同站容量承接。
- 有效服务：实际服务人次乘以满意度后的有效完成量。
- 服务满意度：仅对实际服务对象计算；未服务对象在综合绩效中按 0 处理。

## 5. 容量与财务口径

### 5.1 容量口径

由于附件3仅给出“日最大服务人次”，RQ3 与 RQ2 一致，采用同质化服务人次容量：

$$
L_j=\sum_i\sum_r Q_{ijr}\leq Cap_j
$$

当前阶段不要引入服务项目工作量权重，也不要将容量解释为加权工时容量。

### 5.2 财务口径

问题3统一采用以下规则：

- 收入：由有效服务人次驱动。
- 补贴：由非紧急服务的有效服务人次驱动，并受单站每日补贴上限约束。
- 直接支出：由实际承接的原始服务量驱动，不因满意度下降而减少。
- 固定成本与折旧：沿用问题2站点规模对应参数。

对应到记号上：

- `raw served person-times` -> `Q`
- `effective person-times` -> `E = Q × satisfaction`

## 6. RQ3 实现前建议增加的读取断言

- 文件名不得包含 `rounded`、`report`、`summary_rounded`
- 必须先校验 `rq1_high_precision_metadata.json`
- year5 人口文件必须恰好 10 行小区记录
- 小区分配表必须恰好 10 行记录
- 站点表行数必须等于 `summary.station_count`
- 至少部分人口或需求值应保留非整数小数

## 7. 默认实现顺序

推荐问题3实现按以下顺序接线：

1. 读取 `rq1_high_precision_metadata.json`
2. 读取 `1_1_high_precision_year5_population.csv`
3. 读取 `1_3_high_precision_adjusted_demand.csv`
4. 读取 `1_3_high_precision_adjusted_demand_detail.csv`
5. 读取 `2_1_best_scheme_summary.csv`
6. 读取 `2_1_best_scheme_stations.csv`
7. 读取 `2_1_best_scheme_allocations.csv`
8. 以 `service_satisfaction` 作为固定点迭代初值，未服务小区初值置 0
9. 在固定布局上进入价格枚举、补贴计算和利润率校验
