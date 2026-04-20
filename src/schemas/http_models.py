"""Pydantic models for HTTP request and response bodies (FastAPI / OpenAPI)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.schemas.topic_insights import TopicInsightRow


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class TrendListItem(BaseModel):
    """Slim trend row for ``GET /trends`` (list contract)."""

    model_config = ConfigDict(extra="ignore")

    trend_id: str
    keyword: str
    lambdamart_score: float
    momentum: float
    source_count: int
    summary: str


class TrendDetail(BaseModel):
    """Per-trend detail for ``GET /trends/{trend_id}``."""

    model_config = ConfigDict(extra="ignore")

    trend_id: str
    keyword: str
    dominant_keywords: list[str] = Field(default_factory=list)
    lambdamart_score: float
    summary: str
    campaign_angle: str = ""
    suggested_subject: str = ""
    email_hook: str = ""
    marketing_safe: bool | None = None
    trending_snapshot_date: str = ""


class TrendListResponse(BaseModel):
    items: list[TrendListItem]
    limit: int
    offset: int
    total: int


class TopicInsightsRecordsResponse(BaseModel):
    """Full pipeline rows for ``GET /topic-insights/records``."""

    records: list[TopicInsightRow]
    count: int


class CampaignTrendLink(BaseModel):
    trend_id: str = Field(..., description="Composite id topic:ranking_segment")


class CampaignTrendLinkResponse(BaseModel):
    campaign_id: str
    trend_id: str
    applied_at: str
    status: str
    suggested_subject: str
