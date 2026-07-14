from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import channel as channel_service
import history
import pipeline

router = APIRouter(prefix="/api/channel", tags=["channel"])


class ImpressionEntry(BaseModel):
    date: str
    impressions: int
    ctr: float
    note: str = ""

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


@router.get("/history")
def history_snapshots():
    return history.snapshots()


@router.get("/impressions")
def get_impressions():
    return history.impressions()


@router.post("/impressions")
def add_impressions(entry: ImpressionEntry):
    return history.add_impressions(entry.model_dump())


@router.delete("/impressions/{day}")
def delete_impressions(day: str):
    return history.delete_impressions(day)
