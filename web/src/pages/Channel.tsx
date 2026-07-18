import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  addImpression, createJob, deleteImpression, fetchChannel, fetchHistory,
  fetchImpressions, fmtDuration,
} from '../api'
import type { ChannelVideo, DimRow, FormatRollup, ThemeRollup } from '../api'
import LineChart from '../components/LineChart'

const FORMAT_LABEL: Record<FormatRollup['format'], string> = {
  veo: 'Veo living-world',
  image: 'Ken Burns / DepthFlow',
}

const THEME_TITLE: Record<string, string> = {
  'space-stations': 'Space Stations',
  'alien-planets': 'Alien Planets',
  'cyberpunk-cities': 'Cyberpunk Cities',
  'deep-space': 'Deep Space',
  'japanese-streets': 'Japanese Streets',
  'cozy-anime-rooms': 'Cozy Anime Rooms',
  'ps1-jungle': 'Low-Poly Jungle',
  'fantasy-realms': 'Enchanted Realm',
}
const themeName = (k: string | null) => (k ? THEME_TITLE[k] ?? k : '—')

const fmtInt = (n: number) => n.toLocaleString('en-US')
const fmtHours = (min: number) => `${Math.round(min / 60).toLocaleString('en-US')}h`

function Progress({ label, value, goal, hint }: { label: string; value: number; goal: number; hint: string }) {
  const pct = Math.min(100, (value / goal) * 100)
  return (
    <div className="rounded-xl border border-dusk-800 bg-dusk-900 p-4">
      <div className="flex items-baseline justify-between">
        <span className="text-sm font-medium text-dusk-200">{label}</span>
        <span className="text-xs text-dusk-400">
          <span className="text-white font-semibold">{fmtInt(value)}</span> / {fmtInt(goal)}
        </span>
      </div>
      <div className="mt-2.5 h-2 rounded-full bg-dusk-800 overflow-hidden">
        <div className="h-full rounded-full bg-gradient-to-r from-accent-500 to-accent-300" style={{ width: `${pct}%` }} />
      </div>
      <div className="mt-1.5 flex justify-between text-[11px] text-dusk-500">
        <span>{hint}</span>
        <span>{pct.toFixed(1)}%</span>
      </div>
    </div>
  )
}

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border border-dusk-800 bg-dusk-900 p-3">
      <div className="text-[11px] uppercase tracking-wider text-dusk-400">{label}</div>
      <div className="mt-1 text-lg font-semibold text-white">{value}</div>
      {sub && <div className="text-[11px] text-dusk-500">{sub}</div>}
    </div>
  )
}

