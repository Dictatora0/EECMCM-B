from pathlib import Path
import csv
import os
import tempfile


_MPL_DIR = Path(__file__).resolve().parent / "outputs" / ".mplconfig"
_MPL_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_DIR))


def test_find_output_file_prefers_priority_keywords() -> None:
    from data_loader import find_output_file

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        outputs = root / "Solutions" / "RQX" / "outputs"
        outputs.mkdir(parents=True)
        (outputs / "demo_summary.csv").write_text("a,b\n1,2\n", encoding="utf-8")
        (outputs / "demo_final_summary.csv").write_text("a,b\n3,4\n", encoding="utf-8")
        (outputs / "demo_unified_summary.csv").write_text("a,b\n5,6\n", encoding="utf-8")

        picked = find_output_file(
            module="RQX",
            keywords=["summary"],
            root_dir=root,
        )

        assert picked is not None
        assert picked.name == "demo_unified_summary.csv"


def test_read_first_existing_applies_required_columns_and_aliases() -> None:
    from data_loader import read_first_existing

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        csv_path = root / "sample.csv"
        csv_path.write_text("小区,年份,值\nA,5,10\n", encoding="utf-8")

        frame, used_path = read_first_existing(
            [csv_path],
            required_columns=["community", "year"],
        )

        assert used_path == csv_path
        assert list(frame.columns) == ["community", "year", "值"]
        assert frame.loc[0, "community"] == "A"
        assert int(frame.loc[0, "year"]) == 5


def test_read_module_output_uses_keyword_priority() -> None:
    from data_loader import read_module_output

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        outputs = root / "Solutions" / "RQ3" / "outputs"
        outputs.mkdir(parents=True)
        (outputs / "3_1_financial_summary.csv").write_text("average_service_access_performance,minimum_service_access_performance,annual_net_profit,profit_rate,profit_compliant\n0.6,0.1,100,0.02,1\n", encoding="utf-8")
        (outputs / "3_1_financial_final_summary.csv").write_text("average_service_access_performance,minimum_service_access_performance,annual_net_profit,profit_rate,profit_compliant\n0.7,0.2,200,0.03,1\n", encoding="utf-8")

        from data_loader import MODULE_OUTPUT_DIRS

        original = MODULE_OUTPUT_DIRS["RQ3"]
        MODULE_OUTPUT_DIRS["RQ3"] = outputs
        try:
            frame, used_path = read_module_output(
                "RQ3",
                candidate_keywords=[["financial", "summary"]],
                required_columns=["average_service_access_performance", "annual_net_profit"],
            )
        finally:
            MODULE_OUTPUT_DIRS["RQ3"] = original

        assert used_path.name == "3_1_financial_final_summary.csv"
        assert float(frame.loc[0, "annual_net_profit"]) == 200


def test_write_manifest_rows_preserves_status_and_file_fields() -> None:
    from plot_utils import write_manifest

    with tempfile.TemporaryDirectory() as tmp:
        manifest_path = Path(tmp) / "plot_manifest.csv"
        rows = [
            {
                "figure_id": "rq1_01",
                "title_cn": "测试图",
                "source_module": "RQ1",
                "input_files": "a.csv",
                "output_png": "png/rq1_01.png",
                "output_pdf": "pdf/rq1_01.pdf",
                "output_svg": "svg/rq1_01.svg",
                "recommended_location": "main_text",
                "reason": "正文关键图",
                "data_rows": 10,
                "data_columns": 3,
                "status": "generated",
            },
            {
                "figure_id": "rq1_02",
                "title_cn": "表格更优",
                "source_module": "RQ1",
                "input_files": "b.csv",
                "output_png": "",
                "output_pdf": "",
                "output_svg": "",
                "recommended_location": "table_better",
                "reason": "只有一个数值",
                "data_rows": 1,
                "data_columns": 2,
                "status": "skipped_table_better",
            },
        ]

        write_manifest(manifest_path, rows)

        with manifest_path.open(encoding="utf-8-sig") as handle:
            saved = list(csv.DictReader(handle))

        assert len(saved) == 2
        assert saved[0]["status"] == "generated"
        assert saved[1]["recommended_location"] == "table_better"


