# HANDOFF — cross-session notes between the pipeline session and this studio session

**Why this file exists.** Two Claude sessions work on this system:
- the **pipeline session** — works in `~/myFolder/Programming/animembient/` (the AI video pipeline: scripts, ffmpeg, RIFE, ESRGAN, YouTube).
- the **studio session** — works here in `~/myFolder/Programming/ambiverse-studio/` (this app, which *wraps* that pipeline).

They share the same machine but not the same conversation. **Ambiverse Studio wraps animembient**, so when the pipeline changes (new script, new knob, renamed function), the studio's wizards/jobs may need to catch up. This file is the channel: the pipeline session writes an entry here whenever it changes something the studio should know about; Sasha points the studio session at this file so it picks the change up.

**How to use it**
- **Pipeline session** (when it edits animembient *or* makes a fix here): append a dated entry below — what changed, why, and what the studio should do about it. Newest first.
- **Studio session**: read the newest unresolved entries, apply what's relevant, then mark them `✅ DONE (studio)` with the commit hash. Leave the entry (history).
- **Golden rule still holds:** Studio *wraps, doesn't rewrite*. It invokes animembient's scripts/functions as subprocess jobs — so most animembient fixes are picked up automatically (the studio runs the pipeline's own code). The entries below are mainly "new capability exists, consider surfacing it" + "a function the studio calls changed."

---

## 2026-07-18 (later) — upload progress tag (studio session; 1-line animembient edit)

IDEAS #1: `upload_youtube._retriable_chunk_upload` already printed a bare chunk percent;
the studio session tagged + flushed it — `[upload] N%` — (animembient commit `08ac31c`,
the exact edit IDEAS.md prescribed) and taught `server/progress.py` to parse it:
`main_build` upload phase (bar = upload %), `veo_full` publish phase ("publish: uploading
N%" at 99%), and `short_build` uploads. Pipeline sessions: keep the `[upload]` tag if that
loop is ever reworked — Studio's upload bars key on it.

---

## 2026-07-15 — Veo "living-world" pipeline gained an end-to-end path + real Shorts (pipeline session)

Context: this session built the full Veo slow-mo + ESRGAN-upscale pipeline and just kicked off the first real 2-hour fantasy video (9 clips, 1440p, 40-track music bed). Along the way the animembient repo gained scripts/fixes the studio's current Veo/Shorts wiring predates. **None of this breaks the studio** — it's "new stuff to surface."

**What changed in animembient (all committed there):**
1. **`build_veo_full.py` (NEW)** — full unattended run: enhance each Downloads clip (crop→dedupe→ESRGAN→RIFE, cached) → build a full-length music bed from `music/library/` via `make_music.build_track` (side-effect-free, crossfades 40 tracks) → assemble a **shuffled** 2-hour video + mux the music. Env: `VEO_UPSCALE=1`, `VEO_TARGET_H` (1440). This is the "one button = finished Veo video with music" path.
2. **`veo_assemble.build_shuffled()` now works** — it referenced `tempfile` without importing it (would `NameError` at assembly). Fixed. **This matters for the studio:** `server/jobs.py` currently calls `veo_assemble.assemble()` (fixed 1-2-3 scene order, and its `music=` path loops a SINGLE track). `build_shuffled(clips, out, dur, music=…)` gives **randomized scene order every ~4.6-min cycle** (no repeats across cycles) — a real quality win for long videos. Consider switching the `veo_assemble` job to `build_shuffled`.
3. **`veo_short.py` (NEW)** — a **vertical Short from an enhanced Veo clip** (center-crop 16:9→9:16, loop to 60s, title + music), reusing `make_shorts`' overlay/slice/composite. The studio's Shorts builder (`jobs.py` → `make_shorts.build_short`) is **image-only** (Ken Burns / DepthFlow). Consider adding a "Veo clip" source option to the Shorts builder that calls `veo_short.build_veo_short(clip, music, title, out)`.
4. **Music for Veo = a bed, not one track.** For a 2h video you want variety: call `make_music.build_track(bed_path, duration)` (MUSIC_MODE=library, loops+crossfades the library, loudnorm, fade — and does NOT move tracks to `/used`) to make the bed, then pass that bed as the `music=` arg. The studio's veo_assemble job passing a single library file only loops one track.

**Studio TODO — ✅ ALL DONE 2026-07-15 (implemented from the pipeline session; see git log):**
- [x] Veo assemble job → uses `build_shuffled` (randomized scene order) instead of `assemble`.
- [x] Veo assemble music → `music: "library"` sentinel builds a `make_music.build_track` bed from the library; an explicit track still works; empty = silent. (`_VEO_ASSEMBLE_SNIPPET` + `_veo_assemble_argv` in `server/jobs.py`; UI = "♪ Full library bed" option in the Veo wizard music dropdown.)
- [x] Shorts builder → "Image | Veo clip" source toggle (`ShortsBuilder` in `web/src/pages/Build.tsx`); Veo mode shows the enhanced-clip bank and hides theme/animation; backend `short_build` gained a `veo_clip` branch → `veo_short.build_veo_short`.
- [x] `build_veo_full.py` exposed as job type **`veo_full`** ("Full auto build →" button in the Veo wizard: enhance all → shuffled 2h + library bed).
- [x] Progress bars for the Veo jobs — `server/progress.py` now parses `veo_full` (enhance clips 0-85% with ESRGAN frame sub-progress → music-bed/assembly 85-100% by reel count) and the now-shuffled `veo_assemble` (music bed → reel i/N of the shuffled build). Jobs page bar (already in `Jobs.tsx`) fills for both. Verified against the live render log (`enhancing clip 3/9`, 19%) + synthetic assembly logs.

**Verification:** frontend compiles (`tsc -b && vite build` clean) and the new UI was confirmed rendering in the dev server (library-bed option, Full-auto-build button, Veo-clip Shorts toggle + bank). Backend `jobs.py` imports OK; the changed argv builders were exercised. **NOT yet runtime-tested end-to-end** (an actual `veo_assemble`/`veo_short`/`veo_full` job) — the machine is busy with the first real 2h Veo render; do a quick real run when it's free. Note: `output/veo_slow/` currently holds BOTH old 1080p `veo_NN.mp4` and new `veo_NN_1440p.mp4`; the bank lists both — prefer the `_1440p` ones (the old 1080p set can be deleted once confirmed unneeded).

*(This entry WAS implemented from the pipeline session per Sasha's request — studio code was edited here, committed + pushed. Studio session: nothing to redo; only the optional `[full]` progress counter remains.)*

---

## 2026-07-15 (later) — audio fix: 96kHz → 48kHz (pipeline session; studio auto-inherits)

The first full 2h Veo video built fine but played with **no music in QuickTime** — the muxed AAC came out **96 kHz** (ffmpeg `loudnorm` internally resamples; nothing pinned the output rate), which many players silently refuse to play. Fixed in **animembient `veo_assemble.py`** (commit `b0a09a6`): appended `aresample=48000` to both mux filter chains (`_mux_music` used by `build_shuffled`/`build_veo_full`, and `loop_to`), and clamped the fade-out start to `max(0, dur-fadeout)` so sub-10s music builds don't crash. Verified: `_mux_music` now emits 48000 Hz. The existing `output/fantasy_veo_2h_final.mp4` was re-muxed to 48 kHz in place.

**Studio impact: NONE needed** — the `veo_assemble`/`veo_full` jobs run animembient's `veo_assemble.py` as a subprocess, so they inherit this fix automatically. No studio code change.

**Follow-up worth a look (minor, not urgent):** `make_music.build_track(bed, 7200)` produced a **93-min** bed, not 120 min — so `_mux_music`'s `-stream_loop -1` loops it to fill 2h (works, music plays throughout + fades out), but there's a hard cut at the ~93-min loop seam and the last ~27 min repeats the first. Root cause is in `make_music.pick_library_tracks`/`concat_with_crossfades` duration accounting (crossfades shrink the total below the requested length, and it doesn't top up). Not broken — just a polish item if the loop seam is ever noticeable. Lives in the pipeline (`make_music.py`), so it's a pipeline-session fix if pursued.

---

## 2026-07-18 — Veo one-button-to-publish (pipeline session; studio edits included)

**Pipeline (animembient `22b3578`):** Wave 11d — `veo_publish.py` (theme-aware publish from a build manifest: deterministic metadata — no LLM-invented scenes — custom-or-auto thumb, translations, scheduled upload, staggered Shorts w/ constrained Groq titles; **resumable** via ids written into the manifest) + `build_veo_full.py` generalized (`VEO_THEME` any theme, theme-namespaced bank `<theme>_NN_<H>p.mp4` w/ legacy fantasy fallback, raw sources archived to `clips/<theme>/veo_raw/`, bank-only reruns, `PUBLISH=1` chains build→publish). Context: Sasha plans **one Veo video per channel theme**.

**Studio edits (done here, this commit):**
- `server/jobs.py`: `veo_full` env_keys += `VEO_THEME`, `PUBLISH`, `VEO_SCENES`, `VEO_SHORTS_COUNT`, `VEO_SHORT_TITLES`; title shows theme + PUBLISH flag.
- `server/progress.py`: `veo_full` parser gains the publish phase (`[veo_publish]` stage passthrough at 99%, `[veo_publish] DONE` → "published" 100%). Checked before `[full] DONE` since publishing continues past it.
- `web/src/pages/Build.tsx`: Veo wizard "Full auto build" row now has a **theme select** (all 8), **"Publish when done"** toggle, and an optional **scene-note input** (→ `VEO_SCENES`, human-supplied accuracy). Verified rendering in dev server; `tsc -b && vite build` clean; parser unit-checked.
- **`IDEAS.md` (new):** curated roadmap (Now / Next / Beyond-YouTube / deliberate cuts) from a deep functionality pass. Studio session: treat the "Now" section as the working backlog — top items: upload-progress %, **A/B format tracker (Veo vs image rollup — the channel's live decision)**, publish-event markers on growth charts, output housekeeping.
- Not runtime-tested end-to-end from the UI yet (machine busy publishing fantasy); the underlying scripts are the ones running tonight.
