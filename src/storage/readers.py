"""Read pipeline CSV artifacts (mirror of ``writers`` for local MVP files)."""

from __future__ import annotations

import ast
from pathlib import Path

import pandas as pd

from src.constants.pipeline_io import TOPIC_INSIGHTS_FILENAME, VIDEOS_WITH_TOPICS_FILENAME


def safe_literal_eval(value: object) -> object:
    """Parse list/dict columns stored as strings in CSV back to Python objects."""
    if isinstance(value, (list, dict)):
        return value
    if pd.isna(value):
        return None
    try:
        return ast.literal_eval(value)
    except Exception:
        return value


def load_topic_insights_csv(path: Path | str) -> pd.DataFrame:
    """Load ``topic_insights.csv`` and deserialize list / ``campaign_copy`` columns."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing file: {p}")

    topic_insights = pd.read_csv(p)
    for col in ["topic_keywords", "dominant_topic_keywords", "sample_titles"]:
        if col in topic_insights.columns:
            topic_insights[col] = topic_insights[col].apply(safe_literal_eval)
    if "campaign_copy" in topic_insights.columns:
        topic_insights["campaign_copy"] = topic_insights["campaign_copy"].apply(safe_literal_eval)
    return topic_insights


def load_videos_with_topics_csv(path: Path | str) -> pd.DataFrame:
    """Load ``videos_with_topics.csv`` if present; otherwise return an empty frame."""
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    return pd.read_csv(p)


def load_pipeline_output_csvs(output_dir: Path | str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load final pipeline outputs from ``output_dir`` (same files ``save_final_artifacts`` writes)."""
    out = Path(output_dir)
    topic_insights = load_topic_insights_csv(out / TOPIC_INSIGHTS_FILENAME)
    videos_with_topics = load_videos_with_topics_csv(out / VIDEOS_WITH_TOPICS_FILENAME)
    return topic_insights, videos_with_topics
