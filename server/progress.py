"""Best-effort progress parsing from job logs (raw log stays the truth).

Markers (from the pipeline's own prints):
- main_build KB:  "Rendering N clips across…", "  clip i/N done:", "Concatenating clips…"
- main_build DF:  "[df_batch] i/N variant=…"
- main.py stages: "[ISO] …" log_line entries ((N images planned), music, thumbnail, upload)
- veo_enhance:    "[build_veo] (i/N) slowmo|cached", "[esrgan]   i/N" frame sub-progress
- veo_assemble:   "[veo_assemble] …" stage lines
"""
import re

_PATTERNS = {
    "clip_done": re.compile(r"^\s*clip (\d+)/(\d+) done", re.M),
    "render_total": re.compile(r"Rendering (\d+) clips across", re.M),
    "df_clip": re.compile(r"\[df_batch\] (\d+)/(\d+)", re.M),
    "build_veo": re.compile(r"\[build_veo\] \((\d+)/(\d+)\) (slowmo|cached)", re.M),
    "full_clip": re.compile(r"\[full\] \((\d+)/(\d+)\) (enhance|cached)", re.M),
    "esrgan": re.compile(r"\[esrgan\]\s+(\d+)/(\d+)", re.M),
    "veo_assemble": re.compile(r"\[veo_assemble\][ :]*(.+)", re.M),
    "shuffled": re.compile(r"shuffled build: (\d+) cycles", re.M),
    "building_reel": re.compile(r"\[veo_assemble\] building reel", re.M),
    "planned": re.compile(r"\((\d+) images planned\)", re.M),
}


def _last(rx: re.Pattern, text: str):
    m = None
    for m in rx.finditer(text):
        pass
    return m


def parse(job_type: str, log_tail: str) -> dict | None:
    if not log_tail:
        return None
    if job_type == "main_build":
        return _main_build(log_tail)
    if job_type == "veo_enhance":
        return _veo_enhance(log_tail)
    if job_type == "veo_assemble":
        return _veo_assemble(log_tail)
    if job_type == "veo_full":
        return _veo_full(log_tail)
    return None


def _main_build(text: str) -> dict | None:
    if "Concatenating clips" in text:
        return {"stage": "concatenating clips (xfade master encode)", "pct": None}
    df = _last(_PATTERNS["df_clip"], text)
    if df:
        i, n = int(df.group(1)), int(df.group(2))
        return {"stage": f"DepthFlow clip {i}/{n}", "pct": round(i / n * 100)}
    clip = _last(_PATTERNS["clip_done"], text)
    total_m = _PATTERNS["render_total"].search(text) or _PATTERNS["planned"].search(text)
    if clip:
        i, n = int(clip.group(1)), int(clip.group(2))
        return {"stage": f"rendering clip {i}/{n}", "pct": round(i / n * 100)}
    if total_m:
        return {"stage": f"rendering clips (0/{total_m.group(1)})", "pct": 0}
    # fall back to the last pipeline log_line stage
    stages = re.findall(r"^\[\d{4}-\d{2}-\d{2}T[\d:]+\] (.+)$", text, re.M)
    return {"stage": stages[-1][:80], "pct": None} if stages else None


def _veo_enhance(text: str) -> dict | None:
    bv = _last(_PATTERNS["build_veo"], text)
    if not bv:
        return None
    i, n = int(bv.group(1)), int(bv.group(2))
    stage = f"clip {i}/{n} ({bv.group(3)})"
    pct = round((i - 1) / n * 100)
    es = _last(_PATTERNS["esrgan"], text)
    if es and bv.group(3) == "slowmo":
        fi, fn = int(es.group(1)), int(es.group(2))
        # only trust esrgan counters that appear after the current clip line
        if es.start() > bv.start():
            stage += f" — ESRGAN frame {fi}/{fn}"
            pct = round(((i - 1) + fi / fn) / n * 100)
    return {"stage": stage, "pct": pct}


def _veo_assemble(text: str) -> dict | None:
    """Standalone assemble (build_shuffled): optional music bed -> shuffled reels -> mux."""
    if "[veo_assemble] DONE" in text:
        return {"stage": "done", "pct": 100}
    sb = _PATTERNS["shuffled"].search(text)
    if sb:
        n = int(sb.group(1))
        reels = min(len(_PATTERNS["building_reel"].findall(text)), n)
        pct = round(reels / n * 92) if n else None  # reels ~92%; headroom for concat + mux
        return {"stage": f"reel {reels}/{n} (shuffled) + mux", "pct": pct}
    if "music bed" in text:
        return {"stage": "building music bed from library", "pct": 3}
    m = _last(_PATTERNS["veo_assemble"], text)
    return {"stage": m.group(1).strip()[:80], "pct": None} if m else None


_VEO_PUBLISH_LINE = re.compile(r"\[veo_publish\][ :]*(.+)", re.M)


def _veo_full(text: str) -> dict | None:
    """Full build: enhance (0-85%, ESRGAN sub-progress) -> assembly (85-99%)
    -> optional PUBLISH=1 phase (metadata/upload/shorts, stage passthrough)."""
    if "[veo_publish] DONE" in text:
        return {"stage": "published", "pct": 100}
    pub = _last(_VEO_PUBLISH_LINE, text)
    if pub:  # publish phase (after the build) — show its last stage line
        return {"stage": f"publish: {pub.group(1).strip()[:70]}", "pct": 99}
    if "[full] DONE" in text:
        return {"stage": "done", "pct": 100}
    # once a music bed / shuffled build appears, all clips are enhanced -> assembly phase
    if "music bed" in text or _PATTERNS["shuffled"].search(text):
        sb = _PATTERNS["shuffled"].search(text)
        if sb:
            n = int(sb.group(1))
            reels = min(len(_PATTERNS["building_reel"].findall(text)), n)
            return {"stage": f"assembling reel {reels}/{n} + music",
                    "pct": round(85 + (reels / n if n else 0) * 14)}
        return {"stage": "building music bed from library", "pct": 85}
    # enhancement phase (0-85%)
    fv = _last(_PATTERNS["full_clip"], text)
    if not fv:
        return None
    i, n = int(fv.group(1)), int(fv.group(2))
    if fv.group(3) == "cached":
        return {"stage": f"clip {i}/{n} cached", "pct": round(i / n * 85)}
    stage = f"enhancing clip {i}/{n}"
    pct = round((i - 1) / n * 85)
    es = _last(_PATTERNS["esrgan"], text)
    if es and es.start() > fv.start():
        efi, efn = int(es.group(1)), int(es.group(2))
        stage += f" — ESRGAN {efi}/{efn}"
        pct = round(((i - 1) + efi / efn) / n * 85)
    return {"stage": stage, "pct": pct}
