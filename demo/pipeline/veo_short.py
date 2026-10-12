"""Demo stand-in for veo_short.build_veo_short — a vertical Short from an enhanced clip
(center-crop 16:9 → 9:16, loop, title + music)."""
from pathlib import Path

from _demo import join_clips, pause, say


def build_veo_short(clip, music, title, output) -> Path:
    say(f"  center-cropping {Path(clip).name} to 9:16 and looping...")
    pause(2)
    say("  muxing music + title overlay...")
    join_clips([Path(clip)], Path(output), size=(360, 640), audio=Path(music))
    return Path(output)
