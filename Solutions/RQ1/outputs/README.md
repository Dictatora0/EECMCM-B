# RQ1 Outputs

本目录保存问题1“未来五年老人数量与服务需求预测”的最新输出。当前结果分为主结果与方法扩展两层。

## 主结果

- `1_1_high_precision_population_by_year.csv`
  - 第1年至第5年末、各小区三类老人数量的高精度递推结果。
  - 优化与后续问题应优先读取此文件，而不是取整版。
- `1_1_high_precision_year5_population.csv`
  - 第5年末各小区三类老人数量汇总。
- `1_1_rounded_report_elderly_projection.csv`
  - 仅用于论文展示的取整版人口预测表。

- `1_2_high_precision_theoretical_demand.csv`
  - 第5年末各小区六类服务的理论月需求总量。
  - 不含消费能力约束。
- `1_2_high_precision_theoretical_demand_detail.csv`
  - 理论需求的老人类型分解明细。
- `1_2_rounded_report_theoretical_demand.csv`
- `1_2_rounded_report_theoretical_demand_detail.csv`
  - 仅用于论文展示的取整版理论需求表。

- `1_3_high_precision_adjusted_demand.csv`
  - 第5年末各小区在消费约束下的服务需求结果。
- `1_3_high_precision_adjusted_demand_detail.csv`
  - 消费约束需求的老人类型分解与压缩明细。
- `1_3_rounded_report_adjusted_demand.csv`
- `1_3_rounded_report_adjusted_demand_detail.csv`
  - 仅用于论文展示的取整版消费约束需求表。

## 方法扩展

- `1_4_transition_matrix.csv`
  - 状态转移矩阵，用于说明递推模型的矩阵表达。
- `1_4_validation_sensitivity_summary.csv`
  - 对增长率、转移概率等关键参数的局部敏感性结果。
- `1_4_validation_notes.md`
  - 问题1扩展说明。
  - 当前口径是“矩阵等价验证 + 局部参数敏感性”，不能写成历史回测。

## 元数据

- `rq1_high_precision_metadata.json`
  - 高精度结果的生成口径、字段来源和运行元数据。

## 论文引用建议

- 正文优先引用：
  - `1_1_high_precision_year5_population.csv`
  - `1_2_high_precision_theoretical_demand.csv`
  - `1_3_high_precision_adjusted_demand.csv`
- 附录或方法部分可引用：
  - `1_4_transition_matrix.csv`
  - `1_4_validation_sensitivity_summary.csv`
  - `1_4_validation_notes.md`

## 论文选用清单

### 正文最该引用的 3-5 个文件

- `1_1_high_precision_year5_population.csv`
  - 用于交代第5年末各小区老人规模与结构，是问题2和问题3的需求基础。
- `1_2_high_precision_theoretical_demand.csv`
  - 用于说明“未考虑消费能力约束”的理论服务需求。
- `1_3_high_precision_adjusted_demand.csv`
  - 用于说明消费约束后真正进入后续优化的问题1.3结果。
- `1_3_high_precision_adjusted_demand_detail.csv`
  - 若正文需要解释不同老人类型的需求压缩来源，可补这一张明细表。

### 附录最该引用的 2-4 个文件

- `1_4_transition_matrix.csv`
  - 适合放方法附录，解释单向状态转移结构。
- `1_4_validation_sensitivity_summary.csv`
  - 适合放敏感性附录，说明增长率和转移概率扰动对第5年结果的影响。
- `1_4_validation_notes.md`
  - 适合为附录文字说明提供现成表述框架。

## 注意

- 问题2到问题4的优化模型应使用 `high_precision` 文件，不应使用 `rounded_report` 文件参与计算。
- 理论需求和消费约束需求是两套不同口径，论文中必须明确区分。
