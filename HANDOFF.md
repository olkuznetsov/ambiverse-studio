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
