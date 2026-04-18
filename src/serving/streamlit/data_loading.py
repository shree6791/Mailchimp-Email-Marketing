"""Load pipeline outputs for the dashboard and attach dashboard-only columns."""

from __future__ import annotations

import pandas as pd

from src.config.settings import Settings
from src.storage.readers import load_pipeline_output_csvs


def add_opportunity_score(topic_insights: pd.DataFrame) -> pd.DataFrame:
    topic_insights = topic_insights.copy()

    def normalize(series: pd.Series) -> pd.Series:
        s = series.fillna(0).astype(float)
        if s.max() == s.min():
            return pd.Series([0.0] * len(s), index=s.index)
        return (s - s.min()) / (s.max() - s.min())

    score_norm = normalize(topic_insights["trend_score"])
    momentum_norm = normalize(topic_insights["momentum"])
    views_norm = normalize(topic_insights["avg_views"])
    likes_norm = normalize(topic_insights["avg_likes"])

    topic_insights["opportunity_score"] = (
        0.35 * score_norm
        + 0.30 * momentum_norm
        + 0.20 * views_norm
        + 0.15 * likes_norm
    ) * 100

    topic_insights["opportunity_score"] = topic_insights["opportunity_score"].round(1)
    return topic_insights


def load_trend_dashboard_data(
    settings: Settings | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load ``topic_insights.csv`` and optional ``videos_with_topics.csv``.

    Returns ``(topic_insights, videos_with_topics)`` — same column names as the CSVs,
    plus ``opportunity_score`` on ``topic_insights`` for the UI.
    """
    settings = settings or Settings()
    topic_insights, videos_with_topics = load_pipeline_output_csvs(settings.output_dir)
    topic_insights = add_opportunity_score(topic_insights)
    return topic_insights, videos_with_topics