def test_save_plotly_figure_exports_selected_format() -> None:
    import plotly.graph_objects as go
    from plot_utils import save_plotly_figure

    figure = go.Figure(data=[go.Bar(x=["A"], y=[1])])
    created = []

    def _fake_write_image(path: str) -> None:
        created.append(path)
        Path(path).write_bytes(b"ok")

    figure.write_image = _fake_write_image  # type: ignore[method-assign]
    outputs = save_plotly_figure(figure, "test_plotly_export", ["png"])
    assert outputs["png"] == "png/test_plotly_export.png"
    path = Path("Solutions/plots/outputs") / outputs["png"]
    assert len(created) == 1
    assert Path(created[0]).name == path.name
    assert path.exists()
    path.unlink()


def test_normalize_columns_avoids_duplicate_alias_collision() -> None:
    import pandas as pd
    from data_loader import normalize_columns

    frame = pd.DataFrame(
        {
            "annual_net_profit_after_subsidy": [1],
            "annual_net_profit": [2],
            "community": ["A"],
        }
    )
    normalized = normalize_columns(frame)
    assert list(normalized.columns).count("annual_net_profit") == 1
    assert "annual_net_profit_after_subsidy" in normalized.columns


def test_first_present_column_returns_first_existing_candidate() -> None:
    import pandas as pd
    from data_loader import first_present_column

    frame = pd.DataFrame({"a": [1], "b": [2], "c": [3]})
    assert first_present_column(frame, ["x", "b", "c"]) == "b"


def test_label_map_outputs_human_readable_chinese() -> None:
    from label_maps import pretty_metric_label, pretty_scheme_label

    assert pretty_metric_label("q2_served_demand_coverage") == "服务需求覆盖率"
    assert pretty_metric_label("financial_annual_net_profit") == "年净利润"
    assert pretty_metric_label("epsilon_min_access_threshold") == "最低可及绩效阈值"
    assert pretty_scheme_label("financial_sustainable_scheme") == "财务可持续方案"
    assert pretty_scheme_label("fairness_priority_scheme") == "满意度优先方案"
    assert pretty_scheme_label("satisfaction_priority_scheme") == "满意度优先方案"
    assert pretty_scheme_label("frontier_fairness_peak") == "满意度峰值点"
    assert pretty_scheme_label("frontier_satisfaction_peak") == "满意度峰值点"


def test_alias_maps_support_legacy_and_canonical_satisfaction_keys() -> None:
    import pandas as pd
    from alias_maps import (
        add_canonical_metric_alias_columns,
        add_legacy_scheme_alias_columns,
        canonical_metric_key,
        canonical_scheme_key,
        first_present_metric,
    )

    frame = pd.DataFrame(
        [
            {
                "fairness_average_service_access_performance": 0.75,
                "fairness_minimum_service_access_performance": 0.05,
            }
        ]
    )
    normalized = add_canonical_metric_alias_columns(frame)

    assert canonical_scheme_key("fairness_priority_scheme") == "satisfaction_priority_scheme"
    assert canonical_scheme_key("frontier_fairness_peak") == "frontier_satisfaction_peak"
    assert canonical_metric_key("fairness_profit_rate") == "satisfaction_profit_rate"
    assert "satisfaction_average_service_access_performance" in normalized.columns
    assert "satisfaction_minimum_service_access_performance" in normalized.columns
    scheme_frame = pd.DataFrame([{"scheme_type": "satisfaction_priority_scheme"}])
    legacy_scheme_frame = add_legacy_scheme_alias_columns(scheme_frame)
    assert legacy_scheme_frame.loc[0, "scheme_type"] == "fairness_priority_scheme"
    assert first_present_metric(
        normalized,
        "satisfaction_minimum_service_access_performance",
    ) == "satisfaction_minimum_service_access_performance"


