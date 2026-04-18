"""Per-topic dashboard row (``topic_insights.csv`` after enrichment)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class EmailCampaignCopy(BaseModel):
    """Structured email ideas (subject, hook, angle) for a single topic."""

    model_config = ConfigDict(extra="ignore")

    campaign_angle: str = ""
    suggested_subject: str = ""
    email_hook: str = ""


class TopicInsightRow(BaseModel):
    """One topic's scores, keywords, narrative, and optional campaign copy (``topic_insights.csv``)."""

    model_config = ConfigDict(extra="ignore")

    topic: int
    volume: int = 0
    avg_views: float = 0.0
    avg_likes: float = 0.0
    avg_comments: float = 0.0
    momentum: float = 0.0
    trend_score: float = 0.0

    topic_keywords: list[str] = Field(default_factory=list)
    dominant_topic_keywords: list[str] = Field(default_factory=list)
    topic_label: str = ""
    sample_titles: list[str] = Field(default_factory=list)
    trend_type: str = "general"
    fragmented_trend: bool = False
    topic_display_name: str = ""
    summary: str = ""
    marketing_safe: bool | None = None
    campaign_copy: EmailCampaignCopy = Field(default_factory=EmailCampaignCopy)
