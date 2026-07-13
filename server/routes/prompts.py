"""Prompts: structured scenes/music from logs/prompts_<date>.json (written by
generate_prompts.py — same data the txt files are rendered from), STYLE from
the pipeline config, THUMBNAIL section parsed out of today_prompt.txt.
"""
import json
import re
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException

from config import ANIMEMBIENT_DIR, PIPELINE

router = APIRouter(prefix="/api/prompts", tags=["prompts"])

LOGS_DIR = ANIMEMBIENT_DIR / "logs"
_DATE_RE = re.compile(r"prompts_(\d{4}-\d{2}-\d{2})\.json$")


def _style_for(theme: str) -> str:
    info = PIPELINE.THEMES.get(theme, {})
    return info.get("base_style", PIPELINE.BASE_STYLE_PROMPT)


def _thumbnail_block(theme: str) -> str | None:
    """The paste-able THUMBNAIL section of images/<theme>/today_prompt.txt
    (style line + composition + TEXT ON IMAGE), best-effort."""
    path = ANIMEMBIENT_DIR / "images" / theme / "today_prompt.txt"
    try:
        text = path.read_text()
    except OSError:
        return None
    m = re.search(r"THUMBNAIL[^\n]*\n═+\n(.*?)(?:\n\s*HOW TO USE:|\Z)", text, re.S)
    return m.group(1).strip() if m else None


def _history_files() -> list[tuple[str, Path]]:
    files = []
    for p in LOGS_DIR.glob("prompts_*.json"):
        m = _DATE_RE.search(p.name)
        if m:
            files.append((m.group(1), p))
    return sorted(files, reverse=True)


def _payload(date: str, path, *, with_thumbnails: bool) -> dict:
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise HTTPException(500, f"cannot read {path.name}: {exc}")
    themes = []
    for key in PIPELINE.THEMES:
        scenes = data.get("scenes", {}).get(key, [])
        # tolerate the old shape where a scene was a plain string
        norm = [s if isinstance(s, dict) else {"scene": s, "variations": []} for s in scenes]
        themes.append({
            "key": key,
            "title": PIPELINE.THEMES[key].get("motif") or key.replace("-", " ").title(),
            "style": _style_for(key),
            "scenes": norm,
            "music_prompts": data.get("music_prompts", {}).get(key, []),
            "thumbnail": _thumbnail_block(key) if with_thumbnails else None,
        })
    # local date, not UTC — "how stale are my prompts" is a local-morning question
    age_days = (datetime.now().date() - datetime.strptime(date, "%Y-%m-%d").date()).days
    return {"date": date, "age_days": age_days, "themes": themes}


@router.get("/today")
def today():
    files = _history_files()
    if not files:
        raise HTTPException(404, "no prompts generated yet — run generate_prompts")
    date, path = files[0]
    return _payload(date, path, with_thumbnails=True)


@router.get("/history")
def history():
    return [date for date, _ in _history_files()]


@router.get("/day/{date}")
def day(date: str):
    for d, path in _history_files():
        if d == date:
            # thumbnails only exist for the latest run (today_prompt.txt is overwritten)
            return _payload(d, path, with_thumbnails=False)
    raise HTTPException(404, f"no prompts for {date}")
