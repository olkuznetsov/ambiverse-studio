"""Demo stand-in for main.py — the full build: render → thumbnail → Shorts → upload.

A real 2-hour render takes hours; this one takes ~30 seconds but prints the
real progress markers (`Rendering N clips…`, `clip i/N done`, `[df_batch] i/N`,
`[upload] N%`), so Studio's progress bars, live log and job states behave
exactly as they do for the real thing. Nothing is uploaded anywhere.
"""
import datetime as dt
import os
import sys

import config
from _demo import (OUTPUT, fake_id, human_duration, library_tracks, pause, say, slideshow,
                   stamp, theme_images, thumbnail, upload_bar)


def eligible_theme():
    ready = [(t, theme_images(t)) for t in config.THEMES]
    ready = [(t, imgs) for t, imgs in ready if len(imgs) >= config.MIN_IMAGES_PER_THEME]
    return max(ready, key=lambda r: len(r[1]), default=(None, []))


def main() -> None:
    duration = int(os.getenv("VIDEO_DURATION_SECONDS") or config.VIDEO_DURATION_SECONDS)
    animate = os.getenv("ANIMATE", "")
    upload = os.getenv("YOUTUBE_UPLOAD", "false").lower() == "true"
    make_shorts = os.getenv("MAKE_SHORTS", "true").lower() != "false"
    n_shorts = int(os.getenv("SHORTS_PER_VIDEO") or 3)
    music_mode = os.getenv("MUSIC_MODE") or config.MUSIC_MODE

    theme, images = eligible_theme()
    if theme is None:
        stamp(f"Preflight failed: no theme has >= {config.MIN_IMAGES_PER_THEME} unused images.")
        sys.exit(1)
    cap = int(os.getenv("NUM_IMAGES_PER_VIDEO") or 0)
    images = images[: cap or len(images)]
    n = len(images)
    world = config.THEMES[theme].get("motif") or theme.replace("-", " ").title()
    title = f"{world} — {human_duration(duration)} Ambient for Deep Focus & Sleep"

    stamp(f"Theme: {theme} ({n} images planned)")
    stamp(f"Title: {title}")
    stamp(f"Music: {music_mode} mode")
    pause(1)

    if animate == "depthflow":
        variants = ("orbital drift", "horizontal sway", "dolly breathe", "diagonal")
        for i, img in enumerate(images, 1):
            pause(1.2)
            say(f"[df_batch] {i}/{n} variant={variants[i % 4]} -> clip_{i:02d}.mp4 ({img.name})")
    else:
        say(f"Each image: {max(1, duration // n)}s with Ken Burns motion")
        say(f"Rendering {n} clips across 1 parallel worker(s)...")
        for i, img in enumerate(images, 1):
            pause(1.5)
            say(f"  clip {i}/{n} done: {img.name}")
    say("Concatenating clips with crossfades...")
    pause(2)

    run = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    tracks = library_tracks() if music_mode == "library" else []
    video = OUTPUT / f"{run}_video.mp4"
    slideshow(images[:6], video, audio=tracks[0] if tracks else None)
    thumbnail(images[0], world, OUTPUT / f"{run}_thumbnail.jpg")
    stamp("Thumbnail + 2 A/B variants saved")

    if make_shorts:
        for k in range(1, n_shorts + 1):
            pause(1)
            short = OUTPUT / f"{run}_short{'' if k == 1 else k}.mp4"
            slideshow([images[(2 * k) % n]], short, seconds_each=6.0, size=(360, 640),
                      audio=tracks[k % len(tracks)] if tracks else None)
            stamp(f"Short {k}/{n_shorts} built: {short.name}")

    say("[demo] images stay in place (the real pipeline moves them to images/used/) "
        "so the demo stays replayable")
    if upload:
        stamp("Uploading to YouTube...")
        upload_bar()
        stamp(f"Uploaded: https://youtu.be/{fake_id()}  (demo — nothing left this machine)")
    else:
        stamp("YOUTUBE_UPLOAD=false — skipping upload.")
    stamp(f"Done. Video: {video}")


if __name__ == "__main__":
    main()
