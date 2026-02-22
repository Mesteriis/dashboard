export {}

declare global {
  interface Window {
    __OKO_API_BASE__?: string
    __OKO_DESKTOP_RUNTIME__?: {
      desktop: boolean
      mode: 'web' | 'embedded' | 'remote'
      deploymentMode: 'docker' | 'dev' | 'app'
      appClientMode: 'thin' | 'thick' | null
      apiBaseUrl: string
      remoteBaseUrl: string
      embeddedRunning: boolean
    }
    __TAURI_INTERNALS__?: unknown
  }
}
