export {}

declare global {
  interface ImportMetaEnv {
    readonly BASE_URL?: string
    readonly DEV?: boolean
  }

  interface ImportMeta {
    readonly env: ImportMetaEnv
  }

  interface Window {
    __OKO_API_BASE__?: string
    __OKO_ACTOR__?: string
    __OKO_CAPABILITIES__?: string[]
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
    particlesJS?: (containerId: string, config: unknown) => Promise<unknown>
  }

  interface Navigator {
    deviceMemory?: number
  }
}
