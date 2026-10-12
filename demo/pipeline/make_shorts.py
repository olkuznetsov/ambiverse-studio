"""Demo stand-in for make_shorts.build_short — a vertical Short from one image."""
from pathlib import Path

from _demo import pause, say, slideshow


def build_short(image, music_source, title, theme, output) -> Path:
    say(f"  rendering vertical 2.5D loop ({theme})...")
    pause(2)
    say(f"  slicing music from {Path(music_source).name}...")
    pause(1)
    say("  compositing final Short (title overlay)...")
    slideshow([Path(image)], Path(output), seconds_each=8.0, size=(360, 640),
              audio=Path(music_source))
    return Path(output)
