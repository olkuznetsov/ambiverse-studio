# Ambiverse Studio — Project Notes for Claude

Local web app (FastAPI + React) that is **mission control for the Ambiverse YouTube pipeline** at `~/myFolder/Programming/animembient/`. Read **docs/PLAN.md** (architecture, feature census, milestones) before building anything. Read `animembient/CLAUDE.md` to understand the pipeline being wrapped.

## Cross-session coordination — read HANDOFF.md first

A **separate "pipeline" session** works on the animembient repo this app wraps. When it changes the pipeline (new script/knob/renamed function), it logs an entry in **`HANDOFF.md`** describing what changed and what the studio should do. **At the start of a session, read `HANDOFF.md`** for unresolved entries; apply what's relevant, then mark them `✅ DONE (studio)` with the commit hash. If you (studio session) change something the pipeline session should know, add an entry there too. Since Studio *wraps* the pipeline (runs its code as subprocesses), most pipeline fixes are picked up automatically — HANDOFF entries are mostly "new capability to surface" or "a function you call changed."

## Git — commit & push after every change (standing rule; don't wait to be asked)

After completing any code change, **automatically `git commit` + `git push origin main`** with a descriptive message ending `Co-Authored-By: Claude <noreply@anthropic.com>`.
- Stage files explicitly (`git add <files>`) — never `git add -A`.
- **Never commit:** `.env`, `data/` (sqlite/logs/thumb cache), `node_modules/`, `venv*/`, `web/dist/`, any token/secret file. Verify staged list before committing.

## Core principles (from PLAN.md — do not drift)

1. **Wrap, don't rewrite.** The app spawns animembient's existing scripts (with their own venv interpreters + env vars) as subprocess jobs. Never duplicate pipeline logic. Never edit the animembient repo from sessions in this repo unless explicitly asked.
2. **Localhost only.** Bind 127.0.0.1. No auth, no deploy. Secrets/tokens: status only, never contents.
3. **Read-only first, actions second.** Destructive ops = confirm + move to trash, never `rm`.
4. **Single-flight heavy jobs** (16 GB RAM): one render at a time; wrap in `caffeinate -dimsu`; spawn with `start_new_session=True`; cancel kills the **process group**.

## Status (Oct 2026)

The channel is on hiatus; the repo is public and is a **portfolio piece** (LinkedIn Featured). Keep it working for visitors first: `make demo` must run on a fresh clone with no `.env`. The pipeline gained features after Jul 26 2026 (publish_queue, Omni Flash) that the studio doesn't surface — fine while paused.

## Modes, tests, tooling

- **Real mode:** `ANIMEMBIENT_DIR` set in `.env`. A set-but-wrong path must fail loudly — never fall back to demo silently.
- **Demo mode:** `STUDIO_DEMO=1` or `ANIMEMBIENT_DIR` unset. `server/demo_seed.py` copies the stand-in pipeline `demo/pipeline/` into `data/demo/pipeline/` and generates assets. The stand-ins must print the **same log markers** as the real scripts (progress.py parses them) — when a parser changes, change the stand-in too. Channel data in demo = `demo/fixtures/channel_snapshot.json` (frozen real snapshot). Reset: `make demo-reset`.
- **Before committing:** `make test` (pytest in demo mode + web lint/typecheck/build). CI runs the same on every push.
- **Fixtures go public:** read them fully before committing (no tokens, no emails); never print local absolute paths in demo output — logs and screenshots show `~/…`.
- **Metrics:** compare retention/AVD over long-form only (Shorts loop, view % can pass 100); label inferred attribution as inferred.

## Environment

- **Ports:** API **4700**, Vite dev **5175**, demo-mode preview **4701** (8501 = trading dashboard, 5174 = wishplace — don't collide).
- `.env`: `ANIMEMBIENT_DIR`, `DOWNLOADS_DIR`, `PIPELINE_PYTHON`, `STUDIO_DEMO`, `PORT` — see `.env.example`.
- Server venv: `server/venv`, Python ≥3.12. Frontend: Vite + React + TS + Tailwind, dark theme.
- Preview tool configs live in the **parent** folder's `.claude/launch.json`: **"studio"** (real, :4700, reload), **"studio-web"** (Vite :5175), **"studio-demo"** (demo, :4701, serves `web/dist` — rebuild it after UI changes).
- Planning docs: `docs/PLAN.md` (milestones), `docs/IDEAS.md` (roadmap).

## Hard constraints

- **NO Russian** in any output, ever (Ukrainian + any other language OK).
- This app must never write into animembient's folders except via its scripts (it reads folders + spawns jobs only).
