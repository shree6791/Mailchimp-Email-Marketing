"""Trend scoring, taxonomy, coherence, and insight enrichment (vision: Trend Scorer + aggregator analog)."""

from src.ml.trends.topic_insight_enrichment import (
    add_topic_keyword_columns,
    enrich_topic_insights_marketer_fields,
)
from src.ml.trends.trend_scorer import TrendScorer

__all__ = [
    "TrendScorer",
    "add_topic_keyword_columns",
    "enrich_topic_insights_marketer_fields",
]
