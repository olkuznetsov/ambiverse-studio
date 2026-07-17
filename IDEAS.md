# IDEAS — what Studio + the pipeline could become

*2026-07-18. A curated roadmap from a deep pass over the whole system: what's missing,
what compounds, what's deliberately cut. Studio session: treat "Now" items as a backlog;
everything else needs Sasha's go.*

The lens: Studio is quietly becoming a **local-first production OS for AI media** —
intake → enhancement (ESRGAN/RIFE) → assembly → metadata → distribution → analytics.
YouTube is the first consumer, not the boundary.

---

## Now — gaps that will bite soon (small, concrete)

1. **Upload progress.** The 8 GB upload is a 4-hour black box ("uploading…"). `upload_youtube._retriable_chunk_upload` already loops chunks — print `[upload] N%` per chunk and let `progress.py`/Studio parse it. *One print statement away from a real bar.*
2. **A/B format tracker — the decision the channel actually faces.** Veo-vs-image is THE open question. Manifests now record which videos are Veo; add a `format` dimension to the Channel rollup (Veo living-world vs Ken Burns/DepthFlow, retention + AVD side by side, per theme). This turns "maybe we move this way" into a read-off-the-screen answer.
3. **Publish-event markers on the growth charts.** Studio banks daily snapshots + knows every publishAt. Overlay upload events on the subs/views sparklines → see which video/short moved the needle (approximates the shorts→long conversion no API exposes).
4. **Music-bed length fix.** `make_music.build_track(bed, 7200)` returns ~93 min (crossfade accounting) → bed loops with a mid-video seam. Fix: top up tracks until *post-crossfade* length ≥ target. (Pipeline-side, `make_music.py`.)
5. **Bank housekeeping.** `output/veo_slow/` holds legacy `veo_NN` + new `<theme>_NN` names, plus obsolete 1080p versions; old test outputs accumulate (a silent 4 GB `fantasy_veo_2h.mp4`, `_VEO_TEST_*`…). A Studio "housekeeping" card: size-sorted stale files → one-click trash. Disk is a real constraint (8 GB per video).
6. **Hard disk-space guard** in `build_veo_full` preflight (need ~15 GB free): fail fast, not at hour 5.
7. **Veo intake by folder (multi-theme batches).** 8 themes of "Untitled video*.mp4" through one Downloads folder is now the bottleneck-by-convention: process each batch before generating the next. Folder-first alternative honoring Sasha's preference: drop per theme into `clips/<theme>/veo_raw/` and let build read from there too (`VEO_SRC_DIR`), Downloads stays the quick path.

## Next — leverage on what already exists

8. **24/7 live stream manager.** `live_stream.py` already exists, and the Veo living-world loop is *exactly* the lofi-girl format where a small scene set is the norm. Once a theme proves out: Studio card to start/stop/monitor the stream (ffmpeg → RTMP health, auto-restart, caffeinate). Streams sidestep the impressions bottleneck — they're discovered via live-tab + search.
9. **8-hour sleep variants.** Same reel, `VIDEO_DURATION_SECONDS=28800` — the research memory already flagged: one 8h video ≈ 4,000 watch-hours at ~500 plays. Near-zero marginal cost with banked clips; the YPP watch-hours accelerator.
10. **Export tray for manual platforms.** TikTok/IG APIs stay hostile; make manual posting 30 seconds: a "ready to post" view per Short — file + pre-written caption/hashtags + copy buttons, checkbox when posted.
11. **Notifications beyond the desk.** Job-done/failed → Telegram bot ping (he's away during 5h builds). ~20 lines.
12. **Thumbnail A/B on schedule.** Studio knows publish dates; remind + track Test&Compare results in the impressions log (CTR is the channel's weakest number: 2%).

## Beyond YouTube — the "this is more than a channel app" directions

13. **Etsy digital products — the rail is already validated.** Memory: for UA sellers, **Etsy+Payoneer works** (Gumroad/Ko-fi/Payhip don't). The pipeline's outputs *are* products: 2h ambient MP3 mixes, living-world loop packs (desktop wallpaper engines, stream backgrounds), themed sleep bundles. Same assets, second revenue rail, no new production work. The most concrete "not only YouTube" move on the board.
14. **The enhancement toolbox as its own tool.** dedupe→RIFE→ESRGAN ("make any soft AI clip smooth, crisp and long") is genuinely reusable — wallpaper/screensaver markets, stream overlays, digital signage, meditation/spa screens. Could be a tiny standalone CLI/app ("ClipForge"?) — or simply a well-written README chapter that makes the capability legible to employers.
15. **Multi-channel / multi-brand.** Config-per-channel (tokens, themes, branding, schedule) → one Studio running N channels. If one world outgrows the roster (fantasy?), it graduates into its own channel without new tooling.
16. **Portfolio framing (career transition).** Studio is a real full-stack AI-ops system: local job orchestration (process groups, queues, SSE), media pipelines, API integrations, analytics. Write the README/case-study to say that explicitly — "control plane for an AI media pipeline" — it's a stronger story than "YouTube helper app". Public repo already exists; the story is the missing piece.
17. **Music catalog second life.** 40+ Suno tracks per batch accumulate into a catalog. Options when volume justifies: DistroKid→streaming (check Suno commercial terms on his plan + platform AI policies first), or bundle into the Etsy products above. Park until the channel decision lands.

## Deliberately NOT building (decided before, still right)

- **Market/trend analyzer** — channel is reach-limited; the retention rollup already answers "what next" (premature at this scale).
- **ChatGPT/Suno web automation** — ToS/ban risk; the two manual steps are the human taste-gates by design.
- **config.py editing from the UI** — themes change ~monthly; a text editor is safer than a config-editor feature.
- **Instagram/TikTok API integrations** — repeatedly hostile; the export tray (#10) is the 80/20.
