from __future__ import annotations

from typing import Iterable

import pandas as pd


# Legacy-to-display scheme aliases. Old keys remain readable for cache/CSV compatibility.
SCHEME_KEY_ALIASES = {
    "fairness_priority_scheme": "satisfaction_priority_scheme",
    "fairness_best": "satisfaction_best",
    "frontier_fairness_peak": "frontier_satisfaction_peak",
}


# Legacy-to-canonical metric aliases used by plots/report layers.
METRIC_KEY_ALIASES = {
    "q3_fairness_minimum_service_access_performance": "q3_satisfaction_minimum_service_access_performance",
    "q3_fairness_scheme_performance_stability": "q3_satisfaction_scheme_performance_stability",
    "fairness_average_service_access_performance": "satisfaction_average_service_access_performance",
    "fairness_minimum_service_access_performance": "satisfaction_minimum_service_access_performance",
    "fairness_profit_rate": "satisfaction_profit_rate",
    "fairness_annual_net_profit": "satisfaction_annual_net_profit",
}

CANONICAL_TO_LEGACY_SCHEME_KEYS = {value: key for key, value in SCHEME_KEY_ALIASES.items()}
CANONICAL_TO_LEGACY_METRIC_KEYS = {value: key for key, value in METRIC_KEY_ALIASES.items()}


def canonical_scheme_key(name: str) -> str:
    return SCHEME_KEY_ALIASES.get(name, name)


def canonical_metric_key(name: str) -> str:
    return METRIC_KEY_ALIASES.get(name, name)


def canonicalize_scheme_keys(frame: pd.DataFrame, columns: Iterable[str] = ("scheme_label", "scheme_type", "representative_label")) -> pd.DataFrame:
    normalized = frame.copy()
    for column in columns:
        if column in normalized.columns:
            normalized[column] = normalized[column].map(lambda value: canonical_scheme_key(str(value)) if pd.notna(value) else value)
    return normalized


def add_legacy_scheme_alias_columns(frame: pd.DataFrame, columns: Iterable[str] = ("scheme_label", "scheme_type", "representative_label")) -> pd.DataFrame:
    normalized = frame.copy()
    for column in columns:
        if column not in normalized.columns:
            continue
        normalized[column] = normalized[column].map(
            lambda value: CANONICAL_TO_LEGACY_SCHEME_KEYS.get(str(value), value) if pd.notna(value) else value
        )
    return normalized


def add_canonical_metric_alias_columns(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = frame.copy()
    for legacy_name, canonical_name in METRIC_KEY_ALIASES.items():
        if legacy_name in normalized.columns and canonical_name not in normalized.columns:
            normalized[canonical_name] = normalized[legacy_name]
    for canonical_name, legacy_name in CANONICAL_TO_LEGACY_METRIC_KEYS.items():
        if canonical_name in normalized.columns and legacy_name not in normalized.columns:
            normalized[legacy_name] = normalized[canonical_name]
    return normalized


def first_present_metric(frame: pd.DataFrame, *candidates: str) -> str:
    expanded: list[str] = []
    for candidate in candidates:
        expanded.append(candidate)
        for legacy_name, canonical_name in METRIC_KEY_ALIASES.items():
            if canonical_name == candidate:
                expanded.append(legacy_name)
    seen: set[str] = set()
    for column in expanded:
        if column in seen:
            continue
        seen.add(column)
        if column in frame.columns:
            return column
    raise KeyError(f"None of the candidate metric columns exist: {expanded}")
