from pathlib import Path
import csv
import os
import subprocess
import tempfile
import warnings
from contextlib import contextmanager


_MPL_DIR = Path(__file__).resolve().parent / "outputs" / ".mplconfig"
_MPL_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_DIR))


@contextmanager
def temporary_plot_output_dirs():
    import plot_config
    import plot_utils

    original_output_dir = plot_config.OUTPUT_DIR
    original_png_dir = plot_config.PNG_DIR
    original_pdf_dir = plot_config.PDF_DIR
    original_svg_dir = plot_config.SVG_DIR
    original_mpl_dir = plot_config.MPLCONFIGDIR

    original_plot_utils_png_dir = plot_utils.PNG_DIR
    original_plot_utils_pdf_dir = plot_utils.PDF_DIR
    original_plot_utils_svg_dir = plot_utils.SVG_DIR

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / "plots_output"
        png_dir = base / "png"
        pdf_dir = base / "pdf"
        svg_dir = base / "svg"
        mpl_dir = base / ".mplconfig"
        for path in (base, png_dir, pdf_dir, svg_dir, mpl_dir):
            path.mkdir(parents=True, exist_ok=True)

        plot_config.OUTPUT_DIR = base
        plot_config.PNG_DIR = png_dir
        plot_config.PDF_DIR = pdf_dir
        plot_config.SVG_DIR = svg_dir
        plot_config.MPLCONFIGDIR = mpl_dir
        os.environ["MPLCONFIGDIR"] = str(mpl_dir)

        plot_utils.PNG_DIR = png_dir
        plot_utils.PDF_DIR = pdf_dir
        plot_utils.SVG_DIR = svg_dir
        try:
            yield base
        finally:
            plot_config.OUTPUT_DIR = original_output_dir
            plot_config.PNG_DIR = original_png_dir
            plot_config.PDF_DIR = original_pdf_dir
            plot_config.SVG_DIR = original_svg_dir
            plot_config.MPLCONFIGDIR = original_mpl_dir
            plot_utils.PNG_DIR = original_plot_utils_png_dir
            plot_utils.PDF_DIR = original_plot_utils_pdf_dir
            plot_utils.SVG_DIR = original_plot_utils_svg_dir
            os.environ["MPLCONFIGDIR"] = str(original_mpl_dir)


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


def test_rq1_builder_generates_theoretical_and_adjusted_demand_heatmaps() -> None:
    import plot_rq1

    with tempfile.TemporaryDirectory() as tmp:
        outputs = Path(tmp) / "Solutions" / "RQ1" / "outputs"
        outputs.mkdir(parents=True)
        (outputs / "1_1_high_precision_population_by_year.csv").write_text(
            "year,community,self_care,semi_disabled,disabled\n"
            "5,A,100,20,10\n"
            "5,B,90,18,9\n",
            encoding="utf-8",
        )
        (outputs / "1_2_high_precision_theoretical_demand.csv").write_text(
            "community,service,theoretical_monthly_demand\n"
            "A,助餐,120\n"
            "A,助浴,30\n"
            "B,助餐,100\n"
            "B,助浴,20\n",
            encoding="utf-8",
        )
        (outputs / "1_3_high_precision_adjusted_demand.csv").write_text(
            "community,service,adjusted_monthly_demand\n"
            "A,助餐,110\n"
            "A,助浴,25\n"
            "B,助餐,95\n"
            "B,助浴,18\n",
            encoding="utf-8",
        )
        (outputs / "1_3_high_precision_adjusted_demand_detail.csv").write_text(
            "community,care_level,service,adjustment_scale,adjusted_monthly_demand\n"
            "A,self_care,助餐,0.9,50\n",
            encoding="utf-8",
        )
        (outputs / "1_4_transition_matrix.csv").write_text(
            "target_state,self_care,semi_disabled,disabled\n"
            "self_care_next,0.9,0.0,0.0\n"
            "semi_disabled_next,0.1,0.8,0.0\n"
            "disabled_next,0.0,0.2,1.0\n",
            encoding="utf-8",
        )
        (outputs / "1_4_validation_sensitivity_summary.csv").write_text(
            "case,year5_elderly_total,year5_disabled_share,theoretical_total_monthly_demand,adjusted_total_monthly_demand,matrix_equivalence_max_abs_diff\n"
            "baseline,100,0.1,150,130,0.0\n"
            "growth_plus_10pct,110,0.11,160,140,0.0\n",
            encoding="utf-8",
        )
        original_output = plot_rq1.RQ1_OUTPUT
        plot_rq1.RQ1_OUTPUT = outputs
        try:
            results = plot_rq1.build_rq1_plots(["png"])
        finally:
            plot_rq1.RQ1_OUTPUT = original_output

    by_id = {item.figure_id: item for item in results}
    assert by_id["rq1_03a"].status == "generated"
    assert by_id["rq1_03a"].title_cn == "第5年末理论服务需求热力图"
    assert by_id["rq1_03a"].recommended_location == "main_text"
    assert by_id["rq1_03"].status == "generated"
    assert by_id["rq1_03"].title_cn == "第5年末消费约束后服务需求热力图"