function DimBars({ title, rows, total }: { title: string; rows: DimRow[]; total: number }) {
  return (
    <div className="rounded-xl border border-dusk-800 bg-dusk-900 p-4">
      <h3 className="text-sm font-semibold text-dusk-300 uppercase tracking-wider mb-3">{title}</h3>
      {rows.length === 0 ? (
        <div className="text-xs text-dusk-500">no data</div>
      ) : (
        <ul className="space-y-2">
          {rows.map((r) => {
            const pct = total ? (r.views / total) * 100 : 0
            return (
              <li key={r.label} className="text-xs">
                <div className="flex justify-between text-dusk-300">
                  <span className="truncate">{r.label}</span>
                  <span className="text-dusk-400 shrink-0 ml-2">
                    {pct.toFixed(0)}% · {fmtInt(r.views)}
                  </span>
                </div>
                <div className="mt-1 h-1 rounded-full bg-dusk-800 overflow-hidden">
                  <div className="h-full rounded-full bg-accent-500/70" style={{ width: `${pct}%` }} />
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}

function retentionTone(pct: number | null) {
  if (pct === null) return 'text-dusk-500'
  if (pct >= 20) return 'text-ok-400'
  if (pct >= 10) return 'text-warn-400'
  return 'text-bad-400'
}

function ThemeRollupCard({ rows }: { rows: ThemeRollup[] }) {
  const maxWatch = Math.max(1, ...rows.map((r) => r.minutes_watched))
  return (
    <div className="rounded-xl border border-accent-500/25 bg-accent-500/[0.04] p-4">
      <div className="flex items-baseline justify-between mb-1">
        <h3 className="text-sm font-semibold text-accent-300 uppercase tracking-wider">Theme rollup</h3>
        <span className="text-[11px] text-dusk-500">retention weighted by watch time · what to make next</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-dusk-500 text-left">
              <th className="py-1.5 font-medium">World</th>
              <th className="py-1.5 font-medium text-right">Uploads</th>
              <th className="py-1.5 font-medium text-right">Views</th>
              <th className="py-1.5 font-medium text-right">Watch</th>
              <th className="py-1.5 font-medium text-right">Retention</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.theme} className="border-t border-dusk-800/60">
                <td className="py-2 text-dusk-100 font-medium">{themeName(r.theme)}</td>
                <td className="py-2 text-right text-dusk-300">
                  {r.videos}<span className="text-dusk-600"> long</span> · {r.shorts}<span className="text-dusk-600"> sh</span>
                </td>
                <td className="py-2 text-right text-dusk-300">{fmtInt(r.views)}</td>
                <td className="py-2 text-right text-dusk-300">
                  <div className="flex items-center justify-end gap-2">
                    <span className="hidden sm:block w-16 h-1 rounded-full bg-dusk-800 overflow-hidden">
                      <span className="block h-full bg-accent-500/70" style={{ width: `${(r.minutes_watched / maxWatch) * 100}%` }} />
                    </span>
                    {fmtHours(r.minutes_watched)}
                  </div>
                </td>
                <td className={`py-2 text-right font-semibold ${retentionTone(r.avg_view_pct)}`}>
                  {r.avg_view_pct === null ? '—' : `${r.avg_view_pct}%`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function FormatCard({ rows }: { rows: FormatRollup[] }) {
  // fixed order: the experiment (veo) on top of the control (image)
  const ordered = [...rows].sort((a) => (a.format === 'veo' ? -1 : 1))
  return (
    <div className="rounded-xl border border-ok-400/25 bg-ok-400/[0.04] p-4">
      <div className="flex items-baseline justify-between mb-1">
        <h3 className="text-sm font-semibold text-ok-400 uppercase tracking-wider">Format A/B — Veo vs image</h3>
        <span className="text-[11px] text-dusk-500">the live decision: does real motion out-retain stills?</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-dusk-500 text-left">
              <th className="py-1.5 font-medium">Format</th>
              <th className="py-1.5 font-medium text-right">Uploads</th>
              <th className="py-1.5 font-medium text-right">Views</th>
              <th className="py-1.5 font-medium text-right">Watch</th>
              <th className="py-1.5 font-medium text-right">AVD</th>
              <th className="py-1.5 font-medium text-right">Retention</th>
            </tr>
          </thead>
          <tbody>
            {ordered.map((r) => {
              const pending = r.views === 0 && r.minutes_watched === 0
              return (
                <tr key={r.format} className="border-t border-dusk-800/60">
                  <td className="py-2 text-dusk-100 font-medium">
                    {FORMAT_LABEL[r.format]}
                    {r.format === 'veo' && <span className="ml-1.5 rounded bg-ok-400/15 px-1 text-[9px] text-ok-400">NEW</span>}
                  </td>
                  <td className="py-2 text-right text-dusk-300">
                    {r.videos}<span className="text-dusk-600"> long</span> · {r.shorts}<span className="text-dusk-600"> sh</span>
                  </td>
                  <td className="py-2 text-right text-dusk-300">{fmtInt(r.views)}</td>
                  <td className="py-2 text-right text-dusk-300">{fmtHours(r.minutes_watched)}</td>
                  <td className="py-2 text-right text-dusk-300">
                    {r.avg_view_duration_s != null ? fmtDuration(r.avg_view_duration_s) : '—'}
                  </td>
                  <td className={`py-2 text-right font-semibold ${retentionTone(r.avg_view_pct)}`}>
                    {r.avg_view_pct === null ? (pending ? 'data pending' : '—') : `${r.avg_view_pct}%`}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

type SortKey = 'views' | 'watch' | 'retention' | 'date'

function VideoTable({ videos }: { videos: ChannelVideo[] }) {
  const [sort, setSort] = useState<SortKey>('views')
  const [kind, setKind] = useState<'all' | 'Video' | 'Short'>('all')

  const sorted = useMemo(() => {
    const filtered = videos.filter((v) => kind === 'all' || v.kind === kind)
    const key = (v: ChannelVideo) =>
      sort === 'views' ? v.views
      : sort === 'watch' ? v.analytics?.minutes_watched ?? -1
      : sort === 'retention' ? v.analytics?.avg_view_pct ?? -1
      : Date.parse(v.date)
    return [...filtered].sort((a, b) => key(b) - key(a))
  }, [videos, sort, kind])

  const Th = ({ k, children }: { k: SortKey; children: React.ReactNode }) => (
    <th
      onClick={() => setSort(k)}
      className={`py-1.5 font-medium cursor-pointer select-none text-right ${sort === k ? 'text-accent-300' : 'hover:text-dusk-200'}`}
    >
      {children} {sort === k ? '▾' : ''}
    </th>
  )

  return (
    <div className="rounded-xl border border-dusk-800 bg-dusk-900 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-dusk-300 uppercase tracking-wider">Per-video</h3>
        <div className="flex rounded-lg border border-dusk-800 overflow-hidden text-[11px]">
          {(['all', 'Video', 'Short'] as const).map((k) => (
            <button
              key={k}
              onClick={() => setKind(k)}
              className={`px-2.5 py-1 ${kind === k ? 'bg-accent-500/20 text-accent-300' : 'text-dusk-400 hover:text-dusk-200'}`}
            >
              {k === 'all' ? 'all' : k === 'Video' ? 'long' : 'shorts'}
            </button>
          ))}
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-dusk-500 text-left">
              <th className="py-1.5 font-medium">Title</th>
              <th className="py-1.5 font-medium">World</th>
              <Th k="date">Date</Th>
              <Th k="views">Views</Th>
              <Th k="watch">Watch</Th>
              <Th k="retention">Ret.</Th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((v) => (
              <tr key={v.video_id} className="border-t border-dusk-800/60">
                <td className="py-2 max-w-[22rem]">
                  <a
                    href={`https://youtu.be/${v.video_id}`}
                    target="_blank"
                    rel="noreferrer"
                    className="text-dusk-100 hover:text-accent-300 truncate block"
                    title={v.title}
                  >
                    <span className={`mr-1.5 text-[10px] ${v.kind === 'Short' ? 'text-accent-400' : 'text-dusk-500'}`}>
                      {v.kind === 'Short' ? 'S' : 'L'}
                    </span>
                    {v.title}
                    {v.format === 'veo' && (
                      <span className="ml-1.5 rounded bg-ok-400/15 px-1 text-[9px] text-ok-400" title={`Veo living-world (${v.format_source})`}>
                        veo
                      </span>
                    )}
                    {v.publish_at && <span className="ml-1.5 text-[10px] text-warn-400">scheduled</span>}
                  </a>
                </td>
                <td className="py-2 text-dusk-400">
                  {themeName(v.theme)}
                  {v.theme && v.theme_source !== 'log' && (
                    <span className="ml-1 text-[9px] text-dusk-600" title={`theme ${v.theme_source}`}>~</span>
                  )}
                </td>
                <td className="py-2 text-right text-dusk-500">{v.date.slice(5)}</td>
                <td className="py-2 text-right text-dusk-200">{fmtInt(v.views)}</td>
                <td className="py-2 text-right text-dusk-300">
                  {v.analytics ? fmtHours(v.analytics.minutes_watched) : '—'}
                </td>
                <td className={`py-2 text-right ${retentionTone(v.analytics?.avg_view_pct ?? null)}`}>
                  {v.analytics ? `${v.analytics.avg_view_pct}%` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function GrowthCard({ videos }: { videos: ChannelVideo[] }) {
  const { data } = useQuery({ queryKey: ['channel-history'], queryFn: fetchHistory })
  const snaps = data ?? []
  if (snaps.length === 0) return null
  const series = (pick: (s: typeof snaps[number]) => number | null) =>
    snaps.filter((s) => pick(s) != null).map((s) => ({ x: s.date, y: pick(s) as number }))
  // upload events → one marker per publish date, all titles in the tooltip
  const byDate = new Map<string, string[]>()
  for (const v of videos) {
    const list = byDate.get(v.date) ?? []
    list.push(`${v.kind === 'Short' ? 'S' : 'L'}· ${v.title}`)
    byDate.set(v.date, list)
  }
  const events = [...byDate].map(([x, titles]) => ({
    x,
    label: `${titles.length} upload${titles.length > 1 ? 's' : ''}:\n${titles.join('\n')}`,
  }))
  const charts: [string, { x: string; y: number }[], (v: number) => string, string][] = [
    ['Subscribers', series((s) => s.subscribers), (v) => String(Math.round(v)), ''],
    ['Watch hours (long-form)', series((s) => (s.long_watch_minutes ?? 0) / 60), (v) => String(Math.round(v)), 'h'],
    ['Total views', series((s) => s.total_views), (v) => v.toLocaleString('en-US'), ''],
  ]
  return (
    <div className="rounded-xl border border-dusk-800 bg-dusk-900 p-4">
      <div className="flex items-baseline justify-between mb-3">
        <h3 className="text-sm font-semibold text-dusk-300 uppercase tracking-wider">Growth over time</h3>
        <span className="text-[11px] text-dusk-500">
          {snaps.length === 1
            ? 'first snapshot — banks a point on each refresh'
            : `${snaps.length} daily snapshots · ▍ = upload (hover)`}
        </span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {charts.map(([label, pts, fmt, suffix]) => (
          <div key={label}>
            <div className="text-[11px] uppercase tracking-wider text-dusk-400 mb-1">{label}</div>
            <LineChart points={pts} markers={events} format={fmt} suffix={suffix} />
          </div>
        ))}
      </div>
    </div>
  )
}

function ImpressionsCard({ studioUrl }: { studioUrl: string }) {
  const qc = useQueryClient()
  const { data } = useQuery({ queryKey: ['impressions'], queryFn: fetchImpressions })
  const rows = data ?? []
  const today = new Date().toISOString().slice(0, 10)
  const [date, setDate] = useState(today)
  const [impr, setImpr] = useState('')
  const [ctr, setCtr] = useState('')

  const add = useMutation({
    mutationFn: () => addImpression({ date, impressions: Number(impr), ctr: Number(ctr) }),
    onSuccess: (r) => {
      qc.setQueryData(['impressions'], r)
      setImpr('')
      setCtr('')
    },
  })
  const del = useMutation({
    mutationFn: (day: string) => deleteImpression(day),
    onSuccess: (r) => qc.setQueryData(['impressions'], r),
  })

  const chart = rows.map((r) => ({ x: r.date, y: r.ctr }))
  const inputCls = 'rounded-lg border border-dusk-700 bg-dusk-950 px-2 py-1 text-xs text-dusk-200 focus:border-accent-400 focus:outline-none'

  return (
    <div className="rounded-xl border border-dusk-800 bg-dusk-900 p-4">
      <div className="flex items-baseline justify-between mb-1">
        <h3 className="text-sm font-semibold text-dusk-300 uppercase tracking-wider">Impressions & CTR</h3>
        <a href={studioUrl} target="_blank" rel="noreferrer" className="text-[11px] text-accent-400 hover:text-accent-300">
          read from Studio ↗
        </a>
      </div>
      <p className="text-[11px] text-dusk-500 mb-3">
        The one metric no API exposes — log it from Studio to track the channel's CTR lever over time.
      </p>
      {chart.length > 0 && <LineChart points={chart} format={(v) => v.toFixed(1)} suffix="% CTR" color="var(--color-ok-400)" />}

      <div className="mt-3 flex flex-wrap items-end gap-2">
        <label className="text-[10px] text-dusk-500">
          date
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className={`${inputCls} block mt-0.5`} />
        </label>
        <label className="text-[10px] text-dusk-500">
          impressions
          <input type="number" value={impr} onChange={(e) => setImpr(e.target.value)} placeholder="1200" className={`${inputCls} block mt-0.5 w-24`} />
        </label>
        <label className="text-[10px] text-dusk-500">
          CTR %
          <input type="number" step="0.1" value={ctr} onChange={(e) => setCtr(e.target.value)} placeholder="2.0" className={`${inputCls} block mt-0.5 w-20`} />
        </label>
        <button
          onClick={() => add.mutate()}
          disabled={!impr || !ctr || add.isPending}
          className="rounded-lg bg-accent-500 px-3 py-1 text-xs font-medium text-white hover:bg-accent-400 disabled:opacity-40"
        >
          log
        </button>
      </div>

      {rows.length > 0 && (
        <ul className="mt-3 space-y-1">
          {[...rows].reverse().map((r) => (
            <li key={r.date} className="flex items-center justify-between text-[11px] text-dusk-400 group">
              <span>
                <span className="text-dusk-300">{r.date}</span> · {r.impressions.toLocaleString('en-US')} impr ·{' '}
                <span className="text-ok-400">{r.ctr}%</span>
                {r.note && <span className="text-dusk-600"> — {r.note}</span>}
              </span>
              <button onClick={() => del.mutate(r.date)} className="opacity-0 group-hover:opacity-100 text-bad-400 hover:text-bad-400/80">
                ✕
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default function Channel() {
  const qc = useQueryClient()
  const { data, isLoading, error, isFetching } = useQuery({ queryKey: ['channel'], queryFn: () => fetchChannel(false) })
  const refresh = useMutation({
    mutationFn: () => fetchChannel(true),
    onSuccess: (d) => qc.setQueryData(['channel'], d),
  })
  const reauth = useMutation({ mutationFn: () => createJob('auth_analytics') })

  if (isLoading) return <div className="text-dusk-400 text-sm">Loading channel data (querying YouTube)…</div>
  if (error || !data)
    return <div className="rounded-xl border border-bad-400/30 bg-bad-400/10 p-4 text-sm text-bad-400">{String(error)}</div>

  const a = data.analytics
  const longWatch = a.content_type?.find((c) => c.label === 'Long videos')?.minutes_watched ?? null
  const watchHoursForYpp = longWatch ?? a.lifetime?.minutes_watched ?? 0
  const totalViews = a.traffic?.reduce((s, r) => s + r.views, 0) ?? 0

  return (
    <div className="max-w-6xl space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-white">{data.channel.title}</h1>
        <div className="flex items-center gap-3 text-xs">
          <span className={data.cache === 'stale' ? 'text-warn-400' : 'text-dusk-500'}>
            {data.cache === 'fresh' ? 'cached' : data.cache === 'stale' ? 'stale (refresh failed)' : 'live'} ·{' '}
            {new Date(data.fetched_at * 1000).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
          </span>
          <button
            onClick={() => refresh.mutate()}
            disabled={refresh.isPending || isFetching}
            className="rounded-lg border border-dusk-700 px-3 py-1 text-dusk-300 hover:text-white hover:border-dusk-600 disabled:opacity-50"
          >
            {refresh.isPending ? 'refreshing…' : 'refresh'}
          </button>
          <a
            href={data.studio_impressions_url}
            target="_blank"
            rel="noreferrer"
            className="rounded-lg border border-dusk-700 px-3 py-1 text-dusk-300 hover:text-white hover:border-dusk-600"
          >
            impressions & CTR ↗
          </a>
        </div>
      </div>

      {!a.available && (
        <div className="rounded-xl border border-warn-400/30 bg-warn-400/10 p-4 text-sm">
          <div className="text-warn-400">Analytics API unavailable — {a.reason}</div>
          <button
            onClick={() => reauth.mutate()}
            disabled={reauth.isPending}
            className="mt-2 rounded-lg bg-accent-500 px-3 py-1.5 text-xs font-medium text-white hover:bg-accent-400"
          >
            {reauth.isSuccess ? 'started — open Jobs for the consent URL' : 're-auth analytics'}
          </button>
          {reauth.isSuccess && (
            <Link to="/jobs" className="ml-2 text-xs text-accent-400 hover:text-accent-300">→ Jobs</Link>
          )}
        </div>
      )}

      {/* YPP progress — the channel goal, always on top */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <Progress
          label="Subscribers → YPP"
          value={data.channel.subscribers}
          goal={1000}
          hint="1,000 subscribers"
        />
        <Progress
          label="Watch hours → YPP"
          value={Math.round(watchHoursForYpp / 60)}
          goal={4000}
          hint={longWatch !== null ? 'long-form public, ~12mo' : 'total watch (approx)'}
        />
      </div>

      {a.available && a.lifetime && a.last_28 && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Stat label="Views" value={fmtInt(a.lifetime.views)} sub={`+${fmtInt(a.last_28.views)} last 28d`} />
          <Stat label="Watch time" value={fmtHours(a.lifetime.minutes_watched)} sub={`+${fmtHours(a.last_28.minutes_watched)} last 28d`} />
          <Stat label="Avg view duration" value={fmtDuration(a.lifetime.avg_view_duration_s)} sub={`${a.lifetime.avg_view_pct}% retention`} />
          <Stat label="Subscribers" value={fmtInt(data.channel.subscribers)} sub={`+${a.last_28.subs_gained} / -${a.last_28.subs_lost} (28d)`} />
        </div>
      )}

      <GrowthCard videos={data.videos} />

      {(data.format_rollup?.length ?? 0) > 1 && <FormatCard rows={data.format_rollup!} />}

      {data.theme_rollup.length > 0 && <ThemeRollupCard rows={data.theme_rollup} />}

      <ImpressionsCard studioUrl={data.studio_impressions_url} />

      {data.scheduled.length > 0 && (
        <div className="rounded-xl border border-dusk-800 bg-dusk-900 p-4">
          <h3 className="text-sm font-semibold text-dusk-300 uppercase tracking-wider mb-3">
            Scheduled to publish ({data.scheduled.length})
          </h3>
          <ul className="space-y-1.5">
            {data.scheduled.map((s) => (
              <li key={s.video_id} className="flex items-center justify-between text-xs">
                <span className="text-dusk-200 truncate">
                  <span className="text-accent-400 mr-1.5">{s.kind === 'Short' ? 'S' : 'L'}</span>
                  {s.title}
                </span>
                <span className="text-dusk-400 shrink-0 ml-3">
                  {new Date(s.publish_at).toLocaleString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <VideoTable videos={data.videos} />

      {a.available && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <DimBars title="Traffic sources" rows={a.traffic ?? []} total={totalViews} />
          <DimBars title="Shorts vs long" rows={a.content_type ?? []} total={(a.content_type ?? []).reduce((s, r) => s + r.views, 0)} />
          <DimBars title="Geography" rows={a.geography ?? []} total={(a.geography ?? []).reduce((s, r) => s + r.views, 0)} />
          <DimBars title="Devices" rows={a.devices ?? []} total={(a.devices ?? []).reduce((s, r) => s + r.views, 0)} />
        </div>
      )}

      <p className="text-[11px] text-dusk-600">
        Theme is the pipeline's own attribution from run logs where available; a{' '}
        <span className="text-dusk-500">~</span> marks a title-inferred guess. Impressions &amp; CTR are Studio-web only —
        use the link above.
      </p>
    </div>
  )
}
