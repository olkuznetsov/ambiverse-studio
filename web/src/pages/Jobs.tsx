import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { cancelJob, fetchJobs } from '../api'
import type { Job, JobStatus } from '../api'
import LogViewer from '../components/LogViewer'

const STATUS_STYLE: Record<JobStatus, string> = {
  queued: 'bg-dusk-700/50 text-dusk-300',
  running: 'bg-accent-500/20 text-accent-300',
  done: 'bg-ok-400/15 text-ok-400',
  failed: 'bg-bad-400/15 text-bad-400',
  cancelled: 'bg-warn-400/15 text-warn-400',
}

function duration(j: Job): string {
  if (!j.started_at) return '—'
  const end = j.ended_at ? new Date(j.ended_at).getTime() : Date.now()
  const s = Math.max(0, Math.round((end - new Date(j.started_at).getTime()) / 1000))
  return s < 60 ? `${s}s` : `${Math.floor(s / 60)}m ${s % 60}s`
}

export default function Jobs() {
  const qc = useQueryClient()
  const [selected, setSelected] = useState<number | null>(null)
  const { data: jobs, isLoading } = useQuery({
    queryKey: ['jobs'],
    queryFn: fetchJobs,
    refetchInterval: (q) =>
      (q.state.data ?? []).some((j) => j.status === 'running' || j.status === 'queued') ? 2000 : false,
  })
  const cancel = useMutation({
    mutationFn: cancelJob,
    onSettled: () => qc.invalidateQueries({ queryKey: ['jobs'] }),
  })

  const active = jobs?.find((j) => j.id === selected) ?? jobs?.find((j) => j.status === 'running') ?? jobs?.[0]

  if (isLoading) return <div className="text-dusk-400 text-sm">Loading jobs…</div>

  return (
    <div className="max-w-6xl">
      <h1 className="text-xl font-semibold text-white mb-5">Jobs</h1>
      {!jobs || jobs.length === 0 ? (
        <div className="rounded-xl border border-dashed border-dusk-700 bg-dusk-900/50 p-10 text-center text-sm text-dusk-400">
          No jobs yet — run one from the Prompts (or later, Build) page.
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <ul className="space-y-2">
            {jobs.map((j) => (
              <li
                key={j.id}
                onClick={() => setSelected(j.id)}
                className={`cursor-pointer rounded-xl border px-4 py-3 transition-colors ${
                  active?.id === j.id ? 'border-accent-500/50 bg-dusk-850' : 'border-dusk-800 bg-dusk-900 hover:bg-dusk-850'
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="text-sm text-white truncate">
                      <span className="text-dusk-500 mr-1.5">#{j.id}</span>
                      {j.title}
                    </div>
                    <div className="text-[11px] text-dusk-400 mt-0.5">
                      {new Date(j.created_at).toLocaleString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}
                      {' · '}
                      {duration(j)}
                      {j.status === 'queued' && j.queue_position ? ` · position ${j.queue_position}` : ''}
                      {j.exit_code !== null && j.status !== 'done' ? ` · exit ${j.exit_code}` : ''}
                    </div>
                    {j.status === 'running' && j.progress && (
                      <div className="mt-1.5">
                        <div className="text-[11px] text-accent-300">{j.progress.stage}</div>
                        {j.progress.pct !== null && (
                          <div className="mt-1 h-1 rounded-full bg-dusk-800 overflow-hidden">
                            <div className="h-full rounded-full bg-accent-500" style={{ width: `${j.progress.pct}%` }} />
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${STATUS_STYLE[j.status]}`}>
                      {j.status}
                    </span>
                    {(j.status === 'running' || j.status === 'queued') && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          cancel.mutate(j.id)
                        }}
                        className="rounded-md border border-bad-400/40 px-2 py-0.5 text-[11px] text-bad-400 hover:bg-bad-400/10"
                      >
                        cancel
                      </button>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
          {active && (
            <div>
              <div className="text-xs text-dusk-400 mb-2">
                log — job #{active.id} <span className="text-dusk-600">({active.type})</span>
              </div>
              <LogViewer
                jobId={active.id}
                onEnd={() => qc.invalidateQueries({ queryKey: ['jobs'] })}
              />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
