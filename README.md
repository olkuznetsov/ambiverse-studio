# Ambiverse Studio

Local mission-control app for the [Ambiverse](https://www.youtube.com/@ambiverseworlds) YouTube ambient pipeline (`~/myFolder/Programming/animembient/`).

One UI to see pipeline state (images / music / Veo clip bank / tokens), generate prompts, run builds (Ken Burns · DepthFlow · Veo living-world), watch render jobs live, and track channel stats — instead of ~20 CLI scripts and env vars.

**Status:** M0–M2 done (Dashboard, Assets, job engine, Jobs + Prompts pages live) — see **[PLAN.md](PLAN.md)**. Next: M3 build wizards (daily driver).

## Run

```bash
# API (port 4700)
server/venv/bin/uvicorn app:app --app-dir server --port 4700 --reload
# Web dev server (port 5175, proxies /api -> 4700)
npm run dev --prefix web
```

- Stack: FastAPI (localhost:4700) + React/Vite/TS (dev :5175)
- The pipeline repo is a dependency (path via `.env`), never modified from here.
