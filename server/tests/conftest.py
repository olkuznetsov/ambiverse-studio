"""Tests run in demo mode inside a throwaway data dir — no private pipeline,
no network, no credentials. The env must be set before the app is imported."""
import os
import re
import sys
import tempfile
import time
from pathlib import Path

SERVER = Path(__file__).resolve().parents[1]
os.environ["STUDIO_DEMO"] = "1"
os.environ["STUDIO_DATA_DIR"] = tempfile.mkdtemp(prefix="studio-tests-")
os.environ["DEMO_SPEED"] = "40"
sys.path.insert(0, str(SERVER))

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

TERMINAL = {"done", "failed", "cancelled"}


@pytest.fixture(scope="session")
def client():
    from app import app

    with TestClient(app, base_url="http://localhost") as c:  # lifespan starts the job worker
        yield c


def wait_for(client, job_id: int, statuses: set[str], timeout: float = 90) -> dict:
    deadline = time.time() + timeout
    job = {}
    while time.time() < deadline:
        job = client.get(f"/api/jobs/{job_id}").json()
        if job["status"] in statuses:
            return job
        time.sleep(0.2)
    raise AssertionError(f"job {job_id} stuck in {job.get('status')!r}")


def wait_for_log(client, job_id: int, pattern: str, timeout: float = 30) -> re.Match:
    deadline = time.time() + timeout
    while time.time() < deadline:
        path = client.get(f"/api/jobs/{job_id}").json().get("log_path")
        if path and Path(path).exists():
            m = re.search(pattern, Path(path).read_text(), re.M)
            if m:
                return m
        time.sleep(0.2)
    raise AssertionError(f"{pattern!r} never appeared in job {job_id}'s log")
