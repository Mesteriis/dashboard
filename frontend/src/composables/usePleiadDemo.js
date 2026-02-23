import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";

const TAU = Math.PI * 2;
const EVENT_QUEUE_LIMIT = 20;
const ACTIVE_LINK_LIMIT = 64;
const ACTIVE_LINK_MIN_TTL_MS = 1800;
const ACTIVE_LINK_MAX_TTL_MS = 3400;
const BASE_EVENT_MIN_INTERVAL_MS = 1200;
const BASE_EVENT_MAX_INTERVAL_MS = 2600;
const CHAIN_EVENT_MIN_INTERVAL_MS = 260;
const CHAIN_EVENT_MAX_INTERVAL_MS = 720;
const CHAIN_PROBABILITY = 0.44;
const CHAIN_MAX_STEPS = 3;
const HIGHLIGHT_LINK_TTL_MS = 3200;
const PRIMARY_SWITCH_TRANSITION_MS = 1120;
const DISABLED_AGENT_MIN_COUNT = 2;
const DISABLED_AGENT_MAX_COUNT = 4;
const DISABLED_AGENT_ROTATION_INTERVAL_MS = 3 * 60 * 1000;
const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";
const PLEIAD_KINDS = Object.freeze([
  "all",
  "action",
  "warning",
  "memory",
  "info",
]);
const CENTER_AGENT_ID = "HESTIA";

const AGENTS = Object.freeze([
  {
    id: "HESTIA",
    name: "HESTIA",
    role: "orchestrator core",
    color: "#95b5cc",
    avatarSrc: "/static/img/pleiads/HESTIA.webp",
    sizeScale: 1.28,
    orbit: false,
    glyph: "HE",
  },
  {
    id: "VELES",
    name: "VELES",
    role: "infra",
    color: "#6fb4d4",
    avatarSrc: "/static/img/pleiads/VELES.webp",
    sizeScale: 0.92,
    orbit: true,
    glyph: "VE",
  },
  {
    id: "DOMOVOY",
    name: "DOMOVOY",
    role: "iot",
    color: "#72bea8",
    avatarSrc: "/static/img/pleiads/DOMOVOY.webp",
    sizeScale: 1.04,
    orbit: true,
    glyph: "DO",
  },
  {
    id: "SOKOL",
    name: "SOKOL",
    role: "telemetry",
    color: "#82abcf",
    avatarSrc: "/static/img/pleiads/SOKOL.webp",
    sizeScale: 0.98,
    orbit: true,
    glyph: "SO",
  },
  {
    id: "MORANA",
    name: "MORANA",
    role: "security",
    color: "#b98698",
    avatarSrc: "/static/img/pleiads/MORANA.webp",
    sizeScale: 1.08,
    orbit: true,
    glyph: "MO",
  },
  {
    id: "PERUN",
    name: "PERUN",
    role: "executor",
    color: "#c8a879",
    avatarSrc: "/static/img/pleiads/PERUN.webp",
    sizeScale: 1.12,
    orbit: true,
    glyph: "PE",
  },
  {
    id: "STRIX",
    name: "STRIX",
    role: "analysis",
    color: "#90a8c9",
    avatarSrc: "/static/img/pleiads/STRIX.webp",
    sizeScale: 0.94,
    orbit: true,
    glyph: "ST",
  },
  {
    id: "RADOGOST",
    name: "RADOGOST",
    role: "comms",
    color: "#7ec6bb",
    avatarSrc: "/static/img/pleiads/RADOGOST.webp",
    sizeScale: 1.06,
    orbit: true,
    glyph: "RA",
  },
  {
    id: "LADA",
    name: "LADA",
    role: "social",
    color: "#bda0c0",
    avatarSrc: "/static/img/pleiads/LADA.webp",
    sizeScale: 1.02,
    orbit: true,
    glyph: "LA",
  },
  {
    id: "YARILO",
    name: "YARILO",
    role: "creative",
    color: "#c9ba82",
    avatarSrc: "/static/img/pleiads/YARILO.webp",
    sizeScale: 1.1,
    orbit: true,
    glyph: "YA",
  },
  {
    id: "MAKOSH",
    name: "MAKOSH",
    role: "memory/rag",
    color: "#9f9fc8",
    avatarSrc: "/static/img/pleiads/MAKOSH.webp",
    sizeScale: 0.96,
    orbit: true,
    glyph: "MA",
  },
  {
    id: "SVAROG",
    name: "SVAROG",
    role: "architecture",
    color: "#89b0bc",
    avatarSrc: "/static/img/pleiads/SVAROG.webp",
    sizeScale: 1,
    orbit: true,
    glyph: "SV",
  },
]);

