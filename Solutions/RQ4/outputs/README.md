# RQ4 Outputs

本目录保存问题4的情景重求解结果、灵敏度分析、鲁棒性指标和论文解释备注。生成脚本为 `Solutions/RQ4/4_1.py`。

## 用途

- 汇总 S0 至 S4 的情景化问题2与问题3结果。
- 输出灵敏度系数和鲁棒性评价表。
- 记录 S4 预算放宽后的专项诊断结论。

## 情景定义

- `S0`：baseline
- `S1`：`elderly_growth_rate = 0.08`
- `S2`：`p12 = 0.055`, `p23 = 0.095`
- `S3`：`fixed_cost_multiplier = 1.2`
- `S4`：`budget_limit = 140`

所有主表均显式写出 `budget_limit`, `fixed_cost_multiplier`, `p12`, `p23`, `elderly_growth_rate`，便于追溯。

## 主文件

- `4_1_q2_scenario_summary.csv`
- `4_1_q3_scenario_summary.csv`
- `4_2_sensitivity_coefficients.csv`
- `4_2_robustness_metrics.csv`
- `4_1_s4_diagnostics.json`
- `4_interpretation_notes.md`

## 文件说明

### 情景化问题2汇总

- `4_1_q2_scenario_summary.csv`
  - 含义：各情景下问题2布局与基准价财务评价汇总。
  - 关键字段：
    - 情景配置：`scenario`, `budget_limit`, `fixed_cost_multiplier`, `p12`, `p23`, `elderly_growth_rate`
    - 布局：`station_plan`, `total_construction_cost`
    - 覆盖：`geographic_population_coverage`, `served_population_coverage`, `weighted_served_population_coverage`, `served_demand_coverage`
    - 绩效：`average_service_access_performance`, `minimum_service_access_performance`
    - 安全性：`capacity_safety_rate`, `max_station_utilization`, `fully_safe`
    - 财务：`annual_net_profit_before_subsidy`, `annual_net_profit_after_policy_subsidy`

### 情景化问题3双方案汇总

- `4_1_q3_scenario_summary.csv`
  - 含义：各情景下问题3双方案汇总。
  - 关键字段：
    - 情景配置：`scenario`, `budget_limit`, `fixed_cost_multiplier`, `p12`, `p23`, `elderly_growth_rate`
    - 方案：`scheme_type`, `station_plan`
    - 绩效：`average_service_access_performance`, `minimum_service_access_performance`
    - 财务：`annual_government_subsidy`, `annual_net_profit`, `profit_rate`, `profit_compliant`
    - 收敛：`converged`, `iterations`
    - 缺口：`fiscal_gap_if_any`

### 灵敏度系数

- `4_2_sensitivity_coefficients.csv`
  - 含义：正式论文建议引用的灵敏度系数表。
  - 字段：`scenario, perturbed_parameter, parameter_relative_change, metric, baseline_value, scenario_value, metric_absolute_change, metric_relative_change, sensitivity_coefficient, sensitivity_level`
  - 说明：分母只使用被扰动参数变化率。

- `4_1_sensitivity_coefficients.csv`
  - 含义：兼容副本。
  - 说明：当前内容与 `4_2_sensitivity_coefficients.csv` 一致。

### 鲁棒性指标

- `4_2_robustness_metrics.csv`
  - 含义：正式论文建议引用的鲁棒性表。
  - 字段：`scenario, RS_loc, RS_layout, geographic_population_coverage_stability, served_population_coverage_stability, weighted_served_population_coverage_stability, served_demand_coverage_stability, q2_service_access_performance_stability, q3_financial_scheme_performance_stability, q3_fairness_scheme_performance_stability, financial_compliance_rate, capacity_safety_rate, max_station_utilization, fully_safe`
  - 说明：
    - `RS_loc` 是位置 Jaccard 稳定性。
    - `RS_layout` 是规模一致率。
    - Q2 与 Q3 的服务绩效稳定性已分开报告。

- `4_1_robustness_metrics.csv`
  - 含义：兼容副本。
  - 说明：当前内容与 `4_2_robustness_metrics.csv` 一致。

### S4 诊断与解释

- `4_1_s4_diagnostics.json`
  - 含义：预算放宽到 140 万后的专项核查结果。
  - 典型用途：
    - 检查是否真实使用超过 120 万且不超过 140 万预算。
    - 检查 S4 是否优于或不弱于 S0。
    - 若 S4 与 S0 相同，用于记录原因和候选方案信息。

- `4_interpretation_notes.md`
  - 含义：可直接用于论文撰写的解释要点。
  - 当前已根据真实重跑结果写明：S4 不能再解释为“预算提高无效”。

## 结果口径说明

- `S1`、`S2` 需要重跑 RQ1、RQ2、RQ3。
- `S3` 复用基准需求，主要重跑 RQ2 财务评价与 RQ3 定价/财务。
- `S4` 复用基准需求，但必须真实把 `budget_limit = 140` 传入 RQ2 再重跑 RQ3。
- 鲁棒性表中的 Q2 与 Q3 指标不得混用。

## 当前重跑后已验证的关键事实

- S4 当前真实方案不是 S0 的复制。
- S4 已真实使用 `140.0` 万预算。
- S4 的 `served_demand_coverage` 和 `average_service_access_performance` 均高于 S0。
- 灵敏度分母已修正为仅使用被扰动参数变化率。

## 重跑建议

- 若问题1到问题3任一上游口径变化，应重跑 `python Solutions/RQ4/4_1.py`。
- 若论文引用情景表、灵敏度表或鲁棒性表，建议同时核对本目录的 `README.md` 和 `4_interpretation_notes.md`。
