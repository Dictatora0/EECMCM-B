# Solutions Index

本文件是 `Solutions/` 目录的总索引，用于说明 RQ1 到 RQ4 的运行顺序、上下游依赖关系，以及各题 `outputs/` 目录说明文档的位置。

## 目录结构

- `RQ1/`
  - 人口递推、理论需求与消费约束需求。
- `RQ2/`
  - 选址、规模、分配、容量与基准价财务评价。
- `RQ3/`
  - 以老人满意度为主目标的定价、固定点迭代和主结果/辅助扩展输出。
- `RQ4/`
  - 情景重求解、灵敏度分析、鲁棒性分析与解释输出。

## 推荐运行顺序

推荐在仓库根目录使用统一脚本：

```bash
cd /Users/lifulin/Desktop/B
bash run_full_pipeline.sh full
```

脚本内部按以下顺序执行：

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

若只想做分题重跑，可按下表处理。

## 分题运行关系

### RQ1

- 主脚本：
  - `python3 Solutions/RQ1/1_1.py`
  - `python3 Solutions/RQ1/1_2.py`
  - `python3 Solutions/RQ1/1_3.py`
  - `python3 Solutions/RQ1/1_4_validation_extension.py`
- 作用：
  - 生成人口高精度结果；
  - 生成理论需求；
  - 生成消费约束后的高精度需求。
  - 生成状态转移矩阵验证和局部敏感性扩展输出。
- 下游依赖：
  - RQ2 读取 RQ1 高精度人口与调整后需求；
  - RQ3 通过 RQ2 和 RQ1 高精度文件间接使用；
  - RQ4 的 S1、S2 会重跑 RQ1。
- 输出位置：
  - `Solutions/RQ1/outputs/`

### RQ2

- 主脚本：`python3 Solutions/RQ2/2_1.py`
- 扩展脚本：`python3 Solutions/RQ2/2_2_multiobjective_extension.py`
- 输入来源：
  - RQ1 高精度人口与消费约束需求。
- 作用：
  - 求问题2主方案；
  - 输出安全优先备选方案；
  - 输出小区分配、站点负荷和基准价财务评价。
  - 扩展输出 Pareto 前沿、`epsilon-constraint` 代表方案和容量瓶颈分析。
- 下游依赖：
  - RQ3 默认读取 `best_scheme` 相关输出；
  - RQ4 的 Q2 情景表来自本题重求解结果。
- 输出位置：
  - `Solutions/RQ2/outputs/`

### RQ3

- 主脚本：`python3 Solutions/RQ3/3_1.py`
- 扩展脚本：`python3 Solutions/RQ3/3_4_joint_feasibility_diagnostics.py`
- 输入来源：
  - RQ2 主方案输出；
  - RQ1 高精度人口与消费约束需求。
- 作用：
  - 在既定布局上搜索以老人满意度为主目标的定价方案；
  - 输出题面主结果 `3_1_best_price_scheme_*`；
  - 输出 `3_1_aux_financial_best_price_scheme_*` 与 `3_1_aux_fairness_best_price_scheme_*` 辅助扩展方案；
  - 输出固定点迭代轨迹、站点财务表和小区满意度/可及绩效表。
  - 扩展输出逐站联合可行性绑定约束诊断。
  - 同脚本支持站点—服务项目级扩搜：
    `python3 Solutions/RQ3/3_1.py --expanded-search-only --scenarios S0,S4 --search-levels light,medium,heavy --price-grid full --keep-near-boundary --random-seed 42`
- 下游依赖：
  - RQ4 的 Q3 情景表来自本题重求解结果。
- 说明文档：
  - [RQ3 接口与口径说明](./RQ3/README.md)
  - 输出位置：`Solutions/RQ3/outputs/`
  - 其中 `3_1_best_price_scheme_*` 为主结果；`3_1_aux_*`、`3_2_aux_*` 为辅助扩展结果。

### 兼容命名

仓库内部主口径已统一到 `satisfaction_*`。若你在旧 CSV、缓存或审计链路中看到下列名称，它们都属于兼容层：

- `fairness_priority_scheme` -> `satisfaction_priority_scheme`
- `fair_satisfaction_compliant` -> `satisfaction_compliant`
- `q3_fairness_minimum_service_access_performance` -> `q3_satisfaction_minimum_service_access_performance`
- `q3_fairness_scheme_performance_stability` -> `q3_satisfaction_scheme_performance_stability`

