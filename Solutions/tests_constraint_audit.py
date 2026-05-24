from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import csv
import sys


SOLUTIONS_DIR = Path(__file__).resolve().parent
AUDIT_PATH = SOLUTIONS_DIR / "constraint_audit.py"
ROOT_README_PATH = SOLUTIONS_DIR.parent / "README.md"
SOLUTIONS_README_PATH = SOLUTIONS_DIR / "README.md"
RQ4_README_TARGET_PATH = SOLUTIONS_DIR / "RQ4" / "4_1.py"
RUNNER_PATH = SOLUTIONS_DIR.parent / "run_full_pipeline.sh"
AUDIT_SPEC = spec_from_file_location("constraint_audit_module", AUDIT_PATH)
if AUDIT_SPEC is None or AUDIT_SPEC.loader is None:
    raise RuntimeError(f"Failed to load constraint audit module from {AUDIT_PATH}")
CONSTRAINT_AUDIT = module_from_spec(AUDIT_SPEC)
sys.modules[AUDIT_SPEC.name] = CONSTRAINT_AUDIT
AUDIT_SPEC.loader.exec_module(CONSTRAINT_AUDIT)

rq2_metric_naming_status = CONSTRAINT_AUDIT.rq2_metric_naming_status
audit_rq3 = CONSTRAINT_AUDIT.audit_rq3
AuditRow = CONSTRAINT_AUDIT.AuditRow


def test_rq2_metric_naming_status_accepts_explicit_sync() -> None:
    text = """
`service_satisfaction` 表示已服务对象的满意度。
`service_access_performance` 表示考虑服务承接比例后的可及绩效。
本文统一将 `service_access_performance` 称为“服务可及绩效”，不称为“满意度”；满意度专指 `service_satisfaction` 及其分项 `distance_satisfaction`、`response_satisfaction`、`price_satisfaction`。
"""
    ok, _reason = rq2_metric_naming_status(text)
    assert ok is True


def test_rq2_metric_naming_status_rejects_ambiguous_text() -> None:
    text = """
`service_satisfaction` 表示小区服务满意度。
`service_access_performance` 表示小区服务表现。
"""
    ok, reason = rq2_metric_naming_status(text)
    assert ok is False
    assert "服务可及绩效" in reason


def test_constraint_audit_uses_split_q3_main_and_aux_paths() -> None:
    text = AUDIT_PATH.read_text(encoding="utf-8")
    assert "3_1_best_price_scheme_summary.csv" in text
    assert "3_1_best_price_scheme_communities.csv" in text
    assert "3_1_best_price_scheme_stations.csv" in text
    assert "3_1_aux_financial_best_price_scheme_summary.csv" in text
    assert "3_1_aux_satisfaction_best_price_scheme_summary.csv" in text
    assert 'main_summary_path = RQ3_DIR / "outputs" / "3_1_best_price_scheme_summary.csv"' in text
    assert 'aux_summary_paths = [' in text
    assert 'legacy_paths = [' in text


def test_constraint_audit_checks_q3_service_level_pricing_formula() -> None:
    text = AUDIT_PATH.read_text(encoding="utf-8")
    assert "station_service_level_pricing" in text
    assert "p_{j,r} independent for r=1,...,5; p_{j,6}=0" in text


def test_run_full_pipeline_uses_python3_and_current_q3_chain() -> None:
    text = RUNNER_PATH.read_text(encoding="utf-8")
    assert "PYTHON_BIN" in text
    assert 'PYTHON_BIN="${PYTHON_BIN:-python3}"' in text
    assert "clean_outputs" in text
    assert "run_full()" in text
    assert "clean_outputs\n" in text or "clean_outputs\r\n" in text
    assert "Solutions/RQ3/3_1.py" in text
    assert "Solutions/RQ3/3_4_joint_feasibility_diagnostics.py" in text
    assert "Solutions/plots/build_all_plots.py" in text
    assert "bash run_full_pipeline.sh plots" in text
    assert "Solutions/RQ4/tests.py" in text
    assert "find \"$ROOT_DIR/Solutions/RQ4/cache\"" in text


