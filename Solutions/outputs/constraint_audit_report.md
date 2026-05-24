# Constraint Audit Report

## Summary

- Total checks: 9
- `FAIL`: 6
- `WARN`: 0
- `PASS`: 3
- Remaining P0 count: 6

## P0 Issues

- [RQ1 theoretical detail] `/Users/lifulin/Desktop/B/Solutions/RQ1/outputs/1_2_high_precision_theoretical_demand_detail.csv` `care_level`: 缺少按自理/半失能/失能拆分的 1.2 理论需求明细文件。 修复建议：补充 `1_2_high_precision_theoretical_demand_detail.csv` 与展示版 detail 文件。
- [RQ1 adjusted demand] `/Users/lifulin/Desktop/B/Solutions/RQ1/outputs/1_3_high_precision_adjusted_demand_detail.csv` `file`: 缺少消费约束明细输出。 修复建议：先重跑 RQ1。
- [RQ2 outputs] `/Users/lifulin/Desktop/B/Solutions/RQ2/outputs` `files`: RQ2 主输出不完整。 修复建议：重跑 `python Solutions/RQ2/2_1.py`。
- [RQ3 summary outputs] `/Users/lifulin/Desktop/B/Solutions/RQ3/outputs/3_1_financial_best_price_scheme_summary.csv` `file`: 缺少 RQ3 汇总输出。 修复建议：重跑 `python Solutions/RQ3/3_1.py`。
- [RQ3 summary outputs] `/Users/lifulin/Desktop/B/Solutions/RQ3/outputs/3_1_fairness_best_price_scheme_summary.csv` `file`: 缺少 RQ3 汇总输出。 修复建议：重跑 `python Solutions/RQ3/3_1.py`。
- [RQ4 outputs] `/Users/lifulin/Desktop/B/Solutions/RQ4/outputs` `files`: RQ4 情景汇总输出不完整。 修复建议：重跑 `python Solutions/RQ4/4_1.py`。

## P1 Issues

- None.

## P2 Issues

- None.

## Full Findings

- `PASS` `P0` [RQ1 death rate] `/Users/lifulin/Desktop/B/Solutions/RQ1/common.py` `DEATH_RATE`: 统一使用 0.05。 建议：保持不变。
- `PASS` `P0` [RQ1 growth rate] `/Users/lifulin/Desktop/B/Solutions/RQ1/common.py` `ELDER_GROWTH_RATE`: 基准增长率为 0.07。 建议：保持不变。
- `FAIL` `P0` [RQ1 theoretical detail] `/Users/lifulin/Desktop/B/Solutions/RQ1/outputs/1_2_high_precision_theoretical_demand_detail.csv` `care_level`: 缺少按自理/半失能/失能拆分的 1.2 理论需求明细文件。 建议：补充 `1_2_high_precision_theoretical_demand_detail.csv` 与展示版 detail 文件。
- `FAIL` `P0` [RQ1 adjusted demand] `/Users/lifulin/Desktop/B/Solutions/RQ1/outputs/1_3_high_precision_adjusted_demand_detail.csv` `file`: 缺少消费约束明细输出。 建议：先重跑 RQ1。
- `FAIL` `P0` [RQ2 outputs] `/Users/lifulin/Desktop/B/Solutions/RQ2/outputs` `files`: RQ2 主输出不完整。 建议：重跑 `python Solutions/RQ2/2_1.py`。
- `FAIL` `P0` [RQ3 summary outputs] `/Users/lifulin/Desktop/B/Solutions/RQ3/outputs/3_1_financial_best_price_scheme_summary.csv` `file`: 缺少 RQ3 汇总输出。 建议：重跑 `python Solutions/RQ3/3_1.py`。
- `FAIL` `P0` [RQ3 summary outputs] `/Users/lifulin/Desktop/B/Solutions/RQ3/outputs/3_1_fairness_best_price_scheme_summary.csv` `file`: 缺少 RQ3 汇总输出。 建议：重跑 `python Solutions/RQ3/3_1.py`。
- `PASS` `P1` [RQ3 documentation price tiers] `/Users/lifulin/Desktop/B/Solutions/RQ3/README.md` `价格满意度分段`: 文档已同步题目价格满意度分段。 建议：保持不变。
- `FAIL` `P0` [RQ4 outputs] `/Users/lifulin/Desktop/B/Solutions/RQ4/outputs` `files`: RQ4 情景汇总输出不完整。 建议：重跑 `python Solutions/RQ4/4_1.py`。
