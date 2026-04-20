"""Trend list/detail and full-record endpoints over ``outputs/topic_insights.csv``."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi import APIRouter, HTTPException

from src.config.settings import Settings
from src.constants.pipeline_io import TOPIC_INSIGHTS_FILENAME
from src.schemas.http_models import (
    TopicInsightsRecordsResponse,
    TrendDetail,
    TrendListItem,
    TrendListResponse,
)
from src.schemas.converters import topic_insight_row_from_series
from src.storage.readers import load_topic_insights_csv

router = APIRouter(tags=["trends"])


def _insights_path() -> Path:
    return Path(Settings().output_dir) / TOPIC_INSIGHTS_FILENAME


def _trend_id(row: pd.Series) -> str:
    seg = str(row.get("ranking_segment", "") or "").strip() or "default"
    return f"{int(row['topic'])}:{seg}"


def _row_to_list_item(row: pd.Series) -> TrendListItem:
    kw = row.get("topic_label") or ""
    if pd.isna(kw):
        kw = ""
    return TrendListItem(
        trend_id=_trend_id(row),
        keyword=str(kw),
        lambdamart_score=float(row.get("trend_score", 0) or 0),
        momentum=float(row.get("momentum", 0) or 0),
        source_count=int(row.get("volume", 0) or 0),
        summary=str(row.get("summary", "") or ""),
    )


def _row_to_detail(row: pd.Series) -> TrendDetail:
    cc = row.get("campaign_copy")
    if not isinstance(cc, dict):
        cc = {}
    dk = row.get("dominant_topic_keywords")
    dom: list[str] = dk if isinstance(dk, list) else []

    return TrendDetail(
        trend_id=_trend_id(row),
        keyword=str(row.get("topic_label") or ""),
        dominant_keywords=dom,
        lambdamart_score=float(row.get("trend_score", 0) or 0),
        summary=str(row.get("summary", "") or ""),
        campaign_angle=str(cc.get("campaign_angle", "") or ""),
        suggested_subject=str(cc.get("suggested_subject", "") or ""),
        email_hook=str(cc.get("email_hook", "") or ""),
        marketing_safe=row.get("marketing_safe"),
        trending_snapshot_date=str(row.get("trending_snapshot_date", "") or ""),
    )


@router.get("/topic-insights/records", response_model=TopicInsightsRecordsResponse)
def topic_insights_records() -> TopicInsightsRecordsResponse:
    """
    Full ``topic_insights`` rows for dashboard or other clients (JSON records).

    Prefer this for UIs; use ``/trends`` for the slimmer list contract.
    """
    p = _insights_path()
    if not p.exists():
        raise HTTPException(
            status_code=503,
            detail="topic_insights.csv not found; run the pipeline (python main.py) first.",
        )
    df = load_topic_insights_csv(p)
    if df.empty:
        return TopicInsightsRecordsResponse(records=[], count=0)
    records = [topic_insight_row_from_series(row) for _, row in df.iterrows()]
    return TopicInsightsRecordsResponse(records=records, count=len(records))


@router.get("/trends", response_model=TrendListResponse)
def list_trends(limit: int = 20, offset: int = 0) -> TrendListResponse:
    p = _insights_path()
    if not p.exists():
        raise HTTPException(
            status_code=503,
            detail="topic_insights.csv not found; run the pipeline (python main.py) first.",
        )
    df = load_topic_insights_csv(p)
    if df.empty:
        return TrendListResponse(items=[], limit=limit, offset=offset, total=0)
    total = len(df)
    chunk = df.iloc[offset : offset + limit]
    items = [_row_to_list_item(row) for _, row in chunk.iterrows()]
    return TrendListResponse(items=items, limit=limit, offset=offset, total=total)


@router.get("/trends/{trend_id}", response_model=TrendDetail)
def get_trend(trend_id: str) -> TrendDetail:
    p = _insights_path()
    if not p.exists():
        raise HTTPException(status_code=503, detail="topic_insights.csv not found.")
    df = load_topic_insights_csv(p)
    for _, row in df.iterrows():
        if _trend_id(row) == trend_id:
            return _row_to_detail(row)
    raise HTTPException(status_code=404, detail="Unknown trend_id")
