"""Studio configuration — reads this repo's .env and imports the pipeline's config.

The animembient repo is a dependency: we import its config.py (pure constants)
to get THEMES, MIN_IMAGES_PER_THEME and folder paths, so the dashboard always
reflects what the pipeline itself would do.
"""
import importlib.util
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

STUDIO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(STUDIO_ROOT / ".env")

ANIMEMBIENT_DIR = Path(
    os.getenv("ANIMEMBIENT_DIR", "~/myFolder/Programming/animembient")
).expanduser().resolve()
DOWNLOADS_DIR = Path(os.getenv("DOWNLOADS_DIR", "~/Downloads")).expanduser()
PORT = int(os.getenv("PORT", "4700"))

DATA_DIR = STUDIO_ROOT / "data"
THUMBS_DIR = DATA_DIR / "thumbs"
JOB_LOGS_DIR = DATA_DIR / "logs"
for _d in (DATA_DIR, THUMBS_DIR, JOB_LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def _load_pipeline_config():
    cfg_path = ANIMEMBIENT_DIR / "config.py"
    if not cfg_path.exists():
        raise RuntimeError(
            f"animembient config not found at {cfg_path} — check ANIMEMBIENT_DIR in .env"
        )
    spec = importlib.util.spec_from_file_location("animembient_config", cfg_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["animembient_config"] = mod
    spec.loader.exec_module(mod)  # pure constants + load_dotenv of its own .env
    return mod


PIPELINE = _load_pipeline_config()
