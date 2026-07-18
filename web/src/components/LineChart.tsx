// Tiny dependency-free SVG line chart (single series). Handles 1 point (dot),
// auto-scales Y to the data, labels the first/last X and the latest value.
// Optional `markers` (dated events, e.g. uploads) render as ticks along the
// baseline, positioned by date between the first and last point.

export interface Point {
  x: string // date label
  y: number
}

export interface Marker {
  x: string // date
  label: string // tooltip
}

export default function LineChart({
  points,
  markers = [],
  color = 'var(--color-accent-400)',
  height = 90,
  format = (v: number) => String(v),
  suffix = '',
}: {
  points: Point[]
  markers?: Marker[]
  color?: string
  height?: number
  format?: (v: number) => string
  suffix?: string
}) {
  if (points.length === 0)
    return <div className="text-[11px] text-dusk-600 py-6 text-center">no data yet — accrues over time</div>

  const W = 300
  const H = height
  const padX = 6
  const padY = 14
  const ys = points.map((p) => p.y)
  const min = Math.min(...ys)
  const max = Math.max(...ys)
  const span = max - min || 1
  const n = points.length

  const xAt = (i: number) => (n === 1 ? W / 2 : padX + (i / (n - 1)) * (W - 2 * padX))
  const yAt = (v: number) => padY + (1 - (v - min) / span) * (H - 2 * padY)

  const line = points.map((p, i) => `${xAt(i).toFixed(1)},${yAt(p.y).toFixed(1)}`).join(' ')
  const last = points[n - 1]
  const area = `${padX},${H - padY} ${line} ${xAt(n - 1)},${H - padY}`

  // date-positioned event ticks (only meaningful with a real time span)
  const t0 = Date.parse(points[0].x)
  const t1 = Date.parse(last.x)
  const shownMarkers =
    n > 1 && t1 > t0
      ? markers
          .map((m) => ({ ...m, t: Date.parse(m.x) }))
          .filter((m) => m.t >= t0 && m.t <= t1)
          .map((m) => ({ ...m, mx: padX + ((m.t - t0) / (t1 - t0)) * (W - 2 * padX) }))
      : []

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full" preserveAspectRatio="none" style={{ height }}>
        <polygon points={area} fill={color} opacity={0.08} />
        <polyline points={line} fill="none" stroke={color} strokeWidth={1.5}
                  strokeLinejoin="round" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
        {points.map((p, i) => (
          <circle key={i} cx={xAt(i)} cy={yAt(p.y)} r={i === n - 1 ? 3 : 1.8} fill={color} />
        ))}
        {shownMarkers.map((m, i) => (
          <g key={i}>
            <line x1={m.mx} x2={m.mx} y1={H - padY + 1} y2={H - padY + 7}
                  stroke="var(--color-warn-400)" strokeWidth={2} />
            <circle cx={m.mx} cy={H - padY + 4} r={7} fill="transparent">
              <title>{`${m.x} — ${m.label}`}</title>
            </circle>
          </g>
        ))}
      </svg>
      <div className="flex justify-between text-[10px] text-dusk-600 mt-1">
        <span>{points[0].x.slice(5)}</span>
        <span className="text-dusk-300 font-medium">{format(last.y)}{suffix}</span>
        {n > 1 && <span>{last.x.slice(5)}</span>}
      </div>
    </div>
  )
}
