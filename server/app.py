"""Ambiverse Studio API — mission control for the animembient pipeline.

Dev:  uvicorn app:app --app-dir server --port 4700 --reload  (Vite on 5175 proxies /api)
Prod: same process also serves web/dist on 4700 when it exists.
"""
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

import jobs as jobs_engine
import media
from config import ANIMEMBIENT_DIR, DEMO, STUDIO_ROOT
from routes import assets, build, channel, jobs, prompts, settings, state


@asynccontextmanager
async def lifespan(_app: FastAPI):
    jobs_engine.start_worker()
    yield


app = FastAPI(title="Ambiverse Studio", version="1.0.0", lifespan=lifespan)

# The server binds 127.0.0.1, but a hostile web page can still reach it through
# DNS rebinding (its own domain re-resolved to 127.0.0.1 = same-origin reads).
# Accepting only local Host headers closes that door.
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=os.getenv("STUDIO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(","),
)

app.include_router(state.router)
app.include_router(assets.router)
app.include_router(media.router)
app.include_router(jobs.router)
app.include_router(prompts.router)
app.include_router(build.router)
app.include_router(channel.router)
app.include_router(settings.router)


@app.get("/api/health")
def health():
    return {"ok": True, "demo": DEMO, "animembient_dir": str(ANIMEMBIENT_DIR)}


def resolve_spa_file(dist: Path, full_path: str) -> Path:
    """File to serve for a client-side route: a real file inside `dist`, else the
    SPA's index.html. Resolving first means `../` (raw or %2e-encoded) can never
    reach outside `dist` — e.g. the pipeline's .env or OAuth tokens."""
    if full_path:
        candidate = (dist / full_path).resolve()
        if candidate.is_relative_to(dist) and candidate.is_file():
            return candidate
    return dist / "index.html"


# serve the built SPA in prod mode (web/dist present); dev uses Vite on 5175
_dist = (STUDIO_ROOT / "web" / "dist").resolve()
if _dist.is_dir():
    app.mount("/assets", StaticFiles(directory=_dist / "assets"), name="spa-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path == "api" or full_path.startswith("api/"):
            raise HTTPException(404, f"no API route /{full_path}")
        return FileResponse(resolve_spa_file(_dist, full_path))
