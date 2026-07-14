"""Channel data collector — RUN WITH THE PIPELINE'S PYTHON (has google libs).

    <animembient>/venv/bin/python channel_fetch.py <ANIMEMBIENT_DIR>

Prints ONE JSON blob to stdout: channel totals + per-video Data-API stats,
plus (if the read-only analytics token exists) watch time / retention / traffic
from the Analytics API, and a best-effort per-theme rollup.

Wrap-don't-rewrite: reuses the pipeline's own upload_youtube / channel_analytics
helpers and its THEME_GENRE vocab. Never writes into the pipeline repo.
"""
import glob
import json
import os
import re
import sys
from datetime import date, timedelta

ANIM = sys.argv[1]
sys.path.insert(0, ANIM)
os.chdir(ANIM)  # analytics token path is cwd-relative

import config  # noqa: E402
import upload_youtube  # noqa: E402
import channel_stats  # noqa: E402  (for _dur_to_sec)

try:
    import main as pipeline_main  # THEME_GENRE lives here
    THEME_GENRE = pipeline_main.THEME_GENRE
except Exception:
    THEME_GENRE = {}


# ---- theme attribution -------------------------------------------------

# Distinctive world keywords per theme (the genre suffix alone can't split
# siblings like the two lofi themes, so use world nouns). Lowercased.
THEME_KEYWORDS = {
    "space-stations": ["orbital", "orbit", "space station", "docking", "habitat",
                       "galactic hub", "starport", "station"],
    "deep-space": ["deep space", "nebula", "starfield", "cosmos", "interstellar",
                   "void", "cosmic drift"],
    "alien-planets": ["alien", "exoplanet", "colony", "alien world", "distant planet"],
    "cyberpunk-cities": ["cyberpunk", "synthwave", "darksynth", "megacity", "neon city",
                         "neon metropolis"],
    "japanese-streets": ["tokyo", "japanese street", "neon street", "rainy tokyo",
                         "night street", "shibuya", "izakaya"],
    "cozy-anime-rooms": ["cozy", "bedroom", "study room", "café", "cafe", "rainy room",
                         "reading nook", "dorm"],
    "ps1-jungle": ["ps1", "low-poly", "low poly", "jungle", "dreamcast", "y2k",
                   "polygon"],
    "fantasy-realms": ["fantasy", "tavern", "castle", "medieval", "enchanted", "realm",
                       "apothecary", "library hall"],
}