def test_rq3_representative_fallback_builds_from_frontier() -> None:
    import pandas as pd
    from plot_rq3 import _build_representative_from_frontier

    frontier = pd.DataFrame(
        [
            {
                "annual_net_profit": 100000.0,
                "average_service_satisfaction": 0.78,
                "minimum_service_satisfaction": 0.66,
                "average_service_access_performance": 0.70,
                "minimum_service_access_performance": 0.03,
                "profit_rate": 0.01,
                "profit_compliant": 1,
                "converged": 1,
            },
            {
                "annual_net_profit": 300000.0,
                "average_service_satisfaction": 0.74,
                "minimum_service_satisfaction": 0.61,
                "average_service_access_performance": 0.60,
                "minimum_service_access_performance": 0.01,
                "profit_rate": 0.03,
                "profit_compliant": 1,
                "converged": 1,
            },
            {
                "annual_net_profit": 120000.0,
                "average_service_satisfaction": 0.84,
                "minimum_service_satisfaction": 0.72,
                "average_service_access_performance": 0.80,
                "minimum_service_access_performance": 0.08,
                "profit_rate": 0.02,
                "profit_compliant": 1,
                "converged": 1,
            },
        ]
    )
    representatives = _build_representative_from_frontier(frontier)
    assert set(representatives["representative_label"]) == {
        "frontier_profit_peak",
        "frontier_satisfaction_peak",
        "frontier_converged_reference",
    }


def test_rq3_representative_fallback_keeps_satisfaction_peak_label() -> None:
    import pandas as pd
    from label_maps import pretty_scheme_label
    from plot_rq3 import _build_representative_from_frontier

    frontier = pd.DataFrame(
        [
            {
                "annual_net_profit": 100000.0,
                "average_service_satisfaction": 0.76,
                "minimum_service_satisfaction": 0.63,
                "average_service_access_performance": 0.65,
                "minimum_service_access_performance": 0.03,
                "profit_rate": 0.01,
                "profit_compliant": 1,
                "converged": 1,
            },
            {
                "annual_net_profit": 110000.0,
                "average_service_satisfaction": 0.85,
                "minimum_service_satisfaction": 0.74,
                "average_service_access_performance": 0.81,
                "minimum_service_access_performance": 0.09,
                "profit_rate": 0.02,
                "profit_compliant": 1,
                "converged": 1,
            },
        ]
    )

    representatives = _build_representative_from_frontier(frontier)
    satisfaction_peak_row = representatives[
        representatives["representative_label"] == "frontier_satisfaction_peak"
    ].iloc[0]

    assert pretty_scheme_label(str(satisfaction_peak_row["representative_label"])) == "满意度峰值点"


def test_rq3_representative_fallback_requires_satisfaction_columns() -> None:
    import pandas as pd
    from plot_rq3 import _build_representative_from_frontier

    frontier = pd.DataFrame(
        [
            {
                "annual_net_profit": 100000.0,
                "average_service_access_performance": 0.70,
                "minimum_service_access_performance": 0.03,
                "profit_rate": 0.01,
                "profit_compliant": 1,
                "converged": 1,
            }
        ]
    )
    try:
        _build_representative_from_frontier(frontier)
    except ValueError as exc:
        assert "satisfaction" in str(exc).lower()
    else:
        raise AssertionError("expected ValueError when satisfaction columns are missing")


def test_rq3_select_service_level_scheme_prefers_joint_feasible_label() -> None:
    import pandas as pd
    from plot_rq3 import _select_service_level_scheme

    summary = pd.DataFrame(
        [
            {"scenario": "S4", "scheme_label": "financial_best", "price_scheme_detail": "{}"},
            {"scenario": "S4", "scheme_label": "joint_feasible_best_satisfaction", "price_scheme_detail": "{}"},
        ]
    )
    row = _select_service_level_scheme(summary, scenario="S4")
    assert row["scheme_label"] == "joint_feasible_best_satisfaction"


