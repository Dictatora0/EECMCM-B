# RQ3 Outputs

本目录保存问题3“服务定价与政府补贴优化”的最新输出。当前口径已经统一为：

- 主目标：最大化题目定义的社区平均老人满意度；
- 辅助指标：服务可及绩效；
- 财务约束：逐站利润率、逐站补贴上限、紧急救助免费。

## 3.1 主结果

- `3_1_best_price_scheme_summary.csv`
  - 问题3主结果汇总。
- `3_1_best_price_scheme_stations.csv`
  - 主结果逐站财务与利润率。
- `3_1_best_price_scheme_communities.csv`
  - 主结果小区级满意度分解。
- `3_1_best_price_scheme_iteration_trace.csv`
  - 固定点迭代轨迹。
- `3_1_best_price_scheme_accessibility_groups.csv`
  - 群体可及性分析。

说明：

- `3_1_best_price_scheme_*` 是题面主模型输出，论文正文应优先引用。
- 若 `3_1_aux_scheme_status_summary.csv` 中 `joint_feasible_solution_exists=0`，则不能把该结果写成“联合可行最优解”；只能写成主模型下的代表性方案。

## 3.1 辅助扩展方案

- `3_1_aux_financial_best_price_scheme_*`
  - 财务可持续优先方案。
- `3_1_aux_satisfaction_best_price_scheme_*`
  - 满意度优先辅助方案。
- `3_1_aux_dual_scheme_comparison.csv`
  - 两类代表性方案对照。
- `3_1_aux_pareto_frontier.csv`
  - 辅助 Pareto 前沿。
- `3_1_aux_top_price_schemes.csv`
  - 前若干定价候选汇总。
- `3_1_aux_scheme_status_summary.csv`
  - 方案状态摘要。

说明：

- `aux_satisfaction` 是当前 canonical 前缀。
- 若历史目录里仍出现 `aux_fairness` 前缀，应视为旧结果残留，不再作为论文引用对象。

## 3.2 满意度主轴权衡分析

- `3_2_aux_satisfaction_tradeoff_paper_notes.md`
  - 问题3扩展权衡分析说明。
  - 当前口径是“满意度主轴优先、可及绩效辅轴”。

## 3.4 联合可行性诊断

- `3_4_joint_feasibility_summary.csv`
  - S0/S4 等情景下联合可行性摘要。
- `3_4_joint_feasibility_by_station.csv`
  - 联合可行性逐站利润率诊断。
- `3_4_joint_feasibility_notes.md`
  - 解释 joint feasible 是否存在、卡在哪些站点。

## 3.5 站点—服务项目级定价升级

- `3_5_satisfaction_objective_summary.csv`
  - 升级模型代表方案汇总。
- `3_5_satisfaction_objective_by_station.csv`
  - 升级模型逐站财务。
- `3_5_satisfaction_objective_community_satisfaction.csv`
  - 升级模型小区满意度与价格满意度。
- `3_5_satisfaction_objective_station_candidates.csv`
  - 逐站保留候选。
- `3_5_satisfaction_objective_global_candidates.csv`
  - 全局组合复算候选。
- `3_5_satisfaction_objective_model_comparison.csv`
  - 新旧定价模型对比。
- `3_5_satisfaction_objective_notes.md`
  - 升级模型结果说明。

## 论文引用建议

- 正文优先引用：
  - `3_1_best_price_scheme_summary.csv`
  - `3_1_best_price_scheme_stations.csv`
  - `3_1_best_price_scheme_communities.csv`
  - `3_1_aux_dual_scheme_comparison.csv`
- 附录或扩展分析可引用：
  - `3_1_aux_*`
  - `3_2_aux_satisfaction_tradeoff_paper_notes.md`
  - `3_4_*`
  - `3_5_satisfaction_objective_*`

## 论文选用清单

### 正文最该引用的 3-5 个文件

- `3_1_best_price_scheme_summary.csv`
  - 正文问题3总表，给出主定价方案、满意度、补贴和总财务结果。
- `3_1_best_price_scheme_stations.csv`
  - 用于逐站展示年度利润与利润率。
- `3_1_best_price_scheme_communities.csv`
  - 用于展示每个小区的距离满意度、响应满意度、价格满意度和综合满意度。
- `3_1_aux_dual_scheme_comparison.csv`
  - 适合正文比较财务可持续方案与满意度优先辅助方案。
- `3_1_aux_scheme_status_summary.csv`
  - 适合在正文中明确说明当前是否存在联合可行解。

### 附录最该引用的 2-4 个文件

- `3_2_aux_satisfaction_tradeoff_paper_notes.md`
  - 适合放满意度主轴权衡分析的文字说明。
- `3_4_joint_feasibility_summary.csv`
  - 适合补充“为什么 joint feasible 不存在/是否存在”的诊断摘要。
- `3_4_joint_feasibility_by_station.csv`
  - 适合逐站展示利润率卡点。
- `3_5_satisfaction_objective_model_comparison.csv`
  - 适合展示旧统一溢价模型与新站点—服务项目级定价模型的差异。

## 注意

- `service_satisfaction` 是题面满意度。
- `service_access_performance` 只是辅助可及绩效，不能在论文中混称为满意度。
- 若 `joint_feasible_solution_exists=0`，必须明确写“当前条件下未找到联合可行解”，不能写成已实现逐站完全合规。
