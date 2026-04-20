"""Load pipeline outputs for the dashboard and attach dashboard-only columns."""

from __future__ import annotations

import json
import os

import httpx
import pandas as pd

from src.config.settings import Settings
from src.storage.readers import load_pipeline_output_csvs


def dashboard_api_base() -> str | None:
    """If set, dashboard loads topic rows from the Trend HTTP API (production-style)."""
    v = os.environ.get("TREND_API_BASE_URL", "").strip()
    return v if v else None


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


def _load_topic_insights_from_api(base_url: str) -> pd.DataFrame:
    """Fetch full table JSON from FastAPI ``GET /topic-insights/records``."""
    url = f"{base_url.rstrip('/')}/topic-insights/records"
    try:
        r = httpx.get(url, timeout=60.0)
    except httpx.ConnectError as exc:
        raise RuntimeError(
            f"Cannot reach trend API at {url}. Start the API (e.g. ``python app.py``) "
            "or unset TREND_API_BASE_URL to use local CSV."
        ) from exc
    except httpx.TimeoutException as exc:
        raise RuntimeError(f"Trend API request timed out: {url}") from exc

    if r.status_code == 503:
        raise RuntimeError(
            "Trend API has no data (topic_insights missing on server). Run the pipeline first."
        )
    r.raise_for_status()
    payload = r.json()
    records = payload.get("records")
    if not isinstance(records, list):
        raise RuntimeError("Invalid API response: expected records list.")
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records)


def load_trend_dashboard_data(
    settings: Settings | None = None,
    *,
    api_base: str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load ``topic_insights`` (+ optional ``videos_with_topics``).

    - **Production-style:** set env ``TREND_API_BASE_URL`` (or pass ``api_base``) to load from
      the HTTP API (same contract as ``GET /topic-insights/records``).
    - **Local / batch:** leave unset to read ``outputs/topic_insights.csv`` directly.

    Returns ``(topic_insights, videos_with_topics)`` with ``opportunity_score`` on insights.
    """
    settings = settings or Settings()
    base = api_base if api_base is not None else dashboard_api_base()

    if base:
        topic_insights = _load_topic_insights_from_api(base)
        topic_insights = add_opportunity_score(topic_insights)
        return topic_insights, pd.DataFrame()

    topic_insights, videos_with_topics = load_pipeline_output_csvs(settings.output_dir)
    topic_insights = add_opportunity_score(topic_insights)
    return topic_insights, videos_with_topics
