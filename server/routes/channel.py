from fastapi import APIRouter, HTTPException

import channel as channel_service
import pipeline

router = APIRouter(prefix="/api/channel", tags=["channel"])

STUDIO_ANALYTICS_URL = (
    "https://studio.youtube.com/channel/UCpPbi7maiGv5egwVkliqNMg/analytics/"
    "tab-reach_viewers/period-lifetime"  # impressions & CTR live here (not in any API)
)


@router.get("")
def channel(refresh: bool = False):
    try:
        data = channel_service.get(refresh=refresh)
    except Exception as exc:
        raise HTTPException(502, f"channel fetch failed: {exc}")
    tokens = {t["key"]: t for t in pipeline.token_status()}
    data["analytics_token"] = tokens.get("analytics")
    data["studio_impressions_url"] = STUDIO_ANALYTICS_URL
    return data
