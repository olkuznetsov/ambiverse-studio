"""Local growth history — the two things the channel is limited by, over time.

- Analytics snapshots: captured automatically on each LIVE channel fetch. The
  YouTube APIs only expose *current* totals, so we bank a daily point locally to
  chart the trajectory (subs, views, watch-hours toward YPP).
- Impressions/CTR log: the ONE metric no API exposes (Studio-web only). Typed in
  by hand from Studio screenshots so CTR can be tracked over time.

Both live in the studio's own data/ dir — never in the pipeline repo — and are
keyed by date (one row per day, latest write wins).
"""
import json
from datetime import date

from config import DATA_DIR

SNAPSHOTS = DATA_DIR / "channel_history.json"
IMPRESSIONS = DATA_DIR / "impressions_log.json"


def _load(path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def _save(path, data: dict):
    path.write_text(json.dumps(data, indent=0, sort_keys=True))


def record_snapshot(channel_data: dict) -> None:
    """Bank today's cumulative totals (idempotent per day — latest wins)."""
    ch = channel_data.get("channel", {})
    analytics = channel_data.get("analytics", {})
    lifetime = analytics.get("lifetime") if analytics.get("available") else None
    long_row = None
    for row in (analytics.get("content_type") or []):
        if row.get("label") == "Long videos":
            long_row = row
            break
    snap = {
        "date": date.today().isoformat(),
        "subscribers": ch.get("subscribers"),
        "total_views": ch.get("views"),
        "watch_minutes": lifetime.get("minutes_watched") if lifetime else None,
        "long_watch_minutes": long_row.get("minutes_watched") if long_row else None,
        "retention": lifetime.get("avg_view_pct") if lifetime else None,
    }
    data = _load(SNAPSHOTS)
    data[snap["date"]] = snap
    _save(SNAPSHOTS, data)


def snapshots() -> list[dict]:
    return [v for _, v in sorted(_load(SNAPSHOTS).items())]


def impressions() -> list[dict]:
    return [v for _, v in sorted(_load(IMPRESSIONS).items())]


def add_impressions(entry: dict) -> list[dict]:
    data = _load(IMPRESSIONS)
    day = entry["date"]
    data[day] = {
        "date": day,
        "impressions": int(entry["impressions"]),
        "ctr": float(entry["ctr"]),
        "note": (entry.get("note") or "").strip(),
    }
    _save(IMPRESSIONS, data)
    return impressions()


def delete_impressions(day: str) -> list[dict]:
    data = _load(IMPRESSIONS)
    data.pop(day, None)
    _save(IMPRESSIONS, data)
    return impressions()
