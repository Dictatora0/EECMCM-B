# 社区养老服务建模项目

本仓库包含四个研究问题的代码、输出结果和论文草稿，核心计算代码位于 `Solutions/`，论文正文草稿位于 `RQ/`。

## 目录说明

- `Solutions/`
  - RQ1 到 RQ4 的代码、输出结果和运行说明。
- `RQ/`
  - 论文正文草稿与结果写作内容。

## 如何从零复现全部结果

建议按以下顺序在仓库根目录执行：

```bash
python Solutions/RQ1/run_all.py
python Solutions/RQ2/2_1.py
python Solutions/RQ3/3_1.py
python Solutions/RQ4/4_1.py
```

运行逻辑如下：

1. `RQ1` 生成人口高精度结果、理论需求和消费约束需求。
2. `RQ2` 读取 `RQ1` 高精度输出，生成选址、规模、分配和基准价财务评价。
3. `RQ3` 读取 `RQ2` 主方案与 `RQ1` 高精度需求，生成站点级统一溢价定价结果和双方案比较。
4. `RQ4` 按情景路径重求解 `RQ1` 至 `RQ3`，输出情景汇总、灵敏度系数、鲁棒性指标和解释备注。

完整的数据流、上下游依赖、情景重跑规则和各题输出说明，请优先阅读：

- [Solutions 总索引](./Solutions/README.md)

若只需要查看各题输出文件说明，可直接进入：

- [RQ1 outputs README](./Solutions/RQ1/outputs/README.md)
- [RQ2 outputs README](./Solutions/RQ2/outputs/README.md)
- [RQ3 README](./Solutions/RQ3/README.md)
- [RQ3 outputs README](./Solutions/RQ3/outputs/README.md)
- [RQ4 outputs README](./Solutions/RQ4/outputs/README.md)

## 说明

- 当前问题2和问题3统一采用高精度需求输入，不使用取整展示版结果做计算。
- 当前问题3实现的是站点级统一溢价定价，不是站点-服务项目级独立定价。
- 当前问题4的正式情景汇总、灵敏度和鲁棒性表以 `Solutions/RQ4/outputs/` 中的最新文件为准。
