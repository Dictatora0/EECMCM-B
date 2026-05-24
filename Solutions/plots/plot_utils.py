from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
import csv

import matplotlib.pyplot as plt
import pandas as pd

from plot_config import PDF_DIR, PNG_DIR, SVG_DIR


@dataclass
class PlotResult:
    figure_id: str
    title_cn: str
    source_module: str
    input_files: list[str]
    recommended_location: str
    reason: str
    data_rows: int
    data_columns: int
    status: str
    output_png: str = ""
    output_pdf: str = ""
    output_svg: str = ""
    note: str = ""

    def to_manifest_row(self) -> dict[str, object]:
        return {
            "figure_id": self.figure_id,
            "title_cn": self.title_cn,
            "source_module": self.source_module,
            "input_files": "; ".join(self.input_files),
            "output_png": self.output_png,
            "output_pdf": self.output_pdf,
            "output_svg": self.output_svg,
            "recommended_location": self.recommended_location,
            "reason": self.reason,
            "data_rows": self.data_rows,
            "data_columns": self.data_columns,
            "status": self.status,
        }


def summarize_shape(data: pd.DataFrame | None) -> tuple[int, int]:
    if data is None:
        return 0, 0
    return int(data.shape[0]), int(data.shape[1])


def is_low_information_series(values: Iterable[float]) -> bool:
    normalized = [round(float(value), 10) for value in values if pd.notna(value)]
    return len(set(normalized)) <= 1


def save_figure(fig: plt.Figure, figure_id: str, export_formats: Iterable[str]) -> dict[str, str]:
    outputs = {"png": "", "pdf": "", "svg": ""}
    for fmt in export_formats:
        fmt_lower = fmt.lower()
        if fmt_lower == "png":
            path = PNG_DIR / f"{figure_id}.png"
        elif fmt_lower == "pdf":
            path = PDF_DIR / f"{figure_id}.pdf"
        elif fmt_lower == "svg":
            path = SVG_DIR / f"{figure_id}.svg"
        else:
            continue
        fig.savefig(path, bbox_inches="tight")
        outputs[fmt_lower] = str(path.relative_to(PNG_DIR.parent))
    plt.close(fig)
    return outputs


def save_plotly_figure(fig, figure_id: str, export_formats: Iterable[str]) -> dict[str, str]:
    outputs = {"png": "", "pdf": "", "svg": ""}
    for fmt in export_formats:
        fmt_lower = fmt.lower()
        if fmt_lower == "png":
            path = PNG_DIR / f"{figure_id}.png"
        elif fmt_lower == "pdf":
            path = PDF_DIR / f"{figure_id}.pdf"
        elif fmt_lower == "svg":
            path = SVG_DIR / f"{figure_id}.svg"
        else:
            continue
        try:
            fig.write_image(str(path))
        except Exception as exc:  # pragma: no cover - exercised through caller fallback
            raise RuntimeError(
                "Plotly 静态导出失败，请确认 kaleido 可正常调用本机 Chrome/Chromium。"
            ) from exc
        outputs[fmt_lower] = str(path.relative_to(PNG_DIR.parent))
    return outputs


def write_manifest(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames = [
        "figure_id",
        "title_cn",
        "source_module",
        "input_files",
        "output_png",
        "output_pdf",
        "output_svg",
        "recommended_location",
        "reason",
        "data_rows",
        "data_columns",
        "status",
    ]
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def generated_result(
    figure_id: str,
    title_cn: str,
    source_module: str,
    input_files: list[str],
    recommended_location: str,
    reason: str,
    data: pd.DataFrame,
    outputs: dict[str, str],
    note: str = "",
) -> PlotResult:
    rows, columns = summarize_shape(data)
    return PlotResult(
        figure_id=figure_id,
        title_cn=title_cn,
        source_module=source_module,
        input_files=input_files,
        recommended_location=recommended_location,
        reason=reason,
        data_rows=rows,
        data_columns=columns,
        status="generated",
        output_png=outputs.get("png", ""),
        output_pdf=outputs.get("pdf", ""),
        output_svg=outputs.get("svg", ""),
        note=note,
    )


def skipped_result(
    figure_id: str,
    title_cn: str,
    source_module: str,
    input_files: list[str],
    recommended_location: str,
    reason: str,
    status: str,
    data: pd.DataFrame | None = None,
    note: str = "",
) -> PlotResult:
    rows, columns = summarize_shape(data)
    return PlotResult(
        figure_id=figure_id,
        title_cn=title_cn,
        source_module=source_module,
        input_files=input_files,
        recommended_location=recommended_location,
        reason=reason,
        data_rows=rows,
        data_columns=columns,
        status=status,
        note=note,
    )
