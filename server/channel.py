"""Channel analytics service — runs the collector under the pipeline's venv
(it needs google-api libs the studio venv doesn't have) and caches the result.

Quota-friendly: the YouTube APIs have daily quotas, so we cache to disk with a
1h TTL and only refetch on expiry or an explicit refresh. A failed refetch falls
back to the last good cache (flagged stale) rather than erroring the page.
"""
import json
import subprocess
import time
from pathlib import Path

from config import ANIMEMBIENT_DIR, DATA_DIR

PIPELINE_PYTHON = str(ANIMEMBIENT_DIR / "venv" / "bin" / "python")
COLLECTOR = Path(__file__).resolve().parent / "collectors" / "channel_fetch.py"
CACHE = DATA_DIR / "channel_cache.json"
TTL_SECONDS = 3600


def _load_cache() -> dict | None:
    try:
        return json.loads(CACHE.read_text())
    except (OSError, ValueError):
        return None


def _fetch() -> dict:
    proc = subprocess.run(
        [PIPELINE_PYTHON, str(COLLECTOR), str(ANIMEMBIENT_DIR)],
        capture_output=True, text=True, timeout=180,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip()[-500:] or "collector failed")
    data = json.loads(proc.stdout)
    data["fetched_at"] = time.time()
    CACHE.write_text(json.dumps(data))
    return data


def get(refresh: bool = False) -> dict:
    cached = _load_cache()
    fresh = cached and (time.time() - cached.get("fetched_at", 0) < TTL_SECONDS)
    if fresh and not refresh:
        return {**cached, "cache": "fresh"}
    try:
        data = _fetch()
        return {**data, "cache": "live"}
    except Exception as exc:
        if cached:  # serve stale rather than fail the page
            return {**cached, "cache": "stale", "refresh_error": str(exc)}
        raise
