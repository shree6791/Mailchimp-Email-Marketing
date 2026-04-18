"""Inbound rows from the trending CSV (before text prep and topic modeling)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class TrendingVideoRow(BaseModel):
    """One input row from the YouTube trending CSV (before text prep and topics)."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="ignore")

    title: str = ""
    tags: str = ""
    views: float = 0.0
    likes: float = 0.0
    comment_count: float = 0.0
    trending_date: str = ""
    description: str | None = None
