"""Shared helpers for the demo stand-in pipeline.

Each stand-in script prints the same progress markers as the real pipeline
(`clip i/N done`, `[esrgan] i/N`, `[upload] N%`, ...), so Ambiverse Studio's job
engine, live logs and progress bars run unmodified. Instead of hour-long
renders they sleep briefly and, when ffmpeg is available, write small real
videos built from the sample assets.

DEMO_SPEED scales every pause (tests run with a large value).
"""
import datetime as dt
import os
import random
import shutil
import subprocess
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
IMAGES = BASE / "images"
OUTPUT = BASE / "output"
LOGS = BASE / "logs"
LIBRARY = BASE / "music" / "library"
DOWNLOADS = BASE.parent / "downloads"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
SPEED = max(0.01, float(os.getenv("DEMO_SPEED", "1")))


def say(msg: str = "") -> None:
    print(msg, flush=True)


def stamp(msg: str) -> None:
    """The real main.py's log_line format: `[ISO-timestamp] message`."""
    say(f"[{dt.datetime.now().isoformat(timespec='seconds')}] {msg}")


def pause(seconds: float) -> None:
    time.sleep(seconds / SPEED)


def fake_id() -> str:
    return "demo" + "".join(random.choices("abcdefghijkmnpqrstuvwxyz23456789", k=7))


def human_duration(seconds: int) -> str:
    if seconds >= 3600:
        return f"{seconds / 3600:g} Hours"
    if seconds >= 60:
        return f"{seconds // 60} Minutes"
    return f"{seconds} Seconds"


def upload_bar(step: float = 0.5) -> None:
    """The tagged chunk progress the real resumable upload prints."""
    for pct in (4, 13, 27, 41, 56, 70, 84, 95, 100):
        pause(step)
        say(f"[upload] {pct}%")


def theme_images(theme: str) -> list[Path]:
    folder = IMAGES / theme
    if not folder.is_dir():
        return []
    return sorted(p for p in folder.iterdir()
                  if p.suffix.lower() in IMAGE_EXTS and p.stem.lower() != "thumb")


def library_tracks() -> list[Path]:
    return sorted(LIBRARY.glob("*.wav")) if LIBRARY.is_dir() else []


def have_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def _render(inputs: list[str], n: int, out: Path, size: tuple[int, int],
            audio: Path | None) -> bool:
    """Cover-crop each video input to `size`, concat, optionally mux looped audio."""
    if not have_ffmpeg():
        say(f"[demo] ffmpeg not found — skipped writing {out.name}")
        return False
    w, h = size
    chains = "".join(
        f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,fps=24[v{i}];"
        for i in range(n)
    )
    graph = chains + "".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[out]"
    args = [*inputs]
    maps = ["-map", "[out]"]
    if audio and audio.exists():
        args += ["-stream_loop", "-1", "-i", str(audio)]
        maps += ["-map", f"{n}:a", "-shortest", "-c:a", "aac", "-b:a", "96k"]
    out.parent.mkdir(parents=True, exist_ok=True)
    _ffmpeg(*args, "-filter_complex", graph, *maps,
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-pix_fmt", "yuv420p", str(out))
    return True


def slideshow(images: list[Path], out: Path, *, seconds_each: float = 2.0,
              size: tuple[int, int] = (640, 360), audio: Path | None = None) -> bool:
    inputs = []
    for img in images:
        inputs += ["-loop", "1", "-t", f"{seconds_each}", "-i", str(img)]
    return _render(inputs, len(images), out, size, audio)


def join_clips(clips: list[Path], out: Path, *, size: tuple[int, int] = (640, 360),
               audio: Path | None = None) -> bool:
    inputs = []
    for clip in clips:
        inputs += ["-i", str(clip)]
    return _render(inputs, len(clips), out, size, audio)


def concat_audio(tracks: list[Path], out: Path) -> bool:
    if not (have_ffmpeg() and tracks):
        return False
    inputs = []
    for t in tracks:
        inputs += ["-i", str(t)]
    graph = "".join(f"[{i}:a]" for i in range(len(tracks))) + f"concat=n={len(tracks)}:v=0:a=1[a]"
    _ffmpeg(*inputs, "-filter_complex", graph, "-map", "[a]", "-b:a", "128k", str(out))
    return True


def thumbnail(image: Path, title: str, out: Path) -> None:
    """1280x720 thumbnail: the scene plus a title band (Pillow ships with Studio)."""
    from PIL import Image, ImageDraw, ImageFont

    with Image.open(image) as im:
        im = im.convert("RGB").resize((1280, 720))
    draw = ImageDraw.Draw(im, "RGBA")
    draw.rectangle((0, 560, 1280, 720), fill=(0, 0, 0, 140))
    try:
        font = ImageFont.load_default(size=64)
    except TypeError:  # Pillow < 10.1
        font = ImageFont.load_default()
    draw.text((48, 600), title.upper(), fill=(255, 255, 255), font=font)
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, "JPEG", quality=88)
