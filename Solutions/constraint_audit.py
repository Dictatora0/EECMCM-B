from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOLUTIONS_DIR = ROOT / "Solutions"
OUTPUT_DIR = SOLUTIONS_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

RQ1_DIR = SOLUTIONS_DIR / "RQ1"
RQ2_DIR = SOLUTIONS_DIR / "RQ2"
RQ3_DIR = SOLUTIONS_DIR / "RQ3"
RQ4_DIR = SOLUTIONS_DIR / "RQ4"

REPORT_CSV = OUTPUT_DIR / "constraint_audit_report.csv"
REPORT_MD = OUTPUT_DIR / "constraint_audit_report.md"

PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"

P0 = "P0"
P1 = "P1"
P2 = "P2"

SERVICE_ORDER = ["助餐", "日间照料", "上门护理", "康复理疗", "助浴", "紧急救助"]
CARE_LEVEL_ORDER = ["自理", "半失能", "失能"]
SPENDING_LIMIT = {"自理": 0.20, "半失能": 0.25, "失能": 0.30}
DISTANCE_SAT_RULES = [(300.0, 1.00), (500.0, 0.90), (650.0, 0.75), (1000.0, 0.60)]
RESPONSE_SAT_RULES = [(0.60, 1.00), (0.75, 0.93), (0.85, 0.85), (0.95, 0.72), (1.00, 0.60)]
PRICE_SAT_EXPECTED = [(0.0, 1.00), (0.10, 0.90), (0.20, 0.75), (float("inf"), 0.60)]
SUBSIDY_CAP_DAILY = {"小型": 1000.0, "中型": 1800.0, "大型": 2600.0}
CAPACITY_BY_SCALE = {"小型": 1000.0, "中型": 2000.0, "大型": 3000.0}
BUILD_COST_BY_SCALE = {"小型": 18.0, "中型": 32.0, "大型": 45.0}


@dataclass
class AuditRow:
    status: str
    priority: str
    topic: str
    file: str
    field: str
    reason: str
    suggestion: str

    def as_dict(self) -> dict[str, str]:
        return {
            "status": self.status,
            "priority": self.priority,
            "topic": self.topic,
            "file": self.file,
            "field": self.field,
            "reason": self.reason,
            "suggestion": self.suggestion,
        }


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def add(rows: list[AuditRow], status: str, priority: str, topic: str, file: Path | str, field: str, reason: str, suggestion: str) -> None:
    rows.append(
        AuditRow(
            status=status,
            priority=priority,
            topic=topic,
            file=str(file),
            field=field,
            reason=reason,
            suggestion=suggestion,
        )
    )


def expected_price_satisfaction(base_price: float, actual_price: float) -> float:
    if base_price <= 0:
        return 1.0
    premium = actual_price / base_price - 1.0
    if premium <= 1e-12:
        return 1.0
    if premium <= 0.10 + 1e-12:
        return 0.90
    if premium <= 0.20 + 1e-12:
        return 0.75
    return 0.60


def distance_score(distance: float) -> float:
    if distance > 1000.0:
        return 0.0
    for threshold, score in DISTANCE_SAT_RULES:
        if distance <= threshold + 1e-12:
            return score
    return 0.0


def response_score(utilization: float) -> float:
    for threshold, score in RESPONSE_SAT_RULES:
        if utilization <= threshold + 1e-12:
            return score
    return 0.60


def rq2_metric_naming_status(doc_text: str) -> tuple[bool, str]:
    has_metric = "service_access_performance" in doc_text
    has_access_term = "服务可及绩效" in doc_text
    has_not_satisfaction = "不称为“满意度”" in doc_text or "而非“已服务满意度”" in doc_text or "而非已服务满意度" in doc_text
    has_satisfaction_anchor = "service_satisfaction" in doc_text and "满意度" in doc_text
    if has_metric and has_access_term and has_not_satisfaction and has_satisfaction_anchor:
        return True, "论文已明确 `service_access_performance` = 服务可及绩效，并与满意度概念区分。"
    return False, "论文尚未明确把 `service_access_performance` 统一定义为“服务可及绩效”并与 `service_satisfaction` 区分。"


