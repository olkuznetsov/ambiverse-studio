# Ambiverse Studio — Plan

**One-liner:** a local web app (mission control) for the Ambiverse YouTube pipeline — see everything, run everything, from one UI instead of ~20 CLI scripts + env vars.

- **Date:** 2026-07-13 · **Status:** M0–M4 shipped 2026-07-14; next M5 (channel analytics: YPP progress, per-video table, theme rollup)
- **Pipeline it drives:** `~/myFolder/Programming/animembient/` (read its `CLAUDE.md` first — Waves 1–11b)
- **This repo:** `~/myFolder/Programming/ambiverse-studio/`

---

## 1. Why (the problem)

The animembient pipeline works, but it has outgrown CLI ergonomics:

- ~20 entry-point scripts, each with env-var knobs (`ANIMATE=depthflow VIDEO_FLAVOR=Rainy python main.py`, `VEO_UPSCALE=1 venv/bin/python build_veo.py`, …). Easy to forget a knob, easy to typo one.
- State is invisible: which themes have enough images? how much music is banked? is a thumb.png dropped? are the OAuth tokens alive? what's scheduled to publish? Today the answer = `ls` + memory.
- Long renders run as background shell jobs with log-tailing (`progress.py`) — no persistent history of runs, exit codes, or what was built with which settings.
- Functionality keeps growing (DepthFlow → Veo → ESRGAN in one month). Every new wave adds scripts + knobs. **The UI is the census** — if it's in the app, it can't be forgotten.

Bonus: a full-stack app that operates an AI media pipeline is a strong portfolio piece for the AI-career transition.

**Honest trade-off:** the app doesn't grow the channel by itself (the channel is reach-limited, not tooling-limited). So: timebox it. Get to the M3 "daily driver" fast, don't gold-plate. Ship videos while building it.

---

## 2. Product shape (decision + alternatives)

**Chosen: local web app.** FastAPI (Python) backend on `127.0.0.1` + React SPA frontend. Backend wraps the existing scripts as subprocess jobs; frontend is a dashboard/control panel in the browser.

Why this beats the alternatives:

| Option | Verdict |
|---|---|
| **FastAPI + React (chosen)** | Python = pipeline's language (imports `config.py` directly). React/TS = Sasha's home turf. Browser gives free image grids, `<video>`/`<audio>` previews, SSE log streaming. |
| Textual TUI | Fast to build, but no image/video previews — dealbreaker for an asset-driven pipeline. |
| Electron/Tauri | Packaging overhead for a single-user localhost tool; browser tab is fine. |
| Streamlit/Gradio | Fastest v0, but poor fit for a persistent job queue + media browser + custom layout; would be rewritten anyway. |

**Guiding principles**

1. **Wrap, don't rewrite.** The app spawns the *existing* scripts with env vars (same as the CLI does). Zero pipeline logic is duplicated. The pipeline stays 100% usable without the app.
2. **Read-only first, actions second.** M1 is a dashboard that only *shows* state — immediately useful, zero risk. Actions (running builds) come after.
3. **Localhost only.** Bind 127.0.0.1. No auth, no deploy, no multi-user. Tokens/secrets never leave the machine and never appear in the UI (status only: valid/expired).
4. **The animembient repo is a dependency, not a submodule.** Path configured via `.env` (`ANIMEMBIENT_DIR=~/myFolder/Programming/animembient`). This repo never edits that repo.
5. **Safe by default.** Destructive ops (delete image) = confirm + move to a `.trash/`, never `rm`. Upload toggles default to OFF/private in wizards.

---

## 3. Feature map (the functionality census)

Derived from every script + knob that exists today (Waves 1–11b). *This table doubles as the "don't miss anything" checklist.*

### Pipeline scripts to surface

