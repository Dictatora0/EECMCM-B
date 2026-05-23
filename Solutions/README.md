# Solutions Index

本文件是 `Solutions/` 目录的总索引，用于说明 RQ1 到 RQ4 的运行顺序、上下游依赖关系，以及各题 `outputs/` 目录说明文档的位置。

## 目录结构

- `RQ1/`
  - 人口递推、理论需求与消费约束需求。
- `RQ2/`
  - 选址、规模、分配、容量与基准价财务评价。
- `RQ3/`
  - 站点级统一溢价定价、固定点迭代、双方案比较。
- `RQ4/`
  - 情景重求解、灵敏度分析、鲁棒性分析与解释输出。

## 推荐运行顺序

按当前实现，完整重跑建议严格按以下顺序执行：

```bash
python Solutions/RQ1/run_all.py
python Solutions/RQ2/2_1.py
python Solutions/RQ3/3_1.py
python Solutions/RQ4/4_1.py
```

若只想做分题重跑，可按下表处理。

## 分题运行关系

### RQ1

- 主脚本：`python Solutions/RQ1/run_all.py`
- 作用：
  - 生成人口高精度结果；
  - 生成理论需求；
  - 生成消费约束后的高精度需求。
- 下游依赖：
  - RQ2 读取 RQ1 高精度人口与调整后需求；
  - RQ3 通过 RQ2 和 RQ1 高精度文件间接使用；
  - RQ4 的 S1、S2 会重跑 RQ1。
- 输出说明：
  - [RQ1 outputs README](./RQ1/outputs/README.md)

### RQ2

- 主脚本：`python Solutions/RQ2/2_1.py`
- 输入来源：
  - RQ1 高精度人口与消费约束需求。
- 作用：
  - 求问题2主方案；
  - 输出安全优先备选方案；
  - 输出小区分配、站点负荷和基准价财务评价。
- 下游依赖：
  - RQ3 默认读取 `best_scheme` 相关输出；
  - RQ4 的 Q2 情景表来自本题重求解结果。
- 输出说明：
  - [RQ2 outputs README](./RQ2/outputs/README.md)

### RQ3

- 主脚本：`python Solutions/RQ3/3_1.py`
- 输入来源：
  - RQ2 主方案输出；
  - RQ1 高精度人口与消费约束需求。
- 作用：
  - 在既定布局上搜索站点级统一溢价方案；
  - 输出 `financial_sustainable_scheme` 与 `fairness_priority_scheme`；
  - 输出固定点迭代轨迹、站点财务表和小区服务绩效表。
- 下游依赖：
  - RQ4 的 Q3 情景表来自本题重求解结果。
- 说明文档：
  - [RQ3 接口与口径说明](./RQ3/README.md)
  - [RQ3 outputs README](./RQ3/outputs/README.md)

### RQ4

- 主脚本：`python Solutions/RQ4/4_1.py`
- 输入来源：
  - 根据情景不同，复用或重跑 RQ1、RQ2、RQ3。
- 作用：
  - 输出情景化 Q2/Q3 汇总；
  - 输出灵敏度系数；
  - 输出鲁棒性指标；
  - 输出 S4 预算情景专项诊断和论文解释要点。
- 输出说明：
  - [RQ4 outputs README](./RQ4/outputs/README.md)

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
  -> RQ2 best scheme outputs
    -> RQ3 pricing outputs
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

## 常用说明文档

- [RQ1 outputs README](./RQ1/outputs/README.md)
- [RQ2 outputs README](./RQ2/outputs/README.md)
- [RQ3 README](./RQ3/README.md)
- [RQ3 outputs README](./RQ3/outputs/README.md)
- [RQ4 outputs README](./RQ4/outputs/README.md)

## 使用建议

- 若修改了人口、需求或消费约束口径，从 RQ1 开始全量重跑。
- 若修改了选址、容量、安全阈值或问题2财务口径，从 RQ2 开始重跑，并同步重跑 RQ3、RQ4。
- 若修改了定价、补贴、利润率约束或固定点迭代参数，从 RQ3 开始重跑，并同步重跑 RQ4。
- 若只修改了情景分析写法或情景参数，从 RQ4 开始重跑，但要确认是否需要联动触发 RQ1 至 RQ3 的重算。
