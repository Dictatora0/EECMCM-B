# RQ2 Outputs

本目录保存问题2“服务站选址与规模优化”的最新输出。当前结果分为主结果与算法升级扩展两层。

## 主结果

- `2_1_best_scheme_summary.csv`
  - 问题2主推荐方案汇总。
  - 包含覆盖率、满意度、辅助可及绩效、容量利用、年度财务等核心指标。
- `2_1_best_scheme_stations.csv`
  - 主推荐方案的逐站点结果。
  - 包含站点规模、容量、利用率、年收入、年补贴、年成本、年净利润、利润率。
- `2_1_best_scheme_allocations.csv`
  - 主推荐方案的小区级分配结果。
  - 包含主站、未满足需求、满意度、辅助可及绩效等字段。

- `2_1_safe_scheme_summary.csv`
- `2_1_safe_scheme_stations.csv`
- `2_1_safe_scheme_allocations.csv`
  - 安全优先参考方案。

- `2_1_dual_scheme_compare.csv`
  - 主方案与安全方案的对照表。

## 升级扩展结果

- `2_1_extension_optimized_scheme_summary.csv`
- `2_1_extension_optimized_scheme_stations.csv`
- `2_1_extension_optimized_scheme_allocations.csv`
  - 多目标/MILP 升级方案。

- `2_1_extension_robust_scheme_summary.csv`
- `2_1_extension_robust_scheme_stations.csv`
- `2_1_extension_robust_scheme_allocations.csv`
  - 鲁棒布局参考方案。

- `2_1_extension_model_upgrade_compare.csv`
  - 原主方案与升级方案对照。

## 搜索与权衡分析

- `2_1_top10_schemes.csv`
  - 前10个代表性候选方案。
- `2_1_safety_threshold_tradeoff.csv`
  - 容量安全阈值变化下的方案比较。
- `2_2_pareto_frontier.csv`
  - 问题2扩展 Pareto 前沿。
- `2_2_epsilon_constraint_summary.csv`
  - 最低可及绩效阈值下的代表方案摘要。
- `2_2_capacity_bottleneck_top20.csv`
  - 容量瓶颈最明显的候选方案。
- `2_2_multiobjective_notes.md`
  - 问题2扩展建模与解释说明。

## 论文引用建议

- 正文优先引用：
  - `2_1_best_scheme_summary.csv`
  - `2_1_best_scheme_stations.csv`
  - `2_1_best_scheme_allocations.csv`
  - `2_1_dual_scheme_compare.csv`
- 附录或扩展分析可引用：
  - `2_1_extension_*`
  - `2_2_pareto_frontier.csv`
  - `2_2_epsilon_constraint_summary.csv`
  - `2_2_multiobjective_notes.md`

## 论文选用清单

### 正文最该引用的 3-5 个文件

- `2_1_best_scheme_summary.csv`
  - 正文问题2总表，集中给出覆盖、满意度、容量与财务结果。
- `2_1_best_scheme_stations.csv`
  - 用于回答“建几个站、建在哪、什么规模、每站利润如何”。
- `2_1_best_scheme_allocations.csv`
  - 用于回答“每个站覆盖哪些小区、小区满意度怎样”。
- `2_1_dual_scheme_compare.csv`
  - 适合正文说明主方案与安全优先方案的权衡。
- `2_2_epsilon_constraint_summary.csv`
  - 若正文要增强“最低可及绩效阈值”解释，可以用这一份代表表。

### 附录最该引用的 2-4 个文件

- `2_2_pareto_frontier.csv`
  - 适合放多目标扩展附录。
- `2_2_capacity_bottleneck_top20.csv`
  - 适合支撑容量瓶颈分析。
- `2_2_multiobjective_notes.md`
  - 适合给附录文字解释提供现成表述。
- `2_1_extension_model_upgrade_compare.csv`
  - 适合展示升级模型与原主方案的对比。

## 注意

- `served_population_coverage` 是题面要求的“实际服务人口覆盖率”。
- `weighted_served_population_coverage`、`served_demand_coverage`、`service_access_performance` 都是辅助指标，不能直接替代题面覆盖率与满意度定义。
- 当前结果采用单站选择口径，小区不再主动分流到第二站。
