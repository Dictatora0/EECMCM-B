# 社区养老服务建模项目

本仓库包含四个研究问题的代码、输出结果和论文草稿，核心计算代码位于 `Solutions/`，论文正文草稿位于 `RQ/`。

## 目录说明

- `Solutions/`
  - RQ1 到 RQ4 的代码、输出结果和运行说明。
- `RQ/`
  - 论文正文草稿与结果写作内容。

## 如何运行

推荐优先使用根目录脚本：

```bash
cd /Users/lifulin/Desktop/B
bash run_full_pipeline.sh full
```

该脚本会依次运行：

```bash
python3 Solutions/RQ1/1_1.py
python3 Solutions/RQ1/1_2.py
python3 Solutions/RQ1/1_3.py
python3 Solutions/RQ1/1_4_validation_extension.py
python3 Solutions/RQ2/2_1.py
python3 Solutions/RQ2/2_2_multiobjective_extension.py
python3 Solutions/RQ3/3_1.py --max-candidate-profiles 64 --max-candidates-per-station 30 --price-grid-level full
python3 Solutions/RQ3/3_4_joint_feasibility_diagnostics.py
python3 Solutions/RQ4/4_1.py
```

命令分两组：

### 最短版

```bash
cd /Users/lifulin/Desktop/B

# 完整重跑 Q1 -> Q4
bash run_full_pipeline.sh full

# 跑一遍当前入口/约束测试
bash run_full_pipeline.sh test

# 跑 RQ3 扩搜：light + medium + heavy
bash run_full_pipeline.sh rq3-expanded all

# 清空所有 outputs 和 __pycache__
bash run_full_pipeline.sh clean
```

### 完整版

```bash
cd /Users/lifulin/Desktop/B

# 清空所有 outputs 和 __pycache__
bash run_full_pipeline.sh clean

# 完整重跑 Q1 -> Q4，并包含 3 个算法升级扩展
bash run_full_pipeline.sh full

# 跑入口守护测试
bash run_full_pipeline.sh test

# 仅跑 RQ3 测试
bash run_full_pipeline.sh test-rq3

# 跑 RQ3 扩搜：light + medium + heavy
bash run_full_pipeline.sh rq3-expanded all

# 单独跑 light
bash run_full_pipeline.sh rq3-expanded light

# 单独跑 medium
bash run_full_pipeline.sh rq3-expanded medium

# 单独跑 heavy
bash run_full_pipeline.sh rq3-expanded heavy

# 单独跑 extreme
bash run_full_pipeline.sh rq3-expanded extreme
```

运行逻辑如下：

1. `RQ1` 生成人口高精度结果、理论需求和消费约束需求。
2. `RQ1` 扩展脚本输出状态转移矩阵验证和局部敏感性分析。
3. `RQ2` 读取 `RQ1` 高精度输出，生成选址、规模、分配和基准价财务评价。
4. `RQ2` 扩展脚本输出 Pareto 前沿、`epsilon-constraint` 代表方案和容量瓶颈分析。
5. `RQ3` 读取 `RQ2` 主方案与 `RQ1` 高精度需求，生成题面主结果 `3_1_best_price_scheme_*`，并额外输出 `3_1_aux_*` 辅助扩展比较结果。
6. `RQ3` 扩展脚本输出逐站联合可行性诊断。
7. `RQ4` 按情景路径重求解 `RQ1` 至 `RQ3`，输出情景汇总、灵敏度系数、鲁棒性指标和解释备注。

完整的数据流、上下游依赖、情景重跑规则和各题输出说明，请优先阅读：

- [Solutions 总索引](./Solutions/README.md)

## 进度打印

`RQ3` 和 `RQ4` 的长任务现在会在终端打印进度，包含：

- `elapsed=`：已耗时
- `eta=`：当前阶段 ETA
- `done=x/y`：当前阶段进度
- `feasible=` 或 `station_feasible=` / `aggregate_feasible=`：当前可行数

因此直接运行上面的脚本即可观察长任务推进情况，不需要额外开调试参数。

若只需要查看各题代码说明，可直接进入：

- [Solutions 总索引](./Solutions/README.md)
- [RQ3 README](./Solutions/RQ3/README.md)

## 说明

- 当前问题2和问题3统一采用高精度需求输入，不使用取整展示版结果做计算。
- 当前问题3主链路输出为 `3_1_best_price_scheme_*`；辅助扩展结果统一采用 `3_1_aux_financial_best_price_scheme_*`、`3_1_aux_fairness_best_price_scheme_*`、`3_1_aux_pareto_frontier.csv` 与 `3_2_aux_*` 前缀，不覆盖主结果。
- `service_access_performance` 仅作为辅助可及绩效指标保留，不与题目满意度混称。
- 当前问题4的正式情景汇总、灵敏度和鲁棒性表以 `Solutions/RQ4/outputs/` 中的最新文件为准。
