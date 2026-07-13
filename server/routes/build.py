"""Build-wizard support: read-only preflight + Veo source scanning.

Preflight mirrors main.preflight()'s checks without importing the pipeline —
the pipeline still runs its own real preflight at job start; this one exists
so the wizard can warn BEFORE queueing a 3.5-hour render.
"""
import os
import shutil

from fastapi import APIRouter

import pipeline
from config import ANIMEMBIENT_DIR, DOWNLOADS_DIR, PIPELINE

router = APIRouter(prefix="/api", tags=["build"])


@router.get("/build/preflight")
def preflight(upload: bool = False, music_mode: str = "library", animate: str = ""):
    checks = []

    def check(ok: bool, label: str, detail: str = ""):
        checks.append({"ok": ok, "label": label, "detail": detail})

    themes = [t for t in pipeline.theme_summaries() if t["eligible"]]
    check(
        bool(themes),
        "Eligible theme (≥{} images)".format(PIPELINE.MIN_IMAGES_PER_THEME),
        ", ".join(f"{t['title']} ({t['image_count']})" for t in themes)
        or "no theme has enough unused images — drop more into images/<theme>/",
    )

    if music_mode == "library":
        inv = pipeline.music_inventory(with_durations=True)
        check(
            inv["library_count"] > 0,
            "Music library",
            f"{inv['library_count']} tracks · {inv['library_minutes']} min banked"
            if inv["library_count"]
            else "music/library/ is empty — drop Suno tracks in, or use silent mode",
        )
    else:
        check(True, "Music", f"mode: {music_mode} (no library needed)")

    check(bool(os.environ.get("GROQ_API_KEY")), "GROQ_API_KEY",
          "set" if os.environ.get("GROQ_API_KEY") else "missing from animembient/.env — metadata generation will fail")

    check((ANIMEMBIENT_DIR / "client_secret.json").exists(), "OAuth client secret",
          "client_secret.json present" if (ANIMEMBIENT_DIR / "client_secret.json").exists() else "missing")

    if upload:
        tok = (ANIMEMBIENT_DIR / "youtube_token.json").exists()
        check(tok, "YouTube upload token",
              "present" if tok else "missing — run auth_youtube.py first or disable upload")

    free_gb = shutil.disk_usage(ANIMEMBIENT_DIR).free / 1024**3
    check(free_gb > 5, "Disk space", f"{free_gb:.1f} GB free (need >5)")

    if animate == "depthflow":
        df_python = getattr(PIPELINE, "DEPTHFLOW_PYTHON", "")
        ok = bool(df_python) and os.path.exists(df_python)
        check(ok, "DepthFlow venv",
              df_python if ok else f"interpreter not found: {df_python}")

    return {"ok": all(c["ok"] for c in checks), "checks": checks}


@router.get("/veo/sources")
def veo_sources():
    """Raw Veo exports in Downloads + whether each is already banked (cached
    slow-mo exists for its position, matching build_veo.py's naming)."""
    sources = sorted(DOWNLOADS_DIR.glob("Untitled video*.mp4"))
    slow_dir = ANIMEMBIENT_DIR / "output" / "veo_slow"
    out = []
    for i, p in enumerate(sources, 1):
        st = p.stat()
        cached = [h for h in (1080, 1440, 2160) if (slow_dir / f"veo_{i:02d}_{h}p.mp4").exists()]
        out.append({
            "name": p.name,
            "index": i,
            "size": st.st_size,
            "mtime": st.st_mtime,
            "cached_heights": cached,
        })
    return {"downloads_dir": str(DOWNLOADS_DIR), "sources": out, "bank": pipeline.veo_bank()}
