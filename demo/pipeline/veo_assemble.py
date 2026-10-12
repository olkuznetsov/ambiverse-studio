"""Demo stand-in for veo_assemble.build_shuffled — clips → reels with the scene
order reshuffled every cycle → looped to length → optional music mux."""
from pathlib import Path

from _demo import join_clips, pause, say


def build_shuffled(clips, output, duration, music=None) -> Path:
    cycles = max(2, min(6, int(duration) // 1200))
    say(f"[veo_assemble] shuffled build: {cycles} cycles")
    for c in range(1, cycles + 1):
        pause(1.2)
        say(f"[veo_assemble] building reel {c}/{cycles} (scene order reshuffled)")
    say("[veo_assemble] muxing music" if music else "[veo_assemble] silent build (no music)")
    join_clips([Path(c) for c in clips], Path(output), audio=Path(music) if music else None)
    return Path(output)
