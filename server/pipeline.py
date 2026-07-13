"""Inventory readers over the animembient folders.

Everything reads the filesystem fresh on each request (local fs is cheap) —
files dropped in Finder appear on the next request. Only expensive derived
data (audio durations) is cached, keyed by path+mtime.
"""
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from config import ANIMEMBIENT_DIR, DATA_DIR, PIPELINE

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac"}
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv"}

IMAGES_DIR = ANIMEMBIENT_DIR / "images"
USED_IMAGES_DIR = IMAGES_DIR / "used"
MUSIC_LIBRARY_DIR = ANIMEMBIENT_DIR / "music" / "library"
MUSIC_USED_DIR = ANIMEMBIENT_DIR / "music" / "used"
OUTPUT_DIR = ANIMEMBIENT_DIR / "output"
VEO_SLOW_DIR = OUTPUT_DIR / "veo_slow"
THEME_HISTORY = ANIMEMBIENT_DIR / "logs" / "theme_history.json"

_DURATIONS_CACHE = DATA_DIR / "durations.json"


def _rel(p: Path) -> str:
    return str(p.relative_to(ANIMEMBIENT_DIR))


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _files(folder: Path, exts: set[str]) -> list[Path]:
    if not folder.is_dir():
        return []
    return sorted(
        (p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in exts),
        key=lambda p: p.name.lower(),
    )


# ---------- audio durations (ffprobe, cached by path+mtime) ----------

def _load_duration_cache() -> dict:
    try:
        return json.loads(_DURATIONS_CACHE.read_text())
    except (OSError, ValueError):
        return {}


def _probe_duration(path: Path) -> float | None:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=15,
        )
        return round(float(out.stdout.strip()), 1)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return None


def durations_for(paths: list[Path]) -> dict[str, float | None]:
    """Durations in seconds for each path; cached across restarts."""
    cache = _load_duration_cache()
    result, dirty = {}, False
    for p in paths:
        rel = _rel(p)
        key = f"{rel}:{int(p.stat().st_mtime)}"
        if key not in cache:
            cache[key] = _probe_duration(p)
            dirty = True
        result[rel] = cache[key]
    if dirty:
        # prune entries whose file/mtime is gone so the cache can't grow forever
        live = {f"{_rel(p)}:{int(p.stat().st_mtime)}" for p in paths}
        stale = [k for k in cache if k.split(":", 1)[0].startswith("music/") and k not in live]
        for k in stale:
            del cache[k]
        _DURATIONS_CACHE.write_text(json.dumps(cache))
    return result


# ---------- themes ----------

def _theme_history() -> dict[str, str]:
    try:
        return json.loads(THEME_HISTORY.read_text())
    except (OSError, ValueError):
        return {}


def _find_thumb(theme_dir: Path) -> Path | None:
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        p = theme_dir / f"thumb{ext}"
        if p.exists():
            return p
    return None


def theme_images(theme: str) -> list[dict]:
    """Unused images for a theme (excludes thumb.* — never picked as a scene)."""
    theme_dir = IMAGES_DIR / theme
    out = []
    for p in _files(theme_dir, IMAGE_EXTS):
        if p.stem.lower() == "thumb":
            continue
        st = p.stat()
        out.append({
            "name": p.name,
            "path": _rel(p),
            "size": st.st_size,
            "mtime": _iso(st.st_mtime),
        })
    return out


def theme_summaries() -> list[dict]:
    history = _theme_history()
    min_images = PIPELINE.MIN_IMAGES_PER_THEME
    out = []
    for key, info in PIPELINE.THEMES.items():
        images = theme_images(key)
        thumb = _find_thumb(IMAGES_DIR / key)
        out.append({
            "key": key,
            "title": info.get("motif") or key.replace("-", " ").title(),
            "description": info["description"],
            "image_count": len(images),
            "min_images": min_images,
            "eligible": len(images) >= min_images,
            "has_custom_thumb": thumb is not None,
            "thumb_path": _rel(thumb) if thumb else None,
            "last_video": history.get(key),
            "preview_paths": [img["path"] for img in images[:4]],
        })
    return out


# ---------- music ----------

def music_inventory(*, with_durations: bool = True) -> dict:
    lib_files = _files(MUSIC_LIBRARY_DIR, AUDIO_EXTS)
    used_files = _files(MUSIC_USED_DIR, AUDIO_EXTS)
    durs = durations_for(lib_files) if with_durations else {}

    def entry(p: Path) -> dict:
        st = p.stat()
        return {
            "name": p.name,
            "path": _rel(p),
            "size": st.st_size,
            "mtime": _iso(st.st_mtime),
            "duration": durs.get(_rel(p)),
        }

    library = [entry(p) for p in lib_files]
    known = [t["duration"] for t in library if t["duration"]]
    return {
        "library": library,
        "library_count": len(lib_files),
        "library_minutes": round(sum(known) / 60, 1) if known else 0,
        "used_count": len(used_files),
    }


def used_music(*, with_durations: bool = False) -> list[dict]:
    files = _files(MUSIC_USED_DIR, AUDIO_EXTS)
    durs = durations_for(files) if with_durations else {}
    return [
        {
            "name": p.name,
            "path": _rel(p),
            "size": p.stat().st_size,
            "duration": durs.get(_rel(p)),
        }
        for p in files
    ]


# ---------- veo bank ----------

def veo_bank() -> list[dict]:
    """Cached slowed Veo clips in output/veo_slow/ — the reusable clip library."""
    clips = []
    for p in _files(VEO_SLOW_DIR, VIDEO_EXTS):
        st = p.stat()
        clips.append({
            "name": p.name,
            "path": _rel(p),
            "size": st.st_size,
            "mtime": _iso(st.st_mtime),
            "enhanced": "_1440p" in p.stem or "_2160p" in p.stem,
        })
    return clips


# ---------- tokens / disk ----------

def token_status() -> list[dict]:
    """Presence + age only — token contents are never read or served."""
    tokens = [
        ("upload", "youtube_token.json", "YouTube upload (Data API)"),
        ("analytics", "youtube_analytics_token.json", "YouTube Analytics (read-only)"),
        ("client_secret", "client_secret.json", "OAuth app credentials"),
    ]
    out = []
    for key, fname, label in tokens:
        p = ANIMEMBIENT_DIR / fname
        exists = p.exists()
        out.append({
            "key": key,
            "label": label,
            "present": exists,
            "mtime": _iso(p.stat().st_mtime) if exists else None,
        })
    return out


def disk_free() -> dict:
    usage = shutil.disk_usage(ANIMEMBIENT_DIR)
    return {
        "free_gb": round(usage.free / 1e9, 1),
        "total_gb": round(usage.total / 1e9, 1),
        "used_pct": round(usage.used / usage.total * 100),
    }


# ---------- composed dashboard payload ----------

def overview() -> dict:
    import jobs as jobs_engine

    used_count = len([p for p in _files(USED_IMAGES_DIR, IMAGE_EXTS)])
    return {
        "jobs": jobs_engine.running_summary(),
        "themes": theme_summaries(),
        "music": music_inventory(),
        "veo_bank": veo_bank(),
        "tokens": token_status(),
        "disk": disk_free(),
        "used_images_count": used_count,
        "animembient_dir": str(ANIMEMBIENT_DIR),
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
    }
