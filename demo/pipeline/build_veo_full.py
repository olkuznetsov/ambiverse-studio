"""Demo stand-in for build_veo_full.py — one unattended run:

enhance every raw clip → music bed from the library → shuffled long-form
assembly → manifest → (PUBLISH=1) metadata, scheduled upload, staggered Shorts.

Same progress markers as the real run; nothing leaves the machine.
"""
import datetime as dt
import json
import os
import shutil

from _demo import (DOWNLOADS, OUTPUT, concat_audio, fake_id, human_duration, join_clips,
                   library_tracks, pause, say, upload_bar)


def main() -> None:
    theme = os.getenv("VEO_THEME") or "fantasy-realms"
    upscale = os.getenv("VEO_UPSCALE", "").lower() in ("1", "true", "yes")
    height = int(os.getenv("VEO_TARGET_H") or 1440) if upscale else 1080
    duration = int(os.getenv("VIDEO_DURATION_SECONDS") or 7200)
    publish = os.getenv("PUBLISH") == "1"

    sources = sorted(DOWNLOADS.glob("Untitled video*.mp4"))
    if not sources:
        raise SystemExit("no 'Untitled video*.mp4' clips in the demo downloads folder")
    bank = OUTPUT / "veo_slow"
    bank.mkdir(parents=True, exist_ok=True)
    clips = []
    for i, src in enumerate(sources, 1):
        out = bank / f"veo_{i:02d}_{height}p.mp4"
        if out.exists():
            say(f"[full] ({i}/{len(sources)}) cached {out.name}")
        else:
            say(f"[full] ({i}/{len(sources)}) enhance {src.name}")
            for frame in range(12, 49, 12):
                pause(0.5)
                say(f"[esrgan]   {frame}/48")
            shutil.copyfile(src, out)
        clips.append(out)

    tracks = library_tracks()
    bed = OUTPUT / "veo_music_bed.mp3"
    say(f"[full] building {duration}s music bed from library...")
    pause(1.5)
    concat_audio(tracks, bed)
    say(f"[full] music bed: {bed.name} ({len(tracks)} unique tracks)")

    cycles = max(2, min(6, duration // 1200))
    say(f"[veo_assemble] shuffled build: {cycles} cycles")
    for c in range(1, cycles + 1):
        pause(1.2)
        say(f"[veo_assemble] building reel {c}/{cycles} (scene order reshuffled)")
    video = OUTPUT / f"{theme}_veo_{human_duration(duration).replace(' ', '').lower()}.mp4"
    join_clips(clips, video, audio=bed if bed.exists() else None)

    manifest_path = OUTPUT / f"veo_{theme}_manifest.json"
    manifest = {"theme": theme, "video": str(video), "clips": [str(c) for c in clips],
                "track_names": [t.stem for t in tracks], "duration": duration,
                "target_h": height, "built_at": dt.datetime.now().isoformat(timespec="seconds")}
    manifest_path.write_text(json.dumps(manifest, indent=2))
    say(f"[full] DONE -> {video}\n[full] manifest -> {manifest_path}")

    if publish:
        say("[veo_publish] metadata: deterministic title + description (no invented scenes)")
        say("[veo_publish] main upload starting")
        upload_bar()
        manifest["main_video_id"] = fake_id()
        say(f"[veo_publish] main: https://youtu.be/{manifest['main_video_id']}")
        manifest["short_ids"] = {}
        for k in range(1, 4):
            say(f"[veo_publish] short {k}/3 — scheduled +{2 * k}d")
            upload_bar(step=0.2)
            manifest["short_ids"][str(k)] = fake_id()
        manifest_path.write_text(json.dumps(manifest, indent=2))
        say("[veo_publish] DONE — main + 3/3 shorts (demo — nothing left this machine)")


if __name__ == "__main__":
    main()