def test_rq3_parse_station_service_prices_returns_long_frame() -> None:
    from plot_rq3 import _parse_station_service_prices

    frame = _parse_station_service_prices('{"C": {"助餐": 10, "上门护理": 30}, "E": {"助餐": 12}}')
    assert set(frame.columns) == {"station", "service", "price"}
    assert len(frame) == 3


def test_find_output_file_prefers_newer_when_priority_equal() -> None:
    import time
    from data_loader import find_output_file

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        outputs = root / "Solutions" / "RQX" / "outputs"
        outputs.mkdir(parents=True)
        older = outputs / "demo_report.csv"
        newer = outputs / "demo_snapshot.csv"
        older.write_text("a,b\n1,2\n", encoding="utf-8")
        time.sleep(0.01)
        newer.write_text("a,b\n3,4\n", encoding="utf-8")

        picked = find_output_file(module="RQX", keywords=["demo"], root_dir=root)
        assert picked is not None
        assert picked.name == "demo_snapshot.csv"


def test_rq3_builder_skips_when_outputs_missing() -> None:
    from plot_rq3 import build_rq3_plots
    from data_loader import MODULE_OUTPUT_DIRS

    with tempfile.TemporaryDirectory() as tmp:
        outputs = Path(tmp) / "Solutions" / "RQ3" / "outputs"
        outputs.mkdir(parents=True)
        original = MODULE_OUTPUT_DIRS["RQ3"]
        MODULE_OUTPUT_DIRS["RQ3"] = outputs
        try:
            results = build_rq3_plots(["png"])
        finally:
            MODULE_OUTPUT_DIRS["RQ3"] = original

    status_by_id = {item.figure_id: item.status for item in results}
    assert status_by_id["rq3_01"] == "skipped_missing_data"
    assert status_by_id["rq3_02"] == "skipped_missing_data"
    assert status_by_id["rq3_03"] == "skipped_missing_data"


def test_rq3_plot_titles_and_reasons_use_paper_style_wording() -> None:
    import plot_rq3
    import pandas as pd
    from data_loader import MODULE_OUTPUT_DIRS

    frontier = pd.DataFrame(
        [
            {
                "annual_net_profit": 120000.0,
                "annual_net_profit_wan": 12.0,
                "average_service_satisfaction": 0.82,
                "minimum_service_satisfaction": 0.71,
                "average_service_access_performance": 0.66,
                "minimum_service_access_performance": 0.42,
                "profit_rate": 0.03,
                "profit_compliant": 1,
                "converged": 1,
            }
        ]
    )
    representative = pd.DataFrame(
        [
            {
                "representative_label": "frontier_satisfaction_peak",
                "annual_net_profit_wan": 12.0,
                "minimum_service_satisfaction": 0.71,
                "minimum_service_access_performance": 0.42,
                "profit_rate": 0.03,
                "converged": 1,
            }
        ]
    )

    with tempfile.TemporaryDirectory() as tmp:
        outputs = Path(tmp) / "Solutions" / "RQ3" / "outputs"
        outputs.mkdir(parents=True)
        original = MODULE_OUTPUT_DIRS["RQ3"]
        MODULE_OUTPUT_DIRS["RQ3"] = outputs
        original_read_module_output = plot_rq3.read_module_output

        def fake_read_module_output(module: str, candidate_keywords: list[list[str]], required_columns: list[str]):
            if required_columns == [
                "annual_net_profit",
                "average_service_satisfaction",
                "minimum_service_satisfaction",
                "profit_compliant",
                "converged",
            ]:
                return frontier, outputs / "3_1_pareto_frontier.csv"
            if required_columns == [
                "representative_label",
                "annual_net_profit_wan",
                "minimum_service_satisfaction",
                "converged",
            ]:
                return representative, outputs / "3_2_pareto_representative_schemes.csv"
            raise plot_rq3.MissingDataError("skip unrelated test branches")

        plot_rq3.read_module_output = fake_read_module_output
        try:
            results = plot_rq3.build_rq3_plots(["png"])
        finally:
            plot_rq3.read_module_output = original_read_module_output
            MODULE_OUTPUT_DIRS["RQ3"] = original

    by_id = {item.figure_id: item for item in results}
    assert by_id["rq3_02"].title_cn == "问题3定价方案的利润—满意度权衡前沿"
    assert "满意度主目标下" in by_id["rq3_02"].reason
    assert by_id["rq3_03"].title_cn == "代表性定价方案的最低满意度与年净利润对比"
    assert "最低满意度边界" in by_id["rq3_03"].reason


