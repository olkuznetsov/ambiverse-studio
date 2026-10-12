"""Studio configuration — reads this repo's .env and imports the pipeline's config.

The pipeline (a separate repo, working name "animembient") is a dependency: we
import its config.py (pure constants) to get THEMES, MIN_IMAGES_PER_THEME and
folder paths, so the dashboard always reflects what the pipeline itself would do.

Two modes:
- real — ANIMEMBIENT_DIR points at the pipeline repo; jobs run its scripts.
- demo — STUDIO_DEMO=1, or ANIMEMBIENT_DIR unset (a fresh clone). A stand-in
  pipeline from demo/pipeline/ plus generated sample assets is seeded into
  data/demo/, so every page and job type works without keys or the private repo.
"""
import importlib.util
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

STUDIO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(STUDIO_ROOT / ".env")


def _flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


_configured_dir = os.getenv("ANIMEMBIENT_DIR", "").strip()
DEMO = _flag("STUDIO_DEMO") or not _configured_dir

_data_root = Path(os.getenv("STUDIO_DATA_DIR") or STUDIO_ROOT / "data").expanduser().resolve()
if DEMO:
    DATA_DIR = _data_root / "demo"  # kept apart from real job history/caches
    ANIMEMBIENT_DIR = DATA_DIR / "pipeline"
    DOWNLOADS_DIR = DATA_DIR / "downloads"
    PIPELINE_PYTHON = sys.executable  # the stand-in scripts need only stdlib + Pillow
else:
    DATA_DIR = _data_root
    ANIMEMBIENT_DIR = Path(_configured_dir).expanduser().resolve()
    DOWNLOADS_DIR = Path(os.getenv("DOWNLOADS_DIR", "~/Downloads")).expanduser()
    PIPELINE_PYTHON = os.getenv("PIPELINE_PYTHON") or str(ANIMEMBIENT_DIR / "venv" / "bin" / "python")

PORT = int(os.getenv("PORT", "4700"))
THUMBS_DIR = DATA_DIR / "thumbs"
JOB_LOGS_DIR = DATA_DIR / "logs"
for _d in (DATA_DIR, THUMBS_DIR, JOB_LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

if DEMO:
    import demo_seed

    demo_seed.ensure_seeded(STUDIO_ROOT, DATA_DIR)


def _load_pipeline_config():
    cfg_path = ANIMEMBIENT_DIR / "config.py"
    if not cfg_path.exists():
        raise RuntimeError(
            f"ANIMEMBIENT_DIR={ANIMEMBIENT_DIR} has no config.py. Point it at the "
            "pipeline repo — or unset it (or set STUDIO_DEMO=1) to explore with demo data."
        )
    spec = importlib.util.spec_from_file_location("animembient_config", cfg_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["animembient_config"] = mod
    spec.loader.exec_module(mod)  # pure constants + load_dotenv of its own .env
    return mod


PIPELINE = _load_pipeline_config()
