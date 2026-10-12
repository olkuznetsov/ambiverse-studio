"""Localhost-only and secrets-safe are claims — these tests hold them to it."""
import pytest
from fastapi.testclient import TestClient


def test_spa_route_never_serves_files_outside_dist(tmp_path):
    from app import resolve_spa_file

    dist = (tmp_path / "dist").resolve()
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html></html>")
    (dist / "assets" / "app.js").write_text("console.log(1)")
    (tmp_path / ".env").write_text("SECRET=1")

    assert resolve_spa_file(dist, "../.env") == dist / "index.html"
    assert resolve_spa_file(dist, "assets/../../.env") == dist / "index.html"
    assert resolve_spa_file(dist, "assets/app.js") == dist / "assets" / "app.js"
    assert resolve_spa_file(dist, "") == dist / "index.html"


def test_foreign_host_header_is_rejected():
    """DNS rebinding: a hostile domain re-resolved to 127.0.0.1 arrives with its own Host."""
    from app import app

    assert TestClient(app, base_url="http://attacker.example").get("/api/health").status_code == 400


@pytest.mark.parametrize("path", [
    "../../.env",             # escapes the pipeline dir
    "../../../etc/passwd",
    "config.py",              # inside, but not a media file
    "youtube_token.json",     # credentials are never servable
    "client_secret.json",
])
def test_media_endpoint_serves_only_media_inside_the_pipeline(client, path):
    assert client.get("/api/media/file", params={"path": path}).status_code == 400


def test_trash_refuses_non_media_files(client):
    assert client.post("/api/assets/trash", json={"path": "config.py"}).status_code == 400
    assert client.post("/api/assets/trash", json={"path": "../../.env"}).status_code == 400


def test_job_params_cannot_point_outside_the_pipeline(client):
    r = client.post("/api/jobs", json={"type": "veo_assemble",
                                       "params": {"clips": ["../../../etc/passwd"]}})
    assert r.status_code == 400
