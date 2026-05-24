from __future__ import annotations

import argparse
from collections import Counter
import os
from pathlib import Path


_MPL_DIR = Path(__file__).resolve().parent / "outputs" / ".mplconfig"
_MPL_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(_MPL_DIR))

from plot_config import OUTPUT_DIR, configure_matplotlib, ensure_output_dirs
from plot_rq1 import build_rq1_plots
from plot_rq2 import build_rq2_plots
from plot_rq3 import build_rq3_plots
from plot_rq4 import build_rq4_plots
from plot_utils import PlotResult, write_manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build unified plots for math modeling paper.")
    parser.add_argument("--rq", choices=["RQ1", "RQ2", "RQ3", "RQ4"], default=None)
    parser.add_argument("--format", default="pdf,png,svg")
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def _clean_previous_outputs() -> None:
    for pattern in ("pdf/*.pdf", "png/*.png", "svg/*.svg"):
        for path in OUTPUT_DIR.glob(pattern):
            path.unlink(missing_ok=True)


def _selected_builders(target_rq: str | None):
    builders = {
        "RQ1": build_rq1_plots,
        "RQ2": build_rq2_plots,
        "RQ3": build_rq3_plots,
        "RQ4": build_rq4_plots,
    }
    if target_rq:
        return {target_rq: builders[target_rq]}
    return builders


def _notes_for_results(results: list[PlotResult]) -> str:
    def _display_reason(item: PlotResult) -> str:
        reason = item.reason.strip()
        if reason == "No existing input file found.":
            module_output = f"Solutions/{item.source_module}/outputs/"
            return f"当前工作区缺少可读取的结果文件，未在 `{module_output}` 中找到所需 CSV/Excel/JSON 输出。"
        return reason

    def _section(title: str, items: list[PlotResult]) -> str:
        lines = [f"## {title}"]
        if not items:
            lines.append("- 无")
            return "\n".join(lines)
        for item in items:
            conclusion = _display_reason(item)
            location = "正文" if item.recommended_location == "main_text" else "附录" if item.recommended_location == "appendix" else "表格替代"
            lines.append(f"- `{item.figure_id}` {item.title_cn}：建议放{location}。结论写法建议：{conclusion}")
        return "\n".join(lines)

    generated_main = [item for item in results if item.status == "generated" and item.recommended_location == "main_text"]
    generated_appendix = [item for item in results if item.status == "generated" and item.recommended_location == "appendix"]
    skipped_missing = [item for item in results if item.status == "skipped_missing_data"]
    skipped_table = [item for item in results if item.status == "skipped_table_better"]
    avoid_main = [item for item in generated_appendix + skipped_table if item.recommended_location != "main_text"]

    parts = [
        "# 图表说明",
        "",
        _section("正文推荐图", generated_main),
        "",
        _section("附录推荐图", generated_appendix),
        "",
        _section("因数据缺失跳过的图", skipped_missing),
        "",
        _section("因表格更直观跳过的图", skipped_table),
        "",
        "## 正文控制建议",
    ]
    if avoid_main:
        for item in avoid_main:
            parts.append(f"- `{item.figure_id}` {item.title_cn}：不建议放正文，原因：{_display_reason(item)}")
    else:
        parts.append("- 当前无额外限制。")
    return "\n".join(parts) + "\n"


def main() -> None:
    args = parse_args()
    ensure_output_dirs()
    configure_matplotlib()
    if args.overwrite:
        _clean_previous_outputs()

    manifest_path = OUTPUT_DIR / "plot_manifest.csv"
    notes_path = OUTPUT_DIR / "plot_notes.md"
    export_formats = [token.strip().lower() for token in args.format.split(",") if token.strip()]

    results: list[PlotResult] = []
    for _rq, builder in _selected_builders(args.rq).items():
        results.extend(builder(export_formats))

    rows = [item.to_manifest_row() for item in results]
    write_manifest(manifest_path, rows)
    notes_path.write_text(_notes_for_results(results), encoding="utf-8")

    counter = Counter(row["status"] for row in rows)
    generated = counter.get("generated", 0)
    skipped = sum(value for key, value in counter.items() if key != "generated")
    print(f"生成图数量：{generated}")
    print(f"跳过图数量：{skipped}")
    print(f"manifest 路径：{manifest_path}")
    print(f"notes 路径：{notes_path}")


if __name__ == "__main__":
    main()
