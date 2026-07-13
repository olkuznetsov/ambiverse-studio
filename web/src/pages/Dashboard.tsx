import { useQuery } from '@tanstack/react-query'
import { fetchOverview, fmtBytes, fmtDate, imgUrl, vthumbUrl } from '../api'
import type { ThemeSummary } from '../api'

function Badge({ tone, children }: { tone: 'ok' | 'warn' | 'bad' | 'dim'; children: React.ReactNode }) {
  const tones = {
    ok: 'bg-ok-400/15 text-ok-400',
    warn: 'bg-warn-400/15 text-warn-400',
    bad: 'bg-bad-400/15 text-bad-400',
    dim: 'bg-dusk-700/50 text-dusk-400',
  }
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ${tones[tone]}`}>
      {children}
    </span>
  )
}

function Card({ title, children, right }: { title: string; children: React.ReactNode; right?: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-dusk-800 bg-dusk-900 p-4">
      <div className="flex items-center justify-between mb-3">
        <h2 className="text-sm font-semibold text-dusk-300 uppercase tracking-wider">{title}</h2>
        {right}
      </div>
      {children}
    </section>
  )
}

function ThemeCard({ t }: { t: ThemeSummary }) {
  const pct = Math.min(100, Math.round((t.image_count / t.min_images) * 100))
  return (
    <div className="rounded-xl border border-dusk-800 bg-dusk-900 overflow-hidden">
      <div className="h-20 bg-dusk-850 flex">
        {t.preview_paths.length > 0 ? (
          t.preview_paths.map((p) => (
            <img key={p} src={imgUrl(p, 240)} className="h-20 flex-1 min-w-0 object-cover" loading="lazy" alt="" />
          ))
        ) : (
          <div className="flex-1 flex items-center justify-center text-dusk-600 text-xs">no unused images</div>
        )}
      </div>
      <div className="p-3">
        <div className="flex items-center justify-between gap-2">
          <div className="text-sm font-medium text-white truncate">{t.title}</div>
          {t.eligible ? <Badge tone="ok">ready</Badge> : <Badge tone="dim">{t.min_images - t.image_count} more</Badge>}
        </div>
        <div className="mt-2 h-1.5 rounded-full bg-dusk-800 overflow-hidden">
          <div
            className={`h-full rounded-full ${t.eligible ? 'bg-ok-400' : 'bg-accent-500'}`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <div className="mt-2 flex items-center justify-between text-[11px] text-dusk-400">
          <span>
            {t.image_count}/{t.min_images} images
            {t.has_custom_thumb && <span className="text-accent-400"> · thumb ✓</span>}
          </span>
          <span>last: {fmtDate(t.last_video)}</span>
        </div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { data, error, isLoading } = useQuery({ queryKey: ['overview'], queryFn: fetchOverview })

  if (isLoading) return <div className="text-dusk-400 text-sm">Reading pipeline state…</div>
  if (error || !data)
    return (
      <div className="rounded-xl border border-bad-400/30 bg-bad-400/10 p-4 text-sm text-bad-400">
        API unreachable: {String(error)} — is uvicorn running on 4700?
      </div>
    )

  const eligible = data.themes.filter((t) => t.eligible).length

  return (
    <div className="max-w-6xl">
      <div className="flex items-baseline justify-between mb-5">
        <h1 className="text-xl font-semibold text-white">Dashboard</h1>
        <div className="text-xs text-dusk-400">
          {eligible > 0 ? (
            <span className="text-ok-400">● {eligible} theme{eligible > 1 ? 's' : ''} ready to build</span>
          ) : (
            <span>○ no theme has enough images yet</span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6">
        {data.themes.map((t) => (
          <ThemeCard key={t.key} t={t} />
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        <Card
          title="Music bank"
          right={<Badge tone={data.music.library_count > 0 ? 'ok' : 'dim'}>{data.music.library_count} tracks</Badge>}
        >
          <div className="text-2xl font-semibold text-white">
            {data.music.library_minutes}
            <span className="text-sm text-dusk-400 font-normal"> min banked</span>
          </div>
          <div className="text-xs text-dusk-400 mt-1">{data.music.used_count} tracks used to date</div>
        </Card>

        <Card title="Tokens & disk">
          <ul className="space-y-1.5">
            {data.tokens.map((t) => (
              <li key={t.key} className="flex items-center justify-between text-xs">
                <span className="text-dusk-300">{t.label}</span>
                {t.present ? <Badge tone="ok">present</Badge> : <Badge tone="bad">missing — re-auth</Badge>}
              </li>
            ))}
            <li className="flex items-center justify-between text-xs pt-1.5 border-t border-dusk-800">
              <span className="text-dusk-300">Disk free</span>
              <Badge tone={data.disk.free_gb < 30 ? 'warn' : 'ok'}>
                {data.disk.free_gb} GB ({100 - data.disk.used_pct}%)
              </Badge>
            </li>
          </ul>
        </Card>

        <Card title="Library totals">
          <ul className="space-y-1.5 text-xs">
            <li className="flex justify-between">
              <span className="text-dusk-300">Used images (all time)</span>
              <span className="text-white font-medium">{data.used_images_count}</span>
            </li>
            <li className="flex justify-between">
              <span className="text-dusk-300">Veo clips banked</span>
              <span className="text-white font-medium">{data.veo_bank.length}</span>
            </li>
            <li className="flex justify-between">
              <span className="text-dusk-300">Pipeline dir</span>
              <span className="text-dusk-400 truncate max-w-40" title={data.animembient_dir}>
                {data.animembient_dir.replace(/^\/Users\/[^/]+/, '~')}
              </span>
            </li>
          </ul>
        </Card>
      </div>

      <div className="mt-6">
        <Card title="Veo clip bank" right={<span className="text-[11px] text-dusk-400">output/veo_slow/</span>}>
          {data.veo_bank.length === 0 ? (
            <div className="text-xs text-dusk-400">No slowed clips banked yet.</div>
          ) : (
            <div className="grid grid-cols-3 md:grid-cols-5 gap-2">
              {data.veo_bank.map((c) => (
                <figure key={c.path} className="rounded-lg overflow-hidden bg-dusk-850 border border-dusk-800">
                  <img src={vthumbUrl(c.path, 320)} className="aspect-video w-full object-cover" loading="lazy" alt="" />
                  <figcaption className="px-2 py-1 flex items-center justify-between text-[10px] text-dusk-400">
                    <span className="truncate">{c.name}</span>
                    {c.enhanced && <Badge tone="ok">HD</Badge>}
                  </figcaption>
                  <div className="px-2 pb-1 text-[10px] text-dusk-600">{fmtBytes(c.size)}</div>
                </figure>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}
