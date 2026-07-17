"""Job engine: SQLite queue + single worker thread + process-group control.

Every job is a subprocess of an animembient script, spawned exactly the way
the CLI does it (own venv interpreter, cwd=ANIMEMBIENT_DIR, env knobs), with:
- start_new_session=True → own process group, so cancel kills ffmpeg/RIFE
  children too (SIGTERM → 10s grace → SIGKILL);
- caffeinate -dimsu around heavy jobs so Mac sleep can't kill renders;
- stdout+stderr → data/logs/job_<id>.log (tailed live over SSE);
- a single worker drains the queue — heavy jobs never overlap (16 GB RAM).
"""
import json
import os
import re
import signal
import sqlite3
import subprocess
import threading
import time
from datetime import datetime, timezone

from config import ANIMEMBIENT_DIR, DATA_DIR, JOB_LOGS_DIR, PIPELINE

DB_PATH = DATA_DIR / "studio.sqlite"
PIPELINE_PYTHON = str(ANIMEMBIENT_DIR / "venv" / "bin" / "python")

TERMINAL = ("done", "failed", "cancelled")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    cmd TEXT NOT NULL,
    env_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'queued',
    cancel_requested INTEGER NOT NULL DEFAULT 0,
    pid INTEGER,
    log_path TEXT,
    exit_code INTEGER,
    created_at TEXT NOT NULL,
    started_at TEXT,
    ended_at TEXT
);
"""

_DUMMY_SCRIPT = """\
import subprocess, sys, time
child = subprocess.Popen(["sleep", "600"])   # proves group-kill reaches children
print(f"dummy job started, child sleep pid={child.pid}", flush=True)
for i in range(int(sys.argv[1])):
    print(f"tick {i + 1}", flush=True)
    time.sleep(1)
child.terminate()
print("dummy job finished", flush=True)
"""

# Generalizes the one-off build_df_shorts.py: build one Short from an explicit
# image + track + title (or an enhanced Veo clip via veo_short), optionally
# upload with a scheduled publish_at. Uses the pipeline's own libraries.
_SHORT_BUILD_SNIPPET = """\
import json, sys
from pathlib import Path
import config
a = json.loads(sys.argv[1])
out = Path(config.BASE_DIR) / "output" / a["output"]
if a.get("veo_clip"):
    import veo_short
    print(f"[short] Veo-clip short {a['title']!r} <- {a['veo_clip']}", flush=True)
    veo_short.build_veo_short(Path(a["veo_clip"]), Path(a["track"]), a["title"], out)
else:
    import make_shorts
    print(f"[short] building {a['title']!r} ({a['theme']}) <- {a['image']}", flush=True)
    make_shorts.build_short(Path(a["image"]), Path(a["track"]), a["title"], a["theme"], out)
print(f"[short] built {out}", flush=True)
if a.get("upload"):
    import upload_youtube
    vid = upload_youtube.upload(out, None, a["title"] + " #Shorts",
                                a["description"], a["tags"],
                                publish_at=a.get("publish_at"))
    when = f" (goes public {a['publish_at']})" if a.get("publish_at") else ""
    print(f"[short] uploaded https://youtube.com/shorts/{vid}{when}", flush=True)
print("[short] DONE", flush=True)
"""


def _short_build_argv(p: dict) -> list[str]:
    title = (p.get("title") or "").strip()
    if not title:
        raise ValueError("title is required")
    track = str(_resolve_inside(p["track"]))
    slug = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_") or "short"
    args = {
        "track": track,
        "title": title,
        "output": f"short_{slug}_{datetime.now().strftime('%Y%m%d_%H%M')}.mp4",
        "upload": bool(p.get("upload")),
        "publish_at": p.get("publish_at") or None,
    }
    if p.get("veo_clip"):  # vertical Short from an enhanced Veo clip (living motion)
        args["veo_clip"] = str(_resolve_inside(p["veo_clip"]))
        args["description"] = p.get("description") or "#Shorts #ambient #fantasy #sleep"
        args["tags"] = ["shorts", "ambient", "sleep music", "study music", "fantasy"]
    else:  # classic image Short (Ken Burns / DepthFlow)
        theme = p.get("theme")
        if theme not in PIPELINE.THEMES:
            raise ValueError(f"unknown theme: {theme}")
        args["image"] = str(_resolve_inside(p["image"]))
        args["theme"] = theme
        args["description"] = p.get("description") or f"#Shorts #{theme.replace('-', '')} #ambient"
        args["tags"] = ["shorts", "ambient", "sleep music", "study music", theme.replace("-", " ")]
    return [PIPELINE_PYTHON, "-u", "-c", _SHORT_BUILD_SNIPPET, json.dumps(args)]


# Calls the pipeline's veo_assemble as a library (cwd=ANIMEMBIENT_DIR) so the UI
# can pass an explicit CLIP SELECTION — the script's own CLI only takes a dir.
# Uses build_shuffled (scene order reshuffled each cycle) and, when music=="library",
# builds a full-length crossfaded bed from music/library via make_music.build_track.
_VEO_ASSEMBLE_SNIPPET = """\
import sys
from pathlib import Path
import config, veo_assemble
out, dur, music = sys.argv[1], float(sys.argv[2]), sys.argv[3] or None
clips = [Path(p) for p in sys.argv[4:]]
if music == "library":
    import make_music
    bed = Path(config.OUTPUT_DIR) / "veo_music_bed.mp3"
    print(f"[veo_assemble] building {dur:.0f}s music bed from library...", flush=True)
    r = make_music.build_track(bed, dur)
    if not r:
        raise SystemExit("no tracks in music/library")
    music = str(bed)
    print(f"[veo_assemble] music bed: {len(r[1])} unique tracks", flush=True)
