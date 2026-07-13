"""Ambiverse Studio API — mission control for the animembient pipeline.

Dev:  uvicorn app:app --app-dir server --port 4700 --reload  (Vite on 5175 proxies /api)
Prod: same process also serves web/dist on 4700 when it exists.
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import media
from config import ANIMEMBIENT_DIR, STUDIO_ROOT
from routes import assets, state

app = FastAPI(title="Ambiverse Studio", version="0.1.0")

app.include_router(state.router)
app.include_router(assets.router)
app.include_router(media.router)


@app.get("/api/health")
def health():
    return {"ok": True, "animembient_dir": str(ANIMEMBIENT_DIR)}


# serve the built SPA in prod mode (web/dist present); dev uses Vite on 5175
_dist = STUDIO_ROOT / "web" / "dist"
if _dist.is_dir():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="spa-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        candidate = _dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_dist / "index.html")
