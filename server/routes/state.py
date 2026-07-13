from fastapi import APIRouter

import pipeline

router = APIRouter(prefix="/api/state", tags=["state"])


@router.get("/overview")
def overview():
    return pipeline.overview()
