import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  createJob, fetchMusic, fetchOverview, fetchPreflight, fetchUsedImages,
  fetchVeoSources, fmtBytes, imgUrl, vthumbUrl,
} from '../api'
import LogViewer from '../components/LogViewer'

/* ---------- small form atoms ---------- */

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <div className="text-[11px] uppercase tracking-wider text-dusk-400 mb-1">{label}</div>
      {children}
    </label>
  )
}

const inputCls =
  'w-full rounded-lg border border-dusk-700 bg-dusk-950 px-2.5 py-1.5 text-xs text-dusk-200 focus:border-accent-400 focus:outline-none'

function Seg<T extends string>({ value, onChange, options }: {
  value: T
  onChange: (v: T) => void
  options: { value: T; label: string }[]
}) {
  return (
    <div className="flex rounded-lg border border-dusk-700 overflow-hidden w-fit">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => onChange(o.value)}
          className={`px-3 py-1.5 text-xs ${
            value === o.value ? 'bg-accent-500/20 text-accent-300' : 'bg-dusk-950 text-dusk-400 hover:text-dusk-200'
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className="flex items-center gap-2 text-xs text-dusk-300"
    >
      <span
        className={`inline-flex h-4.5 w-8 items-center rounded-full p-0.5 transition-colors ${
          checked ? 'bg-accent-500' : 'bg-dusk-700'
        }`}
      >
        <span
          className={`h-3.5 w-3.5 rounded-full bg-white transition-transform ${checked ? 'translate-x-3.5' : ''}`}
        />
      </span>
      {label}
    </button>
  )
}

function QueuedBanner({ jobId, onDone }: { jobId: number; onDone: () => void }) {
  return (
    <div className="mt-4">
      <div className="mb-2 flex items-center justify-between text-xs text-dusk-400">
        <span>live output — job #{jobId}</span>
        <Link to="/jobs" className="text-accent-400 hover:text-accent-300">
          open in Jobs →
        </Link>
      </div>
      <LogViewer jobId={jobId} onEnd={onDone} />
    </div>
  )
}

/* ---------- main build wizard ---------- */

const DUR_PRESETS = [
  { label: '30s test', value: 30 },
  { label: '10 min', value: 600 },
  { label: '1 hour', value: 3600 },
  { label: '2 hours', value: 7200 },
]

function MainBuild() {
  const qc = useQueryClient()
  const [animate, setAnimate] = useState<'' | 'depthflow'>('')
  const [duration, setDuration] = useState(7200)
  const [numImages, setNumImages] = useState(0)
  const [flavor, setFlavor] = useState('')
  const [musicMode, setMusicMode] = useState<'library' | 'silent' | 'auto'>('library')
  const [makeShorts, setMakeShorts] = useState(true)
  const [shortsPer, setShortsPer] = useState(3)
  const [shortsSpacing, setShortsSpacing] = useState(2)
  const [upload, setUpload] = useState(false)
  const [privacy, setPrivacy] = useState<'private' | 'unlisted' | 'public'>('private')
  const [publishUtc, setPublishUtc] = useState('19:00')
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [preset, setPreset] = useState('')
  const [crf, setCrf] = useState('')
  const [supersample, setSupersample] = useState('')
  const [jobId, setJobId] = useState<number | null>(null)

  const preflight = useQuery({
    queryKey: ['preflight', upload, musicMode, animate],
    queryFn: () => fetchPreflight(upload, musicMode, animate),
  })

  const env = useMemo(() => {
    const e: Record<string, string> = {
      VIDEO_DURATION_SECONDS: String(duration),
      MUSIC_MODE: musicMode,
      YOUTUBE_UPLOAD: upload ? 'true' : 'false',
    }
    if (animate) e.ANIMATE = animate
    if (numImages > 0) e.NUM_IMAGES_PER_VIDEO = String(numImages)
    if (flavor.trim()) e.VIDEO_FLAVOR = flavor.trim()
    if (!makeShorts) e.MAKE_SHORTS = 'false'
    else {
      if (shortsPer !== 3) e.SHORTS_PER_VIDEO = String(shortsPer)
      if (shortsSpacing !== 2) e.SHORTS_SPACING_DAYS = String(shortsSpacing)
    }
    if (upload) {
      e.YOUTUBE_PRIVACY = privacy
      if (privacy === 'public' && publishUtc.trim()) e.SCHEDULED_PUBLISH_UTC = publishUtc.trim()
    }
    if (preset) e.RENDER_PRESET = preset
    if (crf) e.RENDER_CRF = crf
    if (supersample) e.RENDER_SUPERSAMPLE = supersample
    return e
  }, [animate, duration, numImages, flavor, musicMode, makeShorts, shortsPer, shortsSpacing, upload, privacy, publishUtc, preset, crf, supersample])

  const command = `${Object.entries(env).map(([k, v]) => `${k}=${v}`).join(' ')} venv/bin/python main.py`

  const queue = useMutation({
    mutationFn: () => createJob('main_build', {}, env),
    onSuccess: (job) => {
      setJobId(job.id)
      qc.invalidateQueries({ queryKey: ['jobs'] })
    },
  })

  return (
    <div className="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-4">
      <section className="rounded-xl border border-dusk-800 bg-dusk-900 p-4 space-y-4">
        <Field label="Animation">
          <Seg
            value={animate}
            onChange={setAnimate}
            options={[
              { value: '', label: 'Ken Burns (classic)' },
              { value: 'depthflow', label: 'DepthFlow 2.5D' },
            ]}
          />
        </Field>

        <Field label="Duration">
          <div className="flex items-center gap-2">
            <Seg
              value={String(DUR_PRESETS.some((p) => p.value === duration) ? duration : 'custom')}
              onChange={(v) => v !== 'custom' && setDuration(Number(v))}
              options={DUR_PRESETS.map((p) => ({ value: String(p.value), label: p.label }))}
            />
            <input
              type="number"
              min={10}
              value={duration}
              onChange={(e) => setDuration(Number(e.target.value))}
              className={`${inputCls} w-24`}
            />
            <span className="text-[11px] text-dusk-500">seconds</span>
          </div>
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Image cap (0 = use all)">
            <input type="number" min={0} value={numImages} onChange={(e) => setNumImages(Number(e.target.value))} className={inputCls} />
          </Field>
          <Field label="Flavor (only if assets fit, e.g. Rainy)">
            <input value={flavor} onChange={(e) => setFlavor(e.target.value)} placeholder="neutral" className={inputCls} />
          </Field>
        </div>

        <Field label="Music">
          <Seg
            value={musicMode}
            onChange={setMusicMode}
            options={[
              { value: 'library', label: 'Library (Suno)' },
              { value: 'silent', label: 'Silent (test)' },
              { value: 'auto', label: 'MusicGen' },
            ]}
          />
        </Field>

        <div className="space-y-2.5 rounded-lg border border-dusk-800 bg-dusk-950/60 p-3">
          <Toggle checked={makeShorts} onChange={setMakeShorts} label="Cut Shorts from this render" />
          {makeShorts && (
            <div className="grid grid-cols-2 gap-3 pl-10">
              <Field label="Shorts per video">
                <input type="number" min={1} max={5} value={shortsPer} onChange={(e) => setShortsPer(Number(e.target.value))} className={inputCls} />
              </Field>
              <Field label="Spacing (days)">
                <input type="number" min={1} value={shortsSpacing} onChange={(e) => setShortsSpacing(Number(e.target.value))} className={inputCls} />
              </Field>
            </div>
          )}
        </div>

        <div className="space-y-2.5 rounded-lg border border-dusk-800 bg-dusk-950/60 p-3">
          <Toggle checked={upload} onChange={setUpload} label="Upload to YouTube when done" />
          {upload && (
            <div className="grid grid-cols-2 gap-3 pl-10">
              <Field label="Privacy">
                <Seg
                  value={privacy}
                  onChange={setPrivacy}
                  options={[
                    { value: 'private', label: 'private' },
                    { value: 'unlisted', label: 'unlisted' },
                    { value: 'public', label: 'public' },
                  ]}
                />
              </Field>
              {privacy === 'public' && (
                <Field label="Publish at (UTC, empty = now)">
                  <input value={publishUtc} onChange={(e) => setPublishUtc(e.target.value)} className={inputCls} />
                </Field>
              )}
            </div>
          )}
        </div>

        <button type="button" onClick={() => setShowAdvanced(!showAdvanced)} className="text-xs text-dusk-400 hover:text-dusk-200">
          {showAdvanced ? '▾' : '▸'} render knobs (preset / CRF / supersample)
        </button>
        {showAdvanced && (
          <div className="grid grid-cols-3 gap-3">
            <Field label="Preset (default fast)">
              <input value={preset} onChange={(e) => setPreset(e.target.value)} placeholder="veryfast" className={inputCls} />
            </Field>
            <Field label="CRF (default 20)">
              <input value={crf} onChange={(e) => setCrf(e.target.value)} placeholder="23" className={inputCls} />
            </Field>
            <Field label="Supersample (default off)">
              <input value={supersample} onChange={(e) => setSupersample(e.target.value)} placeholder="2.0" className={inputCls} />
            </Field>
          </div>
        )}

        <div>
          <div className="text-[11px] uppercase tracking-wider text-dusk-400 mb-1">Command (what actually runs)</div>
          <pre className="overflow-x-auto rounded-lg bg-dusk-950 border border-dusk-800 p-2.5 text-[10px] text-dusk-300 font-mono whitespace-pre-wrap">
            {command}
          </pre>
        </div>

        <button
          onClick={() => queue.mutate()}
          disabled={queue.isPending}
          className="rounded-lg bg-accent-500 px-5 py-2 text-sm font-medium text-white hover:bg-accent-400 disabled:opacity-50"
        >
          Queue build
        </button>
        {queue.isError && <div className="text-xs text-bad-400">{String(queue.error)}</div>}
        {jobId !== null && <QueuedBanner jobId={jobId} onDone={() => qc.invalidateQueries({ queryKey: ['jobs'] })} />}
      </section>

      <aside className="rounded-xl border border-dusk-800 bg-dusk-900 p-4 h-fit">
        <h3 className="text-sm font-semibold text-dusk-300 uppercase tracking-wider mb-3">Preflight</h3>
        {preflight.data ? (
          <ul className="space-y-2">
            {preflight.data.checks.map((c) => (
              <li key={c.label} className="text-xs">
                <span className={c.ok ? 'text-ok-400' : 'text-bad-400'}>{c.ok ? '✓' : '✗'}</span>{' '}
                <span className="text-dusk-200">{c.label}</span>
                {c.detail && <div className="pl-4 text-[11px] text-dusk-500">{c.detail}</div>}
              </li>
            ))}
          </ul>
        ) : (
          <div className="text-xs text-dusk-500">checking…</div>
        )}
        {preflight.data && !preflight.data.ok && (
          <div className="mt-3 rounded-lg border border-warn-400/30 bg-warn-400/10 p-2 text-[11px] text-warn-400">
            You can still queue — the pipeline re-checks at start — but fix the ✗ items first for a clean run.
          </div>
        )}
      </aside>
    </div>
  )
}

/* ---------- veo wizard ---------- */

function VeoWizard() {
  const qc = useQueryClient()
  const { data } = useQuery({ queryKey: ['veo-sources'], queryFn: fetchVeoSources })
  const music = useQuery({ queryKey: ['music'], queryFn: fetchMusic })
  const [upscale, setUpscale] = useState(true)
  const [targetH, setTargetH] = useState<'1440' | '2160'>('1440')
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [duration, setDuration] = useState(7200)
  const [track, setTrack] = useState('')
  const [xfade, setXfade] = useState('1.5')
  const [outName, setOutName] = useState('veo_world')
  const [enhanceJob, setEnhanceJob] = useState<number | null>(null)
  const [assembleJob, setAssembleJob] = useState<number | null>(null)

  const enhance = useMutation({
    mutationFn: () =>
      createJob('veo_enhance', {}, upscale ? { VEO_UPSCALE: '1', VEO_TARGET_H: targetH } : {}),
    onSuccess: (j) => {
      setEnhanceJob(j.id)
      qc.invalidateQueries({ queryKey: ['jobs'] })
    },
  })

  const assemble = useMutation({
    mutationFn: () =>
      createJob(
        'veo_assemble',
        { clips: [...selected], duration, music: track || null, output: outName },
        xfade !== '1.5' ? { VEO_XFADE: xfade } : {},
      ),
    onSuccess: (j) => {
      setAssembleJob(j.id)
      qc.invalidateQueries({ queryKey: ['jobs'] })
    },
  })

  const toggle = (path: string) =>
    setSelected((s) => {
      const n = new Set(s)
      if (n.has(path)) n.delete(path)
      else n.add(path)
      return n
    })

  const uncached = data ? data.sources.filter((s) => !s.cached_heights.length).length : 0

  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-dusk-800 bg-dusk-900 p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-dusk-300 uppercase tracking-wider">
            1 · Enhance raw Veo exports
          </h3>
          <span className="text-[11px] text-dusk-500">{data?.downloads_dir}/Untitled video*.mp4</span>
        </div>
        {data && data.sources.length === 0 ? (
          <div className="text-xs text-dusk-400">
            No raw exports found in Downloads — the bank below is still usable for assembly.
          </div>
        ) : (
          <>
            <ul className="grid grid-cols-2 md:grid-cols-3 gap-1.5 mb-3">
              {data?.sources.map((s) => (
                <li key={s.name} className="flex items-center justify-between rounded-lg bg-dusk-850 border border-dusk-800 px-2.5 py-1.5 text-[11px]">
                  <span className="truncate text-dusk-300">{s.name}</span>
                  {s.cached_heights.length ? (
                    <span className="text-ok-400 shrink-0 ml-2">banked {s.cached_heights.map((h) => `${h}p`).join('/')}</span>
                  ) : (
                    <span className="text-dusk-500 shrink-0 ml-2">new</span>
                  )}
                </li>
              ))}
            </ul>
            <div className="flex flex-wrap items-center gap-4">
              <Toggle checked={upscale} onChange={setUpscale} label="ESRGAN upscale (sharper, ~35 min/clip)" />
              {upscale && (
                <Seg
                  value={targetH}
                  onChange={setTargetH}
                  options={[
                    { value: '1440', label: '1440p' },
                    { value: '2160', label: '4K (huge files)' },
                  ]}
                />
              )}
              <button
                onClick={() => enhance.mutate()}
                disabled={enhance.isPending}
                className="rounded-lg bg-accent-500 px-4 py-1.5 text-xs font-medium text-white hover:bg-accent-400 disabled:opacity-50"
              >
                Enhance batch
              </button>
              <span className="text-[11px] text-dusk-500">
                {uncached} new · cached clips are skipped automatically
                {upscale && uncached > 0 && ` · est. ~${Math.round(uncached * 35)} min`}
              </span>
            </div>
          </>
        )}
        {enhanceJob !== null && (
          <QueuedBanner jobId={enhanceJob} onDone={() => qc.invalidateQueries({ queryKey: ['veo-sources'] })} />
        )}
      </section>

      <section className="rounded-xl border border-dusk-800 bg-dusk-900 p-4">
        <h3 className="text-sm font-semibold text-dusk-300 uppercase tracking-wider mb-3">
          2 · Assemble a living-world video from the bank
        </h3>
        {data && data.bank.length === 0 ? (
          <div className="text-xs text-dusk-400">Bank is empty — enhance some clips first.</div>
        ) : (
          <>
            <div className="grid grid-cols-3 md:grid-cols-5 gap-2 mb-4">
              {data?.bank.map((c) => {
                const on = selected.has(c.path)
                return (
                  <button
                    key={c.path}
                    type="button"
                    onClick={() => toggle(c.path)}
                    className={`rounded-lg overflow-hidden border text-left transition-colors ${
                      on ? 'border-accent-400 ring-1 ring-accent-400/50' : 'border-dusk-800 hover:border-dusk-600'
                    }`}
                  >
                    <img src={vthumbUrl(c.path, 320)} className="aspect-video w-full object-cover" loading="lazy" alt="" />
                    <div className="px-2 py-1 flex items-center justify-between text-[10px]">
                      <span className={`truncate ${on ? 'text-accent-300' : 'text-dusk-400'}`}>{c.name}</span>
                      <span className="text-dusk-600 shrink-0 ml-1">{fmtBytes(c.size)}</span>
                    </div>
                  </button>
                )
              })}
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
              <Field label="Duration (s)">
                <input type="number" min={30} value={duration} onChange={(e) => setDuration(Number(e.target.value))} className={inputCls} />
              </Field>
              <Field label="Music (from library)">
                <select value={track} onChange={(e) => setTrack(e.target.value)} className={inputCls}>
                  <option value="">— silent (QC build) —</option>
                  {music.data?.library.map((t) => (
                    <option key={t.path} value={t.path}>{t.name}</option>
                  ))}
                </select>
              </Field>
              <Field label="Crossfade (s)">
                <input value={xfade} onChange={(e) => setXfade(e.target.value)} className={inputCls} />
              </Field>
              <Field label="Output name">
                <input value={outName} onChange={(e) => setOutName(e.target.value)} className={inputCls} />
              </Field>
            </div>
            <button
              onClick={() => assemble.mutate()}
              disabled={assemble.isPending || selected.size === 0}
              className="rounded-lg bg-accent-500 px-4 py-1.5 text-xs font-medium text-white hover:bg-accent-400 disabled:opacity-40"
            >
              Assemble {selected.size || 'no'} clip{selected.size === 1 ? '' : 's'} → output/{outName}.mp4
            </button>
            {assemble.isError && <div className="mt-2 text-xs text-bad-400">{String(assemble.error)}</div>}
          </>
        )}
        {assembleJob !== null && (
          <QueuedBanner jobId={assembleJob} onDone={() => qc.invalidateQueries({ queryKey: ['jobs'] })} />
        )}
      </section>
    </div>
  )
}

/* ---------- shorts builder ---------- */

function ShortsBuilder() {
  const qc = useQueryClient()
  const overview = useQuery({ queryKey: ['overview'], queryFn: fetchOverview })
  const usedImages = useQuery({ queryKey: ['used-images'], queryFn: () => fetchUsedImages(36) })
  const music = useQuery({ queryKey: ['music'], queryFn: fetchMusic })
  const [image, setImage] = useState('')
  const [track, setTrack] = useState('')
  const [title, setTitle] = useState('')
  const [theme, setTheme] = useState('')
  const [animate, setAnimate] = useState<'' | 'depthflow'>('depthflow')
  const [upload, setUpload] = useState(false)
  const [publishAt, setPublishAt] = useState('')
  const [description, setDescription] = useState('')
  const [jobId, setJobId] = useState<number | null>(null)

  const themes = overview.data?.themes ?? []
  // theme + unused-image previews double as an image source alongside used/
  const themeImages = themes.flatMap((t) => t.preview_paths.map((p) => ({ path: p, theme: t.key })))
  const pickable = [
    ...themeImages.map((i) => ({ ...i, from: 'unused' as const })),
    ...(usedImages.data ?? []).map((i) => ({ path: i.path, theme: '', from: 'used' as const })),
  ]
  const tracks = [...(music.data?.library ?? []), ...(music.data?.used ?? [])]

  const pick = (p: { path: string; theme: string }) => {
    setImage(p.path)
    if (p.theme) setTheme(p.theme)
  }

  const queue = useMutation({
    mutationFn: () =>
      createJob(
        'short_build',
        {
          image, track, title, theme,
          upload,
          publish_at: upload && publishAt ? new Date(publishAt).toISOString().replace(/\.\d{3}Z$/, 'Z') : null,
          description: description || undefined,
        },
        animate ? { ANIMATE: animate } : {},
      ),
    onSuccess: (j) => {
      setJobId(j.id)
      qc.invalidateQueries({ queryKey: ['jobs'] })
    },
  })

  const ready = image && track && title.trim() && theme

  return (
    <div className="space-y-4">
      <section className="rounded-xl border border-dusk-800 bg-dusk-900 p-4">
        <h3 className="text-sm font-semibold text-dusk-300 uppercase tracking-wider mb-3">1 · Pick a scene image</h3>
        {pickable.length === 0 ? (
          <div className="text-xs text-dusk-400">No images found — generate assets first.</div>
        ) : (
          <div className="grid grid-cols-4 md:grid-cols-6 gap-2 max-h-72 overflow-y-auto pr-1">
            {pickable.map((p) => (
              <button
                key={p.path}
                type="button"
                onClick={() => pick(p)}
                className={`relative rounded-lg overflow-hidden border transition-colors ${
                  image === p.path ? 'border-accent-400 ring-1 ring-accent-400/50' : 'border-dusk-800 hover:border-dusk-600'
                }`}
              >
                <img src={imgUrl(p.path, 240)} className="aspect-video w-full object-cover" loading="lazy" alt="" />
                {p.from === 'unused' && (
                  <span className="absolute top-1 left-1 rounded bg-ok-400/80 px-1 text-[9px] font-medium text-dusk-950">new</span>
                )}
              </button>
            ))}
          </div>
        )}
      </section>

      <section className="rounded-xl border border-dusk-800 bg-dusk-900 p-4 space-y-4">
        <h3 className="text-sm font-semibold text-dusk-300 uppercase tracking-wider">2 · Sound, title, style</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Field label="Music track">
            <select value={track} onChange={(e) => setTrack(e.target.value)} className={inputCls}>
              <option value="">— pick —</option>
              {tracks.map((t) => (
                <option key={t.path} value={t.path}>{t.name}</option>
              ))}
            </select>
          </Field>
          <Field label="Title overlay">
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Sunset Falls" className={inputCls} />
          </Field>
          <Field label="Theme (atmosphere FX)">
            <select value={theme} onChange={(e) => setTheme(e.target.value)} className={inputCls}>
              <option value="">— pick —</option>
              {themes.map((t) => (
                <option key={t.key} value={t.key}>{t.title}</option>
              ))}
            </select>
          </Field>
          <Field label="Animation">
            <Seg
              value={animate}
              onChange={setAnimate}
              options={[
                { value: 'depthflow', label: '2.5D' },
                { value: '', label: 'Pan' },
              ]}
            />
          </Field>
        </div>

        <div className="space-y-2.5 rounded-lg border border-dusk-800 bg-dusk-950/60 p-3">
          <Toggle checked={upload} onChange={setUpload} label="Upload to YouTube (scheduled publish)" />
          {upload && (
            <div className="grid grid-cols-2 gap-3 pl-10">
              <Field label="Go public at (local time, empty = now)">
                <input type="datetime-local" value={publishAt} onChange={(e) => setPublishAt(e.target.value)} className={inputCls} />
              </Field>
              <Field label="Description (default: hashtags)">
                <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} className={inputCls} />
              </Field>
            </div>
          )}
        </div>

        <button
          onClick={() => queue.mutate()}
          disabled={!ready || queue.isPending}
          className="rounded-lg bg-accent-500 px-5 py-2 text-sm font-medium text-white hover:bg-accent-400 disabled:opacity-40"
        >
          {upload ? 'Build + upload Short' : 'Build Short (no upload)'}
        </button>
        {!ready && <span className="ml-3 text-[11px] text-dusk-500">pick image + track + title + theme</span>}
        {queue.isError && <div className="text-xs text-bad-400">{String(queue.error)}</div>}
        {jobId !== null && <QueuedBanner jobId={jobId} onDone={() => qc.invalidateQueries({ queryKey: ['outputs'] })} />}
      </section>
    </div>
  )
}

/* ---------- page ---------- */

const TABS = { main: 'Main build', veo: 'Veo living-world', shorts: 'Shorts' } as const

export default function Build() {
  const [tab, setTab] = useState<keyof typeof TABS>('main')
  return (
    <div className="max-w-6xl">
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-xl font-semibold text-white">Build</h1>
        <div className="flex rounded-lg border border-dusk-800 overflow-hidden text-xs">
          {(Object.keys(TABS) as (keyof typeof TABS)[]).map((k) => (
            <button
              key={k}
              onClick={() => setTab(k)}
              className={`px-4 py-1.5 ${
                tab === k ? 'bg-accent-500/20 text-accent-300' : 'bg-dusk-900 text-dusk-400 hover:text-dusk-200'
              }`}
            >
              {TABS[k]}
            </button>
          ))}
        </div>
      </div>
      {tab === 'main' && <MainBuild />}
      {tab === 'veo' && <VeoWizard />}
      {tab === 'shorts' && <ShortsBuilder />}
    </div>
  )
}
