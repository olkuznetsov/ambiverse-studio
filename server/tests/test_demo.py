"""Demo mode end to end: every page's API answers, and a full build runs
through the real job engine against the stand-in pipeline."""
from pathlib import Path

import pytest

from conftest import TERMINAL, wait_for

PAGE_ENDPOINTS = [
    "/api/state/overview", "/api/themes", "/api/themes/ps1-jungle/images", "/api/music",
    "/api/outputs", "/api/housekeeping", "/api/assets/used-images", "/api/prompts/today",
    "/api/prompts/history", "/api/build/preflight", "/api/veo/sources", "/api/jobs",
    "/api/channel", "/api/channel/history", "/api/channel/impressions", "/api/settings",
]


def test_health_reports_demo_mode(client):
    assert client.get("/api/health").json()["demo"] is True


@pytest.mark.parametrize("url", PAGE_ENDPOINTS)
def test_every_page_endpoint_answers(client, url):
    assert client.get(url).status_code == 200


def test_seeded_world_is_ready_to_build(client):
    overview = client.get("/api/state/overview").json()
    assert any(t["eligible"] for t in overview["themes"])
    assert overview["music"]["library_count"] > 0
    assert client.get("/api/build/preflight").json()["ok"] is True


def test_channel_rollups_compare_long_form_only(client):
    data = client.get("/api/channel").json()
    assert data["cache"] == "snapshot"
    for row in data["theme_rollup"] + data["format_rollup"]:
        # Shorts loop and can report >100% view rate; rollups must exclude them
        assert row["avg_view_pct"] is None or row["avg_view_pct"] <= 100


def test_full_build_runs_through_the_real_job_engine(client):
    job = client.post("/api/jobs", json={"type": "main_build", "env": {
        "VIDEO_DURATION_SECONDS": "60", "YOUTUBE_UPLOAD": "true", "MAKE_SHORTS": "false",
    }}).json()
    done = wait_for(client, job["id"], TERMINAL, timeout=150)
    log = Path(done["log_path"]).read_text()
    assert done["status"] == "done", log[-2000:]
    assert "clip 1/" in log and "[upload] 100%" in log and "Done. Video:" in log
    assert any(o["name"].endswith("_thumbnail.jpg") for o in client.get("/api/outputs").json())