def test_rq3_builder_skips_satisfaction_plots_when_only_access_fields_exist() -> None:
    import plot_rq3
    import pandas as pd
    from data_loader import MODULE_OUTPUT_DIRS

    access_only_frontier = pd.DataFrame(
        [
            {
                "annual_net_profit": 120000.0,
                "average_service_access_performance": 0.66,
                "minimum_service_access_performance": 0.42,
                "profit_rate": 0.03,
                "profit_compliant": 1,
                "converged": 1,
            }
        ]
    )

    with tempfile.TemporaryDirectory() as tmp:
        outputs = Path(tmp) / "Solutions" / "RQ3" / "outputs"
        outputs.mkdir(parents=True)
        original = MODULE_OUTPUT_DIRS["RQ3"]
        MODULE_OUTPUT_DIRS["RQ3"] = outputs
        original_read_module_output = plot_rq3.read_module_output

        def fake_read_module_output(module: str, candidate_keywords: list[list[str]], required_columns: list[str]):
            if required_columns == [
                "annual_net_profit",
                "average_service_satisfaction",
                "minimum_service_satisfaction",
                "profit_compliant",
                "converged",
            ]:
                return access_only_frontier, outputs / "3_1_pareto_frontier.csv"
            raise plot_rq3.MissingDataError("skip unrelated test branches")

        plot_rq3.read_module_output = fake_read_module_output
        try:
            results = plot_rq3.build_rq3_plots(["png"])
        finally:
            plot_rq3.read_module_output = original_read_module_output
            MODULE_OUTPUT_DIRS["RQ3"] = original

    by_id = {item.figure_id: item for item in results}
    assert by_id["rq3_02"].status == "skipped_missing_data"
    assert by_id["rq3_03"].status == "skipped_missing_data"


def test_rq4_builder_skips_when_outputs_missing() -> None:
    from plot_rq4 import build_rq4_plots
    from data_loader import MODULE_OUTPUT_DIRS

    with tempfile.TemporaryDirectory() as tmp:
        outputs = Path(tmp) / "Solutions" / "RQ4" / "outputs"
        outputs.mkdir(parents=True)
        original = MODULE_OUTPUT_DIRS["RQ4"]
        MODULE_OUTPUT_DIRS["RQ4"] = outputs
        try:
            results = build_rq4_plots(["png"])
        finally:
            MODULE_OUTPUT_DIRS["RQ4"] = original

    status_by_id = {item.figure_id: item.status for item in results}
    assert status_by_id["rq4_01"] == "skipped_missing_data"
    assert status_by_id["rq4_03"] == "skipped_missing_data"
    assert status_by_id["rq4_04"] == "skipped_missing_data"


def test_notes_replace_generic_missing_reason() -> None:
    from build_all_plots import _notes_for_results
    from plot_utils import skipped_result

    note = _notes_for_results(
        [
            skipped_result(
                "rq4_01",
                "测试图",
                "RQ4",
                [],
                "main_text",
                "No existing input file found.",
                "skipped_missing_data",
            )
        ]
    )
    assert "Solutions/RQ4/outputs/" in note
    assert "No existing input file found." not in note


