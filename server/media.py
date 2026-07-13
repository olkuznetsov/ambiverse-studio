"""Media serving: cached thumbnails (Pillow), video poster frames (ffmpeg),
and range-enabled file serving for <audio>/<video> playback.

Path safety: only files inside ANIMEMBIENT_DIR with a media extension are
served — .json/.env/tokens can never leave the machine through this API.
"""
import hashlib
import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse
from PIL import Image, ImageOps

from config import ANIMEMBIENT_DIR, THUMBS_DIR
from pipeline import AUDIO_EXTS, IMAGE_EXTS, VIDEO_EXTS

router = APIRouter(prefix="/api/media", tags=["media"])

SERVABLE_EXTS = IMAGE_EXTS | AUDIO_EXTS | VIDEO_EXTS


def safe_path(rel: str) -> Path:
    p = (ANIMEMBIENT_DIR / rel).resolve()
    if not p.is_relative_to(ANIMEMBIENT_DIR):
        raise HTTPException(400, "path escapes the pipeline directory")
    if p.suffix.lower() not in SERVABLE_EXTS:
        raise HTTPException(400, f"extension {p.suffix!r} is not servable")
    if not p.is_file():
        raise HTTPException(404, f"not found: {rel}")
    return p


def _cache_key(p: Path, *parts) -> Path:
    raw = ":".join([str(p), str(int(p.stat().st_mtime)), *map(str, parts)])
    return THUMBS_DIR / (hashlib.sha1(raw.encode()).hexdigest() + ".jpg")


@router.get("/img")
def image_thumbnail(path: str, size: int = Query(480, ge=64, le=2048)):
    """Downscaled JPEG thumbnail, cached by path+mtime+size."""
    src = safe_path(path)
    if src.suffix.lower() not in IMAGE_EXTS:
        raise HTTPException(400, "not an image")
    cached = _cache_key(src, size)
    if not cached.exists():
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im)
            im.thumbnail((size, size * 4))  # cap width; keep tall images sane
            im.convert("RGB").save(cached, "JPEG", quality=85)
    return FileResponse(cached, media_type="image/jpeg",
                        headers={"Cache-Control": "max-age=86400"})


@router.get("/vthumb")
def video_thumbnail(path: str, size: int = Query(480, ge=64, le=2048)):
    """Poster frame for a video clip, cached by path+mtime+size."""
    src = safe_path(path)
    if src.suffix.lower() not in VIDEO_EXTS:
        raise HTTPException(400, "not a video")
    cached = _cache_key(src, size, "poster")
    if not cached.exists():
        proc = subprocess.run(
            ["ffmpeg", "-y", "-ss", "1", "-i", str(src), "-frames:v", "1",
             "-vf", f"scale={size}:-2", str(cached)],
            capture_output=True, timeout=30,
        )
        if proc.returncode != 0 or not cached.exists():
            raise HTTPException(500, "poster frame extraction failed")
    return FileResponse(cached, media_type="image/jpeg",
                        headers={"Cache-Control": "max-age=86400"})


@router.get("/file")
def media_file(path: str):
    """Full media file; starlette FileResponse handles HTTP Range for seeking."""
    src = safe_path(path)
    return FileResponse(src, filename=src.name)
