"""Demo-mode seeder: a self-contained stand-in for the private pipeline.

The real pipeline is a separate private repo that needs API keys, OAuth tokens
and hours of rendering. Demo mode copies demo/pipeline/ — scripts that speak the
same CLI and log protocol — into data/demo/pipeline/ and generates sample
assets around them, so every page and every job type runs through exactly the
code paths the real setup uses.

Idempotent: the stand-in sources are re-synced on every start (written only
when they differ, so `uvicorn --reload` doesn't loop); assets are generated once.
Delete data/demo/ to start over.
"""
import array
import datetime as dt
import json
import math
import os
import random
import shutil
import subprocess
import sys
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

SEED_VERSION = "1"
W, H = 1280, 720

# images per theme — some worlds "ready to build" (≥ 8), some not, like a real week
IMAGE_COUNTS = {
    "space-stations": 10, "deep-space": 4, "alien-planets": 0, "cyberpunk-cities": 6,
    "japanese-streets": 9, "cozy-anime-rooms": 2, "ps1-jungle": 12, "fantasy-realms": 8,
}
LIBRARY_TRACKS = {  # name: chord (integer Hz → each 1 s wavetable loops seamlessly)
    "Orbital Drift": (110, 165, 220, 262), "Habitat Lights": (98, 147, 196, 247),
    "Nebula Hush": (82, 123, 165, 196), "Lantern Alley": (131, 196, 262, 330),
    "Window Rain": (117, 175, 233, 294), "Polygon Lagoon": (147, 220, 294, 370),
    "Tavern Embers": (110, 147, 220, 277), "Neon Afterglow": (92, 138, 185, 233),
}
USED_TRACKS = {
    "Golden Orbit": (104, 156, 208, 262), "Cosmic Docking Bay": (87, 131, 175, 220),
    "Tokyo Neon Streets": (123, 185, 247, 311), "Misty Jungle Canopy": (139, 208, 277, 349),
    "Enchanted Realm": (98, 147, 196, 233), "Glass Current": (110, 165, 220, 277),
}


def ensure_seeded(studio_root: Path, data_dir: Path) -> None:
    pipe = data_dir / "pipeline"
    src, fixtures = studio_root / "demo" / "pipeline", studio_root / "demo" / "fixtures"
    pipe.mkdir(parents=True, exist_ok=True)
    for f in src.glob("*.py"):
        _sync(f, pipe / f.name)
    _sync(fixtures / "theme_registry.json", pipe / "theme_registry.json")
    _sync(fixtures / "prompts.json", pipe / "fixture_prompts.json")
    _sync(fixtures / "thumbnails.json", pipe / "fixture_thumbnails.json")

    marker = data_dir / ".seeded"
    if marker.exists() and marker.read_text().strip() == SEED_VERSION:
        return
    print(f"[demo] first run — generating sample assets in {data_dir} (~10 s)", flush=True)
    _images(pipe)
    _music(pipe)
    _placeholders(pipe)
    _clips(data_dir / "downloads", pipe)
    for name in ("channel_history.json", "impressions_log.json"):
        shutil.copyfile(fixtures / name, data_dir / name)
    yesterday = (dt.date.today() - dt.timedelta(days=1)).isoformat()
    _run(pipe, data_dir, "generate_prompts.py", DEMO_DATE=yesterday)
    _run(pipe, data_dir, "main.py", YOUTUBE_UPLOAD="false", SHORTS_PER_VIDEO="2")
    marker.write_text(SEED_VERSION)
    print("[demo] sample assets ready", flush=True)


def _sync(src: Path, dst: Path) -> None:
    data = src.read_bytes()
    if not dst.exists() or dst.read_bytes() != data:
        dst.write_bytes(data)


def _run(pipe: Path, data_dir: Path, script: str, **env: str) -> None:
    """Run a stand-in script at full speed — seeding doubles as its smoke test."""
    proc = subprocess.run([sys.executable, "-u", script], cwd=pipe, capture_output=True,
                          text=True, timeout=180, env={**os.environ, "DEMO_SPEED": "1000", **env})
    with open(data_dir / "seed.log", "a") as log:
        log.write(f"$ {script}\n{proc.stdout}{proc.stderr}\n")
    if proc.returncode != 0:
        print(f"[demo] warning: {script} exited {proc.returncode} — see {data_dir / 'seed.log'}")


