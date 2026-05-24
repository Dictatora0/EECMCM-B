# RQ4 Outputs

本目录保存问题4“灵敏度分析与方案比较”的最新输出。

## 主结果

- `4_1_q2_scenario_summary.csv`
  - 各情景下问题2结果摘要。
- `4_1_q3_scenario_summary.csv`
  - 各情景下问题3结果摘要。
- `4_1_scenario_unified_summary.csv`
  - 问题2与问题3的统一汇总表。
- `4_1_sensitivity_coefficients.csv`
  - 核心指标敏感性系数。
- `4_1_robustness_metrics.csv`
  - 鲁棒性指标。
- `4_interpretation_notes.md`
  - 情景比较与论文解释建议。

## 补充分析

- `4_1_s4_diagnostics.json`
  - S4 预算情景专项诊断。
- `4_2_sensitivity_coefficients.csv`
- `4_2_robustness_metrics.csv`
  - 与 4.2 表述对应的整理版结果。
- `4_3_monte_carlo_samples.csv`
- `4_3_monte_carlo_summary.csv`
  - Monte Carlo 扩展分析结果。

## 论文引用建议

- 正文优先引用：
  - `4_1_scenario_unified_summary.csv`
  - `4_1_sensitivity_coefficients.csv`
  - `4_1_robustness_metrics.csv`
- 附录或扩展分析可引用：
  - `4_1_q2_scenario_summary.csv`
  - `4_1_q3_scenario_summary.csv`
  - `4_1_s4_diagnostics.json`
  - `4_3_monte_carlo_summary.csv`
  - `4_interpretation_notes.md`

## 论文选用清单

### 正文最该引用的 3-5 个文件

- `4_1_scenario_unified_summary.csv`
  - 正文问题4主表，集中比较各情景下布局、覆盖、可及绩效和财务结果。
- `4_1_sensitivity_coefficients.csv`
  - 适合正文展示关键参数变化对核心指标的敏感性。
- `4_1_robustness_metrics.csv`
  - 适合正文展示模型鲁棒性。
- `4_1_q2_scenario_summary.csv`
  - 若正文要单列问题2情景差异，可直接引用。
- `4_1_q3_scenario_summary.csv`
  - 若正文要单列问题3情景差异，可直接引用。

### 附录最该引用的 2-4 个文件

- `4_1_s4_diagnostics.json`
  - 适合补充预算扩容情景的专项诊断。
- `4_3_monte_carlo_summary.csv`
  - 适合放随机扰动鲁棒性附录。
- `4_2_sensitivity_coefficients.csv`
  - 适合与 4.2 小节写法配套。
- `4_interpretation_notes.md`
  - 适合作为附录文字说明底稿。

## 注意

- 情景结果必须按 `scenario` 区分解读，不能把不同情景的站点布局、财务和满意度混在一起。
- 问题4中 `service_pricing`、`coverage_metrics`、`satisfaction_metrics` 的比较，应以最新情景重算结果为准，不得回用旧缓存表述。
