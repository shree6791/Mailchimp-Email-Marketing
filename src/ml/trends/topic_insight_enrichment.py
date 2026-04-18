"""
Augment per-topic score rows from ``TrendScorer`` with keywords, heuristics, and LLM copy.
"""

from __future__ import annotations

import pandas as pd

from src.constants.insights import (
    EMPTY_CAMPAIGN_COPY,
    FRAGMENTED_TOPIC_INSIGHT_RESPONSE,
    INCOHERENT_TOPIC_INSIGHT_RESPONSE,
    OUTSIDE_LLM_TOP_N_SUMMARY,
)
from src.constants.scoring import (
    HIGH_ENGAGEMENT_MIN_LIKES,
    HIGH_ENGAGEMENT_MIN_TREND_SCORE,
    HIGH_ENGAGEMENT_MIN_VIEWS,
)
from src.insights.insight_generator import InsightGenerator
from src.ml.nlp.topic_modeler import TopicModeler
from src.ml.nlp.topic_namer import TopicNamer
from src.ml.trends.topic_coherence import topic_is_coherent
from src.ml.trends.trend_taxonomy import classify_trend_type


def _is_high_engagement_row(row: pd.Series) -> bool:
    return (
        float(row.get("avg_likes", 0)) >= HIGH_ENGAGEMENT_MIN_LIKES
        or float(row.get("avg_views", 0)) >= HIGH_ENGAGEMENT_MIN_VIEWS
        or float(row.get("trend_score", 0)) >= HIGH_ENGAGEMENT_MIN_TREND_SCORE
    )


def add_topic_keyword_columns(
    topic_insights: pd.DataFrame,
    topic_modeler: TopicModeler,
) -> None:
    topic_insights["topic_keywords"] = topic_insights["topic"].apply(
        lambda topic_id: topic_modeler.get_topic_keywords(int(topic_id))
    )
    topic_insights["dominant_topic_keywords"] = topic_insights["topic"].apply(
        lambda topic_id: topic_modeler.get_dominant_topic_keywords(int(topic_id))
    )
    topic_insights["topic_label"] = topic_insights["topic_keywords"].apply(
        lambda keywords: ", ".join(keywords[:5]) if keywords else "unknown_topic"
    )


def enrich_topic_insights_marketer_fields(
    videos_with_topics: pd.DataFrame,
    topic_insights: pd.DataFrame,
    topic_namer: TopicNamer,
    insight_generator: InsightGenerator,
    llm_top_n: int,
) -> pd.DataFrame:
    """Heuristics + LLM summaries and campaign copy (expects keyword columns already present)."""
    topic_insights = topic_insights.copy()

    summaries: list[str] = []
    suggestions: list[dict[str, str]] = []
    marketing_safe_flags: list[bool | None] = []
    sample_titles_list: list[list[str]] = []
    trend_types: list[str] = []
    fragmented_flags: list[bool] = []
    topic_display_names: list[str] = []

    for idx, row in topic_insights.iterrows():
        topic_id = int(row["topic"])
        dominant_topic_keywords = row["dominant_topic_keywords"]

        sample_titles = (
            videos_with_topics[videos_with_topics["topic"] == topic_id]["title"]
            .dropna()
            .astype(str)
            .head(3)
            .tolist()
        )
        sample_titles_list.append(sample_titles)

        trend_type = classify_trend_type(dominant_topic_keywords, sample_titles)
        topic_coherent = topic_is_coherent(dominant_topic_keywords, sample_titles)
        high_engagement = _is_high_engagement_row(row)
        fragmented_trend = (not topic_coherent) and high_engagement

        topic_display_name = topic_namer.name_topic(
            keywords=dominant_topic_keywords,
            trend_type=trend_type,
            fragmented_trend=fragmented_trend,
        )

        trend_types.append(trend_type)
        fragmented_flags.append(fragmented_trend)
        topic_display_names.append(topic_display_name)

        if idx < llm_top_n:
            if not topic_coherent:
                canned = (
                    FRAGMENTED_TOPIC_INSIGHT_RESPONSE
                    if fragmented_trend
                    else INCOHERENT_TOPIC_INSIGHT_RESPONSE
                )
                insight = dict(canned)
            else:
                insight = insight_generator.generate_insight(
                    topic_label=row["topic_label"],
                    topic_keywords=dominant_topic_keywords,
                    trend_type=trend_type,
                    row=row,
                    sample_titles=sample_titles,
                )

            summaries.append(insight["summary"])
            marketing_safe_flags.append(insight["marketing_safe"])

            if insight["marketing_safe"]:
                suggestions.append(
                    {
                        "campaign_angle": insight["campaign_angle"],
                        "suggested_subject": insight["suggested_subject"],
                        "email_hook": insight["email_hook"],
                    }
                )
            else:
                suggestions.append(dict(EMPTY_CAMPAIGN_COPY))
        else:
            summaries.append(OUTSIDE_LLM_TOP_N_SUMMARY)
            marketing_safe_flags.append(None)
            suggestions.append(dict(EMPTY_CAMPAIGN_COPY))

    topic_insights["sample_titles"] = sample_titles_list
    topic_insights["trend_type"] = trend_types
    topic_insights["fragmented_trend"] = fragmented_flags
    topic_insights["topic_display_name"] = topic_display_names
    topic_insights["summary"] = summaries
    topic_insights["marketing_safe"] = marketing_safe_flags
    topic_insights["campaign_copy"] = suggestions

    return topic_insights
