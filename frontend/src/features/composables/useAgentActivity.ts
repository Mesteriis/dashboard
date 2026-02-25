import {
  computed,
  getCurrentScope,
  onScopeDispose,
  reactive,
  readonly,
  ref,
  toValue,
  type ComputedRef,
  type Ref,
} from "vue";

export type AgentState = "idle" | "active" | "alert" | "error";

export interface AgentEvent {
  ts: string;
  trace_id: string;
  from: string;
  to: string;
  kind: "info" | "warning" | "action" | "memory";
  status: "ok" | "error" | "pending";
  importance: number;
  summary?: string;
}

export interface AgentFxSnapshot {
  activity: number;
  state: AgentState;
  lastAt: number;
}

interface AgentFxEntry extends AgentFxSnapshot {
  stateUntil: number;
}

const DECAY_PER_SECOND = 0.22;
const EVENT_ACTIVITY_MIN = 0;
const EVENT_ACTIVITY_MAX = 1.6;
const TICK_MIN_MS = 44;
const CLEANUP_IDLE_MS = 20000;
const STATE_DURATIONS = {
  active: 1500,
  alert: 2500,
  error: 3500,
} as const;

const activityByAgent = reactive(new Map<string, AgentFxEntry>());
const isDocumentHidden = ref(
  typeof document === "undefined" ? false : Boolean(document.hidden),
);

let rafId = 0;
let lastTickMs = 0;
let consumerCount = 0;
let listenersBound = false;

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function normalizeAgentId(value: unknown): string {
  return String(value || "")
    .trim()
    .toUpperCase();
}

function nowMs(): number {
  if (typeof performance !== "undefined" && typeof performance.now === "function") {
    return performance.now();
  }
  return Date.now();
}

function createDefaultEntry(): AgentFxEntry {
  return {
    activity: 0,
    state: "idle",
    lastAt: 0,
    stateUntil: 0,
  };
}

function getOrCreateEntry(agentId: string): AgentFxEntry {
  const normalized = normalizeAgentId(agentId);
  const existing = activityByAgent.get(normalized);
  if (existing) return existing;
  const next = createDefaultEntry();
  activityByAgent.set(normalized, next);
  return next;
}

function hasEnergeticEntries(referenceNowMs = nowMs()): boolean {
  for (const entry of activityByAgent.values()) {
    if (entry.activity > 0.001) return true;
    if (entry.state !== "idle") return true;
    if (referenceNowMs - entry.lastAt <= CLEANUP_IDLE_MS) return true;
  }
  return false;
}

function resolveStateForEvent(event: AgentEvent): { state: AgentState; durationMs: number } {
  if (event.status === "error") {
    return { state: "error", durationMs: STATE_DURATIONS.error };
  }
  if (event.kind === "warning") {
    return { state: "alert", durationMs: STATE_DURATIONS.alert };
  }
  return { state: "active", durationMs: STATE_DURATIONS.active };
}

function stopTicker(): void {
  if (!rafId || typeof window === "undefined") {
    rafId = 0;
    return;
  }
  window.cancelAnimationFrame(rafId);
  rafId = 0;
  lastTickMs = 0;
}

function tick(timestamp: number): void {
  if (typeof window === "undefined") return;
  rafId = window.requestAnimationFrame(tick);

  if (isDocumentHidden.value) {
    lastTickMs = timestamp;
    return;
  }

  if (!lastTickMs) {
    lastTickMs = timestamp;
    return;
  }

  const elapsedMs = timestamp - lastTickMs;
  if (elapsedMs < TICK_MIN_MS) {
    return;
  }
  lastTickMs = timestamp;

  const dtSeconds = Math.max(0, Math.min(0.1, elapsedMs / 1000));
  const decayAmount = dtSeconds * DECAY_PER_SECOND;
  const now = timestamp;

  for (const [agentId, entry] of activityByAgent.entries()) {
    entry.activity = clamp(entry.activity - decayAmount, EVENT_ACTIVITY_MIN, EVENT_ACTIVITY_MAX);

    if (now >= entry.stateUntil) {
      entry.state = entry.activity > 0.05 ? "active" : "idle";
      entry.stateUntil = 0;
    }

    if (
      entry.activity <= 0.001 &&
      entry.state === "idle" &&
      now - entry.lastAt > CLEANUP_IDLE_MS
    ) {
      activityByAgent.delete(agentId);
    }
  }

  if (!hasEnergeticEntries(now)) {
    stopTicker();
  }
}

