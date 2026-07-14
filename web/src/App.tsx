import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Assets from './pages/Assets'
import Build from './pages/Build'
import Channel from './pages/Channel'
import Jobs from './pages/Jobs'
import Prompts from './pages/Prompts'
import Stub from './pages/Stub'

const NAV = [
  { to: '/dashboard', label: 'Dashboard', icon: '◈' },
  { to: '/prompts', label: 'Prompts', icon: '✎' },
  { to: '/assets', label: 'Assets', icon: '🗀' },
  { to: '/build', label: 'Build', icon: '⚙' },
  { to: '/jobs', label: 'Jobs', icon: '☰' },
  { to: '/channel', label: 'Channel', icon: '▲' },
  { to: '/settings', label: 'Settings', icon: '⚒' },
]

export default function App() {
  return (
    <div className="flex min-h-screen">
      <aside className="w-52 shrink-0 border-r border-dusk-800 bg-dusk-900 flex flex-col">
        <div className="px-5 py-5 border-b border-dusk-800">
          <div className="text-lg font-semibold tracking-wide text-white">
            Ambiverse<span className="text-accent-400"> Studio</span>
          </div>
          <div className="text-[11px] text-dusk-400 mt-0.5">pipeline mission control</div>
        </div>
        <nav className="p-2 flex flex-col gap-0.5">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              className={({ isActive }) =>
                `flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors ${
                  isActive
                    ? 'bg-accent-500/15 text-accent-300 font-medium'
                    : 'text-dusk-300 hover:bg-dusk-800 hover:text-dusk-200'
                }`
              }
            >
              <span className="w-4 text-center opacity-80">{n.icon}</span>
              {n.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="flex-1 min-w-0 p-6">
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/assets" element={<Assets />} />
          <Route path="/prompts" element={<Prompts />} />
          <Route path="/build" element={<Build />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/channel" element={<Channel />} />
          <Route path="/settings" element={<Stub title="Settings" milestone="M6" note="Paths, knob defaults, token re-auth." />} />
        </Routes>
      </main>
    </div>
  )
}