def test_rq2_extension_plots_use_appendix_location_and_current_profit_field() -> None:
    import plot_rq2

    with tempfile.TemporaryDirectory() as tmp:
        outputs = Path(tmp) / "Solutions" / "RQ2" / "outputs"
        outputs.mkdir(parents=True)
        (outputs / "2_1_best_scheme_summary.csv").write_text(
            "scheme_detail,geographic_population_coverage,served_population_coverage,weighted_served_population_coverage,served_demand_coverage,scheme_type\n"
            "A-小型,0.8,0.7,0.7,0.6,coverage_fairness_capacity_milp\n",
            encoding="utf-8",
        )
        (outputs / "2_1_best_scheme_stations.csv").write_text(
            "station_community,utilization,scale,daily_capacity,assigned_primary_load,total_load,annual_revenue,annual_subsidy,annual_direct_cost,annual_fixed_cost,annual_depreciation,annual_net_profit\n"
            "A,0.7,小型,1000,700,700,100,10,50,20,5,35\n",
            encoding="utf-8",
        )
        (outputs / "2_1_best_scheme_allocations.csv").write_text(
            "community,primary_station,service_access_performance,demand_service_ratio,primary_load_daily,unmet_load_daily\n"
            "A,A,0.8,0.9,100,0\n",
            encoding="utf-8",
        )
        (outputs / "2_2_pareto_frontier.csv").write_text(
            "scheme_label,served_population_coverage,weighted_served_population_coverage,served_demand_coverage,average_service_access_performance,minimum_service_access_performance,capacity_safety_rate,max_station_utilization,annual_net_profit_after_policy_subsidy,profit_compliant\n"
            "pareto_1,0.8,0.8,0.75,0.7,0.5,0.1,0.9,120000,1\n",
            encoding="utf-8",
        )
        (outputs / "2_2_epsilon_constraint_summary.csv").write_text(
            "epsilon_min_access_threshold,epsilon_feasible_count,average_service_access_performance,minimum_service_access_performance,annual_net_profit_after_policy_subsidy\n"
            "0.4,10,0.7,0.5,120000\n",
            encoding="utf-8",
        )
        original_output = plot_rq2.RQ2_OUTPUT
        original_distance = plot_rq2.DISTANCE_XLSX
        plot_rq2.RQ2_OUTPUT = outputs
        plot_rq2.DISTANCE_XLSX = outputs / "fake_distance.xlsx"
        original_topology = plot_rq2.load_distance_topology
        plot_rq2.load_distance_topology = lambda _path: __import__("pandas").DataFrame(
            [{"community": "A", "x": 0.0, "y": 0.0}]
        )
        try:
            with temporary_plot_output_dirs():
                results = plot_rq2.build_rq2_plots(["png"])
        finally:
            plot_rq2.RQ2_OUTPUT = original_output
            plot_rq2.DISTANCE_XLSX = original_distance
            plot_rq2.load_distance_topology = original_topology

    by_id = {item.figure_id: item for item in results}
    assert by_id["rq2_07"].status == "generated"
    assert by_id["rq2_07"].recommended_location == "appendix"
    assert by_id["rq2_08"].status == "generated"
    assert by_id["rq2_08"].recommended_location == "appendix"


