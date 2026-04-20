"""Map ``pandas`` rows to Pydantic models (same shapes written to and read from CSV)."""

from __future__ import annotations

import ast
from typing import Any

import numpy as np
import pandas as pd

from src.schemas.topic_insights import EmailCampaignCopy, TopicInsightRow
from src.schemas.trending_input import TrendingVideoRow
from src.schemas.video_topic import VideoTopicRow


def _pandas_row_as_dict(row: pd.Series) -> dict[str, Any]:
    """Turn a Series into JSON-friendly scalars for ``model_validate``."""
    out: dict[str, Any] = {}
    for key, val in row.items():
        if isinstance(val, (list, tuple)):
            out[key] = list(val)
        elif isinstance(val, dict):
            out[key] = val
        elif isinstance(val, np.ndarray):
            out[key] = val.tolist()
        elif isinstance(val, (np.integer, np.floating)):
            out[key] = val.item()
        elif isinstance(val, np.bool_):
            out[key] = bool(val.item())
        elif pd.isna(val):
            out[key] = None
        else:
            out[key] = val
    return out


def _coerce_str_list(val: Any) -> list[str]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return []
    if isinstance(val, list):
        return [str(x) for x in val]
    if isinstance(val, str) and val.strip():
        try:
            parsed = ast.literal_eval(val)
            if isinstance(parsed, list):
                return [str(x) for x in parsed]
        except (SyntaxError, ValueError, MemoryError):
            return [val]
        return [val]
    return [str(val)]


def _coerce_campaign_copy_dict(val: Any) -> dict[str, str]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return {}
    if isinstance(val, dict):
        return {k: str(v) if v is not None else "" for k, v in val.items()}
    if isinstance(val, str) and val.strip():
        try:
            parsed = ast.literal_eval(val)
            if isinstance(parsed, dict):
                return {k: str(v) if v is not None else "" for k, v in parsed.items()}
        except (SyntaxError, ValueError, MemoryError):
            pass
    return {}


def _topic_insight_from_series(row: pd.Series) -> TopicInsightRow:
    d = _pandas_row_as_dict(row)
    d["topic_keywords"] = _coerce_str_list(d.get("topic_keywords"))
    d["dominant_topic_keywords"] = _coerce_str_list(d.get("dominant_topic_keywords"))
    d["sample_titles"] = _coerce_str_list(d.get("sample_titles"))
    d["campaign_copy"] = EmailCampaignCopy.model_validate(
        _coerce_campaign_copy_dict(d.get("campaign_copy"))
    )
    if d.get("topic") is not None:
        d["topic"] = int(d["topic"])
    if d.get("volume") is not None:
        d["volume"] = int(d["volume"])
    rs = d.get("ranking_segment")
    if rs is None or (isinstance(rs, float) and pd.isna(rs)):
        d["ranking_segment"] = "general"
    else:
        d["ranking_segment"] = str(rs).strip() or "general"
    sr = d.get("segment_rank")
    if sr is None or (isinstance(sr, float) and pd.isna(sr)):
        d["segment_rank"] = 0
    else:
        d["segment_rank"] = int(float(sr))
    td = d.get("trending_snapshot_date")
    if td is None or (isinstance(td, float) and pd.isna(td)):
        d["trending_snapshot_date"] = ""
    else:
        d["trending_snapshot_date"] = str(td).strip()
    return TopicInsightRow.model_validate(d)


def topic_insight_row_from_series(row: pd.Series) -> TopicInsightRow:
    """Build a validated ``TopicInsightRow`` from a ``topic_insights.csv`` row."""
    return _topic_insight_from_series(row)


def validate_trending_video_rows(df: pd.DataFrame, *, sample: int | None = None) -> None:
    """
    Check that each row matches ``TrendingVideoRow`` (raises ``ValidationError``).

    ``sample``: if set, only validate the first N rows (faster on large frames).
    """
    rows = df.head(sample) if sample is not None else df
    for _, row in rows.iterrows():
        TrendingVideoRow.model_validate(_pandas_row_as_dict(row))


def validate_topic_insight_rows(df: pd.DataFrame) -> None:
    """Check that each ``topic_insights.csv`` row matches ``TopicInsightRow``."""
    for _, row in df.iterrows():
        _topic_insight_from_series(row)


def validate_video_topic_rows(df: pd.DataFrame) -> None:
    """Check that each ``videos_with_topics.csv`` row matches ``VideoTopicRow``."""
    for _, row in df.iterrows():
        VideoTopicRow.model_validate(_pandas_row_as_dict(row))
