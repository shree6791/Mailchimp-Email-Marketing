"""Per-video export after topic assignment (``videos_with_topics.csv``)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class VideoTopicRow(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = ""
    tags: str = ""
    trending_date: str = ""
    views: float = 0.0
    likes: float = 0.0
    comment_count: float = 0.0
    topic: int = -1
    topic_confidence: float | None = None
