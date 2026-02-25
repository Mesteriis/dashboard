import type { DashboardHealthPayload, DashboardHealthState, HealthLevel } from "@/features/stores/dashboard/storeTypes";

export function createDashboardHealthSection(ctx: any) {
  function stopHealthPolling(): void {
    if (ctx.healthStreamReconnectTimer) {
      clearTimeout(ctx.healthStreamReconnectTimer);
      ctx.healthStreamReconnectTimer = 0;
    }
    if (ctx.healthStream) {
      ctx.healthStream.close();
      ctx.healthStream = null;
    }
  }

  function healthState(itemId: string): DashboardHealthState | null {
    return ctx.healthStates[itemId] || null;
  }

  function isHealthDegraded(
    state: DashboardHealthState | null | undefined,
  ): boolean {
    return Boolean(
      state?.ok &&
        state.latency_ms != null &&
        state.latency_ms >= ctx.DEGRADED_LATENCY_MS,
    );
  }

  function resolvedHealthLevel(
    state: DashboardHealthState | null | undefined,
  ): HealthLevel {
    if (!state) return "unknown";

    const level = String(state.level || "").toLowerCase();
    if (
      [
        "online",
        "recovering",
        "degraded",
        "down",
        "unknown",
        "indirect_failure",
      ].includes(level)
    ) {
      return level as HealthLevel;
    }

    if (isHealthDegraded(state)) return "degraded";
    return state.ok ? "online" : "down";
  }

  function healthClass(itemId: string): "ok" | "degraded" | "down" | "unknown" {
    const state = healthState(itemId);
    const level = resolvedHealthLevel(state);

    if (level === "online") return "ok";
    if (level === "recovering") return "degraded";
    if (level === "degraded") return "degraded";
    if (level === "down" || level === "indirect_failure") return "down";
    return "unknown";
  }

  function healthLabel(itemId: string): string {
    const state = healthState(itemId);
    if (!state) return "Проверка...";
    const level = resolvedHealthLevel(state);

    if (level === "online") {
      if (state.latency_ms != null) {
        return `Online • ${state.latency_ms} ms`;
      }
      return "Online";
    }

    if (level === "degraded") {
      if (state.latency_ms != null) {
        return `Degraded • ${state.latency_ms} ms`;
      }
      if (state.status_code != null) {
        return `Degraded • HTTP ${state.status_code}`;
      }
      if (state.error) {
        return `Degraded • ${state.error}`;
      }
      if (state.reason) {
        return `Degraded • ${String(state.reason).replaceAll("_", " ")}`;
      }
      return "Degraded";
    }

    if (level === "recovering") {
      const successRateValue =
        typeof state.success_rate === "number" && Number.isFinite(state.success_rate)
          ? Math.max(0, Math.min(1, state.success_rate))
          : null;
      const successPercent =
        successRateValue == null ? null : Math.round(successRateValue * 100);
      if (state.latency_ms != null && successPercent != null) {
        return `Recovering • ${successPercent}% • ${state.latency_ms} ms`;
      }
      if (successPercent != null) {
        return `Recovering • ${successPercent}%`;
      }
      return "Recovering";
    }

    if (level === "indirect_failure") {
      return "Indirect failure";
    }

    if (level === "down") {
      if (state.error) {
        return `Offline • ${state.error}`;
      }

      if (state.status_code != null) {
        return `Offline • HTTP ${state.status_code}`;
      }

      return "Offline";
    }

    return "Unknown";
  }

  function applyHealthPayload(
    payload: DashboardHealthPayload | null | undefined,
    ids: readonly string[] = [],
  ): void {
    const incomingById = new Map<string, DashboardHealthState>();
    for (const itemStatus of payload?.items || []) {
      const status =
        itemStatus && typeof itemStatus === "object"
          ? (itemStatus as DashboardHealthState)
          : null;
      if (!status) continue;
      const statusItemId = String(status?.item_id || "").trim();
      if (!statusItemId) continue;
      incomingById.set(statusItemId, status);
      ctx.healthStates[statusItemId] = status;
    }

    for (const id of ids) {
      const normalizedId = String(id || "").trim();
      if (!normalizedId || incomingById.has(normalizedId)) continue;
      if (!ctx.healthStates[normalizedId]) {
        ctx.healthStates[normalizedId] = {
          item_id: normalizedId,
          ok: false,
          status: "unknown",
          level: "unknown",
          checked_url: "",
          status_code: null,
          latency_ms: null,
          error: null,
        };
      }
    }
  }

  function applyHealthStatusChanged(payload: unknown): void {
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) return;

    const source = payload as Record<string, unknown>;
    const itemId = String(source.item_id || "").trim();
    if (!itemId) return;

    const rawStatus = String(source.current_status || "").toLowerCase();
    const status =
      rawStatus === "online" ||
      rawStatus === "degraded" ||
      rawStatus === "down" ||
      rawStatus === "unknown"
        ? rawStatus
        : "unknown";

    const latencyValue = source.avg_latency_ms == null ? null : Number(source.avg_latency_ms);
    const latencyMs =
      typeof latencyValue === "number" && Number.isFinite(latencyValue)
        ? Math.max(0, Math.round(latencyValue))
        : null;
    const successRateValue = source.success_rate == null ? null : Number(source.success_rate);
    const successRate =
      typeof successRateValue === "number" && Number.isFinite(successRateValue)
        ? Math.max(0, Math.min(1, successRateValue))
        : null;
    const consecutiveFailuresValue =
      source.consecutive_failures == null ? null : Number(source.consecutive_failures);
    const consecutiveFailures =
      typeof consecutiveFailuresValue === "number" && Number.isFinite(consecutiveFailuresValue)
        ? Math.max(0, Math.trunc(consecutiveFailuresValue))
        : null;

    const previous = ctx.healthStates[itemId];
    const previousSuccessRate =
      previous &&
      typeof previous.success_rate === "number" &&
      Number.isFinite(previous.success_rate)
        ? previous.success_rate
        : null;
    const recovering =
      status === "degraded" &&
      consecutiveFailures === 0 &&
      successRate != null &&
      (previous?.status === "down" ||
        (previousSuccessRate != null && successRate > previousSuccessRate + 0.001));

    ctx.healthStates[itemId] = {
      ...(ctx.healthStates[itemId] || {}),
      item_id: itemId,
      ok: status === "online" || status === "degraded",
      status,
      level: recovering ? "recovering" : status,
      latency_ms: latencyMs,
      success_rate: successRate,
      consecutive_failures: consecutiveFailures,
      error: status === "down" ? "check failed" : null,
      checked_url: String(ctx.healthStates[itemId]?.checked_url || ""),
      status_code: null,
    };
  }

  function onHealthStreamEvent(payload: unknown): void {
    if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
      return;
    }
    const envelope = payload as Record<string, unknown>;
    const eventType = String(envelope.type || "").trim();
    if (eventType === "health.state.snapshot") {
      const snapshotPayload =
        envelope.payload &&
        typeof envelope.payload === "object" &&
        !Array.isArray(envelope.payload)
          ? (envelope.payload as DashboardHealthPayload)
          : null;
      applyHealthPayload(snapshotPayload, ctx.visibleTreeItemIds.value);
      return;
    }
    if (!["health.status.changed", "health.status.updated"].includes(eventType)) {
      return;
    }
    applyHealthStatusChanged(envelope.payload);
  }

  function scheduleHealthStreamReconnect(): void {
    if (ctx.healthStreamReconnectTimer || !ctx.isDocumentVisible.value) {
      return;
    }
    ctx.healthStreamReconnectTimer = window.setTimeout(() => {
      ctx.healthStreamReconnectTimer = 0;
      void startHealthPolling();
    }, ctx.EVENT_STREAM_RECONNECT_MS);
  }

  async function refreshHealth(itemIds: string[] | null = null): Promise<void> {
    if (!Array.isArray(itemIds) && !ctx.isDocumentVisible.value) return;

    const sourceIds: string[] =
      Array.isArray(itemIds) && itemIds.length
        ? itemIds
        : (ctx.visibleTreeItemIds.value as string[]);
    const ids = Array.from(
      new Set(
        sourceIds
          .map((value: string) => String(value || "").trim())
          .filter(Boolean),
      ),
    );
    if (!ids.length) return;
    applyHealthPayload({ items: [] }, ids);
  }

  async function startHealthPolling(): Promise<void> {
    stopHealthPolling();
    await refreshHealth();
    if (!ctx.isDocumentVisible.value) {
      return;
    }
    ctx.healthStream = ctx.connectOkoSseStream({
      path: ctx.EVENTS_STREAM_PATH,
      onEvent: (event: any) => {
        onHealthStreamEvent(event.data);
      },
      onError: () => {
        scheduleHealthStreamReconnect();
      },
    });
  }

  return {
    applyHealthPayload,
    healthClass,
    healthLabel,
    healthState,
    refreshHealth,
    startHealthPolling,
    stopHealthPolling,
  };
}
