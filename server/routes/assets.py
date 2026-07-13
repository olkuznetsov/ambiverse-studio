from collections import Counter

from fastapi import APIRouter, HTTPException
from PIL import Image

import pipeline
from config import ANIMEMBIENT_DIR, PIPELINE

router = APIRouter(prefix="/api", tags=["assets"])


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
