"""Demo stand-in for build_veo.py — enhance raw Veo exports into the clip bank.

The real pipeline crops the watermark, drops duplicate padding frames, upscales
with Real-ESRGAN and interpolates with RIFE (~35 min per clip). Here each
"enhanced" clip is a copy, but the progress markers match the real run.
"""
import os
import shutil

from _demo import DOWNLOADS, OUTPUT, pause, say


def main() -> None:
    upscale = os.getenv("VEO_UPSCALE", "").lower() in ("1", "true", "yes")
    height = int(os.getenv("VEO_TARGET_H") or 1440) if upscale else 1080
    sources = sorted(DOWNLOADS.glob("Untitled video*.mp4"))
    if not sources:
        raise SystemExit("no 'Untitled video*.mp4' clips in the demo downloads folder")
    bank = OUTPUT / "veo_slow"
    bank.mkdir(parents=True, exist_ok=True)
    say(f"[build_veo] {len(sources)} clips | upscale={upscale} target={height}p")
    for i, src in enumerate(sources, 1):
        out = bank / f"veo_{i:02d}_{height}p.mp4"
        if out.exists():
            say(f"[build_veo] ({i}/{len(sources)}) cached {out.name}")
            continue
        say(f"[build_veo] ({i}/{len(sources)}) slowmo {src.name}")
        if upscale:
            for frame in range(12, 49, 12):
                pause(0.6)
                say(f"[esrgan]   {frame}/48")
        pause(1)
        shutil.copyfile(src, out)
        say(f"[veo_slowmo] {src.name}: 48 real frames -> {out.name} @ 30fps")
    say("[build_veo] DONE (clips enhanced + reel)")


if __name__ == "__main__":
    main()