| Script | What it does | Key knobs to expose |
|---|---|---|
| `generate_prompts.py` | Daily image+music prompts (Groq) | `MUSIC_SIM_THRESHOLD` |
| `main.py` | Full build: theme pick → music → video → thumbnail → Shorts → upload | `ANIMATE` (ken burns/depthflow), `VIDEO_DURATION_SECONDS`, `NUM_IMAGES_PER_VIDEO`, `VIDEO_FLAVOR`, `MUSIC_MODE`, `YOUTUBE_UPLOAD`, `YOUTUBE_PRIVACY`, `SCHEDULED_PUBLISH_UTC`, `MAKE_SHORTS`, `SHORTS_PER_VIDEO`, `SHORTS_SPACING_DAYS`, `RENDER_PRESET/CRF/WORKERS/SUPERSAMPLE` |
| `veo_slowmo.py` | Veo clip → dedupe → (ESRGAN) → RIFE 0.25× | `VEO_UPSCALE`, `VEO_TARGET_H`, `VEO_SLOWDOWN`, `VEO_CROP` |
| `veo_assemble.py` | Slowed clips → shuffled reels → 2h (+music) | duration, music path, `VEO_XFADE`, shuffle on/off |
| `build_veo.py` | Driver: enhance batch + reel | `VEO_UPSCALE`, `VEO_TARGET_H` |
| `esrgan_upscale.py` | Real-ESRGAN x2plus upscaler (dir batch) | tile, target height |
| `df_batch.py` / `df_assemble.py` / `df_clip.py` / `df_tune.py` | DepthFlow 2.5D loops (via venv_depthflow) | `DEPTHFLOW_LOOP_SECONDS`, motion variants |
| `make_shorts.py` / `build_df_shorts.py` | Vertical Shorts (Ken Burns or DepthFlow) | image, track, title, publish_at |
| `make_thumbnail.py` | Auto thumbnail + A/B variants; custom `thumb.*` path | — |
| `upload_youtube.py` / `reupload*.py` | Resumable upload, scheduled publishAt | privacy, publish_at |
| `channel_stats.py` | Data API: per-video views/likes/comments | — |
| `channel_analytics.py` | Analytics API: watch time, retention, traffic | date range |
| `auth_youtube.py` / `auth_analytics.py` | OAuth re-consent flows (print URL) | — |
| `progress.py` | Parse render logs → stage/clip/ETA | (reuse its parsing in the app) |
| `live_stream.py` | 24/7 RTMP stream | stream key presence only |

### App pages

1. **Dashboard (M1)** — the "can I build today?" view:
   - Per-theme card: unused image count vs `MIN_IMAGES_PER_THEME`, custom `thumb.*` present?, last video date (from theme_history), eligibility badge.
   - Music: library track count + total minutes; used count.
   - Veo bank: cached `veo_slow/*_1440p.mp4` clips w/ thumbnails.
   - Tokens: upload token + analytics token status (valid / needs re-auth). Disk free. Running job banner.
2. **Prompts (M2)** — run `generate_prompts` as a job; render `today_prompt.txt` per theme as copy-button blocks (STYLE / scene / variations / THUMBNAIL section); `today_suno_prompt.txt` as a copy-per-line list. History of past prompt files.
3. **Assets (M1 read, M4 actions)** — image grid per theme (preview, delete→trash, "set as thumb"); music library with in-browser `<audio>` playback; outputs folder with `<video>` preview (range requests).
   - **Folder-first flow (decided 2026-07-13):** Sasha keeps sorting files into `images/<theme>/` and `music/library/` in Finder himself — that manual sort is the curation step, and it prevents mess. **The app never moves assets in; it *sees* the folders**: reads them fresh on every request (local fs is cheap; thumbnail cache keyed by path+mtime) + React Query refetch-on-focus, so files dropped in Finder appear in the UI immediately on tab focus — no restart, no refresh button hunting. Validation stays, as *warnings on display* (odd aspect ratio, non-16:9, suspiciously short audio, dupe names).
   - Ingest-from-UI (drag-drop upload, a Downloads inbox scanner) → **parked in Later**; revisit only if Finder sorting ever feels like friction.
4. **Build (M3)** — wizards that assemble the env + command, show it for transparency, then run as a job:
   - **Main build** (Ken Burns / DepthFlow) with all knobs above + preflight check inline.
   - **Veo wizard**: scan sources → enhance selected (shows ~35min/clip estimate, cached clips marked "banked") → assemble (pick clips + music + duration + shuffle) → optional upload step.
   - **Shorts builder**: pick image/clip + track + title + publish_at (generalizes `build_df_shorts.py`).
