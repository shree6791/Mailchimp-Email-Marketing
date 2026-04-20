"""Campaign–trend linking stub (no persistence)."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from src.schemas.http_models import CampaignTrendLink, CampaignTrendLinkResponse

router = APIRouter(tags=["campaigns"])


@router.post(
    "/campaigns/{campaign_id}/trends",
    response_model=CampaignTrendLinkResponse,
)
def link_campaign_trend(
    campaign_id: str, body: CampaignTrendLink
) -> CampaignTrendLinkResponse:
    """Stub: records that a campaign would pin a trend (no persistence)."""
    return CampaignTrendLinkResponse(
        campaign_id=campaign_id,
        trend_id=body.trend_id,
        applied_at=datetime.now(timezone.utc).isoformat(),
        status="accepted",
        suggested_subject="",
    )
