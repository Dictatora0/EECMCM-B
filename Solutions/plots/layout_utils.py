from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd


COMMUNITY_ORDER = list("ABCDEFGHIJ")


def parse_station_plan(plan_text: str | float | None) -> dict[str, str]:
    if plan_text is None or (isinstance(plan_text, float) and pd.isna(plan_text)):
        return {}
    plan = {}
    for token in str(plan_text).split(";"):
        token = token.strip()
        if not token:
            continue
        community, scale = token.split("-", 1)
        plan[community.strip()] = scale.strip()
    return plan


def load_distance_topology(distance_matrix_path: Path) -> pd.DataFrame:
    try:
        from sklearn.manifold import MDS
    except ImportError as exc:  # pragma: no cover - depends on local environment
        raise RuntimeError(
            "缺少 scikit-learn，无法根据距离矩阵生成拓扑布局。请安装 `scikit-learn` 后再构建相关图表。"
        ) from exc
    frame = pd.read_excel(distance_matrix_path, header=1, index_col=0)
    frame = frame.loc[COMMUNITY_ORDER, COMMUNITY_ORDER].astype(float)
    embedding = MDS(
        n_components=2,
        dissimilarity="precomputed",
        random_state=42,
        normalized_stress="auto",
        n_init=4,
    )
    coords = embedding.fit_transform(frame.values)
    result = pd.DataFrame(coords, columns=["x", "y"], index=COMMUNITY_ORDER).reset_index()
    return result.rename(columns={"index": "community"})


def station_size_value(scale: str | None) -> float:
    mapping = {"小型": 220.0, "中型": 320.0, "大型": 420.0}
    return mapping.get(str(scale), 180.0)


def short_scheme_label(path: str | None) -> str:
    if not path:
        return ""
    return str(path).replace("_", " ")
