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
    "esrgan": re.compile(r"\[esrgan\]\s+(\d+)/(\d+)", re.M),
    "veo_assemble": re.compile(r"\[veo_assemble\][ :]*(.+)", re.M),
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
        m = _last(_PATTERNS["veo_assemble"], log_tail)
        return {"stage": m.group(1).strip()[:80], "pct": None} if m else None
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