5. **Jobs (M2)** — queue (SQLite), live log tail (SSE), cancel (kills process group), history with settings used + exit code + duration. Single-flight: one heavy job at a time (16 GB RAM reality).
6. **Channel / YouTube Analytics (M5)** — a real analytics tab, not just a stats dump:
   - **YPP progress bars, always on top**: subs → 1,000 and watch-hours → 4,000 (the channel goal made visible).
   - **Overview cards**: subs, views, watch time, avg view duration — lifetime + last 28 days.
   - **Per-video table**: views/likes/comments (Data API) + watch time/AVD/retention % (Analytics API), sortable; each video mapped to its theme/world.
   - **Theme-level rollup** — retention/views/watch-time aggregated **per world** (e.g. "PS1 26% retention vs Space 5–6%"): the "what should I make next" signal Studio doesn't show directly. This is the tab's killer feature.
   - **Traffic**: sources breakdown, Shorts-vs-long split, geography, devices.
   - **Scheduled-publish calendar**: pending `publishAt` items (mains + staggered Shorts).
   - Mechanics: quota-friendly caching (~1h TTL + manual refresh); needs the *separate* read-only analytics token — show its status + one-click re-auth (runs `auth_analytics.py` as a job, surfaces the consent URL).
   - **Impressions/CTR are in NO API** (Studio-web only) — deep-link straight to the Studio impressions page; optional manual CTR log parked in Later.
7. **Settings (M6)** — paths, defaults for knobs, token re-auth launcher (runs auth scripts, shows the consent URL), theme registry viewer (rendered from `config.THEMES`, read-only in v1).

### Later / nice-to-haves (parked)
Analytics snapshots over time (local history + charts) · thumbnail A/B tracker · content calendar · clip-library tags/search · macOS notification on job done · multi-channel support · TikTok manual-post checklist · config.py editing from UI · asset ingest from the UI (drag-drop upload, Downloads inbox scanner — parked 2026-07-13, Sasha prefers sorting in Finder) · manual impressions/CTR log (typed in from Studio screenshots, charts CTR over time).

---

## 4. Architecture

```
ambiverse-studio/
├── server/                      # FastAPI app (own venv, py ≥3.12)
│   ├── app.py                   # ASGI entry; serves API + built SPA
│   ├── config.py                # reads .env: ANIMEMBIENT_DIR, PORT, DOWNLOADS_DIR
│   ├── pipeline.py              # inventory readers: themes, images, music, veo bank, tokens, disk
│   ├── jobs.py                  # job queue: SQLite + single worker; spawn/cancel/log
│   ├── progress.py              # log parsers (reuse animembient/progress.py logic)
│   ├── media.py                 # range-enabled file serving + cached thumbnails (Pillow)
│   └── routes/                  # /api/state, /api/assets, /api/prompts, /api/jobs, /api/channel
├── web/                         # Vite + React + TS + Tailwind (dark "Dusk" theme)
│   └── src/pages/{Dashboard,Prompts,Assets,Build,Jobs,Channel,Settings}.tsx
├── data/                        # runtime (gitignored): studio.sqlite, job logs, thumb cache
├── .claude/launch.json          # name "studio" → uvicorn on port 4700 (for Claude preview)
├── PLAN.md · README.md · CLAUDE.md · .gitignore · .env(.example)
```

**Job model** — `jobs(id, type, title, cmd, env_json, status, pid, log_path, exit_code, created/started/ended)`; states `queued → running → done|failed|cancelled`.
- Spawn: `caffeinate -dimsu <venv-python> <script>` with `cwd=ANIMEMBIENT_DIR`, `start_new_session=True` (own process group), stdout/err → `data/logs/job_<id>.log`.
- Cancel: `os.killpg(SIGTERM)` → grace → `SIGKILL` (kills ffmpeg/RIFE children too — the pattern already proven by hand this month).
- Single worker drains the queue; UI shows queue position. Heavy renders never overlap.
- Live logs: SSE endpoint tailing the log file; progress % parsed per job type (ESRGAN `i/192`, RIFE frame count, `[veo_assemble]` lines, `progress.py` parsing for Ken Burns/DepthFlow builds).

**API sketch**

```
GET  /api/state/overview            # dashboard payload (counts, tokens, disk, running job)
GET  /api/themes/{t}/images         # + /media/img?path=… (thumb cache)
POST /api/assets/trash | set-thumb
GET  /api/music                     # library + used, durations
GET  /api/prompts/today             # parsed blocks per theme
GET  /api/veo/sources | /api/veo/bank
POST /api/jobs                      # {type, env, args} → queued job (types: generate_prompts,
                                    #  main_build, veo_enhance, veo_assemble, short_build, stats_refresh, …)
GET  /api/jobs · /api/jobs/{id} · /api/jobs/{id}/log (SSE) · POST /api/jobs/{id}/cancel
GET  /api/channel/stats | /api/channel/analytics
```