def test_rq4_fallback_merge_from_q2_q3_summaries() -> None:
    import plot_rq4

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        outputs = root / "Solutions" / "RQ4" / "outputs"
        outputs.mkdir(parents=True)
        (outputs / "4_1_q2_scenario_summary.csv").write_text(
            "scenario,station_plan,served_demand_coverage,average_service_access_performance,max_station_utilization,capacity_safety_rate\n"
            "S0,A-小型,0.8,0.7,1.0,0.0\n",
            encoding="utf-8",
        )
        (outputs / "4_1_q3_scenario_summary.csv").write_text(
            "scenario,scheme_type,average_service_access_performance,minimum_service_access_performance,annual_government_subsidy,annual_net_profit,profit_rate\n"
            "S0,financial_sustainable_scheme,0.6,0.0,10,100,0.02\n"
            "S0,satisfaction_priority_scheme,0.75,0.05,12,80,0.01\n",
            encoding="utf-8",
        )

        from data_loader import MODULE_OUTPUT_DIRS

        original = MODULE_OUTPUT_DIRS["RQ4"]
        MODULE_OUTPUT_DIRS["RQ4"] = outputs
        try:
            frame, files = plot_rq4._load_scenario_summary()
        finally:
            MODULE_OUTPUT_DIRS["RQ4"] = original

        assert set(files) == {
            str(outputs / "4_1_q2_scenario_summary.csv"),
            str(outputs / "4_1_q3_scenario_summary.csv"),
        }
        assert frame.loc[0, "q2_station_plan"] == "A-小型"
        assert float(frame.loc[0, "financial_annual_net_profit"]) == 100
        assert float(frame.loc[0, "satisfaction_minimum_service_access_performance"]) == 0.05
        assert float(frame.loc[0, "fairness_minimum_service_access_performance"]) == 0.05


def test_rq2_loaders_enforce_plot_contract_fields() -> None:
    import plot_rq2

    with tempfile.TemporaryDirectory() as tmp:
        outputs = Path(tmp) / "Solutions" / "RQ2" / "outputs"
        outputs.mkdir(parents=True)
        (outputs / "2_1_best_scheme_stations.csv").write_text(
            "station_community,utilization,scale,annual_revenue,annual_subsidy,annual_direct_cost,annual_fixed_cost,annual_depreciation,annual_net_profit\n"
            "A,0.7,小型,100,10,50,20,5,35\n",
            encoding="utf-8",
        )
        (outputs / "2_1_best_scheme_allocations.csv").write_text(
            "community,primary_station,overflow_station,service_access_performance,demand_service_ratio,primary_load_daily,overflow_load_daily\n"
            "A,A,,0.8,0.9,100,0\n",
            encoding="utf-8",
        )
        original_output = plot_rq2.RQ2_OUTPUT
        plot_rq2.RQ2_OUTPUT = outputs
        try:
            stations, _ = plot_rq2._load_best_stations()
            allocations, _ = plot_rq2._load_best_allocations()
        finally:
            plot_rq2.RQ2_OUTPUT = original_output

    assert "annual_revenue" in stations.columns
    assert "annual_subsidy" in stations.columns
    assert "primary_load_daily" in allocations.columns
    assert "overflow_load_daily" in allocations.columns


def run_all_tests() -> None:
    tests = [
        test_find_output_file_prefers_priority_keywords,
        test_read_first_existing_applies_required_columns_and_aliases,
        test_read_module_output_uses_keyword_priority,
        test_write_manifest_rows_preserves_status_and_file_fields,
        test_save_plotly_figure_exports_selected_format,
        test_normalize_columns_avoids_duplicate_alias_collision,
        test_first_present_column_returns_first_existing_candidate,
        test_label_map_outputs_human_readable_chinese,
        test_rq3_representative_fallback_builds_from_frontier,
        test_rq3_select_service_level_scheme_prefers_joint_feasible_label,
        test_rq3_parse_station_service_prices_returns_long_frame,
        test_find_output_file_prefers_newer_when_priority_equal,
        test_rq3_builder_skips_when_outputs_missing,
        test_rq4_builder_skips_when_outputs_missing,
        test_notes_replace_generic_missing_reason,
        test_rq4_fallback_merge_from_q2_q3_summaries,
    ]
    for test in tests:
        test()
    print(f"Passed {len(tests)} tests.")


if __name__ == "__main__":
    run_all_tests()
