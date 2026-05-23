# RQ1 Outputs

本目录保存问题1的标准输出。上游脚本为 `Solutions/RQ1/run_all.py`，其内部依次调用 `1_1.py`、`1_2.py`、`1_3.py`。

## 用途

- 为问题2、问题3、问题4提供高精度人口与需求输入。
- 为论文正文提供“取整展示版”表格。
- 通过 `rq1_high_precision_metadata.json` 记录下游应读取的正式文件。

## 主输出与下游读取口径

- 下游正式输入只应读取高精度文件，不应读取取整展示版。
- 当前推荐下游读取：
  - `1_1_high_precision_year5_population.csv`
  - `1_3_high_precision_adjusted_demand.csv`
  - `1_3_high_precision_adjusted_demand_detail.csv`
  - `rq1_high_precision_metadata.json`

## 文件说明

### 高精度主输出

- `1_1_high_precision_population_by_year.csv`
  - 字段：`year, community, self_care, semi_disabled, disabled, elderly_total, new_entrants`
  - 含义：第1年至第5年的高精度人口递推结果。

- `1_1_high_precision_year5_population.csv`
  - 字段：`year, community, self_care, semi_disabled, disabled, elderly_total, new_entrants`
  - 含义：第5年末人口结果，是问题2至问题4的人口基线。

- `1_2_high_precision_theoretical_demand.csv`
  - 字段：`community, service, theoretical_monthly_demand`
  - 含义：未施加消费约束的理论月需求。

- `1_3_high_precision_adjusted_demand.csv`
  - 字段：`community, service, adjusted_monthly_demand`
  - 含义：施加消费约束后的月需求，是问题2和问题3的需求基线。

- `1_3_high_precision_adjusted_demand_detail.csv`
  - 字段：`community, care_level, service, monthly_income, budget_limit, theoretical_per_person, adjusted_per_person, adjustment_scale, population, adjusted_monthly_demand`
  - 含义：消费约束修正明细，可用于解释不同老人类型和服务项目的需求压缩来源。

### 取整展示版

- `1_1_rounded_report_elderly_projection.csv`
- `1_2_rounded_report_theoretical_demand.csv`
- `1_3_rounded_report_adjusted_demand.csv`
- `1_3_rounded_report_adjusted_demand_detail.csv`

这些文件只用于论文表格展示，不应用作问题2至问题4的计算输入。

### 元数据

- `rq1_high_precision_metadata.json`
  - 含义：记录高精度输出的生成时间、年份覆盖和下游推荐读取文件。
  - 当前 `intended_downstream` 为 `RQ2`、`RQ3`、`RQ4`。

## 结果口径说明

- 人口递推采用“死亡 -> 状态转移 -> 新增进入自理”的顺序。
- 新增老人进入 `self_care`。
- 消费约束只压缩收费服务。
- `紧急救助` 免费，不参与消费预算压缩。
- 高精度结果保留浮点精度，取整仅用于报告展示。

## 重跑建议

- 若修改了转移概率、死亡率、老人增长率、收入或服务消费上限，应重跑 `python Solutions/RQ1/run_all.py`。
- 重跑后，问题2至问题4若依赖本目录高精度文件，应同步重跑。
