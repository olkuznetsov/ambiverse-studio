import asyncio
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

import jobs

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class NewJob(BaseModel):
    type: str
    params: dict = {}
    env: dict = {}


@router.post("")
def create(body: NewJob):
    try:
        return jobs.create_job(body.type, body.params, body.env)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.get("")
def index(limit: int = 50):
    return jobs.list_jobs(limit)


@router.get("/{job_id}")
def show(job_id: int):
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(404, f"no job {job_id}")
    return job


@router.post("/{job_id}/cancel")
def cancel(job_id: int):
    try:
        return jobs.cancel_job(job_id)
    except LookupError:
        raise HTTPException(404, f"no job {job_id}")


@router.get("/{job_id}/log")
async def log_stream(job_id: int):
    """SSE: streams the job log as it grows; 'end' event once the job settles."""
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(404, f"no job {job_id}")

    async def gen():
        pos = 0
        while True:
            job_now = jobs.get_job(job_id)
            path = job_now.get("log_path")
            if path and Path(path).exists():
                with open(path, "r", errors="replace") as f:
                    f.seek(pos)
                    chunk = f.read()
                    pos = f.tell()
                if chunk:
                    # JSON-encode: raw SSE data lines lose trailing newlines,
                    # which would glue lines together across chunk boundaries
                    yield {"event": "log", "data": json.dumps(chunk)}
            if job_now["status"] in jobs.TERMINAL:
                yield {"event": "end", "data": job_now["status"]}
                return
            await asyncio.sleep(0.5)

    return EventSourceResponse(gen())
