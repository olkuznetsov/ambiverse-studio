"""Demo stand-in for make_music.build_track — a crossfaded music bed from the library."""
from pathlib import Path

from _demo import concat_audio, library_tracks, pause, say


def build_track(output, duration):
    tracks = library_tracks()
    if not tracks:
        return None
    say(f"  crossfading {len(tracks)} library tracks into a {float(duration):.0f}s bed...")
    pause(1.5)
    concat_audio(tracks, Path(output))
    return Path(output), [t.stem for t in tracks]
