from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

PLOTS_DIR = Path(__file__).resolve().parent
ROOT = PLOTS_DIR.parents[1]
OUTPUT_DIR = PLOTS_DIR / "outputs"
PDF_DIR = OUTPUT_DIR / "pdf"
PNG_DIR = OUTPUT_DIR / "png"
SVG_DIR = OUTPUT_DIR / "svg"
MPLCONFIGDIR = OUTPUT_DIR / ".mplconfig"
MPLCONFIGDIR.mkdir(parents=True, exist_ok=True)
os.environ["MPLCONFIGDIR"] = str(MPLCONFIGDIR)

import matplotlib
from matplotlib import font_manager

matplotlib.use("Agg")


@dataclass(frozen=True)
class PlotStyle:
    font_cn: str
    font_en: str
    dpi: int
    figure_width: float
    figure_height: float
    title_size: int
    axis_size: int
    tick_size: int
    legend_size: int
    line_width: float
    grid_color: str
    grid_alpha: float
    colors: tuple[str, ...]
    cmap: str


CN_FONT_CANDIDATES = (
    "Songti SC",
    "SimSun",
    "STSong",
    "Noto Serif CJK SC",
    "Source Han Serif SC",
    "Microsoft YaHei",
    "Arial Unicode MS",
)

EN_FONT_CANDIDATES = (
    "Times New Roman",
    "Times",
    "DejaVu Serif",
)


def ensure_output_dirs() -> None:
    for path in (OUTPUT_DIR, PDF_DIR, PNG_DIR, SVG_DIR, MPLCONFIGDIR):
        path.mkdir(parents=True, exist_ok=True)


def _available_font_names() -> set[str]:
    return {font.name for font in font_manager.fontManager.ttflist}


def pick_first_available_font(candidates: Iterable[str], fallback: str) -> str:
    available = _available_font_names()
    for candidate in candidates:
        if candidate in available:
            return candidate
    return fallback


def get_plot_style() -> PlotStyle:
    font_cn = pick_first_available_font(CN_FONT_CANDIDATES, "DejaVu Sans")
    font_en = pick_first_available_font(EN_FONT_CANDIDATES, "DejaVu Serif")
    return PlotStyle(
        font_cn=font_cn,
        font_en=font_en,
        dpi=320,
        figure_width=8.8,
        figure_height=5.2,
        title_size=14,
        axis_size=11,
        tick_size=10,
        legend_size=10,
        line_width=2.0,
        grid_color="#b8c2cc",
        grid_alpha=0.28,
        colors=("#5B7C99", "#C08A5A", "#7A9E7E", "#A6676B", "#7D6D9C", "#8C8C8C"),
        cmap="YlOrBr",
    )


def configure_matplotlib() -> PlotStyle:
    ensure_output_dirs()
    style = get_plot_style()
    matplotlib.rcParams.update(
        {
            "figure.dpi": style.dpi,
            "savefig.dpi": style.dpi,
            "savefig.facecolor": "white",
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#555555",
            "axes.grid": True,
            "grid.color": style.grid_color,
            "grid.alpha": style.grid_alpha,
            "grid.linestyle": "--",
            "grid.linewidth": 0.6,
            "axes.titlesize": style.title_size,
            "axes.labelsize": style.axis_size,
            "xtick.labelsize": style.tick_size,
            "ytick.labelsize": style.tick_size,
            "legend.fontsize": style.legend_size,
            "axes.unicode_minus": False,
            "font.family": [style.font_cn],
            "font.serif": [style.font_cn, style.font_en, "Arial Unicode MS", "DejaVu Serif"],
            "font.sans-serif": [style.font_cn, "Arial Unicode MS", "DejaVu Sans"],
            "mathtext.fontset": "dejavuserif",
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            "svg.fonttype": "none",
        }
    )
    return style


def ensure_matplotlib_configured() -> PlotStyle:
    return configure_matplotlib()
