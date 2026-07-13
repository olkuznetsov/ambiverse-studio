# Ambiverse Studio

Local mission-control app for the [Ambiverse](https://www.youtube.com/@ambiverseworlds) YouTube ambient pipeline (`~/myFolder/Programming/animembient/`).

One UI to see pipeline state (images / music / Veo clip bank / tokens), generate prompts, run builds (Ken Burns · DepthFlow · Veo living-world), watch render jobs live, and track channel stats — instead of ~20 CLI scripts and env vars.

**Status:** M0–M3 done — **daily driver reached**: Dashboard, Assets, jobs, Prompts, and Build wizards (main + Veo) live; routine ops no longer need the CLI. See **[PLAN.md](PLAN.md)**. Next: M4 outputs browser + Shorts builder.

## Run

```bash
# API (port 4700)
server/venv/bin/uvicorn app:app --app-dir server --port 4700 --reload
# Web dev server (port 5175, proxies /api -> 4700)
npm run dev --prefix web
```

- Stack: FastAPI (localhost:4700) + React/Vite/TS (dev :5175)
- The pipeline repo is a dependency (path via `.env`), never modified from here.