# ---------- procedural scenes (one look per world) ----------

def _gradient(top, bottom, rng):
    jitter = lambda c: tuple(max(0, min(255, v + rng.randint(-12, 12))) for v in c)  # noqa: E731
    top, bottom = jitter(top), jitter(bottom)
    img = Image.new("RGBA", (W, H))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / (H - 1)
        d.line([(0, y), (W, y)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    return img


def _glow(img, x, y, r, color, blur, alpha=255):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).ellipse((x - r, y - r, x + r, y + r), fill=(*color, alpha))
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(blur)))


def _stars(d, rng, n, depth=0.7):
    for _ in range(n):
        x, y, b = rng.randrange(W), rng.randrange(int(H * depth)), rng.randrange(140, 256)
        s = rng.choice((1, 1, 1, 2))
        d.ellipse((x, y, x + s, y + s), fill=(b, b, b, 255))


def _ridge(d, rng, base_y, amp, color, step=40):
    pts, y = [(0, H)], base_y
    for x in range(0, W + step, step):
        y = max(base_y - amp, min(base_y + amp, y + rng.randint(-amp // 2, amp // 2)))
        pts.append((x, y))
    d.polygon(pts + [(W, H)], fill=color)


def _skyline(d, rng, base_y, color, windows, lo, hi, lit=0.35):
    x = 0
    while x < W:
        bw, bh = rng.randint(40, 110), rng.randint(lo, hi)
        d.rectangle((x, base_y - bh, x + bw, H), fill=color)
        for wy in range(base_y - bh + 10, H - 12, 16):
            for wx in range(x + 6, x + bw - 8, 12):
                if rng.random() < lit:
                    d.rectangle((wx, wy, wx + 5, wy + 7), fill=rng.choice(windows))
        x += bw + rng.randint(2, 10)


def _space_stations(rng):
    img = _gradient((6, 8, 28), (36, 28, 84), rng)
    d = ImageDraw.Draw(img)
    _stars(d, rng, 260, depth=1.0)
    _glow(img, rng.randint(900, 1150), rng.randint(520, 680), 300, (60, 110, 200), 40, 200)
    cx, cy, r = rng.randint(380, 700), rng.randint(250, 380), rng.randint(170, 230)
    d.ellipse((cx - r, cy - r // 3, cx + r, cy + r // 3), outline=(200, 190, 160, 255), width=10)
    for k in range(8):
        a = math.tau * k / 8
        d.line([(cx, cy), (cx + r * math.cos(a), cy + r / 3 * math.sin(a))], fill=(150, 140, 120, 255), width=3)
    _glow(img, cx, cy, 26, (255, 210, 140), 6)
    return img


def _deep_space(rng):
    img = _gradient((3, 3, 12), (30, 10, 46), rng)
    for color in rng.sample([(140, 60, 200), (40, 160, 190), (220, 70, 140), (90, 80, 230)], 3):
        _glow(img, rng.randrange(W), rng.randrange(H), rng.randint(180, 320), color, 90, 140)
    _stars(ImageDraw.Draw(img), rng, 420, depth=1.0)
    return img


def _alien_planets(rng):
    img = _gradient((20, 62, 72), (232, 138, 78), rng)
    _glow(img, rng.randint(150, 450), rng.randint(90, 200), 70, (240, 230, 210), 4)
    _glow(img, rng.randint(700, 1100), rng.randint(60, 160), 34, (200, 220, 240), 3)
    d = ImageDraw.Draw(img)
    _ridge(d, rng, 470, 90, (96, 46, 70, 255), step=60)
    _ridge(d, rng, 580, 60, (52, 24, 44, 255), step=45)
    return img


def _cyberpunk(rng):
    img = _gradient((14, 4, 34), (120, 18, 92), rng)
    d = ImageDraw.Draw(img)
    _skyline(d, rng, H, (18, 10, 32, 255), [(0, 230, 255, 255), (255, 60, 200, 255), (255, 200, 80, 255)], 260, 620)
    for _ in range(5):  # neon signage bars
        x, y = rng.randint(0, W - 300), rng.randint(200, 600)
        d.rectangle((x, y, x + rng.randint(100, 300), y + 3), fill=(255, 60, 200, 200))
    return img


def _japanese_streets(rng):
    img = _gradient((10, 14, 40), (44, 62, 112), rng)
    d = ImageDraw.Draw(img)
    _skyline(d, rng, 560, (16, 18, 34, 255), [(255, 196, 120, 255), (255, 150, 90, 255)], 120, 300, lit=0.25)
    d.rectangle((0, 560, W, H), fill=(22, 26, 48, 255))
    for x in range(60, W, rng.randint(140, 190)):
        y = rng.randint(470, 530)
        _glow(img, x, y, 12, (255, 140, 60), 5)
        _glow(img, x, 560 + (560 - y) // 2, 9, (255, 140, 60), 14, 120)  # wet-street reflection
    return img


def _cozy_rooms(rng):
    img = _gradient((58, 34, 24), (150, 92, 52), rng)
    d = ImageDraw.Draw(img)
    wx, wy = rng.randint(180, 420), 120
    d.rectangle((wx, wy, wx + 460, wy + 330), fill=(30, 44, 80, 255), outline=(40, 24, 16, 255), width=14)
    for _ in range(70):  # rain on the window
        x, y = rng.randint(wx + 10, wx + 450), rng.randint(wy + 10, wy + 300)
        d.line([(x, y), (x - 3, y + 18)], fill=(150, 170, 210, 160), width=1)
    _glow(img, rng.randint(900, 1100), 330, 120, (255, 190, 110), 60, 180)
    d.rectangle((0, 560, W, H), fill=(44, 26, 18, 255))
    return img


def _ps1_jungle(rng):
    img = _gradient((60, 150, 172), (172, 222, 182), rng)
    _glow(img, rng.randint(300, 1000), 150, 80, (255, 250, 220), 30, 230)
    d = ImageDraw.Draw(img)
    _ridge(d, rng, 420, 100, (58, 120, 86, 255), step=110)  # big steps = flat-shaded low-poly
    _ridge(d, rng, 520, 70, (34, 92, 60, 255), step=90)
    d.rectangle((0, 610, W, H), fill=(50, 150, 160, 255))
    for y in range(620, H, 14):
        d.line([(rng.randint(0, 300), y), (rng.randint(700, W), y)], fill=(120, 200, 200, 255), width=2)
    return img


def _fantasy(rng):
    img = _gradient((68, 40, 92), (242, 172, 92), rng)
    _glow(img, rng.randint(250, 1000), rng.randint(380, 470), 90, (255, 220, 150), 40, 230)
    d = ImageDraw.Draw(img)
    _ridge(d, rng, 500, 70, (70, 46, 88, 255), step=70)
    cx, base, castle = rng.randint(300, 980), 520, (40, 26, 54, 255)
    d.rectangle((cx - 130, base - 110, cx + 130, base + 20), fill=castle)
    for tx in (cx - 150, cx - 20, cx + 110):
        th = rng.randint(170, 250)
        d.rectangle((tx, base - th, tx + 40, base + 20), fill=castle)
        d.polygon([(tx - 8, base - th), (tx + 48, base - th), (tx + 20, base - th - 60)], fill=castle)
        _glow(img, tx + 20, base - th + 40, 5, (255, 190, 100), 2)
    _ridge(d, rng, 600, 40, (34, 22, 44, 255), step=50)
    return img


SCENES = {
    "space-stations": _space_stations, "deep-space": _deep_space, "alien-planets": _alien_planets,
    "cyberpunk-cities": _cyberpunk, "japanese-streets": _japanese_streets,
    "cozy-anime-rooms": _cozy_rooms, "ps1-jungle": _ps1_jungle, "fantasy-realms": _fantasy,
}


def _scene(theme: str, idx: int):
    return SCENES[theme](random.Random(f"{theme}-{idx}")).convert("RGB")


def _images(pipe: Path) -> None:
    images = pipe / "images"
    for theme, count in IMAGE_COUNTS.items():
        folder = images / theme
        folder.mkdir(parents=True, exist_ok=True)
        for i in range(1, count + 1):
            _scene(theme, i).save(folder / f"{theme}_{i:02d}.jpg", quality=86)
    # the warnings the Assets page shows for odd inputs
    _scene("ps1-jungle", 99).resize((720, 1280)).save(images / "ps1-jungle" / "ps1-jungle_portrait.jpg", quality=86)
    # a dropped custom thumbnail (the ◆ badge)
    thumb = _scene("space-stations", 50)
    ImageDraw.Draw(thumb).text((60, 60), "SPACE AMBIENT", fill=(255, 255, 255), font=_font(96))
    thumb.save(images / "space-stations" / "thumb.jpg", quality=88)
    used = images / "used"
    used.mkdir(exist_ok=True)
    for i, theme in enumerate(["ps1-jungle", "fantasy-realms", "japanese-streets", "space-stations"] * 3):
        _scene(theme, 200 + i).save(used / f"used_{theme}_{i + 1:02d}.jpg", quality=86)


def _font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1
        return ImageFont.load_default()


# ---------- ambient pads (stdlib only) ----------

def _pad(path: Path, chord, seconds=10, rate=16000) -> None:
    rng = random.Random(path.stem)
    table = [0.0] * rate
    for i, f in enumerate(chord):
        amp, phase = 0.16 / math.sqrt(i + 1), rng.random() * math.tau
        for n in range(rate):
            table[n] += amp * math.sin(math.tau * f * n / rate + phase)
    total, fade = seconds * rate, 2 * rate
    swell = rate * rng.uniform(4, 7)
    samples = array.array("h", (
        int(30000 * min(1.0, n / fade, (total - n) / fade)
            * (0.75 + 0.25 * math.sin(math.tau * n / swell)) * table[n % rate])
        for n in range(total)
    ))
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(samples.tobytes())


def _music(pipe: Path) -> None:
    for sub, tracks in (("library", LIBRARY_TRACKS), ("used", USED_TRACKS)):
        folder = pipe / "music" / sub
        folder.mkdir(parents=True, exist_ok=True)
        for name, chord in tracks.items():
            _pad(folder / f"{name}.wav", chord)


# ---------- credentials, history, raw clips ----------

def _placeholders(pipe: Path) -> None:
    """Token *files* exist so the status chips read 'present' — the studio only
    ever checks presence, never contents. None of these are real credentials."""
    for name in ("client_secret.json", "youtube_token.json", "youtube_analytics_token.json"):
        (pipe / name).write_text(json.dumps({"demo": "placeholder — not a credential"}))
    logs = pipe / "logs"
    logs.mkdir(exist_ok=True)
    today = dt.date.today()
    history = {"ps1-jungle": 3, "fantasy-realms": 9, "japanese-streets": 18, "space-stations": 33}
    (logs / "theme_history.json").write_text(json.dumps(
        {t: (today - dt.timedelta(days=d)).isoformat() + "T19:00:00" for t, d in history.items()}))
    (pipe / "output" / "veo_slow").mkdir(parents=True, exist_ok=True)


def _clips(downloads: Path, pipe: Path) -> None:
    """Raw 'Veo exports' (slow pans over sample scenes) + a partly built bank and
    the leftovers the Housekeeping card exists to find. Needs ffmpeg."""
    if not shutil.which("ffmpeg"):
        print("[demo] ffmpeg not found — skipping sample video clips (pages still work)")
        return
    downloads.mkdir(parents=True, exist_ok=True)
    tmp = downloads / "_frame.jpg"
    names = ["Untitled video.mp4"] + [f"Untitled video ({i}).mp4" for i in range(1, 4)]
    for i, name in enumerate(names):
        _scene("fantasy-realms", 300 + i).save(tmp, quality=90)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-t", "5", "-i", str(tmp),
                        "-vf", "scale=800:450,crop=640:360:'(iw-ow)*t/5':(ih-oh)/2,fps=24",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-pix_fmt", "yuv420p",
                        str(downloads / name)], check=True)
    tmp.unlink()
    raw = sorted(downloads.glob("Untitled video*.mp4"))
    bank, out = pipe / "output" / "veo_slow", pipe / "output"
    for i, src in enumerate(raw[:2], 1):  # two of four already enhanced ("banked")
        shutil.copyfile(src, bank / f"veo_{i:02d}_1440p.mp4")
    shutil.copyfile(raw[0], bank / "veo_01.mp4")  # legacy pre-upscale twin → housekeeping
    shutil.copyfile(raw[0], out / "fantasy_veo_reel.mp4")  # silent pre-mux build…
    shutil.copyfile(raw[0], out / "fantasy_veo_reel_final.mp4")  # …and its final sibling
