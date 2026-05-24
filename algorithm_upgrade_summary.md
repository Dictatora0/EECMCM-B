# Algorithm Upgrade Summary

## 本轮实际修改

### 新增算法扩展脚本

- `Solutions/RQ1/1_4_validation_extension.py`
- `Solutions/RQ2/2_2_multiobjective_extension.py`
- `Solutions/RQ3/3_4_joint_feasibility_diagnostics.py`

### 增强公共能力

- `Solutions/RQ1/common.py`
  - 增加状态转移矩阵接口；
  - 增加矩阵式递推；
  - 增加人口聚合与指标汇总工具。

### 新增/更新测试

- `Solutions/RQ1/tests.py`
- `Solutions/RQ2/tests.py`
- `Solutions/RQ3/tests.py`

### 新增总报告

- `algorithm_upgrade_review.md`
- `algorithm_upgrade_plan.md`
- `algorithm_upgrade_summary.md`

## 实现了哪些升级

### 1. RQ1：预测验证升级

- 将原有三状态递推补充为状态转移矩阵表达。
- 增加递推式与矩阵式的等价性验证接口。
- 增加对 `growth_rate`、`p12`、`p23` 的局部敏感性分析。

### 2. RQ2：多目标离散选址升级

- 将现有有限离散搜索结果重写为：
  - Pareto 前沿；
  - epsilon-constraint 代表方案；
  - 容量瓶颈解释。
- 不改变问题2主结果求解器。

### 3. RQ3：联合可行性诊断升级

- 新增逐站利润率边界诊断。
- 将“找不到联合可行解”从单句失败信息升级为：
  - 哪些站点亏损；
  - 哪些站点超过 8%；
  - 各站点对应的调整方向。

## 对已有结果的影响

- 当前升级均设计为扩展分析层。
- 不应覆盖 `RQ1-RQ4` 主输出。
- 仅新增扩展输出文件，强化论文解释力。

## 是否发现新的硬约束风险

- 本轮没有主动放松任何题目硬约束。
- 仍需通过完整重跑后执行约束审计，确认：
  - `RQ3` 最终主输出没有使用题面外补贴；
  - `RQ4` 情景输出真实反映参数变化；
  - 扩展脚本未误读空输出目录。

## 建议运行命令

在清空 outputs 后，建议按以下顺序运行：

```bash
cd /Users/lifulin/Desktop/B

python Solutions/RQ1/1_1.py
python Solutions/RQ1/1_2.py
python Solutions/RQ1/1_3.py
python Solutions/RQ1/1_4_validation_extension.py

python Solutions/RQ2/2_1.py
python Solutions/RQ2/2_2_multiobjective_extension.py

python Solutions/RQ3/3_1.py --max-candidate-profiles 64 --max-candidates-per-station 30 --price-grid-level full
python Solutions/RQ3/3_4_joint_feasibility_diagnostics.py

python Solutions/RQ4/4_1.py

python Solutions/constraint_audit.py
```

如需测试：

```bash
python Solutions/RQ1/tests.py
python Solutions/RQ2/tests.py
python Solutions/RQ3/tests.py
python Solutions/RQ4/tests.py
python Solutions/tests_constraint_audit.py
```

## 论文应如何表述这些升级

### 建议写法

- `RQ1`：
  - “建立三状态离散转移模型，并进一步写成状态转移矩阵形式，对递推计算结果进行了等价性校验和局部敏感性分析。”

- `RQ2`：
  - “在有限离散候选站点与离散规模条件下，采用精确搜索评价全部预算可行方案，并结合多目标优势关系提取 Pareto 前沿代表布局。”

- `RQ3`：
  - “在问题2固定布局上构建站点—服务项目级离散定价与固定点响应模型，以逐站利润率约束检验联合可行性，并输出绑定约束诊断。”

- `RQ4`：
  - “通过参数扰动重求解，比较布局稳定性、覆盖稳定性、可及性稳定性和财务合规稳定性。”

### 必须避免的写法

- “采用机器学习精确预测未来五年老人数量。”
- “使用智能算法搜索站点最优布局。”
- “通过区域统筹后实现联合可行。”
- “证明绝对不存在联合可行方案。”

这些表述要么不符合现有实现，要么会被评委直接质疑。

## 国奖视角最终判断

当前项目距离高水平提交还差的不是更多模型，而是：

1. 让 `RQ1` 看起来经过验证，而不是只做规则外推。
2. 让 `RQ2` 看起来是规范的离散设施选址，而不是简单枚举。
3. 让 `RQ3` 把“不可行”解释清楚，而不是停留在搜索失败。
4. 让 `RQ4` 只保留最能支撑决策的鲁棒性结论。

本轮新增的 3 个升级点，正是为解决这四个问题服务的。
