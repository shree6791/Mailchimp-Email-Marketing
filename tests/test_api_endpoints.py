"""Tests for FastAPI routes in ``app.py``, ``src/api/trends.py``, and ``src/api/campaigns.py``."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _write_minimal_topic_insights(path: Path) -> None:
    """Minimal CSV that ``load_topic_insights_csv`` + trend handlers accept."""
    df = pd.DataFrame(
        [
            {
                "topic": 5,
                "volume": 100,
                "avg_views": 1.0,
                "avg_likes": 1.0,
                "avg_comments": 1.0,
                "momentum": 0.2,
                "avg_proxy_ctr_recency": 0.5,
                "trend_score": 0.9,
                "ranking_segment": "US",
                "segment_rank": 1,
                "trending_snapshot_date": "2024-01-01",
                "topic_keywords": "['x']",
                "dominant_topic_keywords": "['kw1', 'kw2']",
                "topic_label": "Gadgets",
                "sample_titles": "['t1']",
                "trend_type": "technology",
                "fragmented_trend": False,
                "topic_display_name": "Gadgets",
                "summary": "Summary line",
                "marketing_safe": True,
                "campaign_copy": "{'campaign_angle': 'angle', 'suggested_subject': 'subj', 'email_hook': 'hook'}",
            },
            {
                "topic": 7,
                "volume": 50,
                "avg_views": 2.0,
                "avg_likes": 2.0,
                "avg_comments": 2.0,
                "momentum": 0.1,
                "avg_proxy_ctr_recency": 0.4,
                "trend_score": 0.5,
                "ranking_segment": "US",
                "segment_rank": 2,
                "trending_snapshot_date": "2024-01-02",
                "topic_keywords": "['y']",
                "dominant_topic_keywords": "[]",
                "topic_label": "Other",
                "sample_titles": "['t2']",
                "trend_type": "entertainment",
                "fragmented_trend": False,
                "topic_display_name": "Other",
                "summary": "Other summary",
                "marketing_safe": False,
                "campaign_copy": "{}",
            },
        ]
    )
    df.to_csv(path, index=False)


def test_health(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.parametrize(
    "path",
    ["/trends", "/topic-insights/records", "/trends/1:US"],
)
def test_trends_routes_503_when_csv_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, client: TestClient, path: str
) -> None:
    missing = tmp_path / "topic_insights.csv"
    monkeypatch.setattr("src.api.trends._insights_path", lambda: missing)
    r = client.get(path)
    assert r.status_code == 503


def test_list_trends_returns_items_and_pagination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    p = tmp_path / "topic_insights.csv"
    _write_minimal_topic_insights(p)
    monkeypatch.setattr("src.api.trends._insights_path", lambda: p)

    r = client.get("/trends")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert len(body["items"]) == 2
    assert body["items"][0]["trend_id"] == "5:US"
    assert body["items"][0]["keyword"] == "Gadgets"

    r2 = client.get("/trends", params={"limit": 1, "offset": 1})
    assert r2.status_code == 200
    b2 = r2.json()
    assert b2["total"] == 2
    assert len(b2["items"]) == 1
    assert b2["items"][0]["trend_id"] == "7:US"


def test_get_trend_detail_and_404(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    p = tmp_path / "topic_insights.csv"
    _write_minimal_topic_insights(p)
    monkeypatch.setattr("src.api.trends._insights_path", lambda: p)

    r = client.get("/trends/5:US")
    assert r.status_code == 200
    d = r.json()
    assert d["trend_id"] == "5:US"
    assert d["keyword"] == "Gadgets"
    assert d["dominant_keywords"] == ["kw1", "kw2"]
    assert d["campaign_angle"] == "angle"
    assert d["suggested_subject"] == "subj"
    assert d["email_hook"] == "hook"

    r404 = client.get("/trends/99:US")
    assert r404.status_code == 404


def test_topic_insights_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    p = tmp_path / "topic_insights.csv"
    _write_minimal_topic_insights(p)
    monkeypatch.setattr("src.api.trends._insights_path", lambda: p)

    r = client.get("/topic-insights/records")
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2
    assert len(body["records"]) == 2
    assert body["records"][0]["topic"] == 5


def test_topic_insights_records_empty_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, client: TestClient
) -> None:
    p = tmp_path / "topic_insights.csv"
    # Header-only file (parsable by pandas; matches "pipeline ran, zero rows" edge case).
    pd.DataFrame(
        columns=[
            "topic",
            "volume",
            "trend_score",
            "ranking_segment",
            "topic_label",
            "summary",
        ]
    ).to_csv(p, index=False)
    monkeypatch.setattr("src.api.trends._insights_path", lambda: p)

    r = client.get("/topic-insights/records")
    assert r.status_code == 200
    assert r.json() == {"records": [], "count": 0}


def test_link_campaign_trend_stub(client: TestClient) -> None:
    r = client.post(
        "/campaigns/camp-1/trends",
        json={"trend_id": "5:US"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["campaign_id"] == "camp-1"
    assert data["trend_id"] == "5:US"
    assert data["status"] == "accepted"
    assert "applied_at" in data
