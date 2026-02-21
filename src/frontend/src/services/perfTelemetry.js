/**
 * @param {Record<string, unknown>} detail
 * @returns {void}
 */
function emitMetric(detail) {
  if (typeof window === 'undefined') return
  window.dispatchEvent(
    new CustomEvent('oko:perf-metric', {
      detail,
    })
  )
}

/**
 * @param {string} name
 * @param {number} value
 * @param {Record<string, unknown>} [meta]
 * @returns {void}
 */
function logMetric(name, value, meta = {}) {
  const rounded = Number.isFinite(value) ? Number(value.toFixed(2)) : value
  emitMetric({ type: 'metric', name, value: rounded, ...meta })
}

/**
 * @returns {void}
 */
function attachLongTaskObserver() {
  if (typeof window === 'undefined' || typeof PerformanceObserver === 'undefined') return
  const supported = PerformanceObserver.supportedEntryTypes || []
  if (!supported.includes('longtask')) return

  const observer = new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      logMetric('LONG_TASK', entry.duration, {
        start: Number(entry.startTime.toFixed(1)),
      })
    }
  })

  observer.observe({ type: 'longtask', buffered: true })
}

/**
 * @typedef {Object} PerfTelemetryOptions
 * @property {boolean} enabled
 */

/**
 * @param {PerfTelemetryOptions} options
 * @returns {Promise<void>}
 */
export async function initDevPerfTelemetry(options) {
  if (!options.enabled || typeof window === 'undefined') return

  attachLongTaskObserver()

  try {
    const { onCLS, onFCP, onINP, onLCP, onTTFB } = await import('web-vitals')
    onCLS((metric) => logMetric('CLS', metric.value, { rating: metric.rating }))
    onINP((metric) => logMetric('INP', metric.value, { rating: metric.rating }))
    onLCP((metric) => logMetric('LCP', metric.value, { rating: metric.rating }))
    onFCP((metric) => logMetric('FCP', metric.value, { rating: metric.rating }))
    onTTFB((metric) => logMetric('TTFB', metric.value, { rating: metric.rating }))
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error)
    emitMetric({ type: 'error', source: 'web-vitals', message })
  }
}