def test_rq3_satisfaction_plots_use_explicit_average_and_minimum_titles() -> None:
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
                return frontier, outputs / "3_1_aux_pareto_frontier.csv"
            if required_columns == [
                "representative_label",
                "annual_net_profit_wan",
                "minimum_service_satisfaction",
                "converged",
            ]:
                return representative, outputs / "3_2_aux_pareto_representative_schemes.csv"
            raise plot_rq3.MissingDataError("skip unrelated test branches")

        plot_rq3.read_module_output = fake_read_module_output
        try:
            results = plot_rq3.build_rq3_plots(["png"])
        finally:
            plot_rq3.read_module_output = original_read_module_output
            MODULE_OUTPUT_DIRS["RQ3"] = original

    by_id = {item.figure_id: item for item in results}
    assert by_id["rq3_02"].title_cn == "问题3社区平均老人满意度前沿图"
    assert "社区平均老人满意度" in by_id["rq3_02"].reason
    assert by_id["rq3_03"].title_cn == "问题3最低老人满意度边界图"
    assert "最低老人满意度边界" in by_id["rq3_03"].reason


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
            "station_community,utilization,scale,daily_capacity,assigned_primary_load,total_load,annual_revenue,annual_subsidy,annual_direct_cost,annual_fixed_cost,annual_depreciation,annual_net_profit\n"
            "A,0.7,小型,1000,700,700,100,10,50,20,5,35\n",
            encoding="utf-8",
        )
        (outputs / "2_1_best_scheme_allocations.csv").write_text(
            "community,primary_station,service_access_performance,demand_service_ratio,primary_load_daily,unmet_load_daily\n"
            "A,A,0.8,0.9,100,0\n",
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
    assert "unmet_load_daily" in allocations.columns
    assert "overflow_station" not in allocations.columns
    assert "overflow_load_daily" not in allocations.columns
    assert "assigned_overflow_load" not in stations.columns


def test_rq2_main_plots_use_single_station_wording_and_multi_station_topology() -> None:
    import pandas as pd
    import plot_rq2

    with tempfile.TemporaryDirectory() as tmp:
        outputs = Path(tmp) / "Solutions" / "RQ2" / "outputs"
        outputs.mkdir(parents=True)
        (outputs / "2_1_best_scheme_summary.csv").write_text(
            "scheme_detail,geographic_population_coverage,served_population_coverage,weighted_served_population_coverage,served_demand_coverage,scheme_type\n"
            "A-大型;C-小型;E-大型,1.0,0.84,0.84,0.83,coverage_priority_baseline\n",
            encoding="utf-8",
        )
        (outputs / "2_1_best_scheme_stations.csv").write_text(
            "station_community,utilization,scale,daily_capacity,assigned_primary_load,total_load,annual_revenue,annual_subsidy,annual_direct_cost,annual_fixed_cost,annual_depreciation,annual_net_profit\n"
            "A,1.0,大型,3000,1550,1550,100,10,50,20,5,35\n"
            "C,1.0,小型,1000,1000,1000,80,8,40,18,4,26\n"
            "E,1.0,大型,3000,2223,2223,110,11,55,22,5,39\n",
            encoding="utf-8",
        )
        (outputs / "2_1_best_scheme_allocations.csv").write_text(
            "community,primary_station,service_access_performance,demand_service_ratio,primary_load_daily,unmet_load_daily\n"
            "A,A,0.87,0.99,850,0\n"
            "B,A,0.82,0.99,700,0\n"
            "C,C,0.49,0.56,649,0\n"
            "D,C,0.45,0.56,351,0\n"
            "E,E,0.76,0.87,840,0\n"
            "F,E,0.74,0.87,452,0\n"
            "G,E,0.74,0.87,931,0\n"
            "H,A,,0.79,0.99,652,0\n"
            "I,E,,0.74,0.87,777,0\n"
            "J,A,,0.85,0.99,775,0\n",
            encoding="utf-8",
        )
        (outputs / "2_1_safe_scheme_summary.csv").write_text(
            "scheme_type,scheme_detail,geographic_population_coverage,served_population_coverage,weighted_served_population_coverage,served_demand_coverage\n"
            "safety_priority,A-大型;C-小型;E-大型,1.0,0.84,0.84,0.83\n",
            encoding="utf-8",
        )
        (outputs / "2_2_pareto_frontier.csv").write_text(
            "scheme_label,served_population_coverage,weighted_served_population_coverage,served_demand_coverage,average_service_access_performance,minimum_service_access_performance,capacity_safety_rate,max_station_utilization,annual_net_profit_after_policy_subsidy,profit_compliant\n"
            "pareto_1,0.84,0.84,0.83,0.72,0.45,0.0,1.0,-20000,0\n",
            encoding="utf-8",
        )
        (outputs / "2_2_epsilon_constraint_summary.csv").write_text(
            "epsilon_min_access_threshold,epsilon_feasible_count,average_service_access_performance,minimum_service_access_performance,annual_net_profit_after_policy_subsidy\n"
            "0.4,10,0.7,0.5,-20000\n",
            encoding="utf-8",
        )
        original_output = plot_rq2.RQ2_OUTPUT
        original_distance = plot_rq2.DISTANCE_XLSX
        original_topology = plot_rq2.load_distance_topology
        plot_rq2.RQ2_OUTPUT = outputs
        plot_rq2.DISTANCE_XLSX = outputs / "fake_distance.xlsx"
        plot_rq2.load_distance_topology = lambda _path: pd.DataFrame(
            [
                {"community": "A", "x": 0.0, "y": 0.0},
                {"community": "B", "x": 1.0, "y": 0.0},
                {"community": "C", "x": 0.0, "y": 1.0},
                {"community": "D", "x": 1.0, "y": 1.0},
                {"community": "E", "x": 2.0, "y": 1.0},
                {"community": "F", "x": 3.0, "y": 1.0},
                {"community": "G", "x": 2.0, "y": 2.0},
                {"community": "H", "x": 1.0, "y": 2.0},
                {"community": "I", "x": 3.0, "y": 2.0},
                {"community": "J", "x": 2.0, "y": 0.0},
            ]
        )
        try:
            with temporary_plot_output_dirs() as plot_dir:
                results = plot_rq2.build_rq2_plots(["png"])
                rq2_01 = plot_dir / "png" / "rq2_01_topology_layout.png"
                rq2_02 = plot_dir / "png" / "rq2_02_service_flow.png"
                assert rq2_01.exists()
                assert rq2_02.exists()
        finally:
            plot_rq2.RQ2_OUTPUT = original_output
            plot_rq2.DISTANCE_XLSX = original_distance
            plot_rq2.load_distance_topology = original_topology

    by_id = {item.figure_id: item for item in results}
    assert by_id["rq2_01"].title_cn == "服务站拓扑布局与覆盖关系图"
    assert by_id["rq2_02"].title_cn == "小区—服务站唯一主站服务承接图"
    assert "唯一主站" in by_id["rq2_02"].reason
    assert "协同站" not in by_id["rq2_02"].title_cn


def test_rq3_stability_plot_keeps_epsilon_as_access_threshold() -> None:
    import plot_rq3

    text = Path(plot_rq3.__file__).read_text(encoding="utf-8")
    assert "可及绩效阈值与财政缺口" in text
    assert "最低可及绩效阈值 ε" in text
    assert "可及绩效阈值与服务可及绩效" in text
    assert "满意度阈值与财政缺口" not in text
    assert "最低满意度阈值 ε" not in text


def test_plot_config_prefers_songti_sc_when_available() -> None:
    import plot_config

    original = plot_config._available_font_names
    plot_config._available_font_names = lambda: {"Songti SC", "SimSun", "Arial Unicode MS"}
    try:
        style = plot_config.get_plot_style()
    finally:
        plot_config._available_font_names = original

    assert style.font_cn == "Songti SC"


def test_plot_config_import_avoids_default_matplotlib_cache_warning() -> None:
    result = subprocess.run(
        [
            "python3",
            "-c",
            (
                "import sys; "
                "sys.path.insert(0, 'Solutions/plots'); "
                "import plot_config; "
                "print(plot_config.MPLCONFIGDIR)"
            ),
        ],
        cwd="/Users/lifulin/Desktop/B",
        capture_output=True,
        text=True,
        check=True,
    )

    stderr = result.stderr.strip()
    assert "not a writable directory" not in stderr
    assert "temporary cache directory" not in stderr


def test_rq1_builder_configures_songti_sc_without_glyph_warnings() -> None:
    import matplotlib
    import plot_rq1

    with tempfile.TemporaryDirectory() as tmp:
        outputs = Path(tmp) / "Solutions" / "RQ1" / "outputs"
        outputs.mkdir(parents=True)
        (outputs / "1_1_high_precision_population_by_year.csv").write_text(
            "year,community,self_care,semi_disabled,disabled\n"
            "5,A,100,20,10\n"
            "5,B,90,18,9\n",
            encoding="utf-8",
        )
        (outputs / "1_2_high_precision_theoretical_demand.csv").write_text(
            "community,service,theoretical_monthly_demand\n"
            "A,助餐,120\n"
            "A,助浴,30\n"
            "B,助餐,100\n"
            "B,助浴,20\n",
            encoding="utf-8",
        )
        (outputs / "1_3_high_precision_adjusted_demand.csv").write_text(
            "community,service,adjusted_monthly_demand\n"
            "A,助餐,110\n"
            "A,助浴,25\n"
            "B,助餐,95\n"
            "B,助浴,18\n",
            encoding="utf-8",
        )
        (outputs / "1_3_high_precision_adjusted_demand_detail.csv").write_text(
            "community,care_level,service,adjustment_scale,adjusted_monthly_demand\n"
            "A,self_care,助餐,0.9,50\n",
            encoding="utf-8",
        )
        (outputs / "1_4_transition_matrix.csv").write_text(
            "target_state,self_care,semi_disabled,disabled\n"
            "self_care_next,0.9,0.0,0.0\n"
            "semi_disabled_next,0.1,0.8,0.0\n"
            "disabled_next,0.0,0.2,1.0\n",
            encoding="utf-8",
        )
        (outputs / "1_4_validation_sensitivity_summary.csv").write_text(
            "case,year5_elderly_total,year5_disabled_share,theoretical_total_monthly_demand,adjusted_total_monthly_demand,matrix_equivalence_max_abs_diff\n"
            "baseline,100,0.1,150,130,0.0\n"
            "growth_plus_10pct,110,0.11,160,140,0.0\n",
            encoding="utf-8",
        )
        original_output = plot_rq1.RQ1_OUTPUT
        plot_rq1.RQ1_OUTPUT = outputs
        matplotlib.rcParams["font.family"] = ["DejaVu Sans"]
        matplotlib.rcParams["font.sans-serif"] = ["DejaVu Sans"]
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                plot_rq1.build_rq1_plots(["png"])
        finally:
            plot_rq1.RQ1_OUTPUT = original_output

    messages = [str(item.message) for item in caught]
    assert any("Songti SC" == str(font) for font in matplotlib.rcParams["font.family"])
    assert not any("Glyph" in message for message in messages)


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
        test_rq3_representative_fallback_keeps_satisfaction_peak_label,
        test_rq3_representative_fallback_requires_satisfaction_columns,
        test_rq3_select_service_level_scheme_prefers_joint_feasible_label,
        test_rq3_parse_station_service_prices_returns_long_frame,
        test_find_output_file_prefers_newer_when_priority_equal,
        test_rq3_builder_skips_when_outputs_missing,
        test_rq3_builder_skips_satisfaction_plots_when_only_access_fields_exist,
        test_rq1_builder_generates_theoretical_and_adjusted_demand_heatmaps,
        test_rq2_extension_plots_use_appendix_location_and_current_profit_field,
        test_rq3_satisfaction_plots_use_explicit_average_and_minimum_titles,
        test_rq4_builder_skips_when_outputs_missing,
        test_notes_replace_generic_missing_reason,
        test_rq4_fallback_merge_from_q2_q3_summaries,
        test_rq2_loaders_enforce_plot_contract_fields,
        test_rq3_stability_plot_keeps_epsilon_as_access_threshold,
        test_plot_config_prefers_songti_sc_when_available,
        test_plot_config_import_avoids_default_matplotlib_cache_warning,
        test_rq1_builder_configures_songti_sc_without_glyph_warnings,
    ]
    for test in tests:
        test()
    print(f"Passed {len(tests)} tests.")


if __name__ == "__main__":
    run_all_tests()
