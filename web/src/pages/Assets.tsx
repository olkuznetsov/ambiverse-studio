import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  fetchHousekeeping, fetchMusic, fetchOutputs, fetchOverview, fetchThemeImages,
  fileUrl, fmtBytes, fmtDuration, imgUrl, setThumb, trashAsset, vthumbUrl,
} from '../api'
import type { ImageEntry, OutputEntry, TrackEntry } from '../api'

function ActionBtn({ label, tone = 'dim', onClick }: {
  label: string
  tone?: 'dim' | 'danger' | 'accent'
  onClick: () => void
}) {
  const tones = {
    dim: 'border-dusk-700 text-dusk-400 hover:text-dusk-200 hover:border-dusk-600',
    danger: 'border-bad-400/40 text-bad-400 hover:bg-bad-400/10',
    accent: 'border-accent-400/40 text-accent-300 hover:bg-accent-500/10',
  }
  return (
    <button onClick={onClick} className={`rounded-md border px-2 py-0.5 text-[10px] transition-colors ${tones[tone]}`}>
      {label}
    </button>
  )
}

function ImageTile({ img, theme, onChanged }: { img: ImageEntry; theme: string; onChanged: () => void }) {
  const [open, setOpen] = useState(false)
  const warn = (img.warnings ?? []).length > 0
  const trash = useMutation({ mutationFn: trashAsset, onSuccess: onChanged })
  const thumb = useMutation({ mutationFn: setThumb, onSuccess: onChanged })
  return (
    <figure className="rounded-lg overflow-hidden border border-dusk-800 bg-dusk-850">
      <button className="block w-full cursor-zoom-in" onClick={() => setOpen(!open)} title={img.name}>
        <img
          src={imgUrl(img.path, open ? 1600 : 480)}
          className={open ? 'w-full object-contain' : 'aspect-video w-full object-cover'}
          loading="lazy"
          alt={img.name}
        />
      </button>
      <figcaption className="px-2 py-1.5">
        <div className="flex items-center justify-between gap-2 text-[11px]">
          <span className="truncate text-dusk-300">{img.name}</span>
          <span className="text-dusk-600 shrink-0">
            {img.width && img.height ? `${img.width}×${img.height}` : ''} · {fmtBytes(img.size)}
          </span>
        </div>
        {warn && (
          <ul className="mt-1 space-y-0.5">
            {img.warnings!.map((w) => (
              <li key={w} className="text-[10px] text-warn-400">⚠ {w}</li>
            ))}
          </ul>
        )}
        <div className="mt-1.5 flex gap-1.5">
          <ActionBtn
            label="set as thumb"
            tone="accent"
            onClick={() => {
              if (confirm(`Use ${img.name} as the custom thumbnail for ${theme}? (replaces any existing thumb.*)`))
                thumb.mutate(img.path)
            }}
          />
          <ActionBtn
            label="trash"
            tone="danger"
            onClick={() => {
              if (confirm(`Move ${img.name} to the studio trash? (recoverable from data/trash/)`))
                trash.mutate(img.path)
            }}
          />
        </div>
      </figcaption>
    </figure>
  )
}

function TrackRow({ t }: { t: TrackEntry }) {
  return (
    <li className="flex items-center gap-3 rounded-lg border border-dusk-800 bg-dusk-900 px-3 py-2">
      <div className="min-w-0 flex-1">
        <div className="text-xs text-dusk-200 truncate" title={t.name}>{t.name}</div>
        <div className="text-[10px] text-dusk-500">
          {fmtDuration(t.duration)} · {fmtBytes(t.size)}
        </div>
      </div>
      <audio controls preload="none" src={fileUrl(t.path)} className="h-8 w-64 shrink-0" />
    </li>
  )
}

