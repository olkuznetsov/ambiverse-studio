# Ambiverse Studio

Local mission-control app for the [Ambiverse](https://www.youtube.com/@ambiverseworlds) YouTube ambient pipeline (`~/myFolder/Programming/animembient/`).

One UI to see pipeline state (images / music / Veo clip bank / tokens), generate prompts, run builds (Ken Burns · DepthFlow · Veo living-world), watch render jobs live, and track channel stats — instead of ~20 CLI scripts and env vars.

**Status:** planning — see **[PLAN.md](PLAN.md)** for the full architecture, feature census, and milestones.

- Stack: FastAPI (localhost:4700) + React/Vite/TS (dev :5175)
- The pipeline repo is a dependency (path via `.env`), never modified from here.
