// Typed fetchers for the Studio API (proxied /api in dev, same-origin in prod).

export interface ThemeSummary {
  key: string
  title: string
  description: string
  image_count: number
  min_images: number
  eligible: boolean
  has_custom_thumb: boolean
  thumb_path: string | null
  last_video: string | null
  preview_paths: string[]
}

export interface ImageEntry {
  name: string
  path: string
  size: number
  mtime: string
  width?: number | null
  height?: number | null
  warnings?: string[]
}

export interface TrackEntry {
  name: string
  path: string
  size: number
  mtime?: string
  duration: number | null
}

export interface MusicInventory {
  library: TrackEntry[]
  library_count: number
  library_minutes: number
  used_count: number
  used?: TrackEntry[]
}

export interface VeoClip {
  name: string
  path: string
  size: number
  mtime: string
  enhanced: boolean
}

export interface TokenStatus {
  key: string
  label: string
  present: boolean
  mtime: string | null
}

export interface Overview {
  themes: ThemeSummary[]
  music: MusicInventory
  veo_bank: VeoClip[]
  tokens: TokenStatus[]
  disk: { free_gb: number; total_gb: number; used_pct: number }
  used_images_count: number
  animembient_dir: string
  generated_at: string
}

export interface ThemeImages {
  theme: string
  images: ImageEntry[]
  min_images: number
}

async function get<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${url} → ${res.status} ${await res.text()}`)
  return res.json()
}

export const fetchOverview = () => get<Overview>('/api/state/overview')
export const fetchThemeImages = (theme: string) =>
  get<ThemeImages>(`/api/themes/${theme}/images`)
export const fetchMusic = () => get<MusicInventory>('/api/music')

export const imgUrl = (path: string, size = 480) =>
  `/api/media/img?path=${encodeURIComponent(path)}&size=${size}`
export const vthumbUrl = (path: string, size = 480) =>
  `/api/media/vthumb?path=${encodeURIComponent(path)}&size=${size}`
export const fileUrl = (path: string) =>
  `/api/media/file?path=${encodeURIComponent(path)}`

export const fmtBytes = (n: number) =>
  n >= 1e9 ? `${(n / 1e9).toFixed(1)} GB` : n >= 1e6 ? `${(n / 1e6).toFixed(1)} MB` : `${Math.round(n / 1e3)} KB`

export const fmtDuration = (s: number | null | undefined) => {
  if (!s) return '—'
  const m = Math.floor(s / 60)
  return `${m}:${String(Math.round(s % 60)).padStart(2, '0')}`
}

export const fmtDate = (iso: string | null | undefined) => {
  if (!iso) return 'never'
  const d = new Date(iso)
  const days = Math.floor((Date.now() - d.getTime()) / 86400000)
  const abs = d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
  return days <= 0 ? `today (${abs})` : days === 1 ? `yesterday` : `${days}d ago (${abs})`
}
