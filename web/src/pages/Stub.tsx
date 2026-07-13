export default function Stub({ title, milestone, note }: { title: string; milestone: string; note: string }) {
  return (
    <div>
      <h1 className="text-xl font-semibold text-white mb-4">{title}</h1>
      <div className="rounded-xl border border-dashed border-dusk-700 bg-dusk-900/50 p-10 text-center">
        <div className="text-dusk-400 text-sm">
          Coming in <span className="text-accent-400 font-medium">{milestone}</span>
        </div>
        <div className="text-dusk-400/70 text-xs mt-2">{note}</div>
      </div>
    </div>
  )
}
