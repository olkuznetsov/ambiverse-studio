import json
import shutil
import time
from collections import Counter
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from PIL import Image

import pipeline
from config import ANIMEMBIENT_DIR, DATA_DIR, PIPELINE
from media import safe_path

router = APIRouter(prefix="/api", tags=["assets"])

TRASH_DIR = DATA_DIR / "trash"


class PathBody(BaseModel):
    path: str


@router.get("/themes")
def themes():
    return pipeline.theme_summaries()


@router.get("/themes/{theme}/images")
def theme_images(theme: str):
    if theme not in PIPELINE.THEMES:
        raise HTTPException(404, f"unknown theme: {theme}")
    images = pipeline.theme_images(theme)

    # display-time warnings, never blockers (validation stays out of the way)
    stem_counts = Counter(i["name"].rsplit(".", 1)[0].lower() for i in images)
    for img in images:
        warnings = []
        try:
            with Image.open(ANIMEMBIENT_DIR / img["path"]) as im:
                w, h = im.size
            img["width"], img["height"] = w, h
            if h > w:
                warnings.append("portrait — will be center-cropped in the render")
            elif w / h < 1.5:
                warnings.append(f"aspect {w}:{h} — not ~16:9, edges will crop")
            if w < 1280:
                warnings.append(f"low resolution ({w}px wide)")
        except OSError:
            img["width"] = img["height"] = None
            warnings.append("unreadable image file")
        if stem_counts[img["name"].rsplit(".", 1)[0].lower()] > 1:
            warnings.append("duplicate name (different extension)")
        img["warnings"] = warnings

    return {
        "theme": theme,
        "images": images,
        "min_images": PIPELINE.MIN_IMAGES_PER_THEME,
    }


@router.get("/music")
def music():
    inv = pipeline.music_inventory()
    inv["used"] = pipeline.used_music()
    return inv


@router.get("/veo/bank")
def veo_bank():
    return pipeline.veo_bank()


@router.get("/outputs")
def outputs():
    return pipeline.outputs()


@router.get("/assets/used-images")
def used_images(limit: int = 48):
    return pipeline.used_images(limit)


@router.post("/assets/trash")
def trash(body: PathBody):
    """Safe delete: move the file into the studio's data/trash/ (never rm).
    A manifest line records the original path for manual recovery."""
    src = safe_path(body.path)
    TRASH_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    dest = TRASH_DIR / f"{stamp}__{src.name}"
    n = 1
    while dest.exists():
        dest = TRASH_DIR / f"{stamp}__{n}__{src.name}"
        n += 1
    shutil.move(str(src), dest)
    with open(TRASH_DIR / "manifest.jsonl", "a") as f:
        f.write(json.dumps({"trashed_at": stamp, "original": str(src),
                            "trash_name": dest.name}) + "\n")
    return {"ok": True, "trashed_to": str(dest)}


@router.post("/assets/set-thumb")
def set_thumb(body: PathBody):
    """Copy an image to images/<theme>/thumb.<ext> — main.py then uses it as
    the custom thumbnail for that theme's next build (and moves it to used/)."""
    src = safe_path(body.path)
    rel = Path(body.path)
    if len(rel.parts) != 3 or rel.parts[0] != "images" or rel.parts[1] not in PIPELINE.THEMES:
        raise HTTPException(400, "image must live in images/<theme>/")
    theme_dir = ANIMEMBIENT_DIR / "images" / rel.parts[1]
    for ext in (".png", ".jpg", ".jpeg", ".webp"):  # replace an existing thumb
        old = theme_dir / f"thumb{ext}"
        if old.exists():
            trash(PathBody(path=str(old.relative_to(ANIMEMBIENT_DIR))))
    dest = theme_dir / f"thumb{src.suffix.lower()}"
    shutil.copy2(src, dest)
    return {"ok": True, "thumb": str(dest.relative_to(ANIMEMBIENT_DIR))}
