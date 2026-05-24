# Algorithm Upgrade Plan

## 升级总原则

本轮只实施 3 个高收益升级点，满足以下要求：

1. 不放松题目硬约束。
2. 不改写现有主结果口径。
3. 不把尚未找到的联合可行解伪装成可行。
4. 优先补“论文竞争力”和“数学解释力”，而不是堆额外复杂度。

## Upgrade 1: RQ1 状态转移矩阵验证与局部敏感性

### 算法名称

- 状态转移矩阵等价验证与局部参数敏感性分析

### 数学模型

设第 `t` 年末三类老人状态向量为：

`x_t = [N_self, N_semi, N_disabled]^T`

则有：

`x_(t+1) = A x_t`

其中 `A` 由统一死亡率、单向转移和新增老人进入自理状态构成。

### 状态变量

- `x_t`
- 转移矩阵 `A`

### 目标

- 验证递推实现与矩阵实现的一致性；
- 定量解释 `growth_rate`、`p12`、`p23` 对第5年总量、失能占比、需求总量的影响。

### 约束

- `death_rate = 0.05`
- `growth_rate = 0.07`
- 只能单向转移，不允许恢复或跨级跳转。

### 求解方法

1. 从现有递推式构造状态转移矩阵。
2. 对每个小区分别用递推式和矩阵式计算第1至5年结果。
3. 校验最大绝对误差。
4. 对关键参数做小幅单因素扰动，输出第5年关键指标变化。

### 复杂度

- `O(社区数 × 年数)`，极低。

### 读取输入

- `附件1` 的人口和转移概率；
- `附件2` 的需求与价格数据。

### 新输出

- `Solutions/RQ1/outputs/1_4_transition_matrix.csv`
- `Solutions/RQ1/outputs/1_4_validation_sensitivity_summary.csv`
- `Solutions/RQ1/outputs/1_4_validation_notes.md`

### 是否建议实现

- 建议实现，且已实现。

### 是否建议放入论文正文

- 建议。
- 可用较短篇幅增强“预测有验证”。

### 题意风险

- 低。
- 该升级只增强解释，不改变主模型。

## Upgrade 2: RQ2 有限离散精确搜索的多目标扩展

### 算法名称

- Pareto 前沿与 epsilon-constraint 代表方案筛选

### 数学模型

问题2可表述为：

- 离散候选站点集合 `J = {A,...,J}`
- 离散规模集合 `K = {0, 小, 中, 大}`
- 目标同时考虑：
  - 服务人口覆盖；
  - 最低服务可及绩效；
  - 容量安全率；
  - 建设成本

### 决策变量

- `y_(j,k)`：站点 `j` 是否采用规模 `k`

### 目标函数

主扩展不重新求解，而在现有可行方案集上评价：

1. Pareto 非支配前沿；
2. 给定最低可及性阈值的 epsilon-constraint 最优方案。

### 约束

- 候选站点仅限 `A-J`
- 半径 `<= 1000m`
- 预算 `<= 120`
- 容量上限按规模固定

### 求解方法

1. 使用现有离散可行方案集。
2. 对每个方案计算：
   - `served_population_coverage`
   - `minimum_service_access_performance`
   - `capacity_safety_rate`
   - `build_cost_wan`
3. 按 Pareto 优势关系提取前沿。
4. 用多组 `minimum_access` 阈值做 epsilon-constraint 代表解筛选。

### 复杂度

- 依赖现有可行方案枚举结果。
- 后处理复杂度约为 `O(M^2)`，其中 `M` 为可行方案数。

### 读取输入

- `RQ1` 高精度需求；
- 现有 `RQ2 common` 中的距离、成本、满意度规则。

### 新输出

- `Solutions/RQ2/outputs/2_2_pareto_frontier.csv`
- `Solutions/RQ2/outputs/2_2_epsilon_constraint_summary.csv`
- `Solutions/RQ2/outputs/2_2_capacity_bottleneck_top20.csv`
- `Solutions/RQ2/outputs/2_2_multiobjective_notes.md`

### 是否建议实现

- 建议实现，且已实现。

### 是否建议放入论文正文

- 建议放正文。
- 这能显著提高问题2的建模含金量。

### 题意风险

- 低。
- 因为没有改动主优化，只是对现有精确搜索结果进行多目标重解释。

## Upgrade 3: RQ3 联合可行性绑定约束诊断

### 算法名称

- 逐站利润率绑定约束诊断

### 数学模型

在现有问题3主模型不变的前提下，对候选或近可行方案中的每个服务站计算：

- `annual_revenue`
- `annual_government_subsidy`
- `annual_total_cost`
- `annual_net_profit`
- `profit_rate`

并诊断其相对约束区间 `[0, 0.08]` 的偏离方向。

### 决策变量

- 不新增主决策变量。
- 仅对既有定价候选进行诊断分析。

### 目标

- 解释“为什么找不到 joint feasible”；
- 定位卡点站点是亏损下界还是超 8% 上界；
- 输出可写进论文的近可行解释。

### 约束

- 必须逐站核算；
- 不能用区域总利润率；
- 不能用站点间调剂解释主模型可行性。

### 求解方法

1. 从每站候选中选取靠近利润率边界的代表组合。
2. 组装成全局价格方案。
3. 用现有固定点与财务复算模块做最终验算。
4. 输出逐站卡点方向：
   - `raise_revenue_or_cut_cost`
   - `lower_price_or_expand_public_service_mix`
   - `within_band`

### 复杂度

- 低于完整扩搜。
- 本质是对既有候选的解释性复算。

### 读取输入

- `RQ3` 主输入；
- `3_1.py` 中现有服务级候选和固定点模块。

### 新输出

- `Solutions/RQ3/outputs/3_4_joint_feasibility_summary.csv`
- `Solutions/RQ3/outputs/3_4_joint_feasibility_by_station.csv`
- `Solutions/RQ3/outputs/3_4_joint_feasibility_notes.md`

### 是否建议实现

- 建议实现，且已实现。

### 是否建议放入论文正文

- 建议将“诊断结论”放正文；
- 详细逐站表格放附录。

### 题意风险

- 低。
- 只解释现有模型，不改变合规判断。

## 不建议当前实现的升级

### 不建议 1：引入时间序列/机器学习预测

- 原因：题面没有多期历史时间序列，无法支撑可信训练或回测。

### 不建议 2：元启发式选址

- 原因：候选空间小，精确法比启发式更强、更可信。

### 不建议 3：复杂连续博弈定价

- 原因：当前离散定价 + 固定点 + 逐站利润率约束已经足够，继续加复杂度会破坏论文主线。

## 论文正文建议

### 必进正文

- `RQ1` 状态转移矩阵与局部敏感性简表。
- `RQ2` Pareto / epsilon-constraint 代表方案。
- `RQ3` 逐站联合可行性卡点诊断结论。
- `RQ4` 布局稳定性、覆盖/可及性敏感性、财务合规稳定性。

### 更适合附录

- 全部逐站财务表；
- 全部候选方案表；
- 扩搜细节；
- 更细的鲁棒性样本和中间日志。
