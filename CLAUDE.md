# Ambiverse Studio — Project Notes for Claude

Local web app (FastAPI + React) that is **mission control for the Ambiverse YouTube pipeline** at `~/myFolder/Programming/animembient/`. Read **PLAN.md** (architecture, feature census, milestones) before building anything. Read `animembient/CLAUDE.md` to understand the pipeline being wrapped.

## Git — commit & push after every change (standing rule; don't wait to be asked)

After completing any code change, **automatically `git commit` + `git push origin main`** with a descriptive message ending `Co-Authored-By: Claude <noreply@anthropic.com>`.
- Stage files explicitly (`git add <files>`) — never `git add -A`.
- **Never commit:** `.env`, `data/` (sqlite/logs/thumb cache), `node_modules/`, `venv*/`, `web/dist/`, any token/secret file. Verify staged list before committing.

## Core principles (from PLAN.md — do not drift)

1. **Wrap, don't rewrite.** The app spawns animembient's existing scripts (with their own venv interpreters + env vars) as subprocess jobs. Never duplicate pipeline logic. Never edit the animembient repo from sessions in this repo unless explicitly asked.
2. **Localhost only.** Bind 127.0.0.1. No auth, no deploy. Secrets/tokens: status only, never contents.
3. **Read-only first, actions second.** Destructive ops = confirm + move to trash, never `rm`.
4. **Single-flight heavy jobs** (16 GB RAM): one render at a time; wrap in `caffeinate -dimsu`; spawn with `start_new_session=True`; cancel kills the **process group**.

## Environment

- **Ports:** API **4700**, Vite dev **5175** (8501 = trading dashboard, 5174 = wishplace — don't collide).
- `.env`: `ANIMEMBIENT_DIR` (default `~/myFolder/Programming/animembient`), `DOWNLOADS_DIR`, `PORT`.
- Server venv: `server/venv`, Python ≥3.12. Frontend: Vite + React + TS + Tailwind, dark theme.
- `.claude/launch.json` name **"studio"** for the preview tool.

## Hard constraints

- **NO Russian** in any output, ever (Ukrainian + any other language OK).
- This app must never write into animembient's folders except via its scripts (it reads folders + spawns jobs only).
