# Compatibility Matrix

本表用于统一仓库内部 canonical 命名与 legacy 兼容字段名，便于论文写作、答辩表述和代码排查时保持口径一致。

## 方案标签

| Canonical | Legacy | 说明 |
| --- | --- | --- |
| `satisfaction_priority_scheme` | `fairness_priority_scheme` | 问题3/4 中“满意度优先方案” |
| `satisfaction_best` | `fairness_best` | 代码内部候选选择结果 |
| `frontier_satisfaction_peak` | `frontier_fairness_peak` | Pareto 前沿代表点 |

## 合规字段

| Canonical | Legacy | 说明 |
| --- | --- | --- |
| `satisfaction_compliant` | `fair_satisfaction_compliant` | 是否达到满意度阈值 |

## 问题4统计字段

| Canonical | Legacy | 说明 |
| --- | --- | --- |
| `q3_satisfaction_minimum_service_access_performance` | `q3_fairness_minimum_service_access_performance` | 问题3 方案最低辅助可及绩效 |
| `q3_satisfaction_scheme_performance_stability` | `q3_fairness_scheme_performance_stability` | 问题3 方案绩效稳定性 |
| `satisfaction_average_service_access_performance` | `fairness_average_service_access_performance` | 满意度方案平均辅助可及绩效 |
| `satisfaction_minimum_service_access_performance` | `fairness_minimum_service_access_performance` | 满意度方案最低辅助可及绩效 |
| `satisfaction_profit_rate` | `fairness_profit_rate` | 满意度方案利润率 |
| `satisfaction_annual_net_profit` | `fairness_annual_net_profit` | 满意度方案年净利润 |

## 当前使用原则

- 论文正文、图题、结果说明：优先使用 canonical `satisfaction_*` 命名。
- 缓存、旧 CSV、旧审计链路：允许继续出现 legacy `fairness_*` 字段。
- 新增代码：默认写 canonical；如需兼容旧接口，应通过 alias/适配层回写 legacy 字段，而不是在主逻辑中直接扩散旧名。