function HousekeepingCard() {
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)
  const { data } = useQuery({ queryKey: ['housekeeping'], queryFn: fetchHousekeeping })
  const trash = useMutation({
    mutationFn: trashAsset,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['housekeeping'] })
      qc.invalidateQueries({ queryKey: ['outputs'] })
      qc.invalidateQueries({ queryKey: ['overview'] })
    },
  })
  if (!data || data.candidates.length === 0) return null
  return (
    <div className="mb-4 rounded-xl border border-warn-400/25 bg-warn-400/[0.05]">
      <button onClick={() => setOpen(!open)} className="flex w-full items-center justify-between px-4 py-3 text-left">
        <span className="text-sm font-medium text-warn-400">
          🧹 Housekeeping — {fmtBytes(data.total_bytes)} reclaimable in {data.candidates.length} file
          {data.candidates.length > 1 ? 's' : ''}
        </span>
        <span className="text-[11px] text-dusk-400">
          {data.disk_free_gb} GB free {open ? '▾' : '▸'}
        </span>
      </button>
      {open && (
        <ul className="border-t border-warn-400/15 px-4 py-2 space-y-1.5">
          {data.candidates.map((c) => (
            <li key={c.path} className="flex items-center justify-between gap-3 text-xs">
              <div className="min-w-0">
                <span className="text-dusk-200">{c.name}</span>
                <span className="text-dusk-500"> · {fmtBytes(c.size)}</span>
                <div className="text-[10px] text-dusk-500">{c.reason}</div>
              </div>
              <ActionBtn
                label="trash"
                tone="danger"
                onClick={() => {
                  if (confirm(`Move ${c.name} (${fmtBytes(c.size)}) to the studio trash?\nReason: ${c.reason}`))
                    trash.mutate(c.path)
                }}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

const KIND_LABEL: Record<OutputEntry['kind'], string> = {
  video: 'main videos',
  short: 'shorts',
  thumbnail: 'thumbnails',
  music: 'music intermediates',
}

function OutputRow({ o, onChanged }: { o: OutputEntry; onChanged: () => void }) {
  const [open, setOpen] = useState(false)
  const trash = useMutation({ mutationFn: trashAsset, onSuccess: onChanged })
  const isVideo = o.kind === 'video' || o.kind === 'short'
  return (
    <li className="rounded-lg border border-dusk-800 bg-dusk-900 overflow-hidden">
      <div className="flex items-center gap-3 px-3 py-2">
        {isVideo && (
          <img src={vthumbUrl(o.path, 160)} className="h-10 w-[71px] rounded object-cover shrink-0" loading="lazy" alt="" />
        )}
        {o.kind === 'thumbnail' && (
          <img src={imgUrl(o.path, 160)} className="h-10 w-[71px] rounded object-cover shrink-0" loading="lazy" alt="" />
        )}
        <div className="min-w-0 flex-1">
          <div className="text-xs text-dusk-200 truncate" title={o.name}>{o.name}</div>
          <div className="text-[10px] text-dusk-500">
            {fmtBytes(o.size)}
            {o.duration ? ` · ${fmtDuration(o.duration)}` : ''} ·{' '}
            {new Date(o.mtime).toLocaleString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
          </div>
        </div>
        <div className="flex gap-1.5 shrink-0">
          {(isVideo || o.kind === 'music') && (
            <ActionBtn label={open ? 'close' : 'preview'} onClick={() => setOpen(!open)} />
          )}
          <ActionBtn
            label="trash"
            tone="danger"
            onClick={() => {
              if (confirm(`Move ${o.name} (${fmtBytes(o.size)}) to the studio trash?`)) trash.mutate(o.path)
            }}
          />
        </div>
      </div>
      {open && isVideo && (
        <video controls preload="none" poster={vthumbUrl(o.path, 960)} src={fileUrl(o.path)} className="w-full bg-black" />
      )}
      {open && o.kind === 'music' && (
        <audio controls src={fileUrl(o.path)} className="w-full px-3 pb-2" />
      )}
    </li>
  )
}

export default function Assets() {
  const qc = useQueryClient()
  const overview = useQuery({ queryKey: ['overview'], queryFn: fetchOverview })
  const [tab, setTab] = useState<string>('images')
  const [theme, setTheme] = useState<string | null>(null)
  const [showUsedMusic, setShowUsedMusic] = useState(false)
  const [outputKind, setOutputKind] = useState<OutputEntry['kind'] | 'all'>('all')

  const themes = overview.data?.themes ?? []
  const activeTheme = theme ?? themes[0]?.key ?? null

  const images = useQuery({
    queryKey: ['theme-images', activeTheme],
    queryFn: () => fetchThemeImages(activeTheme!),
    enabled: tab === 'images' && !!activeTheme,
  })
  const music = useQuery({
    queryKey: ['music'],
    queryFn: fetchMusic,
    enabled: tab === 'music',
  })
  const outputs = useQuery({
    queryKey: ['outputs'],
    queryFn: fetchOutputs,
    enabled: tab === 'outputs',
  })

  const invalidateImages = () => {
    qc.invalidateQueries({ queryKey: ['theme-images'] })
    qc.invalidateQueries({ queryKey: ['overview'] })
  }

  const shownOutputs = (outputs.data ?? []).filter((o) => outputKind === 'all' || o.kind === outputKind)

  return (
    <div className="max-w-6xl">
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-xl font-semibold text-white">Assets</h1>
        <div className="flex rounded-lg border border-dusk-800 overflow-hidden text-xs">
          {(['images', 'music', 'outputs'] as const).map((k) => (
            <button
              key={k}
              onClick={() => setTab(k)}
              className={`px-4 py-1.5 capitalize ${
                tab === k ? 'bg-accent-500/20 text-accent-300' : 'bg-dusk-900 text-dusk-400 hover:text-dusk-200'
              }`}
            >
              {k}
            </button>
          ))}
        </div>
      </div>

      {tab === 'images' && (
        <>
          <div className="flex flex-wrap gap-1.5 mb-4">
            {themes.map((t) => (
              <button
                key={t.key}
                onClick={() => setTheme(t.key)}
                className={`rounded-full px-3 py-1 text-xs border transition-colors ${
                  activeTheme === t.key
                    ? 'border-accent-400/50 bg-accent-500/15 text-accent-300'
                    : 'border-dusk-800 bg-dusk-900 text-dusk-400 hover:text-dusk-200'
                }`}
              >
                {t.title}
                <span className={`ml-1.5 ${t.image_count > 0 ? 'text-ok-400' : 'text-dusk-600'}`}>{t.image_count}</span>
                {t.has_custom_thumb && <span className="ml-1 text-accent-400">◆</span>}
              </button>
            ))}
          </div>

          {images.isLoading && <div className="text-dusk-400 text-sm">Loading images…</div>}
          {images.data && images.data.images.length === 0 && (
            <div className="rounded-xl border border-dashed border-dusk-700 bg-dusk-900/50 p-10 text-center text-sm text-dusk-400">
              No unused images in <span className="text-dusk-200">images/{activeTheme}/</span>.
              <div className="text-xs text-dusk-500 mt-1.5">
                Drop files in via Finder — they appear here on next tab focus.
              </div>
            </div>
          )}
          {images.data && images.data.images.length > 0 && (
            <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3">
              {images.data.images.map((img) => (
                <ImageTile key={img.path} img={img} theme={activeTheme!} onChanged={invalidateImages} />
              ))}
            </div>
          )}
        </>
      )}

      {tab === 'music' && (
        <>
          {music.isLoading && <div className="text-dusk-400 text-sm">Loading music (probing durations)…</div>}
          {music.data && (
            <>
              <div className="text-xs text-dusk-400 mb-3">
                Library: <span className="text-white">{music.data.library_count} tracks</span> ·{' '}
                <span className="text-white">{music.data.library_minutes} min</span> banked
              </div>
              {music.data.library.length === 0 ? (
                <div className="rounded-xl border border-dashed border-dusk-700 bg-dusk-900/50 p-10 text-center text-sm text-dusk-400">
                  Music library is empty — drop Suno tracks into <span className="text-dusk-200">music/library/</span>.
                </div>
              ) : (
                <ul className="space-y-2">
                  {music.data.library.map((t) => (
                    <TrackRow key={t.path} t={t} />
                  ))}
                </ul>
              )}

              <button
                onClick={() => setShowUsedMusic(!showUsedMusic)}
                className="mt-5 text-xs text-dusk-400 hover:text-dusk-200"
              >
                {showUsedMusic ? '▾' : '▸'} used tracks ({music.data.used_count})
              </button>
              {showUsedMusic && (
                <ul className="space-y-2 mt-2 opacity-70">
                  {(music.data.used ?? []).map((t) => (
                    <TrackRow key={t.path} t={t} />
                  ))}
                </ul>
              )}
            </>
          )}
        </>
      )}

      {tab === 'outputs' && (
        <>
          <HousekeepingCard />
          <div className="flex flex-wrap gap-1.5 mb-4">
            {(['all', 'video', 'short', 'thumbnail', 'music'] as const).map((k) => (
              <button
                key={k}
                onClick={() => setOutputKind(k)}
                className={`rounded-full px-3 py-1 text-xs border transition-colors ${
                  outputKind === k
                    ? 'border-accent-400/50 bg-accent-500/15 text-accent-300'
                    : 'border-dusk-800 bg-dusk-900 text-dusk-400 hover:text-dusk-200'
                }`}
              >
                {k === 'all' ? 'all' : KIND_LABEL[k]}
                <span className="ml-1.5 text-dusk-600">
                  {(outputs.data ?? []).filter((o) => k === 'all' || o.kind === k).length}
                </span>
              </button>
            ))}
          </div>
          {outputs.isLoading && <div className="text-dusk-400 text-sm">Scanning output/ (probing durations)…</div>}
          {outputs.data && shownOutputs.length === 0 && (
            <div className="rounded-xl border border-dashed border-dusk-700 bg-dusk-900/50 p-10 text-center text-sm text-dusk-400">
              Nothing here yet.
            </div>
          )}
          <ul className="space-y-2">
            {shownOutputs.map((o) => (
              <OutputRow key={o.path} o={o} onChanged={() => qc.invalidateQueries({ queryKey: ['outputs'] })} />
            ))}
          </ul>
        </>
      )}
    </div>
  )
}