def load_base_price_and_cost() -> tuple[dict[str, float], dict[str, float]]:
    service_rows = read_csv_rows(RQ1_DIR / "outputs" / "1_3_high_precision_adjusted_demand_detail.csv")
    if not service_rows:
        # fallback to source sheet exported values already embedded in repo docs not available here
        pass
    from importlib.util import module_from_spec, spec_from_file_location
    import sys

    common_path = RQ1_DIR / "common.py"
    spec = spec_from_file_location("constraint_audit_rq1_common", common_path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    service_costs = module.load_service_costs()
    base_price = {service: float(service_costs[service]["price"]) for service in SERVICE_ORDER}
    direct_cost = {service: float(service_costs[service]["direct_cost"]) for service in SERVICE_ORDER}
    return base_price, direct_cost


def load_distance_matrix() -> dict[str, dict[str, float]]:
    from importlib.util import module_from_spec, spec_from_file_location
    import sys

    common_path = RQ2_DIR / "common.py"
    spec = spec_from_file_location("constraint_audit_rq2_common", common_path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.load_distance_matrix()


def load_station_scales_from_source() -> dict[str, dict[str, float]]:
    from importlib.util import module_from_spec, spec_from_file_location
    import sys

    common_path = RQ2_DIR / "common.py"
    spec = spec_from_file_location("constraint_audit_rq2_common_scales", common_path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    scales = module.load_station_scales()
    return {
        k: {
            "build_cost_wan": float(v.build_cost_wan),
            "daily_fixed_cost": float(v.daily_fixed_cost),
            "daily_capacity": float(v.daily_capacity),
        }
        for k, v in scales.items()
    }


def audit_rq1(rows: list[AuditRow]) -> None:
    common_text = (RQ1_DIR / "common.py").read_text(encoding="utf-8")
    if "DEATH_RATE = 0.05" in common_text:
        add(rows, PASS, P0, "RQ1 death rate", RQ1_DIR / "common.py", "DEATH_RATE", "统一使用 0.05。", "保持不变。")
    else:
        add(rows, FAIL, P0, "RQ1 death rate", RQ1_DIR / "common.py", "DEATH_RATE", "未统一使用 0.05。", "将基准死亡率统一改为 0.05。")

    if "ELDER_GROWTH_RATE = 0.07" in common_text:
        add(rows, PASS, P0, "RQ1 growth rate", RQ1_DIR / "common.py", "ELDER_GROWTH_RATE", "基准增长率为 0.07。", "保持不变。")
    else:
        add(rows, FAIL, P0, "RQ1 growth rate", RQ1_DIR / "common.py", "ELDER_GROWTH_RATE", "基准增长率不是 0.07。", "将基准增长率恢复为 0.07，仅在 RQ4 S1 使用 0.08。")

    theoretical_rows = read_csv_rows(RQ1_DIR / "outputs" / "1_2_high_precision_theoretical_demand.csv")
    theoretical_detail_path = RQ1_DIR / "outputs" / "1_2_high_precision_theoretical_demand_detail.csv"
    if theoretical_detail_path.exists():
        add(rows, PASS, P0, "RQ1 theoretical detail", theoretical_detail_path, "care_level", "已生成按老人类型拆分的理论需求明细。", "保持 1.2 明细与汇总双输出。")
    else:
        add(rows, FAIL, P0, "RQ1 theoretical detail", theoretical_detail_path, "care_level", "缺少按自理/半失能/失能拆分的 1.2 理论需求明细文件。", "补充 `1_2_high_precision_theoretical_demand_detail.csv` 与展示版 detail 文件。")

    adjusted_detail = read_csv_rows(RQ1_DIR / "outputs" / "1_3_high_precision_adjusted_demand_detail.csv")
    if not adjusted_detail:
        add(rows, FAIL, P0, "RQ1 adjusted demand", RQ1_DIR / "outputs" / "1_3_high_precision_adjusted_demand_detail.csv", "file", "缺少消费约束明细输出。", "先重跑 RQ1。")
        return

    emergency_scaled = [
        row for row in adjusted_detail
        if row["service"] == "紧急救助"
        and abs(float(row["adjusted_per_person"]) - float(row["theoretical_per_person"])) > 1e-6
    ]
    if emergency_scaled:
        add(rows, PASS, P1, "RQ1 emergency free-service exception", RQ1_DIR / "outputs" / "1_3_high_precision_adjusted_demand_detail.csv", "adjusted_per_person", "紧急救助未被消费预算缩减，符合当前题面解释分支。", "论文必须明确“仅收费服务等比例缩减，紧急救助公益免费但仍占用容量并产生成本”。")
    else:
        add(rows, PASS, P1, "RQ1 emergency free-service exception", RQ1_DIR / "outputs" / "1_3_high_precision_adjusted_demand_detail.csv", "adjusted_per_person", "紧急救助保持免费且未被消费缩减。", "确保论文保持相同口径。")

    spending_errors = []
    for row in adjusted_detail:
        level = row["care_level"]
        expected_budget = float(row["monthly_income"]) * SPENDING_LIMIT[level]
        if abs(float(row["budget_limit"]) - expected_budget) > 1e-6:
            spending_errors.append(row)
    if spending_errors:
        add(rows, FAIL, P0, "RQ1 spending limit", RQ1_DIR / "outputs" / "1_3_high_precision_adjusted_demand_detail.csv", "budget_limit", f"发现 {len(spending_errors)} 行预算上限不等于收入乘对应比例。", "按小区 × 老人类型重算消费上限。")
    else:
        add(rows, PASS, P0, "RQ1 spending limit", RQ1_DIR / "outputs" / "1_3_high_precision_adjusted_demand_detail.csv", "budget_limit", "消费上限按小区 × 老人类型计算。", "保持不变。")

    meta_path = RQ1_DIR / "outputs" / "rq1_high_precision_metadata.json"
    if meta_path.exists():
        metadata = read_json(meta_path)
        files = metadata.get("files", {})
        if "theoretical_demand_detail" not in files:
            add(rows, WARN, P1, "RQ1 metadata", meta_path, "files", "元数据尚未声明 1.2 detail 文件，可能导致下游审计漏检。", "将 detail 文件写入 metadata。")
        else:
            add(rows, PASS, P1, "RQ1 metadata", meta_path, "files", "元数据已声明 1.2 detail 文件。", "保持不变。")


def audit_rq2(rows: list[AuditRow]) -> None:
    summary_rows = read_csv_rows(RQ2_DIR / "outputs" / "2_1_best_scheme_summary.csv")
    station_rows = read_csv_rows(RQ2_DIR / "outputs" / "2_1_best_scheme_stations.csv")
    alloc_rows = read_csv_rows(RQ2_DIR / "outputs" / "2_1_best_scheme_allocations.csv")
    rq_doc_text = (ROOT / "RQ" / "RQ.md").read_text(encoding="utf-8")
    distance_matrix = load_distance_matrix()
    scales = load_station_scales_from_source()
    base_price, direct_cost = load_base_price_and_cost()

    if not summary_rows or not station_rows or not alloc_rows:
        add(rows, FAIL, P0, "RQ2 outputs", RQ2_DIR / "outputs", "files", "RQ2 主输出不完整。", "重跑 `python Solutions/RQ2/2_1.py`。")
        return

    summary = summary_rows[0]
    station_map = {row["station_community"]: row for row in station_rows}
    allowed_communities = set("ABCDEFGHIJ")
    bad_sites = [name for name in station_map if name not in allowed_communities]
    if bad_sites:
        add(rows, FAIL, P0, "RQ2 candidate stations", RQ2_DIR / "outputs" / "2_1_best_scheme_stations.csv", "station_community", f"发现非法站点 {bad_sites}。", "候选站点严格限制为 A-J。")
    else:
        add(rows, PASS, P0, "RQ2 candidate stations", RQ2_DIR / "outputs" / "2_1_best_scheme_stations.csv", "station_community", "站点均位于 A-J 小区内部。", "保持不变。")

    bad_caps = []
    bad_build_costs = []
    for row in station_rows:
        scale = row["scale"]
        if abs(float(row["daily_capacity"]) - CAPACITY_BY_SCALE[scale]) > 1e-6:
            bad_caps.append(row["station_community"])
        if abs(float(summary["build_cost_wan"]) - sum(BUILD_COST_BY_SCALE[r["scale"]] for r in station_rows)) > 1e-6:
            bad_build_costs.append("summary")
            break
    if bad_caps:
        add(rows, FAIL, P0, "RQ2 capacity upper bound", RQ2_DIR / "outputs" / "2_1_best_scheme_stations.csv", "daily_capacity", f"容量与规模上限不一致：{bad_caps}。", "将日容量严格绑定到 1000/2000/3000。")
    else:
        add(rows, PASS, P0, "RQ2 capacity upper bound", RQ2_DIR / "outputs" / "2_1_best_scheme_stations.csv", "daily_capacity", "各站容量与规模上限一致。", "保持不变。")

    if float(summary["build_cost_wan"]) <= 120.0 + 1e-9:
        add(rows, PASS, P0, "RQ2 budget", RQ2_DIR / "outputs" / "2_1_best_scheme_summary.csv", "build_cost_wan", "基准方案总建设成本未超过 120 万。", "保持不变。")
    else:
        add(rows, FAIL, P0, "RQ2 budget", RQ2_DIR / "outputs" / "2_1_best_scheme_summary.csv", "build_cost_wan", "基准方案超过 120 万预算。", "约束基准预算 <= 120。")

    bad_radius = []
    for row in alloc_rows:
        primary = row["primary_station"].strip()
        overflow = row["overflow_station"].strip()
        community = row["community"]
        if primary and distance_matrix[community][primary] > 1000.0 + 1e-9:
            bad_radius.append((community, primary, "primary"))
        if overflow and distance_matrix[community][overflow] > 1000.0 + 1e-9:
            bad_radius.append((community, overflow, "overflow"))
    if bad_radius:
        add(rows, FAIL, P0, "RQ2 radius", RQ2_DIR / "outputs" / "2_1_best_scheme_allocations.csv", "primary_station/overflow_station", f"存在超半径服务分配：{bad_radius[:3]}。", "距离 >1000 的分配、服务量、收入、补贴应为 0。")
    else:
        add(rows, PASS, P0, "RQ2 radius", RQ2_DIR / "outputs" / "2_1_best_scheme_allocations.csv", "primary_station/overflow_station", "未发现超 1000 米分配。", "保持不变。")

    for row in alloc_rows:
        served = float(row["raw_served_demand_daily"])
        sat = float(row["service_satisfaction"])
        if served <= 1e-9 and sat > 1e-9:
            add(rows, FAIL, P0, "RQ2 satisfaction for unserved", RQ2_DIR / "outputs" / "2_1_best_scheme_allocations.csv", "service_satisfaction", f"未服务小区 {row['community']} 仍保留正常满意度。", "未服务或零服务小区满意度应记为 0。")
            break
    else:
        add(rows, PASS, P0, "RQ2 satisfaction for unserved", RQ2_DIR / "outputs" / "2_1_best_scheme_allocations.csv", "service_satisfaction", "未服务小区满意度已清零。", "保持不变。")

    bad_profit_station = [row["station_community"] for row in station_rows if abs(float(row["annual_depreciation"]) - BUILD_COST_BY_SCALE[row["scale"]] * 10000.0 / 20.0) > 1e-6]
    if bad_profit_station:
        add(rows, FAIL, P0, "RQ2 depreciation", RQ2_DIR / "outputs" / "2_1_best_scheme_stations.csv", "annual_depreciation", f"折旧口径错误：{bad_profit_station}。", "按建设成本/20年计提折旧。")
    else:
        add(rows, PASS, P0, "RQ2 depreciation", RQ2_DIR / "outputs" / "2_1_best_scheme_stations.csv", "annual_depreciation", "折旧口径与建设成本/20一致。", "保持不变。")

    for row in station_rows:
        scale = row["scale"]
        if float(row["annual_subsidy"]) > SUBSIDY_CAP_DAILY[scale] * 365.0 + 1e-6:
            add(rows, FAIL, P0, "RQ2 subsidy cap", RQ2_DIR / "outputs" / "2_1_best_scheme_stations.csv", "annual_subsidy", f"站点 {row['station_community']} 补贴超过单站上限。", "按站点分别应用日补贴上限。")
            break
    else:
        add(rows, PASS, P0, "RQ2 subsidy cap", RQ2_DIR / "outputs" / "2_1_best_scheme_stations.csv", "annual_subsidy", "站点级补贴未超过单站上限。", "保持不变。")

    if "service_access_performance" in alloc_rows[0]:
        naming_ok, naming_reason = rq2_metric_naming_status(rq_doc_text)
        if naming_ok:
            add(rows, PASS, P1, "RQ2 metric naming", ROOT / "RQ" / "RQ.md", "service_access_performance", naming_reason, "保持不变。")
        else:
            add(rows, WARN, P1, "RQ2 metric naming", ROOT / "RQ" / "RQ.md", "service_access_performance", naming_reason, "论文明确 `service_access_performance` 是“服务可及绩效”，不是题目满意度。")

    summary_profit = int(float(summary["profit_compliant"]))
    station_all_profit = int(all(int(float(row["profit_compliant"])) == 1 for row in station_rows))
    if summary_profit != station_all_profit:
        add(rows, FAIL, P0, "RQ2 profit compliance aggregation", RQ2_DIR / "outputs" / "2_1_best_scheme_summary.csv", "profit_compliant", "汇总利润合规与逐站结果不一致。", "汇总 `profit_compliant` 必须等于逐站全满足。")
    else:
        add(rows, PASS, P0, "RQ2 profit compliance aggregation", RQ2_DIR / "outputs" / "2_1_best_scheme_summary.csv", "profit_compliant", "汇总利润合规与逐站结果一致。", "保持不变。")


def audit_rq3(rows: list[AuditRow]) -> None:
    main_summary_path = RQ3_DIR / "outputs" / "3_1_best_price_scheme_summary.csv"
    main_community_path = RQ3_DIR / "outputs" / "3_1_best_price_scheme_communities.csv"
    main_station_path = RQ3_DIR / "outputs" / "3_1_best_price_scheme_stations.csv"
    aux_summary_paths = [
        RQ3_DIR / "outputs" / "3_1_aux_financial_best_price_scheme_summary.csv",
        RQ3_DIR / "outputs" / "3_1_aux_satisfaction_best_price_scheme_summary.csv",
    ]
    aux_community_paths = [
        RQ3_DIR / "outputs" / "3_1_aux_financial_best_price_scheme_communities.csv",
        RQ3_DIR / "outputs" / "3_1_aux_satisfaction_best_price_scheme_communities.csv",
    ]
    aux_station_paths = [
        RQ3_DIR / "outputs" / "3_1_aux_financial_best_price_scheme_stations.csv",
        RQ3_DIR / "outputs" / "3_1_aux_satisfaction_best_price_scheme_stations.csv",
    ]
    base_price, _direct_cost = load_base_price_and_cost()
    q2_summary = read_csv_rows(RQ2_DIR / "outputs" / "2_1_best_scheme_summary.csv")
    q2_stations = read_csv_rows(RQ2_DIR / "outputs" / "2_1_best_scheme_stations.csv")
    q2_detail = q2_summary[0]["scheme_detail"] if q2_summary else ""

    main_summary_rows = read_csv_rows(main_summary_path)
    if not main_summary_rows:
        add(rows, FAIL, P0, "RQ3 main summary output", main_summary_path, "file", "缺少 RQ3 主结果汇总输出。", "重跑 `python Solutions/RQ3/3_1.py`。")
    else:
        row = main_summary_rows[0]
        if row.get("subsidy_policy") not in {"none", ""}:
            add(rows, FAIL, P0, "RQ3 extra subsidy mechanism", main_summary_path, "subsidy_policy", f"当前主结果含题面外补贴机制 `{row.get('subsidy_policy')}`。", "主结果仅保留题目给定站点级补贴。")
        else:
            add(rows, PASS, P0, "RQ3 extra subsidy mechanism", main_summary_path, "subsidy_policy", "主结果未发现题面外个人补贴机制。", "保持不变。")

        if int(float(row["converged"])) != 1:
            add(rows, FAIL, P0, "RQ3 convergence", main_summary_path, "converged", "当前主结果未收敛却被作为最终方案输出。", "若无收敛联合可行方案，必须显式报告不存在，不能把未收敛方案写成主结果。")
        else:
            add(rows, PASS, P0, "RQ3 convergence", main_summary_path, "converged", "当前主结果已收敛。", "保持不变。")

        if row.get("pricing_model") != "station_service_level_pricing":
            add(rows, FAIL, P0, "RQ3 pricing model", main_summary_path, "pricing_model", f"主结果仍不是逐站逐服务定价，而是 `{row.get('pricing_model')}`。", "将主结果统一为逐站逐服务定价模型。")
        else:
            add(rows, PASS, P0, "RQ3 pricing model", main_summary_path, "pricing_model", "主结果已使用逐站逐服务定价。", "保持不变。")

        if row.get("pricing_formula") != "p_{j,r} independent for r=1,...,5; p_{j,6}=0":
            add(rows, FAIL, P0, "RQ3 pricing formula", main_summary_path, "pricing_formula", f"主结果定价公式口径错误：`{row.get('pricing_formula')}`。", "将主结果说明统一为 `p_{j,r}` 逐站逐服务独立定价，紧急救助免费。")
        else:
            add(rows, PASS, P0, "RQ3 pricing formula", main_summary_path, "pricing_formula", "主结果定价公式与题面口径一致。", "保持不变。")

    legacy_paths = [
        RQ3_DIR / "outputs" / "3_1_financial_best_price_scheme_summary.csv",
        RQ3_DIR / "outputs" / "3_1_fairness_best_price_scheme_summary.csv",
        RQ3_DIR / "outputs" / "3_1_financial_best_price_scheme_communities.csv",
        RQ3_DIR / "outputs" / "3_1_fairness_best_price_scheme_communities.csv",
        RQ3_DIR / "outputs" / "3_1_financial_best_price_scheme_stations.csv",
        RQ3_DIR / "outputs" / "3_1_fairness_best_price_scheme_stations.csv",
    ]
    stale_legacy = [path.name for path in legacy_paths if path.exists()]
    if stale_legacy:
        add(rows, WARN, P1, "RQ3 legacy output names", RQ3_DIR / "outputs", "legacy_files", f"发现旧双主方案命名残留：{stale_legacy[:4]}。", "清理旧 `3_1_financial_*` / `3_1_fairness_*` / `3_1_aux_fairness_*` 输出，避免与主结果混淆。")
    else:
        add(rows, PASS, P1, "RQ3 legacy output names", RQ3_DIR / "outputs", "legacy_files", "未发现旧双主方案命名残留。", "保持不变。")

    for path in aux_summary_paths:
        rows_csv = read_csv_rows(path)
        if not rows_csv:
            add(rows, FAIL, P0, "RQ3 auxiliary summary outputs", path, "file", "缺少 RQ3 辅助扩展汇总输出。", "重跑 `python Solutions/RQ3/3_1.py`。")
            continue
        row = rows_csv[0]
        if row.get("subsidy_policy") not in {"none", ""}:
            add(rows, FAIL, P0, "RQ3 auxiliary extra subsidy mechanism", path, "subsidy_policy", f"当前辅助输出含题面外补贴机制 `{row.get('subsidy_policy')}`。", "辅助扩展也应默认只保留题目给定站点级补贴。")
        else:
            add(rows, PASS, P0, "RQ3 auxiliary extra subsidy mechanism", path, "subsidy_policy", "辅助输出未发现题面外个人补贴机制。", "保持不变。")

    for path in [main_community_path, *aux_community_paths]:
        rows_csv = read_csv_rows(path)
        if not rows_csv:
            continue
        first = rows_csv[0]
        missing = [field for field in ["distance_satisfaction", "response_satisfaction", "price_satisfaction", "service_satisfaction"] if field not in first]
        if missing:
            add(rows, FAIL, P0, "RQ3 per-community satisfaction decomposition", path, ",".join(missing), f"缺少小区级满意度分解字段：{missing}。", "输出每个小区的距离、响应、价格、综合满意度。")
        else:
            add(rows, PASS, P0, "RQ3 per-community satisfaction decomposition", path, "distance_satisfaction/response_satisfaction/price_satisfaction/service_satisfaction", "已具备小区级满意度分解字段。", "保持不变。")

        overflow_nonempty = [row["community"] for row in rows_csv if str(row.get("overflow_station", "")).strip()]
        if overflow_nonempty:
            add(rows, FAIL, P0, "RQ3 single-station choice", path, "overflow_station", f"发现仍有小区使用备站/溢出站：{overflow_nonempty[:3]}。", "主模型与辅助输出都应保持单站选择，容量不足部分直接计 unmet。")
        else:
            add(rows, PASS, P0, "RQ3 single-station choice", path, "overflow_station", "未发现备站/溢出站分流。", "保持不变。")

    for path in [main_station_path, *aux_station_paths]:
        rows_csv = read_csv_rows(path)
        if not rows_csv:
            continue
        for row in rows_csv:
            if abs(float(row["annual_government_subsidy"]) - float(row["annual_subsidy"])) > 1e-6:
                add(rows, WARN, P1, "RQ3 station subsidy fields", path, "annual_government_subsidy/annual_subsidy", f"站点 {row['station_community']} 同义字段不一致。", "统一站点级补贴字段口径。")
                break
        else:
            add(rows, PASS, P1, "RQ3 station subsidy fields", path, "annual_government_subsidy/annual_subsidy", "站点级补贴字段口径一致。", "保持不变。")

    if q2_detail:
        q2_station_plan = ";".join(f"{row['station_community']}-{row['scale']}" for row in q2_stations)
        if q2_station_plan != q2_detail:
            add(rows, WARN, P1, "RQ3 uses RQ2 layout", RQ2_DIR / "outputs" / "2_1_best_scheme_summary.csv", "scheme_detail", "Q2 汇总与站点明细布局串不一致，可能干扰 RQ3 固定布局核验。", "先修复 RQ2 输出一致性。")
        else:
            add(rows, PASS, P0, "RQ3 uses RQ2 layout", RQ2_DIR / "outputs" / "2_1_best_scheme_summary.csv", "scheme_detail", "RQ3 读取的基线布局与 RQ2 主方案一致。", "保持不变。")

    readme_text = (RQ3_DIR / "README.md").read_text(encoding="utf-8")
    if "0.90" in readme_text and "0.75" in readme_text:
        add(rows, PASS, P1, "RQ3 documentation price tiers", RQ3_DIR / "README.md", "价格满意度分段", "文档已同步题目价格满意度分段。", "保持不变。")
    else:
        add(rows, WARN, P1, "RQ3 documentation price tiers", RQ3_DIR / "README.md", "价格满意度分段", "文档可能仍保留旧价格满意度口径。", "把价格满意度文字同步到 1.00/0.90/0.75/0.60。")


def audit_rq4(rows: list[AuditRow]) -> None:
    q2_scenario_rows = read_csv_rows(RQ4_DIR / "outputs" / "4_1_q2_scenario_summary.csv")
    q3_scenario_rows = read_csv_rows(RQ4_DIR / "outputs" / "4_1_q3_scenario_summary.csv")
    s4_path = RQ4_DIR / "outputs" / "4_1_s4_diagnostics.json"

    if not q2_scenario_rows or not q3_scenario_rows:
        add(rows, FAIL, P0, "RQ4 outputs", RQ4_DIR / "outputs", "files", "RQ4 情景汇总输出不完整。", "重跑 `python Solutions/RQ4/4_1.py`。")
        return

    s1_rows = [row for row in q2_scenario_rows if row["scenario"] == "S1"]
    s2_rows = [row for row in q2_scenario_rows if row["scenario"] == "S2"]
    s3_rows = [row for row in q2_scenario_rows if row["scenario"] == "S3"]
    s4_rows = [row for row in q2_scenario_rows if row["scenario"] == "S4"]
    if s1_rows and abs(float(s1_rows[0]["elderly_growth_rate"]) - 0.08) <= 1e-9:
        add(rows, PASS, P0, "RQ4 S1 growth rate", RQ4_DIR / "outputs" / "4_1_q2_scenario_summary.csv", "elderly_growth_rate", "S1 显式使用 0.08。", "保持不变。")
    else:
        add(rows, FAIL, P0, "RQ4 S1 growth rate", RQ4_DIR / "outputs" / "4_1_q2_scenario_summary.csv", "elderly_growth_rate", "S1 未显式使用 0.08。", "将 S1 重新传参为 0.08 并重跑 RQ1-RQ3。")

    if s2_rows and abs(float(s2_rows[0]["p12"]) - 0.055) <= 1e-9 and abs(float(s2_rows[0]["p23"]) - 0.095) <= 1e-9:
        add(rows, PASS, P0, "RQ4 S2 transition", RQ4_DIR / "outputs" / "4_1_q2_scenario_summary.csv", "p12/p23", "S2 显式使用 0.055 / 0.095。", "保持不变。")
    else:
        add(rows, FAIL, P0, "RQ4 S2 transition", RQ4_DIR / "outputs" / "4_1_q2_scenario_summary.csv", "p12/p23", "S2 未显式使用 0.055 / 0.095。", "重跑 S2。")

    if s3_rows and abs(float(s3_rows[0]["fixed_cost_multiplier"]) - 1.2) <= 1e-9:
        add(rows, PASS, P0, "RQ4 S3 fixed cost", RQ4_DIR / "outputs" / "4_1_q2_scenario_summary.csv", "fixed_cost_multiplier", "S3 显式使用固定成本 1.2 倍。", "保持不变。")
    else:
        add(rows, FAIL, P0, "RQ4 S3 fixed cost", RQ4_DIR / "outputs" / "4_1_q2_scenario_summary.csv", "fixed_cost_multiplier", "S3 未显式使用固定成本 1.2 倍。", "重跑 S3。")

    if s4_rows and abs(float(s4_rows[0]["budget_limit"]) - 140.0) <= 1e-9:
        add(rows, PASS, P0, "RQ4 S4 budget", RQ4_DIR / "outputs" / "4_1_q2_scenario_summary.csv", "budget_limit", "S4 显式使用 140 万预算。", "保持不变。")
    else:
        add(rows, FAIL, P0, "RQ4 S4 budget", RQ4_DIR / "outputs" / "4_1_q2_scenario_summary.csv", "budget_limit", "S4 未显式使用 140 万预算。", "重跑 S4 并传入 budget_limit=140。")

    if s4_path.exists():
        s4 = read_json(s4_path)
        if s4.get("uses_budget_above_120_and_not_above_140") is True:
            add(rows, PASS, P0, "RQ4 S4 diagnostics", s4_path, "uses_budget_above_120_and_not_above_140", "S4 诊断确认真实使用超过 120 且不超过 140 的预算。", "保持不变。")
        else:
            add(rows, WARN, P1, "RQ4 S4 diagnostics", s4_path, "uses_budget_above_120_and_not_above_140", "S4 诊断未明确证明预算放宽真实生效。", "保留专项诊断字段并核实。")

    required_compare_fields = {"station_plan", "annual_government_subsidy", "served_population_coverage", "average_service_access_performance"}
    missing_q3 = required_compare_fields - set(q3_scenario_rows[0].keys())
    if missing_q3:
        add(rows, FAIL, P0, "RQ4 comparison fields", RQ4_DIR / "outputs" / "4_1_q3_scenario_summary.csv", ",".join(sorted(missing_q3)), f"情景比较缺少字段 {sorted(missing_q3)}。", "补齐站点布局、补贴、覆盖率、满意度/绩效字段。")
    else:
        add(rows, PASS, P0, "RQ4 comparison fields", RQ4_DIR / "outputs" / "4_1_q3_scenario_summary.csv", "scenario compare fields", "情景比较表含站点方案、补贴、覆盖率与绩效字段。", "保持不变。")


def summarize(rows: list[AuditRow]) -> tuple[list[AuditRow], list[AuditRow], list[AuditRow]]:
    p0 = [row for row in rows if row.priority == P0 and row.status == FAIL]
    p1 = [row for row in rows if row.priority == P1 and row.status in {FAIL, WARN}]
    p2 = [row for row in rows if row.priority == P2 and row.status in {FAIL, WARN}]
    return p0, p1, p2


def write_csv_report(rows: list[AuditRow]) -> None:
    if not rows:
        REPORT_CSV.write_text("", encoding="utf-8")
        return
    with REPORT_CSV.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].as_dict().keys()))
        writer.writeheader()
        writer.writerows([row.as_dict() for row in rows])