def _norm(t: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", (t or "").lower())).strip()


def build_log_theme_map():
    """From run_*.log: pair each recorded `Title:` with the most recent `Theme:`.

    The pipeline logs `Theme: <t> ...` then `Title: <t>` inside one build, so this
    is the pipeline's own ground-truth attribution for those exact titles.
    """
    theme_re = re.compile(r"^\[[^\]]+\]\s*Theme:\s*([a-z0-9-]+)")
    title_re = re.compile(r"^\[[^\]]+\]\s*Title:\s*(.+?)\s*$")
    mapping = {}
    for path in sorted(glob.glob(os.path.join(config.LOGS_DIR, "run_*.log"))):
        current = None
        try:
            with open(path, errors="replace") as f:
                for line in f:
                    mt = theme_re.match(line)
                    if mt:
                        current = mt.group(1)
                        continue
                    tt = title_re.match(line)
                    if tt and current:
                        # title before the "—" em-dash is the evocative scene name
                        head = _norm(tt.group(1).split("—")[0])
                        if head:
                            mapping[head] = current
        except OSError:
            pass
    return mapping


def infer_theme(title: str, log_map: dict):
    n = _norm(title)
    # 1) exact scene-name match from the logs (ground truth)
    head = n.split("—")[0].strip()
    for key, theme in log_map.items():
        if key and (key == head or (len(key) > 6 and key in n)):
            return theme, "log"
    # 2) distinctive world-keyword scoring
    best, best_score = None, 0
    for theme, kws in THEME_KEYWORDS.items():
        score = sum(1 for kw in kws if kw in n)
        if score > best_score:
            best, best_score = theme, score
    if best:
        return best, "inferred"
    # 3) genre-label fallback (may be ambiguous across sibling themes)
    for theme, spec in THEME_GENRE.items():
        for label in spec[0]:
            if _norm(label) and _norm(label) in n:
                return theme, "genre"
    return None, "unknown"


# ---- Data API: channel + per-video ------------------------------------

def data_api():
    svc = upload_youtube.get_service()
    ch = svc.channels().list(part="snippet,statistics,contentDetails",
                             mine=True).execute()["items"][0]
    st = ch["statistics"]
    channel = {
        "title": ch["snippet"]["title"],
        "subscribers": int(st.get("subscriberCount", 0)),
        "views": int(st.get("viewCount", 0)),
        "video_count": int(st.get("videoCount", 0)),
    }
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, req = [], svc.playlistItems().list(part="contentDetails",
                                            playlistId=uploads, maxResults=50)
    while req:
        res = req.execute()
        ids += [it["contentDetails"]["videoId"] for it in res["items"]]
        req = svc.playlistItems().list_next(req, res)
    vids = []
    for i in range(0, len(ids), 50):
        vids += svc.videos().list(part="snippet,statistics,contentDetails,status",
                                  id=",".join(ids[i:i + 50])).execute()["items"]
    rows, scheduled = [], []
    for v in vids:
        stt = v["statistics"]
        status = v.get("status", {})
        secs = channel_stats._dur_to_sec(v["contentDetails"]["duration"])
        privacy = status.get("privacyStatus")
        publish_at = status.get("publishAt")  # set only on scheduled uploads
        rows.append({
            "video_id": v["id"],
            "title": v["snippet"]["title"],
            "kind": "Short" if secs <= 65 else "Video",
            "date": v["snippet"]["publishedAt"][:10],
            "secs": secs,
            "views": int(stt.get("viewCount", 0)),
            "likes": int(stt.get("likeCount", 0)),
            "comments": int(stt.get("commentCount", 0)),
            "privacy": privacy,
            "publish_at": publish_at,
        })
        if publish_at:
            scheduled.append({
                "video_id": v["id"],
                "title": v["snippet"]["title"],
                "kind": "Short" if secs <= 65 else "Video",
                "publish_at": publish_at,
            })
    scheduled.sort(key=lambda s: s["publish_at"])
    return channel, rows, scheduled


# ---- Analytics API ----------------------------------------------------

CORE_METRICS = ("views,estimatedMinutesWatched,averageViewDuration,"
                "averageViewPercentage,subscribersGained,subscribersLost,"
                "likes,comments,shares")


def _core(svc, start, end):
    from channel_analytics import query
    r = query(svc, startDate=start, endDate=end, metrics=CORE_METRICS)
    rows = r.get("rows") or [[0] * 9]
    m = dict(zip([c["name"] for c in r["columnHeaders"]], rows[0]))
    return {
        "views": int(m["views"]),
        "minutes_watched": int(m["estimatedMinutesWatched"]),
        "avg_view_duration_s": round(m["averageViewDuration"], 1),
        "avg_view_pct": round(m["averageViewPercentage"], 1),
        "subs_gained": int(m["subscribersGained"]),
        "subs_lost": int(m["subscribersLost"]),
        "likes": int(m["likes"]),
        "comments": int(m["comments"]),
        "shares": int(m["shares"]),
    }


def _dim(svc, dimension, start, end, label_map, with_time=True, maxResults=25):
    from channel_analytics import query
    metrics = "views,estimatedMinutesWatched" if with_time else "views"
    r = query(svc, startDate=start, endDate=end, dimensions=dimension,
              metrics=metrics, sort="-views", maxResults=maxResults)
    out = []
    for row in (r.get("rows") or []):
        out.append({
            "label": (label_map or {}).get(row[0], row[0]),
            "views": int(row[1]),
            "minutes_watched": int(row[2]) if with_time and len(row) > 2 else None,
        })
    return out


def _per_video_analytics(svc, start, end):
    from channel_analytics import query
    r = query(svc, startDate=start, endDate=end, dimensions="video",
              metrics="estimatedMinutesWatched,views,averageViewDuration,averageViewPercentage",
              sort="-estimatedMinutesWatched", maxResults=200)
    out = {}
    for row in (r.get("rows") or []):
        vid, mins, views, avd, avp = row
        out[vid] = {
            "minutes_watched": int(mins),
            "avg_view_duration_s": round(avd, 1),
            "avg_view_pct": round(avp, 1),
        }
    return out


def analytics_api():
    from channel_analytics import (analytics_service, ANALYTICS_TOKEN,
                                    TRAFFIC_LABELS, CONTENT_LABELS, LIFETIME_START)
    if not ANALYTICS_TOKEN.exists():
        return {"available": False, "reason": "no analytics token — run auth_analytics.py"}
    try:
        svc = analytics_service()
        today = date.today().isoformat()
        d28 = (date.today() - timedelta(days=28)).isoformat()
        return {
            "available": True,
            "lifetime": _core(svc, LIFETIME_START, today),
            "last_28": _core(svc, d28, today),
            "per_video": _per_video_analytics(svc, LIFETIME_START, today),
            "traffic": _dim(svc, "insightTrafficSourceType", LIFETIME_START, today, TRAFFIC_LABELS),
            "content_type": _dim(svc, "creatorContentType", LIFETIME_START, today, CONTENT_LABELS),
            "geography": _dim(svc, "country", LIFETIME_START, today, None, with_time=False, maxResults=10),
            "devices": _dim(svc, "deviceType", LIFETIME_START, today, None, with_time=False),
        }
    except Exception as e:  # HttpError (API disabled), token issues, etc.
        return {"available": False, "reason": f"{type(e).__name__}: {e}"}


# ---- theme rollup -----------------------------------------------------

def build_rollup(rows, analytics):
    per_video = (analytics or {}).get("per_video", {})
    agg = {}
    for r in rows:
        theme = r.get("theme")
        if not theme:
            continue
        a = agg.setdefault(theme, {
            "theme": theme, "videos": 0, "shorts": 0, "views": 0,
            "minutes_watched": 0, "_avp_weight": 0.0, "_avp_num": 0.0,
        })
        if r["kind"] == "Short":
            a["shorts"] += 1
        else:
            a["videos"] += 1
        a["views"] += r["views"]
        pv = per_video.get(r["video_id"])
        if pv:
            a["minutes_watched"] += pv["minutes_watched"]
            # weight retention by watch time (long videos dominate the signal)
            w = pv["minutes_watched"] or 1
            a["_avp_weight"] += w
            a["_avp_num"] += pv["avg_view_pct"] * w
    out = []
    for a in agg.values():
        avp = round(a["_avp_num"] / a["_avp_weight"], 1) if a["_avp_weight"] else None
        out.append({
            "theme": a["theme"],
            "videos": a["videos"], "shorts": a["shorts"],
            "views": a["views"], "minutes_watched": a["minutes_watched"],
            "avg_view_pct": avp,
        })
    out.sort(key=lambda x: (x["avg_view_pct"] or -1, x["minutes_watched"]), reverse=True)
    return out


def main():
    channel, rows, scheduled = data_api()
    log_map = build_log_theme_map()
    for r in rows:
        theme, source = infer_theme(r["title"], log_map)
        r["theme"], r["theme_source"] = theme, source
    analytics = analytics_api()
    # attach analytics per-video onto rows for the table
    pv = analytics.get("per_video", {}) if analytics.get("available") else {}
    for r in rows:
        r["analytics"] = pv.get(r["video_id"])
    rollup = build_rollup(rows, analytics)
    print(json.dumps({
        "channel": channel,
        "videos": rows,
        "scheduled": scheduled,
        "analytics": analytics,
        "theme_rollup": rollup,
        "generated_at": __import__("datetime").datetime.now().isoformat(),
    }))


if __name__ == "__main__":
    main()
