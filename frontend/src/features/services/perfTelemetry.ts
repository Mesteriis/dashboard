import { EVENT_PERF_METRIC, emitOkoEvent } from "@/features/services/events";

interface PerfTelemetryOptions {
  enabled: boolean;
}

function emitMetric(detail: Record<string, unknown>): void {
  emitOkoEvent(EVENT_PERF_METRIC, detail);
}

function logMetric(
  name: string,
  value: number,
  meta: Record<string, unknown> = {},
): void {
  const rounded = Number.isFinite(value) ? Number(value.toFixed(2)) : value;
  emitMetric({ type: "metric", name, value: rounded, ...meta });
}

function attachLongTaskObserver(): void {
  if (
    typeof window === "undefined" ||
    typeof PerformanceObserver === "undefined"
  )
    return;
  const supported = PerformanceObserver.supportedEntryTypes || [];
  if (!supported.includes("longtask")) return;

  const observer = new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      logMetric("LONG_TASK", entry.duration, {
        start: Number(entry.startTime.toFixed(1)),
      });
    }
  });

  observer.observe({ type: "longtask", buffered: true });
}

export async function initDevPerfTelemetry(
  options: PerfTelemetryOptions,
): Promise<void> {
  if (!options.enabled || typeof window === "undefined") return;

  attachLongTaskObserver();

  try {
    const { onCLS, onFCP, onINP, onLCP, onTTFB } = await import("web-vitals");
    onCLS((metric: { value: number; rating: string }) =>
      logMetric("CLS", metric.value, { rating: metric.rating }),
    );
    onINP((metric: { value: number; rating: string }) =>
      logMetric("INP", metric.value, { rating: metric.rating }),
    );
    onLCP((metric: { value: number; rating: string }) =>
      logMetric("LCP", metric.value, { rating: metric.rating }),
    );
    onFCP((metric: { value: number; rating: string }) =>
      logMetric("FCP", metric.value, { rating: metric.rating }),
    );
    onTTFB((metric: { value: number; rating: string }) =>
      logMetric("TTFB", metric.value, { rating: metric.rating }),
    );
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    emitMetric({ type: "error", source: "web-vitals", message });
  }
}
