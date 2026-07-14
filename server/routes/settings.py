"""Settings — read-only view of paths, pipeline knob defaults, token status,
and the theme registry (rendered from config.THEMES). No writes in v1: the
pipeline's .env / config.py stay the source of truth, edited in the editor.
"""
from fastapi import APIRouter

import pipeline
from config import ANIMEMBIENT_DIR, DATA_DIR, DOWNLOADS_DIR, PIPELINE, PORT, STUDIO_ROOT

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _get(name: str, default=None):
    return getattr(PIPELINE, name, default)


@router.get("")
def settings():
    return {
        "paths": {
            "animembient_dir": str(ANIMEMBIENT_DIR),
            "downloads_dir": str(DOWNLOADS_DIR),
            "studio_root": str(STUDIO_ROOT),
            "data_dir": str(DATA_DIR),
            "pipeline_config": str(ANIMEMBIENT_DIR / "config.py"),
            "depthflow_python": str(_get("DEPTHFLOW_PYTHON", "")),
        },
        "ports": {"api": PORT, "vite_dev": 5175},
        "defaults": [
            {"key": "VIDEO_DURATION_SECONDS", "value": _get("VIDEO_DURATION_SECONDS"), "note": "full build length (7200 = 2h)"},
            {"key": "NUM_IMAGES_PER_VIDEO", "value": _get("NUM_IMAGES_PER_VIDEO"), "note": "0 = use all available"},
            {"key": "MIN_IMAGES_PER_THEME", "value": _get("MIN_IMAGES_PER_THEME"), "note": "eligibility gate"},
            {"key": "MAX_IMAGES_PER_VIDEO", "value": _get("MAX_IMAGES_PER_VIDEO"), "note": "safety cap"},
            {"key": "MUSIC_MODE", "value": _get("MUSIC_MODE"), "note": "library | auto | silent"},
            {"key": "RENDER_PRESET", "value": _get("RENDER_PRESET"), "note": "x264 preset"},
            {"key": "RENDER_CRF", "value": _get("RENDER_CRF"), "note": "quality (lower = better)"},
            {"key": "RENDER_WORKERS", "value": _get("RENDER_WORKERS"), "note": "1 = sequential (geq saturates cores)"},
            {"key": "VEO_TARGET_H", "value": _get("VEO_TARGET_H"), "note": "upscale target height"},
            {"key": "VEO_SLOWDOWN", "value": _get("VEO_SLOWDOWN"), "note": "4 = 0.25x speed"},
            {"key": "DEPTHFLOW_LOOP_SECONDS", "value": _get("DEPTHFLOW_LOOP_SECONDS"), "note": "2.5D loop length"},
        ],
        "tokens": pipeline.token_status(),
        "themes": [
            {
                "key": key,
                "title": info.get("motif") or key.replace("-", " ").title(),
                "description": info.get("description", ""),
                "style_notes": info.get("style_notes", ""),
                "custom_style": bool(info.get("base_style")),
            }
            for key, info in PIPELINE.THEMES.items()
        ],
    }