**Ports:** API **4700**, Vite dev **5175** (proxy → 4700). Avoids 8501 (trading dashboard) and 5174 (wishplace). Prod mode = FastAPI serves `web/dist` on 4700, one process.

**Stack:** FastAPI + uvicorn + sse-starlette, stdlib `sqlite3`, Pillow (thumbs). React 18 + Vite + TS + Tailwind (dark slate/violet "Dusk Atlas"-adjacent look, minimal component deps). No ORM, no state library beyond React Query.

---

## 5. Milestones (each ≈ one session)

- **M0 — Skeleton.** Repo scaffolding, venv, FastAPI hello + Vite hello + proxy, launch.json, `.env.example`. ✓ = both dev servers run, page loads.
- **M1 — Read-only Dashboard + Assets.** Inventory readers (themes/images/music/veo bank/tokens/disk), image grid w/ thumbnail cache, audio playback. **The census win — already useful daily.** ✓ = dashboard matches reality vs `ls`.
- **M2 — Job engine + Prompts.** Queue/spawn/cancel/SSE logs; Prompts page runs `generate_prompts` and renders copy-blocks. ✓ = generate prompts from UI, watch it stream, cancel a dummy job cleanly; drop a PNG into a theme folder in Finder → it's in the app on next tab focus.
- **M3 — Build wizards.** Main build + Veo wizard + preflight inline; progress % parsing. **Daily-driver reached — CLI no longer needed for routine ops.** ✓ = kick a short test build (`VIDEO_DURATION_SECONDS=30 YOUTUBE_UPLOAD=false`) fully from UI.
- **M4 — Outputs + Shorts.** Output browser w/ video preview (range requests), trash/set-thumb actions, Shorts builder w/ schedule. ✓ = build + schedule a Short from UI.
- **M5 — Channel / Analytics.** YPP progress, overview cards, per-video table, theme rollup, traffic, scheduled calendar. ✓ = numbers match Studio (minus impressions/CTR, Studio-only) and the theme rollup reproduces the known ranking (PS1 > Tokyo > Space on retention).
- **M6 — Polish.** Settings page, token re-auth flow, macOS notifications on job end, error surfacing, keyboard niceties.

---

## 6. Risks & gotchas (bake into implementation)

- **Two venvs in the pipeline** (main py3.14, `venv_depthflow` py3.12/torch): always spawn via explicit interpreter paths from animembient's own config — never "activate".
- **Mac sleep kills renders** → every heavy job wrapped in `caffeinate -dimsu` (already the proven pattern).
- **Cancellation must kill the process *group*** — ffmpeg/RIFE children survive a naive kill.
- **RAM (16 GB)** → hard single-flight for renders; queue everything else behind.
- **Big media over HTTP** → HTTP Range support for `<video>` seeking; never load 4 GB into memory; thumbnail cache for grids (ffprobe/Pillow are too slow to run per-request).
- **Secrets** — `.env`, tokens, `client_secret*.json` never rendered, never proxied, never committed (mirror animembient's gitignore discipline). API binds 127.0.0.1 only.
- **YouTube API quota** — cache stats responses (e.g. 1h TTL) instead of hammering on every dashboard load.
- **Log-parse brittleness** — progress %s are best-effort; always show raw log tail as truth.
- **Don't let the app write into animembient's git state** — it only reads folders + spawns scripts.

## 7. Open questions (decide during build)

1. In-browser playback of full 2h/4GB outputs OK (range streaming), or generate lightweight preview proxies?
2. Delete semantics: `.trash/` inside each folder vs one global trash?
3. Shorts builder: generalize `build_df_shorts.py` into a parametrized script inside *animembient* (small, allowed exception to "don't touch"), or reimplement arg-passing in the app?
4. Notifications: macOS `osascript` banner enough?
5. Name check: **Ambiverse Studio** OK? (repo `ambiverse-studio`)

---

## 8. Kickoff for the next session (copy-paste)

> Read `~/myFolder/Programming/ambiverse-studio/CLAUDE.md` and `PLAN.md`, plus `~/myFolder/Programming/animembient/CLAUDE.md` (the pipeline being wrapped). Then build **M0 + M1** per the plan: scaffold server+web, then the read-only Dashboard + Assets pages against the real animembient folders. Commit + push per completed change.
