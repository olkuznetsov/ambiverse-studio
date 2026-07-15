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

**Studio TODO (when convenient — not urgent, videos ship fine today):**
- [ ] Veo assemble job → use `build_shuffled` (randomized order) instead of `assemble`.
- [ ] Veo assemble music → build a `make_music.build_track` bed from the library, not a single track.
- [ ] Shorts builder → add a "from Veo clip" option (`veo_short.py`).
- [ ] Optionally expose `build_veo_full.py` as a one-click "full Veo video" job (enhance-all → music → shuffled 2h).
- Progress parsing note: `build_veo_full.py` emits `[full] (i/N) …`, `[esrgan] i/192`, `[veo_assemble] …` — `server/progress.py` already matches the esrgan/veo_assemble lines; add a `[full]` clip counter if you wire it as a job.

*(No studio code was edited from the pipeline session in this entry — animembient-only changes. The studio picks up the `veo_assemble` fix automatically since it runs the pipeline's code; the rest are new capabilities to surface.)*
