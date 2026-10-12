"""Progress bars are parsed from the pipeline's own log markers."""
import progress

MAIN_RENDER = """[2026-07-18T02:00:00] Theme: ps1-jungle (20 images planned)
Rendering 20 clips across 1 parallel worker(s)...
  clip 7/20 done: a.png
"""


def test_main_build_render_phase():
    assert progress.parse("main_build", MAIN_RENDER) == {"stage": "rendering clip 7/20", "pct": 35}


def test_main_build_depthflow_phase():
    assert progress.parse("main_build", "[df_batch] 3/12 variant=sway -> clip_03.mp4")["pct"] == 25


def test_main_build_concat_then_upload():
    concat = MAIN_RENDER + "Concatenating clips with crossfades...\n"
    assert progress.parse("main_build", concat)["pct"] is None
    upload = concat + "[2026-07-18T04:10:00] Uploading to YouTube...\n[upload] 12%\n[upload] 43%\n"
    assert progress.parse("main_build", upload) == {"stage": "uploading to YouTube 43%", "pct": 43}


def test_veo_full_enhance_with_esrgan_subprogress():
    log = "[full] (2/4) enhance Untitled video (1).mp4\n[esrgan]   24/48\n"
    assert progress.parse("veo_full", log) == {
        "stage": "enhancing clip 2/4 — ESRGAN 24/48", "pct": round((1 + 0.5) / 4 * 85)}


def test_veo_full_assembly_then_publish():
    assembly = "[full] building 7200s music bed from library...\n[veo_assemble] shuffled build: 4 cycles\n" \
               "[veo_assemble] building reel 1/4\n[veo_assemble] building reel 2/4\n"
    assert progress.parse("veo_full", assembly)["stage"] == "assembling reel 2/4 + music"
    publishing = assembly + "[full] DONE -> x.mp4\n[veo_publish] main upload starting\n[upload] 61%\n"
    assert progress.parse("veo_full", publishing)["stage"] == "publish: uploading 61%"
    assert progress.parse("veo_full", publishing + "[veo_publish] DONE\n")["pct"] == 100


def test_short_build_upload():
    assert progress.parse("short_build", "[short] built x\n[upload] 88%\n") == {"stage": "uploading 88%", "pct": 88}
    assert progress.parse("short_build", "[short] building...\n") is None


def test_unparseable_logs_yield_nothing():
    assert progress.parse("main_build", "") is None
    assert progress.parse("generate_prompts", "anything") is None
