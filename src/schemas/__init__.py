"""
Typed shapes for the batch CSV pipeline.

Models mirror raw input columns (after loader projection), the slim
``videos_with_topics.csv`` / ``topic_insights.csv`` export columns, and what Streamlit consumes.
Use ``src.schemas.converters`` to validate ``pandas`` rows at load and save boundaries.
"""

from src.schemas.converters import (
    validate_topic_insight_rows,
    validate_trending_video_rows,
    validate_video_topic_rows,
)
from src.schemas.topic_insights import EmailCampaignCopy, TopicInsightRow
from src.schemas.trending_input import TrendingVideoRow
from src.schemas.video_topic import VideoTopicRow
from src.schemas.version import PIPELINE_SCHEMA_VERSION

__all__ = [
    "PIPELINE_SCHEMA_VERSION",
    "EmailCampaignCopy",
    "TopicInsightRow",
    "TrendingVideoRow",
    "VideoTopicRow",
    "validate_topic_insight_rows",
    "validate_trending_video_rows",
    "validate_video_topic_rows",
]
