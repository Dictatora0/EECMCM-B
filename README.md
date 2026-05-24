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
python3 Solutions/plots/build_all_plots.py
```

命令分两组：

### 最短版

```bash
cd /Users/lifulin/Desktop/B

# 完整重跑 Q1 -> Q4
bash run_full_pipeline.sh full

# 只重建论文图表
bash run_full_pipeline.sh plots

# 跑一遍当前入口/约束测试（含 plot 守护）
bash run_full_pipeline.sh test

# 跑 RQ3 扩搜：light + medium + heavy
bash run_full_pipeline.sh rq3-expanded all

# 清空所有 outputs、RQ4/cache 和 __pycache__
bash run_full_pipeline.sh clean
```

### 完整版

```bash
cd /Users/lifulin/Desktop/B

# 清空所有 outputs、RQ4/cache 和 __pycache__
bash run_full_pipeline.sh clean

# 完整重跑 Q1 -> Q4，并包含 3 个算法升级扩展
bash run_full_pipeline.sh full

# 只重建论文图表
bash run_full_pipeline.sh plots

# 跑入口守护测试（含约束审计、plot 守护、RQ2-RQ4 测试）
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

当前脚本支持的命令与作用如下：

- `bash run_full_pipeline.sh full`
  - 重算 RQ1 到 RQ4 的主结果与扩展结果，并在最后统一生图。
- `bash run_full_pipeline.sh plots`
  - 直接基于现有 `Solutions/RQ1-4/outputs/` 重建论文图，不重算模型。
- `bash run_full_pipeline.sh test`
  - 跑入口守护测试：约束审计、`Solutions/plots/tests.py`、`RQ2/tests.py`、`RQ3/tests.py`、`RQ4/tests.py`。
  - 若缺少 RQ1/RQ2 的基础输出，会先自动补齐最小前置结果。
- `bash run_full_pipeline.sh test-rq3`
  - 仅运行 `Solutions/RQ3/tests.py`。
- `bash run_full_pipeline.sh clean`
  - 清空 `Solutions/*/outputs/` 下的数值结果、统一生图图片、`plot_manifest.csv`、`plot_notes.md`、`.mplconfig`，以及 `Solutions/RQ4/cache/*.json` 和 `__pycache__`。
- `bash run_full_pipeline.sh rq3-expanded {all|light|medium|heavy|extreme}`
  - 运行 RQ3 站点-服务级扩搜，默认针对 `S0,S4`。

运行逻辑如下：

1. `RQ1` 生成人口高精度结果、理论需求和消费约束需求。
2. `RQ1` 扩展脚本输出状态转移矩阵验证和局部敏感性分析。
3. `RQ2` 读取 `RQ1` 高精度输出，生成选址、规模、单站分配和基准价财务评价。
4. `RQ2` 扩展脚本输出 Pareto 前沿、`epsilon-constraint` 代表方案和容量瓶颈分析。
5. `RQ3` 读取 `RQ2` 主方案与 `RQ1` 高精度需求，生成题面主结果 `3_1_best_price_scheme_*`，并额外输出 `3_1_aux_*` 辅助扩展比较结果。
6. `RQ3` 扩展脚本输出逐站联合可行性诊断。
7. `RQ4` 按情景路径重求解 `RQ1` 至 `RQ3`，输出情景汇总、灵敏度系数、鲁棒性指标和解释备注。
8. `Plots` 统一读取 `RQ1` 至 `RQ4` 最新结果，生成论文图、图清单和图注建议。

说明：

- `run_full_pipeline.sh clean` 会同时清空 `Solutions/*/outputs/` 下的数值输出与图片类结果、`Solutions/RQ4/cache/` 和 `__pycache__`，适合做全量复现实验。
- `RQ4` 会校验缓存是否仍符合当前主模型口径；若发现旧版 `alpha_j` 定价、溢出分流或过期摘要结构，会自动重算对应场景。
- `bash run_full_pipeline.sh full` 现在会在数值结果后自动生图；图表统一输出到 `Solutions/plots/outputs/`。
- 若只调整图题、图注或论文图表映射，不必重算模型，可直接执行 `bash run_full_pipeline.sh plots`。
- `bash run_full_pipeline.sh test` 当前也会覆盖 `Solutions/plots/tests.py`，用于守护论文图命名、落位、字段口径和字体配置。
- `Plots` 入口会在运行前统一配置 Matplotlib 缓存目录和中文字体；当前默认优先使用 `Songti SC`，已消除此前 `DejaVu Sans` 的中文 glyph warning。
- 当前 `bash run_full_pipeline.sh plots` 若仍出现 warning，通常只剩 `sklearn.manifold._mds` 的 `FutureWarning`，不影响图文件生成。

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
- 当前问题3主链路输出为 `3_1_best_price_scheme_*`；辅助扩展结果统一采用 `3_1_aux_financial_best_price_scheme_*`、`3_1_aux_satisfaction_best_price_scheme_*`、`3_1_aux_pareto_frontier.csv` 与 `3_2_aux_*` 前缀，不覆盖主结果。
- `service_access_performance` 仅作为辅助可及绩效指标保留，不与题目满意度混称。
- 当前问题4的正式情景汇总、灵敏度和鲁棒性表以 `Solutions/RQ4/outputs/` 中的最新文件为准。
- 统一论文图、`plot_manifest.csv` 和 `plot_notes.md` 以 `Solutions/plots/outputs/` 中的最新文件为准。
- 统一论文图当前默认采用 `Songti SC` 作为中文字体；直接调用 `build_all_plots.py` 或单独调用各 `plot_rq*.py` builder 时都会先应用同一套字体配置。

## 实验命令

如果你现在要从头重跑并拿论文结果，直接按下面这组命令执行：

```bash
cd /Users/lifulin/Desktop/B

# 1. 清空已有数值结果、统一生图结果和缓存
bash run_full_pipeline.sh clean

# 2. 重跑 Q1 -> Q4 主结果、扩展结果，并自动统一生图
bash run_full_pipeline.sh full

# 3. 跑一遍守护测试，确认当前代码和结果链路一致
bash run_full_pipeline.sh test
```

跑完后重点看这些目录和文件：

- 数值结果：`Solutions/RQ1/outputs/`、`Solutions/RQ2/outputs/`、`Solutions/RQ3/outputs/`、`Solutions/RQ4/outputs/`
- 统一论文图：`Solutions/plots/outputs/png/`、`Solutions/plots/outputs/pdf/`、`Solutions/plots/outputs/svg/`
- 图清单：`Solutions/plots/outputs/plot_manifest.csv`
- 图注建议：`Solutions/plots/outputs/plot_notes.md`

如果中途只改了图题、图注或图筛选，不想重算模型，补跑这一条就够：

```bash
cd /Users/lifulin/Desktop/B
bash run_full_pipeline.sh plots
```
