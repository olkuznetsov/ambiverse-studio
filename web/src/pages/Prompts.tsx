import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { createJob, fetchPrompts } from '../api'
import type { PromptTheme } from '../api'
import LogViewer from '../components/LogViewer'

function CopyBtn({ text, label = 'copy' }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      onClick={() => {
        navigator.clipboard.writeText(text)
        setCopied(true)
        setTimeout(() => setCopied(false), 1200)
      }}
      className={`shrink-0 rounded-md border px-2 py-0.5 text-[11px] transition-colors ${
        copied
          ? 'border-ok-400/50 text-ok-400'
          : 'border-dusk-700 text-dusk-400 hover:text-dusk-200 hover:border-dusk-600'
      }`}
    >
      {copied ? 'copied ✓' : label}
    </button>
  )
}

function ThemeBlock({ t }: { t: PromptTheme }) {
  const [open, setOpen] = useState(false)
  return (
    <section className="rounded-xl border border-dusk-800 bg-dusk-900">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-4 py-3 text-left"
      >
        <span className="text-sm font-medium text-white">{t.title}</span>
        <span className="text-[11px] text-dusk-400">
          {t.scenes.length} scenes · {t.music_prompts.length} music prompts {open ? '▾' : '▸'}
        </span>
      </button>
      {open && (
        <div className="border-t border-dusk-800 p-4 space-y-4">
          <div className="flex items-start gap-2">
            <div className="min-w-0 flex-1">
              <div className="text-[11px] uppercase tracking-wider text-dusk-400 mb-1">Style (include with every image)</div>
              <p className="text-xs text-dusk-300 leading-relaxed">{t.style}</p>
            </div>
            <CopyBtn text={t.style} />
          </div>

          {t.scenes.map((s, i) => (
            <div key={i} className="rounded-lg border border-dusk-800 bg-dusk-850 p-3">
              <div className="flex items-start gap-2">
                <div className="min-w-0 flex-1">
                  <div className="text-[11px] uppercase tracking-wider text-dusk-400 mb-1">Scene {i + 1}</div>
                  <p className="text-xs text-dusk-200 leading-relaxed">{s.scene}</p>
                </div>
                <CopyBtn text={`${t.style}\n\n${s.scene}`} label="style+scene" />
              </div>
              {s.variations.length > 0 && (
                <ul className="mt-2.5 space-y-1">
                  {s.variations.map((v, k) => (
                    <li key={k} className="flex items-center gap-2 text-[11px] text-dusk-400">
                      <CopyBtn text={`${t.style}\n\n${s.scene}\n${v}`} label={`${k + 1}`} />
                      <span className="truncate">{v}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          ))}

          {t.thumbnail && (
            <div className="rounded-lg border border-accent-500/25 bg-accent-500/5 p-3">
              <div className="flex items-start gap-2">
                <div className="min-w-0 flex-1">
                  <div className="text-[11px] uppercase tracking-wider text-accent-400 mb-1">
                    Thumbnail — save result as thumb.png in images/{t.key}/
                  </div>
                  <p className="text-xs text-dusk-300 leading-relaxed whitespace-pre-wrap line-clamp-4">{t.thumbnail}</p>
                </div>
                <CopyBtn text={t.thumbnail} />
              </div>
            </div>
          )}

          {t.music_prompts.length > 0 && (
            <div>
              <div className="text-[11px] uppercase tracking-wider text-dusk-400 mb-1.5">
                Suno prompts — paste one per track, keep both generations
              </div>
              <ul className="space-y-1">
                {t.music_prompts.map((m, k) => (
                  <li key={k} className="flex items-center gap-2 text-[11px] text-dusk-300">
                    <CopyBtn text={m} label={`${k + 1}`} />
                    <span className="truncate">{m}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  )
}

export default function Prompts() {
  const qc = useQueryClient()
  const [genJobId, setGenJobId] = useState<number | null>(null)
  const [genStatus, setGenStatus] = useState<string | null>(null)
  const { data, error, isLoading } = useQuery({ queryKey: ['prompts'], queryFn: fetchPrompts, retry: false })

  const generate = useMutation({
    mutationFn: () => createJob('generate_prompts'),
    onSuccess: (job) => {
      setGenJobId(job.id)
      setGenStatus('running')
      qc.invalidateQueries({ queryKey: ['jobs'] })
    },
  })

  const noneYet = error && String(error).includes('404')

  return (
    <div className="max-w-4xl">
      <div className="flex items-center justify-between mb-5">
        <h1 className="text-xl font-semibold text-white">Prompts</h1>
        <div className="flex items-center gap-3">
          {data && (
            <span className={`text-xs ${data.age_days > 1 ? 'text-warn-400' : 'text-dusk-400'}`}>
              from {data.date}
              {data.age_days === 0 ? ' (today)' : data.age_days === 1 ? ' (yesterday)' : ` (${data.age_days} days old)`}
            </span>
          )}
          <button
            onClick={() => generate.mutate()}
            disabled={generate.isPending || genStatus === 'running'}
            className="rounded-lg bg-accent-500 px-4 py-1.5 text-sm font-medium text-white hover:bg-accent-400 disabled:opacity-50"
          >
            {genStatus === 'running' ? 'Generating…' : 'Generate fresh prompts'}
          </button>
        </div>
      </div>

      {genJobId !== null && genStatus === 'running' && (
        <div className="mb-5">
          <div className="text-xs text-dusk-400 mb-2">generate_prompts — live output (job #{genJobId})</div>
          <LogViewer
            jobId={genJobId}
            onEnd={(status) => {
              setGenStatus(status)
              qc.invalidateQueries({ queryKey: ['prompts'] })
              qc.invalidateQueries({ queryKey: ['jobs'] })
            }}
          />
        </div>
      )}
      {genStatus && genStatus !== 'running' && (
        <div
          className={`mb-5 rounded-lg border px-3 py-2 text-xs ${
            genStatus === 'done'
              ? 'border-ok-400/30 bg-ok-400/10 text-ok-400'
              : 'border-bad-400/30 bg-bad-400/10 text-bad-400'
          }`}
        >
          generation {genStatus} — {genStatus === 'done' ? 'prompts below are fresh' : 'see the Jobs page for the log'}
        </div>
      )}

      {isLoading && <div className="text-dusk-400 text-sm">Loading prompts…</div>}
      {noneYet && (
        <div className="rounded-xl border border-dashed border-dusk-700 bg-dusk-900/50 p-10 text-center text-sm text-dusk-400">
          No prompts generated yet — hit “Generate fresh prompts”.
        </div>
      )}
      {data && (
        <div className="space-y-3">
          <p className="text-xs text-dusk-500">
            Workflow: per image, copy <span className="text-dusk-300">style+scene+one variation</span> (numbered buttons)
            → paste into ChatGPT → drop results into <span className="text-dusk-300">images/&lt;theme&gt;/</span>. Music:
            one Suno prompt per track → <span className="text-dusk-300">music/library/</span>.
          </p>
          {data.themes.map((t) => (
            <ThemeBlock key={t.key} t={t} />
          ))}
        </div>
      )}
    </div>
  )
}