function startTicker(): void {
  if (typeof window === "undefined") return;
  if (rafId) return;
  lastTickMs = 0;
  rafId = window.requestAnimationFrame(tick);
}

function handleVisibilityChange(): void {
  if (typeof document === "undefined") return;
  isDocumentHidden.value = Boolean(document.hidden);
  if (isDocumentHidden.value) return;
  if (hasEnergeticEntries()) {
    startTicker();
  }
}

function bindListeners(): void {
  if (listenersBound || typeof document === "undefined") return;
  listenersBound = true;
  document.addEventListener("visibilitychange", handleVisibilityChange);
}

function unbindListeners(): void {
  if (!listenersBound || typeof document === "undefined") return;
  listenersBound = false;
  document.removeEventListener("visibilitychange", handleVisibilityChange);
}

function ingestEvent(event: AgentEvent): void {
  if (!event) return;

  const participants = [normalizeAgentId(event.from), normalizeAgentId(event.to)].filter(Boolean);
  if (!participants.length) return;

  const uniqueParticipants = [...new Set(participants)];
  const importance = Number.isFinite(Number(event.importance)) ? Number(event.importance) : 0;
  const delta = clamp(0.15 + importance * 0.35, 0, 0.6);
  const stateData = resolveStateForEvent(event);
  const eventNow = nowMs();

  for (const agentId of uniqueParticipants) {
    const entry = getOrCreateEntry(agentId);
    entry.activity = clamp(entry.activity + delta, EVENT_ACTIVITY_MIN, EVENT_ACTIVITY_MAX);
    entry.lastAt = eventNow;
    entry.state = stateData.state;
    entry.stateUntil = eventNow + stateData.durationMs;
  }

  startTicker();
}

function getSnapshot(agentId: string): AgentFxSnapshot {
  const normalized = normalizeAgentId(agentId);
  if (!normalized) {
    return {
      activity: 0,
      state: "idle",
      lastAt: 0,
    };
  }

  const entry = getOrCreateEntry(normalized);
  return {
    activity: entry.activity,
    state: entry.state,
    lastAt: entry.lastAt,
  };
}

function getFx(agentIdInput: string | Ref<string>): ComputedRef<AgentFxSnapshot> {
  return computed<AgentFxSnapshot>(() => {
    const normalized = normalizeAgentId(toValue(agentIdInput));
    if (!normalized) {
      return {
        activity: 0,
        state: "idle",
        lastAt: 0,
      };
    }

    const entry = getOrCreateEntry(normalized);
    return {
      activity: entry.activity,
      state: entry.state,
      lastAt: entry.lastAt,
    };
  });
}

function resetActivity(agentId?: string): void {
  if (!agentId) {
    activityByAgent.clear();
    stopTicker();
    return;
  }
  const normalized = normalizeAgentId(agentId);
  if (!normalized) return;
  activityByAgent.delete(normalized);
  if (!hasEnergeticEntries()) {
    stopTicker();
  }
}

function retainScope(): void {
  consumerCount += 1;
  bindListeners();
  if (hasEnergeticEntries() && !isDocumentHidden.value) {
    startTicker();
  }
}

function releaseScope(): void {
  consumerCount = Math.max(0, consumerCount - 1);
  if (consumerCount > 0) return;
  unbindListeners();
  if (!hasEnergeticEntries()) {
    stopTicker();
  }
}

export function useAgentActivity(): {
  activityMap: ReadonlyMap<string, AgentFxEntry>;
  ingestEvent: (event: AgentEvent) => void;
  getFx: (agentId: string | Ref<string>) => ComputedRef<AgentFxSnapshot>;
  getSnapshot: (agentId: string) => AgentFxSnapshot;
  resetActivity: (agentId?: string) => void;
} {
  retainScope();

  if (getCurrentScope()) {
    onScopeDispose(() => {
      releaseScope();
    });
  }

  return {
    activityMap: readonly(activityByAgent),
    ingestEvent,
    getFx,
    getSnapshot,
    resetActivity,
  };
}