const ORBIT_AGENT_IDS = Object.freeze(
  AGENTS.filter((agent) => agent.orbit).map((agent) => agent.id),
);
const AGENT_IDS = Object.freeze(AGENTS.map((agent) => agent.id));
const AGENT_BY_ID = new Map(AGENTS.map((agent) => [agent.id, agent]));

const KIND_WEIGHT_TABLE = [
  { kind: "info", weight: 32 },
  { kind: "action", weight: 30 },
  { kind: "warning", weight: 20 },
  { kind: "memory", weight: 18 },
];

const KIND_TOPICS = {
  info: [
    "mesh health pulse",
    "telemetry window updated",
    "channel snapshot",
    "heartbeat reconciliation",
    "routing map refresh",
  ],
  action: [
    "deploy sequence",
    "policy rollout",
    "runtime patch",
    "queue rebalance",
    "service handoff",
  ],
  warning: [
    "latency spike",
    "auth anomaly",
    "sensor drift",
    "packet loss burst",
    "quota threshold",
  ],
  memory: [
    "context compaction",
    "vector recall",
    "trace merge",
    "artifact retention",
    "knowledge graft",
  ],
};

const KIND_SUMMARY_TEMPLATES = {
  info: [
    "{from} synced {topic} with {to}",
    "{from} published {topic} to {to}",
    "{from} reported {topic}; {to} acknowledged",
  ],
  action: [
    "{from} requested {topic} from {to}",
    "{from} delegated {topic} to {to}",
    "{to} executing {topic} initiated by {from}",
  ],
  warning: [
    "{from} flagged {topic} for {to}",
    "{to} escalated {topic} to {from}",
    "{from} opened caution on {topic} for {to}",
  ],
  memory: [
    "{from} wrote {topic} for {to}",
    "{from} linked {topic} into {to} memory",
    "{to} requested {topic} replay from {from}",
  ],
};

const KIND_STATUS_WEIGHT_TABLE = {
  info: [
    { status: "ok", weight: 76 },
    { status: "pending", weight: 20 },
    { status: "error", weight: 4 },
  ],
  action: [
    { status: "ok", weight: 58 },
    { status: "pending", weight: 30 },
    { status: "error", weight: 12 },
  ],
  warning: [
    { status: "ok", weight: 18 },
    { status: "pending", weight: 30 },
    { status: "error", weight: 52 },
  ],
  memory: [
    { status: "ok", weight: 66 },
    { status: "pending", weight: 24 },
    { status: "error", weight: 10 },
  ],
};

