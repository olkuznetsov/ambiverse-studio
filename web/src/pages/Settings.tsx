import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { createJob, fetchSettings } from '../api'
import type { TokenStatus } from '../api'

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-dusk-800 bg-dusk-900 p-4">
      <h2 className="text-sm font-semibold text-dusk-300 uppercase tracking-wider mb-3">{title}</h2>
      {children}
    </section>
  )
}

const REAUTH_JOB: Record<string, string> = {
  upload: 'auth_youtube',
  analytics: 'auth_analytics',
}

function TokenRow({ t }: { t: TokenStatus }) {
  const qc = useQueryClient()
  const reauth = useMutation({
    mutationFn: () => createJob(REAUTH_JOB[t.key]),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['jobs'] }),
  })
  const jobType = REAUTH_JOB[t.key]
  return (
    <li className="flex items-center justify-between gap-3 text-xs py-1.5 border-b border-dusk-800/60 last:border-0">
      <div className="min-w-0">
        <div className="text-dusk-200">{t.label}</div>
        {t.mtime && (
          <div className="text-[11px] text-dusk-500">
            updated {new Date(t.mtime).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
          </div>
        )}
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${t.present ? 'bg-ok-400/15 text-ok-400' : 'bg-bad-400/15 text-bad-400'}`}>
          {t.present ? 'present' : 'missing'}
        </span>
        {jobType && (
          reauth.isSuccess ? (
            <Link to="/jobs" className="text-[11px] text-accent-400 hover:text-accent-300">
              consent URL in Jobs →
            </Link>
          ) : (
            <button
              onClick={() => reauth.mutate()}
              disabled={reauth.isPending}
              className="rounded-md border border-dusk-700 px-2 py-0.5 text-[11px] text-dusk-300 hover:text-white hover:border-dusk-600 disabled:opacity-50"
            >
              re-auth
            </button>
          )
        )}
      </div>
    </li>
  )
}

const homeShort = (p: string) => p.replace(/^\/Users\/[^/]+/, '~')

export default function Settings() {
  const { data, isLoading, error } = useQuery({ queryKey: ['settings'], queryFn: fetchSettings })

  if (isLoading) return <div className="text-dusk-400 text-sm">Loading settings…</div>
  if (error || !data)
    return <div className="rounded-xl border border-bad-400/30 bg-bad-400/10 p-4 text-sm text-bad-400">{String(error)}</div>

  return (
    <div className="max-w-4xl space-y-4">
      <h1 className="text-xl font-semibold text-white">Settings</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card title="Paths & ports">
          <ul className="space-y-1.5 text-xs">
            {Object.entries(data.paths).map(([k, v]) => (
              <li key={k} className="flex justify-between gap-3">
                <span className="text-dusk-400 shrink-0">{k.replace(/_/g, ' ')}</span>
                <span className="text-dusk-200 font-mono text-[11px] truncate" title={v}>{homeShort(v)}</span>
              </li>
            ))}
            <li className="flex justify-between gap-3 pt-1.5 border-t border-dusk-800">
              <span className="text-dusk-400">ports</span>
              <span className="text-dusk-200 font-mono text-[11px]">API {data.ports.api} · Vite {data.ports.vite_dev}</span>
            </li>
          </ul>
        </Card>

        <Card title="Tokens">
          <ul>
            {data.tokens.map((t) => (
              <TokenRow key={t.key} t={t} />
            ))}
          </ul>
          <p className="mt-2 text-[11px] text-dusk-600">
            Re-auth runs the auth script as a job and prints a consent URL in its live log — open it in the
            channel's Google account.
          </p>
        </Card>
      </div>

      <Card title="Pipeline defaults (config.py — read-only)">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1.5">
          {data.defaults.map((d) => (
            <div key={d.key} className="flex items-baseline justify-between gap-3 text-xs">
              <span className="font-mono text-[11px] text-dusk-300">{d.key}</span>
              <span className="text-right">
                <span className="text-white font-medium">{String(d.value)}</span>
                <span className="block text-[10px] text-dusk-600">{d.note}</span>
              </span>
            </div>
          ))}
        </div>
        <p className="mt-3 text-[11px] text-dusk-600">
          These are the pipeline's own defaults — override per-build in the Build wizard, or edit
          <span className="font-mono text-dusk-500"> config.py</span> / <span className="font-mono text-dusk-500">.env</span> directly.
        </p>
      </Card>

      <Card title="Theme registry">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
          {data.themes.map((t) => (
            <div key={t.key} className="rounded-lg border border-dusk-800 bg-dusk-850 p-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-white">{t.title}</span>
                <span className={`rounded-full px-2 py-0.5 text-[10px] ${t.custom_style ? 'bg-accent-500/15 text-accent-300' : 'bg-dusk-700/50 text-dusk-400'}`}>
                  {t.custom_style ? 'own art style' : 'anime base'}
                </span>
              </div>
              <div className="text-[11px] text-dusk-500 font-mono mt-0.5">{t.key}</div>
              <p className="text-[11px] text-dusk-400 mt-1.5 leading-relaxed">{t.description}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
