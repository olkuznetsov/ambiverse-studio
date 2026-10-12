"""Demo stand-in for the pipeline's config.py.

Same constants the studio reads from the real one — the theme registry and
defaults are the real values (theme_registry.json), only the paths point at
this demo folder.
"""
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
IMAGES_DIR = BASE_DIR / "images"
USED_DIR = IMAGES_DIR / "used"
MUSIC_DIR = BASE_DIR / "music"
MUSIC_LIBRARY_DIR = MUSIC_DIR / "library"
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"

_registry = json.loads((BASE_DIR / "theme_registry.json").read_text())
THEMES = _registry["THEMES"]
BASE_STYLE_PROMPT = _registry["BASE_STYLE_PROMPT"]
MIN_IMAGES_PER_THEME = _registry["MIN_IMAGES_PER_THEME"]
VIDEO_DURATION_SECONDS = _registry["VIDEO_DURATION_SECONDS"]
NUM_IMAGES_PER_VIDEO = _registry["NUM_IMAGES_PER_VIDEO"]
MAX_IMAGES_PER_VIDEO = _registry["MAX_IMAGES_PER_VIDEO"]
MUSIC_MODE = _registry["MUSIC_MODE"]
RENDER_PRESET = _registry["RENDER_PRESET"]
RENDER_CRF = _registry["RENDER_CRF"]
RENDER_WORKERS = 1
VEO_TARGET_H = _registry["VEO_TARGET_H"]
VEO_SLOWDOWN = _registry["VEO_SLOWDOWN"]
DEPTHFLOW_LOOP_SECONDS = _registry["DEPTHFLOW_LOOP_SECONDS"]
DEPTHFLOW_PYTHON = sys.executable  # DepthFlow is simulated — any interpreter "exists"