function randomFloat(min, max) {
  return min + Math.random() * (max - min);
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function randomInt(min, max) {
  return Math.floor(randomFloat(min, max + 1));
}

function pickRandom(list) {
  if (!Array.isArray(list) || !list.length) return undefined;
  return list[randomInt(0, list.length - 1)];
}

function pickRandomSubset(list, count) {
  if (!Array.isArray(list) || !list.length) return [];
  const pool = [...list];
  for (let index = pool.length - 1; index > 0; index -= 1) {
    const swapIndex = randomInt(0, index);
    [pool[index], pool[swapIndex]] = [pool[swapIndex], pool[index]];
  }
  const normalizedCount = clamp(Number(count || 0), 0, pool.length);
  return pool.slice(0, normalizedCount);
}

function pickWeighted(entries) {
  const total = entries.reduce((sum, entry) => sum + Number(entry.weight || 0), 0);
  if (total <= 0) return entries[0];
  let cursor = randomFloat(0, total);
  for (const entry of entries) {
    cursor -= Number(entry.weight || 0);
    if (cursor <= 0) return entry;
  }
  return entries[entries.length - 1];
}

function normalizeFxMode(mode) {
  if (mode === "off" || mode === "lite" || mode === "full") return mode;
  return "full";
}

function resolveFxModeFromDom() {
  if (typeof document === "undefined") return "full";
  return normalizeFxMode(document.documentElement?.dataset?.fxMode || "full");
}

function buildSummary(kind, from, to, topic) {
  const templates = KIND_SUMMARY_TEMPLATES[kind] || KIND_SUMMARY_TEMPLATES.info;
  const template = pickRandom(templates) || "{from} -> {to}: {topic}";
  return template
    .replaceAll("{from}", from)
    .replaceAll("{to}", to)
    .replaceAll("{topic}", topic);
}

function resolveEventKind() {
  const picked = pickWeighted(KIND_WEIGHT_TABLE);
  return picked?.kind || "info";
}

function resolveEventStatus(kind) {
  const table = KIND_STATUS_WEIGHT_TABLE[kind] || KIND_STATUS_WEIGHT_TABLE.info;
  const picked = pickWeighted(table);
  return picked?.status || "ok";
}

function resolveImportance(kind) {
  if (kind === "warning") return Number(randomFloat(0.55, 1).toFixed(2));
  if (kind === "action") return Number(randomFloat(0.46, 0.92).toFixed(2));
  if (kind === "memory") return Number(randomFloat(0.34, 0.8).toFixed(2));
  return Number(randomFloat(0.22, 0.74).toFixed(2));
}

function resolveLatencyMs(kind) {
  if (kind === "warning") return randomInt(120, 1900);
  if (kind === "action") return randomInt(80, 1600);
  if (kind === "memory") return randomInt(60, 980);
  return randomInt(20, 720);
}

function resolveFxProfile(mode, prefersReducedMotion) {
  const effectiveMode = prefersReducedMotion ? "off" : mode;
  if (effectiveMode === "off") {
    return {
      mode: effectiveMode,
      rotationRadPerMs: 0,
      eventCadenceMultiplier: 2.15,
      glowAlpha: 0,
      linkWidthScale: 0.82,
      starDensity: 0.52,
      twinkleAmplitude: 0,
      nebulaAlpha: 0.08,
    };
  }

  if (effectiveMode === "lite") {
    return {
      mode: effectiveMode,
      rotationRadPerMs: 0.000010,
      eventCadenceMultiplier: 1.45,
      glowAlpha: 0.42,
      linkWidthScale: 0.92,
      starDensity: 0.72,
      twinkleAmplitude: 0.14,
      nebulaAlpha: 0.12,
    };
  }

  return {
    mode: "full",
    rotationRadPerMs: 0.000017,
    eventCadenceMultiplier: 1,
    glowAlpha: 0.86,
    linkWidthScale: 1,
    starDensity: 1,
    twinkleAmplitude: 0.22,
    nebulaAlpha: 0.15,
  };
}

function resolveOrbitAgentIds(centerAgentId) {
  const normalizedCenter = AGENT_BY_ID.has(centerAgentId)
    ? String(centerAgentId)
    : CENTER_AGENT_ID;
  return AGENT_IDS.filter((agentId) => agentId !== normalizedCenter);
}

function resolveEnabledAgentContext(centerAgentId, enabledAgentIds) {
  const preferredCenter = AGENT_BY_ID.has(centerAgentId)
    ? String(centerAgentId)
    : CENTER_AGENT_ID;
  const normalizedEnabled = Array.isArray(enabledAgentIds)
    ? enabledAgentIds
      .map((agentId) => String(agentId || ""))
      .filter((agentId, index, list) => AGENT_BY_ID.has(agentId) && list.indexOf(agentId) === index)
    : [];
  const enabledPool = normalizedEnabled.length ? normalizedEnabled : [...AGENT_IDS];
  const normalizedCenter = enabledPool.includes(preferredCenter)
    ? preferredCenter
    : enabledPool[0] || preferredCenter;
  return { enabledPool, normalizedCenter };
}

function resolveAgentEndpoints(centerAgentId, orbitAgentIds, enabledAgentIds) {
  const { enabledPool, normalizedCenter } = resolveEnabledAgentContext(
    centerAgentId,
    enabledAgentIds,
  );
  if (enabledPool.length < 2) return null;

  const normalizedOrbit = Array.isArray(orbitAgentIds) && orbitAgentIds.length
    ? orbitAgentIds.filter(
      (agentId) =>
        enabledPool.includes(String(agentId || "")) && agentId !== normalizedCenter,
    )
    : enabledPool.filter((agentId) => agentId !== normalizedCenter);
  const fromPool =
    Math.random() < 0.3
      ? [normalizedCenter, ...normalizedOrbit]
      : [...enabledPool];
  const from = pickRandom(fromPool) || normalizedCenter;

  const toPool = enabledPool.filter((agentId) => agentId !== from);
  if (!toPool.length) return null;
  let to = pickRandom(toPool) || toPool[0];
  if (from !== normalizedCenter && toPool.includes(normalizedCenter) && Math.random() < 0.26) {
    to = normalizedCenter;
  }
  if (to === from) {
    to = toPool[0];
  }

  return { from, to };
}

function resolveChainEndpoints(from, centerAgentId, enabledAgentIds) {
  const { enabledPool, normalizedCenter } = resolveEnabledAgentContext(
    centerAgentId,
    enabledAgentIds,
  );
  if (enabledPool.length < 2) return null;

  const sourceCandidate = String(from || normalizedCenter);
  const source = enabledPool.includes(sourceCandidate) ? sourceCandidate : normalizedCenter;
  const toPool = enabledPool.filter((agentId) => agentId !== source);
  if (!toPool.length) return null;

  let to = pickRandom(toPool) || toPool[0];
  if (source !== normalizedCenter && toPool.includes(normalizedCenter) && Math.random() < 0.32) {
    to = normalizedCenter;
  }
  if (to === source) {
    to = toPool[0];
  }
  return { from: source, to };
}

export function usePleiadDemo(options = {}) {
  const autoStart = options.autoStart !== false;
  const screensaverVisible = ref(Boolean(options.screensaverVisible));
  const events = ref([]);
  const activeLinks = ref([]);
  const frame = ref(0);
  const rotationRad = ref(Math.random() * TAU);
  const isPaused = ref(false);
  const isRunning = ref(false);
  const filterKind = ref("all");
  const pinnedAgentId = ref("");
  const primaryAgentId = ref(CENTER_AGENT_ID);
  const orbitAgentIds = computed(() => resolveOrbitAgentIds(primaryAgentId.value));
  const disabledAgentIds = ref([]);
  const disabledAgentIdSet = computed(
    () => new Set(disabledAgentIds.value),
  );
  const enabledAgentIds = computed(() =>
    AGENT_IDS.filter((agentId) => !disabledAgentIdSet.value.has(agentId)),
  );
  const enabledAgentIdSet = computed(() => {
    const disabled = disabledAgentIdSet.value;
    return new Set(AGENT_IDS.filter((agentId) => !disabled.has(agentId)));
  });
  const primaryTransition = ref(null);
  const hoveredAgentId = ref("");
  const highlightedTraceId = ref("");
  const highlightUntilMs = ref(0);
  const isDocumentVisible = ref(
    typeof document === "undefined"
      ? true
      : document.visibilityState !== "hidden",
  );
  const fxMode = ref(resolveFxModeFromDom());
  const prefersReducedMotion = ref(
    Boolean(globalThis.matchMedia?.(REDUCED_MOTION_QUERY)?.matches),
  );
  const fxProfile = computed(() =>
    resolveFxProfile(fxMode.value, prefersReducedMotion.value),
  );
  const highlightedAgentIds = computed(() => {
    const ids = new Set();
    if (hoveredAgentId.value) ids.add(hoveredAgentId.value);
    if (pinnedAgentId.value) ids.add(pinnedAgentId.value);

    if (highlightedTraceId.value) {
      const highlightedEvent = events.value.find(
        (event) => event.trace_id === highlightedTraceId.value,
      );
      if (highlightedEvent) {
        ids.add(highlightedEvent.from);
        ids.add(highlightedEvent.to);
      }
    }

    return [...ids];
  });

  let rafId = 0;
  let eventTimerId = 0;
  let disabledRotationTimerId = 0;
  let lastFrameTs = 0;
  let mediaQueryList = null;
  let traceSequence = 0;
  let pendingChainEvents = [];

  function nextTraceId() {
    traceSequence += 1;
    return `pld-${Date.now().toString(36)}-${traceSequence.toString(36)}`;
  }

  function clearEventTimer() {
    if (!eventTimerId) return;
    window.clearTimeout(eventTimerId);
    eventTimerId = 0;
  }

  function clearDisabledRotationTimer() {
    if (!disabledRotationTimerId) return;
    window.clearTimeout(disabledRotationTimerId);
    disabledRotationTimerId = 0;
  }

  function normalizeAgentId(agentId) {
    const normalized = String(agentId || "")
      .trim()
      .toUpperCase();
    return AGENT_BY_ID.has(normalized) ? normalized : "";
  }

  function isEventAllowed(eventLike, disabledSet = disabledAgentIdSet.value) {
    if (!eventLike) return false;
    const from = String(eventLike.from || "");
    const to = String(eventLike.to || "");
    if (!from || !to || from === to) return false;
    if (!AGENT_BY_ID.has(from) || !AGENT_BY_ID.has(to)) return false;
    return !disabledSet.has(from) && !disabledSet.has(to);
  }

  function pruneCommunicationForDisabled(disabledSet = disabledAgentIdSet.value) {
    events.value = events.value.filter((event) => isEventAllowed(event, disabledSet));
    activeLinks.value = activeLinks.value.filter((link) => isEventAllowed(link, disabledSet));
    pendingChainEvents = pendingChainEvents.filter((record) =>
      isEventAllowed(record?.event, disabledSet),
    );
    if (
      highlightedTraceId.value &&
      !events.value.some((event) => event.trace_id === highlightedTraceId.value)
    ) {
      highlightedTraceId.value = "";
      highlightUntilMs.value = 0;
    }
  }

  function reseedDisabledAgents() {
    const available = AGENT_IDS.filter((agentId) => agentId !== primaryAgentId.value);
    if (!available.length) {
      disabledAgentIds.value = [];
      return;
    }

    const minCount = Math.min(DISABLED_AGENT_MIN_COUNT, available.length);
    const maxCount = Math.min(DISABLED_AGENT_MAX_COUNT, available.length);
    const nextCount = randomInt(minCount, maxCount);
    const nextDisabledIds = pickRandomSubset(available, nextCount);
    disabledAgentIds.value = nextDisabledIds;
    pruneCommunicationForDisabled(new Set(nextDisabledIds));
  }

  function scheduleDisabledAgentRotation() {
    clearDisabledRotationTimer();
    if (!isRunning.value || !isDocumentVisible.value) return;

    disabledRotationTimerId = window.setTimeout(() => {
      disabledRotationTimerId = 0;
      reseedDisabledAgents();
      scheduleDisabledAgentRotation();
    }, DISABLED_AGENT_ROTATION_INTERVAL_MS);
  }

  function isAgentEnabled(agentId) {
    const normalized = normalizeAgentId(agentId);
    if (!normalized) return false;
    return !disabledAgentIdSet.value.has(normalized);
  }

  function matchesEventFilters(eventLike) {
    if (!eventLike) return false;
    if (!isEventAllowed(eventLike)) return false;
    if (filterKind.value !== "all" && eventLike.kind !== filterKind.value) {
      return false;
    }
    if (
      pinnedAgentId.value &&
      eventLike.from !== pinnedAgentId.value &&
      eventLike.to !== pinnedAgentId.value
    ) {
      return false;
    }
    return true;
  }

  const filteredEvents = computed(() =>
    events.value.filter((event) => matchesEventFilters(event)),
  );

  const filteredActiveLinks = computed(() =>
    activeLinks.value.filter((link) => matchesEventFilters(link)),
  );

  function pruneActiveLinks(nowMs) {
    const nextLinks = activeLinks.value.filter((link) => link.expiresAtMs > nowMs);
    if (nextLinks.length === activeLinks.value.length) return;
    activeLinks.value = nextLinks;
  }

  function scheduleNextEvent() {
    clearEventTimer();
    if (!isRunning.value || isPaused.value || !isDocumentVisible.value) {
      return;
    }

    const hasPendingChain = pendingChainEvents.length > 0;
    let delayMs = 0;

    if (hasPendingChain) {
      const chainDelay = Number(pendingChainEvents[0]?.delayMs || 0);
      if (chainDelay > 0) {
        delayMs = Math.max(
          120,
          Math.round(chainDelay * fxProfile.value.eventCadenceMultiplier),
        );
      } else {
        const minDelay = Math.round(
          CHAIN_EVENT_MIN_INTERVAL_MS * fxProfile.value.eventCadenceMultiplier,
        );
        const maxDelay = Math.round(
          CHAIN_EVENT_MAX_INTERVAL_MS * fxProfile.value.eventCadenceMultiplier,
        );
        delayMs = randomInt(minDelay, maxDelay);
      }
    } else {
      const minDelay = Math.round(
        BASE_EVENT_MIN_INTERVAL_MS * fxProfile.value.eventCadenceMultiplier,
      );
      const maxDelay = Math.round(
        BASE_EVENT_MAX_INTERVAL_MS * fxProfile.value.eventCadenceMultiplier,
      );
      delayMs = randomInt(minDelay, maxDelay);
    }

    eventTimerId = window.setTimeout(() => {
      eventTimerId = 0;
      if (!isRunning.value || isPaused.value || !isDocumentVisible.value) {
        return;
      }
      emitNextEvent();
      scheduleNextEvent();
    }, delayMs);
  }

  function appendEvent(event, nowMs = performance.now()) {
    if (!isEventAllowed(event)) return false;
    events.value = [event, ...events.value].slice(0, EVENT_QUEUE_LIMIT);
    const ttlMs = randomInt(ACTIVE_LINK_MIN_TTL_MS, ACTIVE_LINK_MAX_TTL_MS);
    const link = {
      id: `link-${event.trace_id}-${Math.round(nowMs)}`,
      trace_id: event.trace_id,
      from: event.from,
      to: event.to,
      kind: event.kind,
      status: event.status,
      importance: event.importance,
      createdAtMs: nowMs,
      expiresAtMs: nowMs + ttlMs,
      manual: false,
    };
    activeLinks.value = [link, ...activeLinks.value].slice(0, ACTIVE_LINK_LIMIT);
    return true;
  }

  function appendPrimarySwitchEvent(previousAgentId, nextAgentId, reason = "api") {
    const nowMs = performance.now();
    const durationMs = Math.round(
      clamp(
        Number(primaryTransition.value?.durationMs || PRIMARY_SWITCH_TRANSITION_MS),
        280,
        2600,
      ),
    );
    const traceId = nextTraceId();
    const reasonText = String(reason || "api");
    const event = {
      ts: new Date().toISOString(),
      trace_id: traceId,
      from: previousAgentId,
      to: nextAgentId,
      kind: "action",
      topic: "primary handoff",
      summary: `${previousAgentId} handed primary role to ${nextAgentId}`,
      status: "ok",
      importance: 0.97,
      latency_ms: randomInt(24, 140),
      system: true,
      handoff_reason: reasonText,
    };
    events.value = [event, ...events.value].slice(0, EVENT_QUEUE_LIMIT);

    const ttlMs = Math.max(durationMs + randomInt(420, 980), 1400);
    const link = {
      id: `handoff-${traceId}-${Math.round(nowMs)}`,
      trace_id: traceId,
      from: previousAgentId,
      to: nextAgentId,
      kind: "action",
      status: "ok",
      importance: 1,
      createdAtMs: nowMs,
      expiresAtMs: nowMs + ttlMs,
      manual: true,
    };
    activeLinks.value = [link, ...activeLinks.value].slice(0, ACTIVE_LINK_LIMIT);
  }

  function createEvent({
    from,
    to,
    kind,
    topic,
    chainId = "",
    chainStep = 0,
  }) {
    const resolvedKind = kind || resolveEventKind();
    const resolvedTopic =
      topic || pickRandom(KIND_TOPICS[resolvedKind] || KIND_TOPICS.info) || "sync cycle";
    const summary = buildSummary(resolvedKind, from, to, resolvedTopic);
    const status = resolveEventStatus(resolvedKind);
    const importance = resolveImportance(resolvedKind);
    const latencyMs = resolveLatencyMs(resolvedKind);
    const traceId = nextTraceId();

    return {
      ts: new Date().toISOString(),
      trace_id: traceId,
      from,
      to,
      kind: resolvedKind,
      topic: resolvedTopic,
      summary,
      status,
      importance,
      latency_ms: latencyMs,
      chain_id: chainId || undefined,
      chain_step: chainStep || undefined,
    };
  }

  function createRandomEvent() {
    const kind = resolveEventKind();
    const endpoints = resolveAgentEndpoints(
      primaryAgentId.value,
      orbitAgentIds.value,
      enabledAgentIds.value,
    );
    if (!endpoints) return null;
    const { from, to } = endpoints;
    return createEvent({ from, to, kind });
  }

  function enqueueChainEvents(seedEvent) {
    if (!seedEvent || Math.random() > CHAIN_PROBABILITY) return;
    const steps = randomInt(1, CHAIN_MAX_STEPS);
    const chainId = `chn-${Date.now().toString(36)}-${randomInt(0, 46655).toString(36)}`;

    let from = String(seedEvent.to || primaryAgentId.value || CENTER_AGENT_ID);
    let topic = String(seedEvent.topic || "");
    let inheritedKind = String(seedEvent.kind || "info");

    for (let step = 1; step <= steps; step += 1) {
      const endpoints = resolveChainEndpoints(
        from,
        primaryAgentId.value,
        enabledAgentIds.value,
      );
      if (!endpoints) break;
      const kind = Math.random() < 0.64 ? inheritedKind : resolveEventKind();
      if (!topic || Math.random() < 0.42) {
        topic = pickRandom(KIND_TOPICS[kind] || KIND_TOPICS.info) || topic;
      }

      const chainedEvent = createEvent({
        from: endpoints.from,
        to: endpoints.to,
        kind,
        topic,
        chainId,
        chainStep: step,
      });

      pendingChainEvents.push({
        delayMs: randomInt(CHAIN_EVENT_MIN_INTERVAL_MS, CHAIN_EVENT_MAX_INTERVAL_MS),
        event: chainedEvent,
      });

      from = endpoints.to;
      inheritedKind = kind;
    }
  }

  function emitNextEvent() {
    while (pendingChainEvents.length) {
      const nextRecord = pendingChainEvents.shift();
      if (nextRecord?.event) {
        if (appendEvent(nextRecord.event)) {
          return;
        }
      }
    }

    const event = createRandomEvent();
    if (!event) return;
    appendEvent(event);
    enqueueChainEvents(event);
  }

  function highlightEvent(event) {
    if (!event?.trace_id) return;
    highlightedTraceId.value = event.trace_id;
    const nowMs = performance.now();
    highlightUntilMs.value = nowMs + HIGHLIGHT_LINK_TTL_MS;
    const link = {
      id: `focus-${event.trace_id}-${Math.round(nowMs)}`,
      trace_id: event.trace_id,
      from: event.from,
      to: event.to,
      kind: event.kind,
      status: event.status,
      importance: Math.max(0.9, Number(event.importance || 0.5)),
      createdAtMs: nowMs,
      expiresAtMs: nowMs + HIGHLIGHT_LINK_TTL_MS,
      manual: true,
    };
    activeLinks.value = [link, ...activeLinks.value].slice(0, ACTIVE_LINK_LIMIT);
  }

  function setFilterKind(kind) {
    if (!PLEIAD_KINDS.includes(kind)) return;
    if (kind !== "all" && filterKind.value === kind) {
      filterKind.value = "all";
      return;
    }
    filterKind.value = kind;
  }

  function pinAgent(agentId) {
    const normalized = String(agentId || "");
    if (!normalized || !AGENT_BY_ID.has(normalized)) return;
    pinnedAgentId.value =
      pinnedAgentId.value === normalized ? "" : normalized;
  }

  function clearPin() {
    pinnedAgentId.value = "";
  }

  function setHoveredAgent(agentId) {
    const normalized = String(agentId || "");
    hoveredAgentId.value = AGENT_BY_ID.has(normalized) ? normalized : "";
  }

  function setPrimaryAgent(agentId, options = {}) {
    const normalized = normalizeAgentId(agentId);
    if (!normalized) return false;
    if (normalized === primaryAgentId.value) return true;

    if (disabledAgentIdSet.value.has(normalized)) {
      disabledAgentIds.value = disabledAgentIds.value.filter((id) => id !== normalized);
    }

    const previousPrimary = primaryAgentId.value;
    const prefersMinimalMotion =
      prefersReducedMotion.value || fxProfile.value.mode === "off";
    const requestedDuration = Number(options?.durationMs || PRIMARY_SWITCH_TRANSITION_MS);
    const durationMs = Math.round(
      clamp(
        prefersMinimalMotion ? requestedDuration * 0.55 : requestedDuration,
        280,
        2400,
      ),
    );
    const nowMs = performance.now();

    primaryAgentId.value = normalized;
    primaryTransition.value = {
      id: `handoff-${previousPrimary}-${normalized}-${Math.round(nowMs)}`,
      from: previousPrimary,
      to: normalized,
      startedAtMs: nowMs,
      endsAtMs: nowMs + durationMs,
      durationMs,
      reason: String(options?.reason || "api"),
    };
    appendPrimarySwitchEvent(
      previousPrimary,
      normalized,
      String(options?.reason || "api"),
    );
    scheduleNextEvent();
    return true;
  }

  function resetPrimaryAgent(options = {}) {
    return setPrimaryAgent(CENTER_AGENT_ID, {
      reason: options.reason || "reset",
      durationMs: options.durationMs,
    });
  }

  function cyclePrimaryAgent(step = 1, options = {}) {
    const direction = Number(step || 1);
    const safeStep = Number.isFinite(direction) ? Math.trunc(direction) : 1;
    if (!safeStep) return false;

    const currentIndex = AGENT_IDS.indexOf(primaryAgentId.value);
    const baseIndex = currentIndex >= 0 ? currentIndex : 0;
    const normalizedStep = Math.abs(safeStep) % AGENT_IDS.length || 1;
    const offset = safeStep > 0 ? normalizedStep : -normalizedStep;
    const nextIndex =
      (baseIndex + offset + AGENT_IDS.length * 2) % AGENT_IDS.length;
    return setPrimaryAgent(AGENT_IDS[nextIndex], {
      reason: options.reason || "cycle",
      durationMs: options.durationMs,
    });
  }

  function togglePause() {
    isPaused.value = !isPaused.value;
    scheduleNextEvent();
  }

  function animationTick(timestamp) {
    if (!isRunning.value) return;
    if (!lastFrameTs) {
      lastFrameTs = timestamp;
    }
    const deltaMs = Math.max(0, Math.min(84, timestamp - lastFrameTs));
    lastFrameTs = timestamp;

    if (!isPaused.value && isDocumentVisible.value) {
      const nextRotation =
        (rotationRad.value + deltaMs * fxProfile.value.rotationRadPerMs) % TAU;
      rotationRad.value = nextRotation;
    }

    pruneActiveLinks(timestamp);
    if (
      highlightedTraceId.value &&
      highlightUntilMs.value &&
      timestamp >= highlightUntilMs.value
    ) {
      highlightedTraceId.value = "";
      highlightUntilMs.value = 0;
    }
    if (
      primaryTransition.value &&
      timestamp >= Number(primaryTransition.value.endsAtMs || 0)
    ) {
      primaryTransition.value = null;
    }

    frame.value = timestamp;
    rafId = window.requestAnimationFrame(animationTick);
  }

  function startAnimationLoop() {
    if (rafId) return;
    lastFrameTs = 0;
    rafId = window.requestAnimationFrame(animationTick);
  }

  function stopAnimationLoop() {
    if (!rafId) return;
    window.cancelAnimationFrame(rafId);
    rafId = 0;
    lastFrameTs = 0;
  }

  function handleVisibilityChange() {
    isDocumentVisible.value = document.visibilityState !== "hidden";
    if (isDocumentVisible.value) {
      scheduleNextEvent();
      scheduleDisabledAgentRotation();
      return;
    }
    clearEventTimer();
    clearDisabledRotationTimer();
  }

  function handleFxModeChange(event) {
    const nextMode = normalizeFxMode(event?.detail?.mode || resolveFxModeFromDom());
    fxMode.value = nextMode;
  }

  function handleReducedMotionChange(event) {
    prefersReducedMotion.value = Boolean(event?.matches);
  }

  function attachRuntimeListeners() {
    document.addEventListener("visibilitychange", handleVisibilityChange);
    window.addEventListener("oko:fx-mode-change", handleFxModeChange);

    if (!globalThis.matchMedia) return;
    mediaQueryList = globalThis.matchMedia(REDUCED_MOTION_QUERY);
    prefersReducedMotion.value = Boolean(mediaQueryList.matches);
    if (mediaQueryList.addEventListener) {
      mediaQueryList.addEventListener("change", handleReducedMotionChange);
      return;
    }
    if (mediaQueryList.addListener) {
      mediaQueryList.addListener(handleReducedMotionChange);
    }
  }

  function detachRuntimeListeners() {
    document.removeEventListener("visibilitychange", handleVisibilityChange);
    window.removeEventListener("oko:fx-mode-change", handleFxModeChange);

    if (!mediaQueryList) return;
    if (mediaQueryList.removeEventListener) {
      mediaQueryList.removeEventListener("change", handleReducedMotionChange);
    } else if (mediaQueryList.removeListener) {
      mediaQueryList.removeListener(handleReducedMotionChange);
    }
    mediaQueryList = null;
  }

  function start() {
    if (isRunning.value) return;
    isRunning.value = true;
    attachRuntimeListeners();
    reseedDisabledAgents();
    startAnimationLoop();
    scheduleNextEvent();
    scheduleDisabledAgentRotation();
  }

  function stop() {
    if (!isRunning.value) return;
    isRunning.value = false;
    clearEventTimer();
    clearDisabledRotationTimer();
    pendingChainEvents = [];
    primaryTransition.value = null;
    stopAnimationLoop();
    detachRuntimeListeners();
  }

  function show() {
    screensaverVisible.value = true;
  }

  function hide() {
    screensaverVisible.value = false;
  }

  watch(
    () => isPaused.value,
    () => {
      scheduleNextEvent();
    },
  );

  watch(
    () => isDocumentVisible.value,
    () => {
      scheduleNextEvent();
      scheduleDisabledAgentRotation();
    },
  );

  watch(
    () => fxProfile.value.eventCadenceMultiplier,
    () => {
      scheduleNextEvent();
    },
  );

  watch(
    () => primaryAgentId.value,
    () => {
      reseedDisabledAgents();
      scheduleDisabledAgentRotation();
    },
  );

  onMounted(() => {
    if (autoStart) {
      start();
    }
  });

  onBeforeUnmount(() => {
    stop();
  });

  return {
    AGENTS,
    AGENT_BY_ID,
    CENTER_AGENT_ID,
    ORBIT_AGENT_IDS,
    PLEIAD_KINDS,
    activeLinks,
    clearPin,
    cyclePrimaryAgent,
    disabledAgentIdSet,
    disabledAgentIds,
    enabledAgentIdSet,
    events,
    filterKind,
    filteredActiveLinks,
    filteredEvents,
    frame,
    fxMode,
    fxProfile,
    hide,
    highlightedAgentIds,
    highlightedTraceId,
    highlightEvent,
    hoveredAgentId,
    isDocumentVisible,
    isAgentEnabled,
    isPaused,
    isRunning,
    orbitAgentIds,
    pinAgent,
    pinnedAgentId,
    primaryAgentId,
    primaryTransition,
    prefersReducedMotion,
    resetPrimaryAgent,
    rotationRad,
    screensaverVisible,
    setFilterKind,
    setPrimaryAgent,
    setHoveredAgent,
    show,
    start,
    stop,
    togglePause,
  };
}
