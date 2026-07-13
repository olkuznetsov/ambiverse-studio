import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchMusic, fetchOverview, fetchThemeImages, fileUrl, fmtBytes, fmtDuration, imgUrl } from '../api'
import type { ImageEntry, TrackEntry } from '../api'

function ImageTile({ img }: { img: ImageEntry }) {
  const [open, setOpen] = useState(false)
  const warn = (img.warnings ?? []).length > 0
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

export default function Assets() {
  const overview = useQuery({ queryKey: ['overview'], queryFn: fetchOverview })
  const [tab, setTab] = useState<string>('images')
  const [theme, setTheme] = useState<string | null>(null)
  const [showUsedMusic, setShowUsedMusic] = useState(false)

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

  return (
    <div className="max-w-6xl">
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-xl font-semibold text-white">Assets</h1>
        <div className="flex rounded-lg border border-dusk-800 overflow-hidden text-xs">
          {(['images', 'music'] as const).map((k) => (
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
                <ImageTile key={img.path} img={img} />
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
    </div>
  )
}
