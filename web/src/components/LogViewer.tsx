import { useEffect, useRef, useState } from 'react'
import { jobLogUrl } from '../api'

/** Live SSE tail of a job log; calls onEnd with the final status. */
export default function LogViewer({ jobId, onEnd }: { jobId: number; onEnd?: (status: string) => void }) {
  const [text, setText] = useState('')
  const pre = useRef<HTMLPreElement>(null)
  const onEndRef = useRef(onEnd)
  onEndRef.current = onEnd

  useEffect(() => {
    setText('')
    const es = new EventSource(jobLogUrl(jobId))
    es.addEventListener('log', (e) => setText((t) => t + JSON.parse((e as MessageEvent).data)))
    es.addEventListener('end', (e) => {
      es.close()
      onEndRef.current?.((e as MessageEvent).data)
    })
    es.onerror = () => es.close()
    return () => es.close()
  }, [jobId])

  useEffect(() => {
    const el = pre.current
    if (el) el.scrollTop = el.scrollHeight
  }, [text])

  return (
    <pre
      ref={pre}
      className="max-h-80 overflow-auto rounded-lg bg-dusk-950 border border-dusk-800 p-3 text-[11px] leading-relaxed text-dusk-300 font-mono whitespace-pre-wrap"
    >
      {text || 'waiting for output…'}
    </pre>
  )
}