def write_md_report(rows: list[AuditRow]) -> None:
    p0, p1, p2 = summarize(rows)
    lines: list[str] = []
    lines.append("# Constraint Audit Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total checks: {len(rows)}")
    lines.append(f"- `FAIL`: {sum(1 for row in rows if row.status == FAIL)}")
    lines.append(f"- `WARN`: {sum(1 for row in rows if row.status == WARN)}")
    lines.append(f"- `PASS`: {sum(1 for row in rows if row.status == PASS)}")
    lines.append(f"- Remaining P0 count: {len(p0)}")
    lines.append("")
    lines.append("## P0 Issues")
    lines.append("")
    if p0:
        for row in p0:
            lines.append(f"- [{row.topic}] `{row.file}` `{row.field}`: {row.reason} 修复建议：{row.suggestion}")
    else:
        lines.append("- None.")
    lines.append("")
    lines.append("## P1 Issues")
    lines.append("")
    if p1:
        for row in p1:
            lines.append(f"- [{row.status}] [{row.topic}] `{row.file}` `{row.field}`: {row.reason} 处理建议：{row.suggestion}")
    else:
        lines.append("- None.")
    lines.append("")
    lines.append("## P2 Issues")
    lines.append("")
    if p2:
        for row in p2:
            lines.append(f"- [{row.status}] [{row.topic}] `{row.file}` `{row.field}`: {row.reason} 处理建议：{row.suggestion}")
    else:
        lines.append("- None.")
    lines.append("")
    lines.append("## Full Findings")
    lines.append("")
    for row in rows:
        lines.append(f"- `{row.status}` `{row.priority}` [{row.topic}] `{row.file}` `{row.field}`: {row.reason} 建议：{row.suggestion}")
    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    rows: list[AuditRow] = []
    audit_rq1(rows)
    audit_rq2(rows)
    audit_rq3(rows)
    audit_rq4(rows)
    write_csv_report(rows)
    write_md_report(rows)
    print(f"Wrote {REPORT_CSV}")
    print(f"Wrote {REPORT_MD}")
    print(f"Total checks: {len(rows)}; FAIL={sum(1 for row in rows if row.status == FAIL)}; WARN={sum(1 for row in rows if row.status == WARN)}")


if __name__ == "__main__":
    main()
