"""Demo stand-in for generate_prompts.py.

The real script asks an LLM (Groq) for 4 scenes × 5 variations and 20 music
prompts per theme. This one replays a real run (fixture_prompts.json) dated
today, writing the same files: logs/prompts_<date>.json and
images/<theme>/today_prompt.txt (with its THUMBNAIL section).
"""
import datetime as dt
import json
import os

import config
from _demo import BASE, IMAGES, LOGS, pause, say

BAR = "═" * 55


def prompt_txt(theme: str, date: str, scenes: list, thumb: str | None) -> str:
    style = config.THEMES[theme].get("base_style", config.BASE_STYLE_PROMPT)
    lines = [BAR, f"{theme.upper()} — {date} — {len(scenes)} SCENES (each with variations)", BAR, "",
             "STYLE (always include with every image):", style, ""]
    for i, s in enumerate(scenes, 1):
        lines += [f"── SCENE {i} of {len(scenes)} ──", s["scene"], "",
                  "  Variations — paste STYLE + this scene + ONE directive per image:"]
        lines += [f"    {k}. {v}" for k, v in enumerate(s.get("variations", []), 1)]
        lines.append("")
    if thumb:
        lines += [BAR, "THUMBNAIL — paste into ChatGPT for the video's thumbnail; "
                       "save the result as thumb.png in this folder", BAR, thumb, ""]
    lines += ["HOW TO USE:",
              "  1. For each image, paste:  STYLE  +  the SCENE  +  ONE variation directive.",
              "  2. Set 16:9 / landscape (wide) — square/portrait images get center-cropped."]
    return "\n".join(lines) + "\n"


def main() -> None:
    run = json.loads((BASE / "fixture_prompts.json").read_text())
    thumbs = json.loads((BASE / "fixture_thumbnails.json").read_text())
    date = os.getenv("DEMO_DATE") or dt.date.today().isoformat()
    run["date"] = date
    for theme in config.THEMES:
        scenes = run["scenes"].get(theme, [])
        variations = sum(len(s.get("variations", [])) for s in scenes)
        say(f"Generating {len(scenes)} scenes (×5 variations) for {theme}...")
        pause(0.8)
        path = IMAGES / theme / "today_prompt.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(prompt_txt(theme, date, scenes, thumbs.get(theme)))
        say(f"  wrote {len(scenes)} scenes + {variations} variations → {path.relative_to(BASE)}")
        say(f"Generating music prompts for {theme}...")
        pause(0.4)
        say(f"  {len(run['music_prompts'].get(theme, []))} music prompts generated")
    LOGS.mkdir(parents=True, exist_ok=True)
    (LOGS / f"prompts_{date}.json").write_text(json.dumps(run, indent=1, ensure_ascii=False))
    say(f"Saved logs/prompts_{date}.json")


if __name__ == "__main__":
    main()