完整对照表见：

- [兼容字段矩阵](./compatibility_matrix.md)

### RQ4

- 主脚本：`python3 Solutions/RQ4/4_1.py`
- 输入来源：
  - 根据情景不同，复用或重跑 RQ1、RQ2、RQ3。
- 作用：
  - 输出情景化 Q2/Q3 汇总；
  - 输出灵敏度系数；
  - 输出鲁棒性指标；
  - 输出 S4 预算情景专项诊断和论文解释要点。
- 输出位置：
  - `Solutions/RQ4/outputs/`

## 情景重跑规则

RQ4 当前情景路径如下：

- `S0`
  - 基准情景。
- `S1`
  - 老人增长率变化；
  - 需要重跑 RQ1、RQ2、RQ3。
- `S2`
  - 转移概率变化；
  - 需要重跑 RQ1、RQ2、RQ3。
- `S3`
  - 固定管理成本上升；
  - 复用 baseline 的 RQ1；
  - 主要重跑 RQ2 财务评价和 RQ3 定价/财务。
- `S4`
  - 建设预算调整为 140 万；
  - 复用 baseline 的 RQ1；
  - 需要用 `budget_limit = 140` 重跑 RQ2，再重跑 RQ3。

## 当前默认数据流

```text
RQ1 high-precision outputs
  -> RQ1 validation extension outputs
  -> RQ2 best scheme outputs
    -> RQ2 multiobjective extension outputs
    -> RQ3 satisfaction-objective pricing outputs
      -> RQ3 joint-feasibility diagnostics
      -> RQ4 scenario summaries / sensitivity / robustness
```

关键默认输入链如下：

- RQ2 <- RQ1
  - `1_1_high_precision_year5_population.csv`
  - `1_3_high_precision_adjusted_demand.csv`
  - `1_3_high_precision_adjusted_demand_detail.csv`

- RQ3 <- RQ2 + RQ1
  - `2_1_best_scheme_summary.csv`
  - `2_1_best_scheme_stations.csv`
  - `2_1_best_scheme_allocations.csv`
  - RQ1 高精度人口与需求文件

- RQ4 <- RQ1 + RQ2 + RQ3
  - 按情景路径重求解并写出情景总表

## 常用命令

### 最短版

```bash
cd /Users/lifulin/Desktop/B

# 完整重跑
bash run_full_pipeline.sh full

# 入口守护测试
bash run_full_pipeline.sh test

# RQ3 扩搜：light + medium + heavy
bash run_full_pipeline.sh rq3-expanded all

# 清空所有 outputs 和缓存
bash run_full_pipeline.sh clean
```

### 完整版

```bash
cd /Users/lifulin/Desktop/B

# 清空所有 outputs 和缓存
bash run_full_pipeline.sh clean

# 完整重跑，并包含 3 个算法升级扩展
bash run_full_pipeline.sh full

# 入口守护测试
bash run_full_pipeline.sh test

# 仅跑 RQ3 测试
bash run_full_pipeline.sh test-rq3

# RQ3 扩搜：light + medium + heavy
bash run_full_pipeline.sh rq3-expanded all

# RQ3 扩搜：light
bash run_full_pipeline.sh rq3-expanded light

# RQ3 扩搜：medium
bash run_full_pipeline.sh rq3-expanded medium

# RQ3 扩搜：heavy
bash run_full_pipeline.sh rq3-expanded heavy

# RQ3 扩搜：extreme
bash run_full_pipeline.sh rq3-expanded extreme
```

## 终端进度

`RQ3` 与 `RQ4` 的长任务会在终端打印：

- `elapsed=`：已耗时
- `eta=`：阶段 ETA
- `done=x/y`：当前进度
- `feasible=` 或 `station_feasible=` / `aggregate_feasible=`：当前可行数

## 使用建议

- 若修改了人口、需求或消费约束口径，从 RQ1 开始全量重跑。
- 若修改了选址、容量、安全阈值或问题2财务口径，从 RQ2 开始重跑，并同步重跑 RQ3、RQ4。
- 若修改了定价、补贴、利润率约束或固定点迭代参数，从 RQ3 开始重跑，并同步重跑 RQ4。
- 若只修改了情景分析写法或情景参数，从 RQ4 开始重跑，但要确认是否需要联动触发 RQ1 至 RQ3 的重算。
