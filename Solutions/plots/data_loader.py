from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import json
import pandas as pd

from alias_maps import add_canonical_metric_alias_columns


PLOTS_DIR = Path(__file__).resolve().parent
ROOT = PLOTS_DIR.parents[1]

MODULE_OUTPUT_DIRS = {
    "RQ1": ROOT / "Solutions" / "RQ1" / "outputs",
    "RQ2": ROOT / "Solutions" / "RQ2" / "outputs",
    "RQ3": ROOT / "Solutions" / "RQ3" / "outputs",
    "RQ4": ROOT / "Solutions" / "RQ4" / "outputs",
}

PRIORITY_KEYWORDS = ("unified", "final", "summary", "high_precision", "scenario", "pareto")
COLUMN_ALIASES = {
    "小区": "community",
    "社区": "community",
    "小区编号": "community",
    "年份": "year",
    "year": "year",
    "community": "community",
    "站点": "station",
    "服务站": "station",
    "服务站点": "station",
    "service_access_performance": "service_access_performance",
    "average_service_access_performance": "average_service_access_performance",
    "annual_net_profit": "annual_net_profit",
    "profit_rate": "profit_rate",
}


@dataclass(frozen=True)
class MissingDataError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


def get_module_output_dir(module: str) -> Path:
    return MODULE_OUTPUT_DIRS[module]


def normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    normalized.columns = [str(column).strip() for column in normalized.columns]
    rename_map: dict[str, str] = {}
    existing_columns = set(normalized.columns)
    planned_targets: set[str] = set()
    for column in normalized.columns:
        canonical = COLUMN_ALIASES.get(column)
        if canonical is None or canonical == column:
            continue
        if canonical in existing_columns or canonical in planned_targets:
            continue
        rename_map[column] = canonical
        planned_targets.add(canonical)
    normalized = normalized.rename(columns=rename_map)
    if "annual_net_profit_after_policy_subsidy" in normalized.columns and "annual_net_profit" not in normalized.columns:
        normalized["annual_net_profit"] = normalized["annual_net_profit_after_policy_subsidy"]
    if "annual_net_profit_after_subsidy" in normalized.columns and "annual_net_profit" not in normalized.columns:
        normalized["annual_net_profit"] = normalized["annual_net_profit_after_subsidy"]
    return add_canonical_metric_alias_columns(normalized)


def _score_path(path: Path, keywords: Sequence[str]) -> tuple[int, int, str]:
    name = path.name.lower()
    priority_score = 0
    for idx, keyword in enumerate(PRIORITY_KEYWORDS):
        if keyword in name:
            priority_score += (len(PRIORITY_KEYWORDS) - idx) * 10
    for idx, keyword in enumerate(keywords):
        if keyword.lower() in name:
            priority_score += (len(keywords) - idx) * 100
    try:
        mtime_key = -path.stat().st_mtime_ns
    except OSError:
        mtime_key = 0
    return (-priority_score, mtime_key, name)


def find_output_file(
    module: str,
    keywords: Sequence[str],
    root_dir: Path | None = None,
) -> Path | None:
    search_root = root_dir or ROOT
    if root_dir is None:
        output_dir = MODULE_OUTPUT_DIRS.get(module)
    else:
        output_dir = search_root / "Solutions" / module / "outputs"
    if output_dir is None or not output_dir.exists():
        return None
    candidates = []
    lowered = [keyword.lower() for keyword in keywords]
    for path in output_dir.iterdir():
        if not path.is_file():
            continue
        name = path.name.lower()
        if all(token in name for token in lowered):
            candidates.append(path)
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: _score_path(item, lowered))[0]


def _read_path(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, encoding="utf-8-sig")
    if suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return pd.DataFrame(payload)
        if isinstance(payload, dict):
            return pd.json_normalize(payload)
    if suffix in {".xls", ".xlsx"}:
        return pd.read_excel(path)
    raise MissingDataError(f"Unsupported input format: {path}")


def _resolve_required_columns(frame: pd.DataFrame, required_columns: Sequence[str] | None) -> pd.DataFrame:
    normalized = normalize_columns(frame)
    if not required_columns:
        return normalized
    missing = [column for column in required_columns if column not in normalized.columns]
    if missing:
        raise MissingDataError(f"Missing required columns {missing}")
    return normalized


def first_present_column(frame: pd.DataFrame, candidates: Sequence[str]) -> str:
    for column in candidates:
        if column in frame.columns:
            return column
    raise MissingDataError(f"None of the candidate columns exist: {list(candidates)}")


def read_first_existing(
    paths: Iterable[Path],
    required_columns: Sequence[str] | None = None,
) -> tuple[pd.DataFrame, Path]:
    for path in paths:
        if not path.exists():
            continue
        frame = _read_path(path)
        return _resolve_required_columns(frame, required_columns), path
    raise MissingDataError("No existing input file found.")


def read_latest_csv(
    patterns: Sequence[str],
    required_columns: Sequence[str] | None = None,
    search_dir: Path | None = None,
) -> tuple[pd.DataFrame, Path]:
    directory = search_dir or ROOT
    candidates: list[Path] = []
    for pattern in patterns:
        candidates.extend(directory.glob(pattern))
    candidates = [path for path in candidates if path.is_file()]
    if not candidates:
        raise MissingDataError(f"No file matched patterns: {patterns}")
    ordered = sorted(candidates, key=lambda item: _score_path(item, patterns))
    frame = _read_path(ordered[0])
    return _resolve_required_columns(frame, required_columns), ordered[0]


def load_csv_if_exists(path: Path, required_columns: Sequence[str] | None = None) -> tuple[pd.DataFrame | None, Path | None]:
    if not path.exists():
        return None, None
    frame = _read_path(path)
    return _resolve_required_columns(frame, required_columns), path


def read_module_output(
    module: str,
    candidate_keywords: Sequence[Sequence[str]],
    required_columns: Sequence[str] | None = None,
    allowed_suffixes: Sequence[str] = (".csv", ".xlsx", ".xls", ".json"),
) -> tuple[pd.DataFrame, Path]:
    output_dir = MODULE_OUTPUT_DIRS.get(module)
    if output_dir is None or not output_dir.exists():
        raise MissingDataError(f"Output directory not found for {module}.")

    normalized_suffixes = {suffix.lower() for suffix in allowed_suffixes}
    for keywords in candidate_keywords:
        path = find_output_file(module=module, keywords=keywords)
        if path is None:
            continue
        if path.suffix.lower() not in normalized_suffixes:
            continue
        frame = _read_path(path)
        return _resolve_required_columns(frame, required_columns), path

    keyword_text = " | ".join("+".join(group) for group in candidate_keywords)
    raise MissingDataError(f"No matched output file found in {output_dir} for candidate keywords: {keyword_text}")