print(f"[veo_assemble] {len(clips)} clips -> {out} ({dur:.0f}s, music={music or 'none'}, shuffled)", flush=True)
veo_assemble.build_shuffled(clips, out, dur, music=music)
print("[veo_assemble] DONE", flush=True)
"""


def _resolve_inside(rel: str, *, must_exist: bool = True):
    p = (ANIMEMBIENT_DIR / rel).resolve()
    if not p.is_relative_to(ANIMEMBIENT_DIR):
        raise ValueError(f"path escapes pipeline dir: {rel}")
    if must_exist and not p.exists():
        raise ValueError(f"not found: {rel}")
    return p


def _veo_assemble_argv(p: dict) -> list[str]:
    clips = p.get("clips") or []
    if not clips:
        raise ValueError("no clips selected")
    clip_paths = [str(_resolve_inside(c)) for c in clips]
    duration = float(p.get("duration", 7200))
    music_val = p.get("music")
    if music_val == "library":       # sentinel → build a crossfaded bed from music/library
        music = "library"
    elif music_val:                  # an explicit track file
        music = str(_resolve_inside(music_val))
    else:                            # silent
        music = ""
    name = os.path.basename(p.get("output") or "veo_custom.mp4")
    if not name.endswith(".mp4"):
        name += ".mp4"
    out = str(_resolve_inside(f"output/{name}", must_exist=False))
    return [PIPELINE_PYTHON, "-u", "-c", _VEO_ASSEMBLE_SNIPPET,
            out, str(duration), music, *clip_paths]

# Registry of everything the UI can run. argv is relative to ANIMEMBIENT_DIR;
# env_keys whitelists which knobs the client may set for this job type.
JOB_TYPES = {
    "generate_prompts": {
        "title": "Generate today's prompts",
        "argv": lambda p: [PIPELINE_PYTHON, "-u", "generate_prompts.py"],
        "env_keys": {"MUSIC_SIM_THRESHOLD", "SCENES_PER_THEME"},
        "heavy": False,
    },
    "dummy_sleep": {
        "title": "Dummy job (cancel test)",
        "argv": lambda p: [PIPELINE_PYTHON, "-u", "-c", _DUMMY_SCRIPT,
                           str(int(p.get("seconds", 60)))],
        "env_keys": set(),
        "heavy": False,
    },
    "main_build": {
        "title": lambda p, env: "Main build ({}, {}s{})".format(
            "DepthFlow" if env.get("ANIMATE") == "depthflow" else "Ken Burns",
            env.get("VIDEO_DURATION_SECONDS", "7200"),
            ", upload" if env.get("YOUTUBE_UPLOAD") == "true" else ", no upload",
        ),
        "argv": lambda p: [PIPELINE_PYTHON, "-u", "main.py"],
        "env_keys": {
            "ANIMATE", "VIDEO_DURATION_SECONDS", "NUM_IMAGES_PER_VIDEO",
            "VIDEO_FLAVOR", "MUSIC_MODE", "YOUTUBE_UPLOAD", "YOUTUBE_PRIVACY",
            "SCHEDULED_PUBLISH_UTC", "MAKE_SHORTS", "SHORTS_PER_VIDEO",
            "SHORTS_SPACING_DAYS", "RENDER_PRESET", "RENDER_CRF",
            "RENDER_WORKERS", "RENDER_SUPERSAMPLE",
        },
        "heavy": True,
    },
    "veo_enhance": {
        "title": lambda p, env: "Veo enhance batch{}".format(
            f" (upscale {env.get('VEO_TARGET_H', '1440')}p)"
            if env.get("VEO_UPSCALE") == "1" else " (no upscale)",
        ),
        "argv": lambda p: [PIPELINE_PYTHON, "-u", "build_veo.py"],
        "env_keys": {"VEO_UPSCALE", "VEO_TARGET_H", "VEO_SLOWDOWN"},
        "heavy": True,
    },
    "veo_assemble": {
        "title": lambda p, env: "Veo assemble ({} clips, {}s{})".format(
            len(p.get("clips") or []), int(float(p.get("duration", 7200))),
            ", music" if p.get("music") else ", silent",
        ),
        "argv": _veo_assemble_argv,
        "env_keys": {"VEO_XFADE"},
        "heavy": True,
    },
    "veo_full": {
        "title": lambda p, env: "Veo full build: {} ({}h{})".format(
            env.get("VEO_THEME", "fantasy-realms"),
            round(int(env.get("VIDEO_DURATION_SECONDS", "7200")) / 3600, 1),
            ", PUBLISH" if env.get("PUBLISH") == "1" else "",
        ),
        "argv": lambda p: [PIPELINE_PYTHON, "-u", "build_veo_full.py"],
        "env_keys": {"VEO_UPSCALE", "VEO_TARGET_H", "VIDEO_DURATION_SECONDS",
                     "VEO_THEME", "PUBLISH", "VEO_SCENES", "VEO_SHORTS_COUNT",
                     "VEO_SHORT_TITLES"},
        "heavy": True,
    },
    "short_build": {
        "title": lambda p, env: "Short: {}{}".format(
            (p.get("title") or "?")[:40],
            " (upload)" if p.get("upload") else "",
        ),
        "argv": _short_build_argv,
        "env_keys": {"ANIMATE"},
        "heavy": True,
    },
    "auth_analytics": {
        "title": "Re-auth YouTube Analytics (read-only)",
        "argv": lambda p: [PIPELINE_PYTHON, "-u", "auth_analytics.py"],
        "env_keys": set(),
        "heavy": False,  # short + interactive: prints a consent URL, waits for redirect
    },
    "auth_youtube": {
        "title": "Re-auth YouTube upload token",
        "argv": lambda p: [PIPELINE_PYTHON, "-u", "auth_youtube.py"],
        "env_keys": set(),
        "heavy": False,
    },
}


def _notify(title: str, message: str):
    """Fire-and-forget macOS banner (osascript). Never raises."""
    try:
        script = f'display notification {message!r} with title {title!r}'
        subprocess.Popen(["osascript", "-e", script],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with _db() as conn:
        conn.execute(_SCHEMA)


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["cmd"] = json.loads(d["cmd"])
    d["env"] = json.loads(d.pop("env_json"))
    d["cancel_requested"] = bool(d["cancel_requested"])
    if d["status"] == "running":
        d["progress"] = _progress_for(d)
    return d


def _progress_for(job: dict) -> dict | None:
    import progress as progress_mod

    path = job.get("log_path")
    if not path:
        return None
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 65536))
            tail = f.read().decode(errors="replace")
    except OSError:
        return None
    return progress_mod.parse(job["type"], tail)


# ---------- public API ----------

def create_job(job_type: str, params: dict | None = None, env: dict | None = None) -> dict:
    spec = JOB_TYPES.get(job_type)
    if spec is None:
        raise ValueError(f"unknown job type: {job_type}")
    params = params or {}
    argv = spec["argv"](params)
    if spec["heavy"]:
        argv = ["caffeinate", "-dimsu", *argv]
    safe_env = {k: str(v) for k, v in (env or {}).items() if k in spec["env_keys"]}
    title = spec["title"](params, safe_env) if callable(spec["title"]) else spec["title"]
    with _db() as conn:
        cur = conn.execute(
            "INSERT INTO jobs (type, title, cmd, env_json, created_at) VALUES (?,?,?,?,?)",
            (job_type, title, json.dumps(argv), json.dumps(safe_env), _now()),
        )
        job_id = cur.lastrowid
    return get_job(job_id)  # after commit — a fresh connection must see the row


def get_job(job_id: int) -> dict | None:
    with _db() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
    return _row_to_dict(row) if row else None


def list_jobs(limit: int = 50) -> list[dict]:
    with _db() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    jobs = [_row_to_dict(r) for r in rows]
    queued = [j["id"] for j in jobs if j["status"] == "queued"]
    for j in jobs:  # oldest queued job runs first
        j["queue_position"] = (
            sorted(queued).index(j["id"]) + 1 if j["status"] == "queued" else None
        )
    return jobs


def running_summary() -> dict:
    with _db() as conn:
        running = conn.execute(
            "SELECT id, type, title, started_at FROM jobs WHERE status='running'"
        ).fetchone()
        queued = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE status='queued'"
        ).fetchone()[0]
    return {"running": dict(running) if running else None, "queued": queued}


def cancel_job(job_id: int) -> dict:
    job = get_job(job_id)
    if job is None:
        raise LookupError(job_id)
    if job["status"] == "queued":
        with _db() as conn:
            conn.execute(
                "UPDATE jobs SET status='cancelled', ended_at=? WHERE id=? AND status='queued'",
                (_now(), job_id),
            )
        return get_job(job_id)
    if job["status"] != "running" or not job["pid"]:
        return job
    with _db() as conn:
        conn.execute("UPDATE jobs SET cancel_requested=1 WHERE id=?", (job_id,))
    pid = job["pid"]
    _signal_group(pid, signal.SIGTERM)
    threading.Thread(target=_escalate_kill, args=(pid,), daemon=True).start()
    return get_job(job_id)


def _signal_group(pid: int, sig: int):
    try:
        os.killpg(os.getpgid(pid), sig)
    except (ProcessLookupError, PermissionError):
        pass


def _escalate_kill(pid: int, grace: float = 10.0):
    deadline = time.time() + grace
    while time.time() < deadline:
        if not _pid_alive(pid):
            return
        time.sleep(0.5)
    _signal_group(pid, signal.SIGKILL)


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


# ---------- worker ----------

_worker_lock = threading.Lock()
_worker_started = False


def start_worker():
    global _worker_started
    with _worker_lock:
        if _worker_started:
            return
        _worker_started = True
    init_db()
    _reconcile_orphans()
    threading.Thread(target=_worker_loop, name="job-worker", daemon=True).start()


def _reconcile_orphans():
    """Jobs left 'running' by a previous server process (dev --reload restarts).

    The subprocess survives (own session); we just lost the wait handle. If the
    pid is alive, watch it until it exits — the exit code is unrecoverable for
    a non-child, so we finish as done with exit_code NULL and a log note; the
    raw log stays the source of truth. Dead pid → failed.
    """
    with _db() as conn:
        rows = conn.execute("SELECT id, pid, log_path FROM jobs WHERE status='running'").fetchall()
    for row in rows:
        if row["pid"] and _pid_alive(row["pid"]):
            threading.Thread(
                target=_watch_orphan, args=(row["id"], row["pid"], row["log_path"]),
                daemon=True,
            ).start()
        else:
            _finish(row["id"], "failed", None, note="server restarted; process already gone")


def _watch_orphan(job_id: int, pid: int, log_path: str | None):
    while _pid_alive(pid):
        time.sleep(2)
    _finish(job_id, "done", None,
            note="exit code unknown — studio server restarted mid-job; the log above is the truth",
            log_path=log_path)


def _finish(job_id: int, status: str, exit_code: int | None, *,
            note: str | None = None, log_path: str | None = None):
    with _db() as conn:
        conn.execute(
            "UPDATE jobs SET status=?, exit_code=?, ended_at=? WHERE id=?",
            (status, exit_code, _now(), job_id),
        )
    if note and log_path:
        try:
            with open(log_path, "a") as f:
                f.write(f"\n[studio] {note}\n")
        except OSError:
            pass


def _worker_loop():
    while True:
        job = _claim_next()
        if job is None:
            time.sleep(0.7)
            continue
        try:
            _run_job(job)
        except Exception as exc:  # engine bug — mark failed, keep the worker alive
            _finish(job["id"], "failed", None, note=f"job engine error: {exc}",
                    log_path=job.get("log_path"))


def _claim_next() -> dict | None:
    with _db() as conn:
        row = conn.execute(
            "SELECT * FROM jobs WHERE status='queued' ORDER BY id LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        conn.execute(
            "UPDATE jobs SET status='running', started_at=? WHERE id=?",
            (_now(), row["id"]),
        )
    return _row_to_dict(row)


def _run_job(job: dict):
    log_path = JOB_LOGS_DIR / f"job_{job['id']}.log"
    env = {**os.environ, **job["env"], "PYTHONUNBUFFERED": "1"}
    with open(log_path, "w") as log:
        log.write(f"[studio] job {job['id']} ({job['type']}) — {' '.join(job['cmd'])}\n")
        if job["env"]:
            log.write(f"[studio] env: {job['env']}\n")
        log.flush()
        proc = subprocess.Popen(
            job["cmd"], cwd=ANIMEMBIENT_DIR, env=env,
            stdout=log, stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        with _db() as conn:
            conn.execute("UPDATE jobs SET pid=?, log_path=? WHERE id=?",
                         (proc.pid, str(log_path), job["id"]))
        rc = proc.wait()
    cancelled = get_job(job["id"])["cancel_requested"]
    status = "cancelled" if (cancelled and rc != 0) else ("done" if rc == 0 else "failed")
    _finish(job["id"], status, rc)
    # ping the desktop for heavy jobs (the long ones you walk away from)
    if status != "cancelled" and JOB_TYPES.get(job["type"], {}).get("heavy"):
        icon = "✅" if status == "done" else "❌"
        _notify("Ambiverse Studio", f"{icon} {job['title']} — {status}")
