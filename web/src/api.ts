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
  jobs: { running: { id: number; type: string; title: string; started_at: string } | null; queued: number }
}

export type JobStatus = 'queued' | 'running' | 'done' | 'failed' | 'cancelled'

export interface JobProgress {
  stage: string
  pct: number | null
}

export interface PreflightCheck {
  ok: boolean
  label: string
  detail: string
}

export interface Preflight {
  ok: boolean
  checks: PreflightCheck[]
}

export interface VeoSource {
  name: string
  index: number
  size: number
  mtime: number
  cached_heights: number[]
}

export interface VeoSources {
  downloads_dir: string
  sources: VeoSource[]
  bank: VeoClip[]
}

export interface OutputEntry {
  name: string
  path: string
  kind: 'video' | 'short' | 'thumbnail' | 'music'
  size: number
  mtime: string
  duration: number | null
}

export interface UsedImage {
  name: string
  path: string
  mtime: string
}

export interface VideoAnalytics {
  minutes_watched: number
  avg_view_duration_s: number
  avg_view_pct: number
}

export interface ChannelVideo {
  video_id: string
  title: string
  kind: 'Video' | 'Short'
  date: string
  secs: number
  views: number
  likes: number
  comments: number
  privacy: string | null
  publish_at: string | null
  theme: string | null
  theme_source: 'log' | 'inferred' | 'genre' | 'unknown'
  analytics: VideoAnalytics | null
}

export interface CoreBlock {
  views: number
  minutes_watched: number
  avg_view_duration_s: number
  avg_view_pct: number
  subs_gained: number
  subs_lost: number
  likes: number
  comments: number
  shares: number
}

export interface DimRow {
  label: string
  views: number
  minutes_watched: number | null
}

export interface ChannelAnalytics {
  available: boolean
  reason?: string
  lifetime?: CoreBlock
  last_28?: CoreBlock
  traffic?: DimRow[]
  content_type?: DimRow[]
  geography?: DimRow[]
  devices?: DimRow[]
}

export interface ThemeRollup {
  theme: string
  videos: number
  shorts: number
  views: number
  minutes_watched: number
  avg_view_pct: number | null
}

export interface ScheduledUpload {
  video_id: string
  title: string
  kind: 'Video' | 'Short'
  publish_at: string
}

export interface ChannelData {
  channel: { title: string; subscribers: number; views: number; video_count: number }
  videos: ChannelVideo[]
  scheduled: ScheduledUpload[]
  analytics: ChannelAnalytics
  theme_rollup: ThemeRollup[]
  generated_at: string
  fetched_at: number
  cache: 'fresh' | 'live' | 'stale'
  refresh_error?: string
  analytics_token: TokenStatus | null
  studio_impressions_url: string
}

export interface Job {
  id: number
  type: string
  title: string
  cmd: string[]
  env: Record<string, string>
  status: JobStatus
  progress?: JobProgress | null
  cancel_requested: boolean
  pid: number | null
  log_path: string | null
  exit_code: number | null
  created_at: string
  started_at: string | null
  ended_at: string | null
  queue_position?: number | null
}

export interface PromptScene {
  scene: string
  variations: string[]
}

export interface PromptTheme {
  key: string
  title: string
  style: string
  scenes: PromptScene[]
  music_prompts: string[]
  thumbnail: string | null
}

export interface Prompts {
  date: string
  age_days: number
  themes: PromptTheme[]
}

export interface ThemeImages {
  theme: string
  images: ImageEntry[]
  min_images: number
}

export interface Settings {
  paths: Record<string, string>
  ports: { api: number; vite_dev: number }
  defaults: { key: string; value: string | number | null; note: string }[]
  tokens: TokenStatus[]
  themes: { key: string; title: string; description: string; style_notes: string; custom_style: boolean }[]
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
export const fetchJobs = () => get<Job[]>('/api/jobs')
export const fetchJob = (id: number) => get<Job>(`/api/jobs/${id}`)
export const fetchPrompts = () => get<Prompts>('/api/prompts/today')
export const fetchPromptHistory = () => get<string[]>('/api/prompts/history')
export const fetchPromptsForDay = (date: string) => get<Prompts>(`/api/prompts/day/${date}`)
export const fetchPreflight = (upload: boolean, musicMode: string, animate: string) =>
  get<Preflight>(`/api/build/preflight?upload=${upload}&music_mode=${musicMode}&animate=${animate}`)
export const fetchVeoSources = () => get<VeoSources>('/api/veo/sources')

async function post<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`${url} → ${res.status} ${await res.text()}`)
  return res.json()
}

export const createJob = (type: string, params: Record<string, unknown> = {}, env: Record<string, string> = {}) =>
  post<Job>('/api/jobs', { type, params, env })
export const cancelJob = (id: number) => post<Job>(`/api/jobs/${id}/cancel`)
export const fetchChannel = (refresh = false) => get<ChannelData>(`/api/channel${refresh ? '?refresh=1' : ''}`)
export const fetchSettings = () => get<Settings>('/api/settings')
export const fetchOutputs = () => get<OutputEntry[]>('/api/outputs')
export const fetchUsedImages = (limit = 48) => get<UsedImage[]>(`/api/assets/used-images?limit=${limit}`)
export const trashAsset = (path: string) => post<{ ok: boolean }>('/api/assets/trash', { path })
export const setThumb = (path: string) => post<{ ok: boolean; thumb: string }>('/api/assets/set-thumb', { path })

export const jobLogUrl = (id: number) => `/api/jobs/${id}/log`

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