def test_run_full_pipeline_clean_preserves_outputs_readme_files() -> None:
    text = RUNNER_PATH.read_text(encoding="utf-8")
    assert "outputs/README.md" in text
    assert "! -name 'README.md'" in text
    assert "find \"$ROOT_DIR/Solutions\" -type f -path '*/outputs/*'" in text


def test_readmes_use_current_main_aux_q3_wording() -> None:
    root_text = ROOT_README_PATH.read_text(encoding="utf-8")
    solutions_text = SOLUTIONS_README_PATH.read_text(encoding="utf-8")
    assert "3_1_best_price_scheme_*" in root_text
    assert "3_1_aux_financial_best_price_scheme_*" in root_text
    assert "3_5_satisfaction_objective_*" in root_text
    assert "3_1_best_price_scheme_*" in solutions_text
    assert "3_1_aux_financial_best_price_scheme_*" in solutions_text
    assert "3_5_satisfaction_objective_*" in solutions_text
    assert "bash run_full_pipeline.sh plots" in root_text
    assert "bash run_full_pipeline.sh plots" in solutions_text
    assert "Solutions/plots/outputs/" in root_text
    assert "Solutions/plots/outputs/" in solutions_text
    assert "bash run_full_pipeline.sh full" in root_text
    assert "bash run_full_pipeline.sh full" in solutions_text
    assert "会先清空旧 outputs、旧图片结果和 RQ4 cache，再按当前主链重算" in root_text
    assert "会先清空旧 outputs、旧图片结果和 RQ4 cache，再按当前主链重算" in solutions_text


def test_rq4_source_drops_coordination_diversion_wording() -> None:
    text = RQ4_README_TARGET_PATH.read_text(encoding="utf-8")
    assert "不再分流至第二站" in text
    assert "协同站点分流" not in text


def test_main_csv_exports_drop_overflow_schema_fields() -> None:
    csv_paths = [
        SOLUTIONS_DIR / "RQ2" / "outputs" / "2_1_best_scheme_stations.csv",
        SOLUTIONS_DIR / "RQ2" / "outputs" / "2_1_best_scheme_allocations.csv",
        SOLUTIONS_DIR / "RQ3" / "outputs" / "3_1_best_price_scheme_communities.csv",
        SOLUTIONS_DIR / "RQ3" / "outputs" / "3_1_best_price_scheme_stations.csv",
        SOLUTIONS_DIR / "RQ4" / "outputs" / "4_1_q3_scenario_summary.csv",
    ]
    forbidden = {"assigned_overflow_load", "overflow_station", "overflow_load_daily"}
    for path in csv_paths:
        assert path.exists(), f"Missing expected output for audit: {path}"
        with path.open(encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            fieldnames = set(reader.fieldnames or [])
        assert forbidden.isdisjoint(fieldnames), f"{path.name} still exports legacy overflow schema: {forbidden & fieldnames}"


def run_all_tests() -> None:
    tests = [
        test_rq2_metric_naming_status_accepts_explicit_sync,
        test_rq2_metric_naming_status_rejects_ambiguous_text,
        test_constraint_audit_uses_split_q3_main_and_aux_paths,
        test_constraint_audit_checks_q3_service_level_pricing_formula,
        test_run_full_pipeline_uses_python3_and_current_q3_chain,
        test_run_full_pipeline_clean_preserves_outputs_readme_files,
        test_readmes_use_current_main_aux_q3_wording,
        test_rq4_source_drops_coordination_diversion_wording,
        test_main_csv_exports_drop_overflow_schema_fields,
    ]
    for test in tests:
        test()
    print(f"Passed {len(tests)} tests.")


if __name__ == "__main__":
    run_all_tests()
