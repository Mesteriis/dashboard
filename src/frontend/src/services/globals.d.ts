export {}

declare global {
  interface Window {
    __DASHBOARD_ADMIN_TOKEN__?: string
    __OKO_API_BASE__?: string
    __OKO_DESKTOP_RUNTIME__?: {
      desktop: boolean
      mode: 'web' | 'embedded' | 'remote'
      apiBaseUrl: string
      remoteBaseUrl: string
      embeddedRunning: boolean
    }
    __TAURI_INTERNALS__?: unknown
  }
}
