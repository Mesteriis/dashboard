import { createApp } from 'vue'
import { MotionPlugin } from '@vueuse/motion'
import App from './App.vue'
import { initDevPerfTelemetry } from './services/perfTelemetry.js'
import './styles.scss'

function resolveFxMode() {
  const prefersReduced = globalThis.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches
  if (prefersReduced) return 'off'

  const cores = Number(globalThis.navigator?.hardwareConcurrency || 8)
  const memory = Number(globalThis.navigator?.deviceMemory || 8)
  if (cores <= 4 || memory <= 4) return 'lite'
  return 'full'
}

function applyFxMode(mode) {
  const root = document.documentElement
  const previousMode = root.dataset.fxMode || ''
  root.dataset.fxMode = mode

  if (mode === 'off') {
    root.style.setProperty('--glow-enabled', '0')
  } else if (mode === 'lite') {
    root.style.setProperty('--glow-enabled', '0.58')
  } else {
    root.style.setProperty('--glow-enabled', '1')
  }

  if (previousMode && previousMode !== mode) {
    window.dispatchEvent(
      new CustomEvent('oko:fx-mode-change', {
        detail: { mode, previousMode },
      })
    )
  }
}

function initFxModeProfile() {
  const mq = globalThis.matchMedia?.('(prefers-reduced-motion: reduce)')
  const sync = () => applyFxMode(resolveFxMode())
  sync()

  if (mq?.addEventListener) {
    mq.addEventListener('change', sync)
  } else if (mq?.addListener) {
    mq.addListener(sync)
  }
}

initFxModeProfile()
initDevPerfTelemetry({ enabled: import.meta.env.DEV })
createApp(App).use(MotionPlugin).mount('#app')
