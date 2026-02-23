<template>
  <section class="pleiad-root" :class="{ 'pleiad-root--screensaver': isScreensaver }">
    <section class="pleiad-layout">
      <section class="pleiad-canvas-panel">
        <PleiadCanvas
          :agents="demo.AGENTS"
          :center-agent-id="demo.primaryAgentId.value"
          :orbit-agent-ids="demo.orbitAgentIds.value"
          :avatar-zoom="AVATAR_ZOOM"
          :render-agent-faces="false"
          :primary-transition="demo.primaryTransition.value"
          :active-links="demo.filteredActiveLinks.value"
          :highlighted-trace-id="demo.highlightedTraceId.value"
          :highlighted-agent-ids="demo.highlightedAgentIds.value"
          :hovered-agent-id="demo.hoveredAgentId.value"
          :pinned-agent-id="demo.pinnedAgentId.value"
          :rotation-rad="demo.rotationRad.value"
          :frame="demo.frame.value"
          :fx-profile="demo.fxProfile.value"
          @hover-agent="handleAgentHover"
          @select-agent="handleAgentSelect"
          @layout-update="handleLayoutUpdate"
        />

        <div class="pleiad-avatar-layer" aria-hidden="true">
          <div
            v-for="entry in avatarLayerEntries"
            :key="entry.id"
            class="pleiad-avatar-node"
            :class="{
              'is-disabled': entry.isDisabled,
              'is-dimmed': entry.isDimmed,
            }"
            :style="entry.style"
          >
            <AgentAvatarSphereParticlesThree
              :src="entry.avatarSrc"
              :mask-src="entry.avatarSrc"
              :size="entry.size"
              :particle-count="entry.particleCount"
              :point-size="entry.pointSize"
              :swirl-speed="entry.swirlSpeed"
              :stream-count="entry.streamCount"
              :transform-mode="entry.transformMode"
              :animated="entry.animated"
              :transparent-shell="true"
              projection-mode="ring2d"
              :ring-angle-deg="entry.ringAngleDeg"
              :ring-tilt-deg="entry.ringTiltDeg"
              :ring-yaw-deg="entry.ringYawDeg"
              :ring-radius="entry.ringRadius"
              :ring-band="entry.ringBand"
              :mask-strength="entry.maskStrength"
            />
          </div>
        </div>
      </section>
    </section>

    <div class="pleiad-top-actions">
      <button
        class="ghost pleiad-icon-btn"
        type="button"
        :title="closeButtonLabel"
        :aria-label="closeButtonLabel"
        @click="emitClose"
      >
        <X class="ui-icon pleiad-action-icon" />
      </button>
    </div>

    <div v-if="pinnedAgent" class="pleiad-pin-banner">
      <p class="pleiad-pin-label">Pin: {{ pinnedAgent.name }}</p>
      <button class="ghost pleiad-clear-pin" type="button" @click="demo.clearPin">
        Clear pin
      </button>
    </div>

    <button
      class="pleiad-feed-toggle"
      type="button"
      :class="{ active: isFeedOpen }"
      :aria-pressed="isFeedOpen"
      :title="isFeedOpen ? 'Hide event feed' : 'Show event feed'"
      :aria-label="isFeedOpen ? 'Hide event feed' : 'Show event feed'"
      @click="toggleFeed"
    >
      <List class="ui-icon pleiad-feed-toggle-icon" />
    </button>

    <aside class="pleiad-feed-panel" :class="{ open: isFeedOpen }">
      <header class="pleiad-feed-head">
        <div class="pleiad-feed-head-top">
          <h3>Event Feed</h3>
          <div class="pleiad-feed-head-actions">
            <p>{{ demo.filteredEvents.value.length }}/{{ demo.events.value.length }}</p>
            <button
              class="pleiad-feed-close"
              type="button"
              aria-label="Close event feed"
              @click="isFeedOpen = false"
            >
              <X class="ui-icon" />
            </button>
          </div>
        </div>

        <div class="pleiad-filter-group pleiad-feed-filters" role="group" aria-label="Event kind filters">
          <button
            v-for="option in kindOptions"
            :key="option.id"
            class="pleiad-kind-chip"
            :class="[
              `kind-${option.id}`,
              { active: demo.filterKind.value === option.id },
            ]"
            type="button"
            :aria-pressed="demo.filterKind.value === option.id"
            :title="option.title"
            :aria-label="option.title"
            @click="demo.setFilterKind(option.id)"
          >
            <component :is="option.icon" class="ui-icon pleiad-kind-icon" />
          </button>
        </div>
      </header>

      <div class="pleiad-feed-list">
        <button
          v-for="event in demo.filteredEvents.value"
          :key="event.trace_id"
          class="pleiad-event-item"
          type="button"
          :class="[
            `kind-${event.kind}`,
            `status-${event.status}`,
            { active: demo.highlightedTraceId.value === event.trace_id },
          ]"
          @click="demo.highlightEvent(event)"
        >
          <div class="pleiad-event-line">
            <span class="pleiad-route">{{ event.from }} -> {{ event.to }}</span>
            <span class="pleiad-kind">{{ event.kind }}</span>
          </div>
          <p class="pleiad-summary">{{ event.summary }}</p>
          <div class="pleiad-event-meta">
            <span>{{ formatEventTime(event.ts) }}</span>
            <span>{{ event.latency_ms }}ms</span>
            <span>imp {{ Number(event.importance).toFixed(2) }}</span>
          </div>
        </button>

        <p v-if="!demo.filteredEvents.value.length" class="pleiad-feed-empty">
          Нет событий под текущий фильтр.
        </p>
      </div>
    </aside>

    <div
      v-if="tooltip.visible && hoveredAgent"
      class="pleiad-tooltip"
      :style="tooltipStyle"
    >
      <strong>{{ hoveredAgent.name }}</strong>
      <span>{{ hoveredAgent.role }}</span>
      <small>Click: pin | Shift+Click: primary</small>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";
import {
  Brain,
  Circle,
  Info,
  List,
  TriangleAlert,
  X,
  Zap,
} from "lucide-vue-next";
import { usePleiadDemo } from "../../composables/usePleiadDemo.js";
import { PLEIAD_PRIMARY_AGENT_EVENT } from "../../services/pleiadNavigation.js";
import AgentAvatarSphereParticlesThree from "../agents/AgentAvatarSphereParticlesThree.vue";
import PleiadCanvas from "./PleiadCanvas.vue";

const props = defineProps({
  mode: {
    type: String,
    default: "route",
  },
});

const emit = defineEmits(["close"]);
const demo = usePleiadDemo({
  autoStart: true,
  screensaverVisible: props.mode === "screensaver",
});
const AVATAR_ZOOM = 3;
const WINDOW_PLEIAD_API_KEY = "okoPleiadApi";

const kindOptions = [
  { id: "all", title: "All", icon: Circle },
  { id: "action", title: "Action", icon: Zap },
  { id: "warning", title: "Warning", icon: TriangleAlert },
  { id: "memory", title: "Memory", icon: Brain },
  { id: "info", title: "Info", icon: Info },
];

const tooltip = reactive({
  visible: false,
  x: 0,
  y: 0,
});
const isFeedOpen = ref(false);
const avatarLayout = ref({
  width: 0,
  height: 0,
  nodes: [],
});

const isScreensaver = computed(() => props.mode === "screensaver");
const closeButtonLabel = computed(() =>
  isScreensaver.value ? "Close screensaver" : "Close",
);
const hoveredAgent = computed(
  () => demo.AGENT_BY_ID.get(demo.hoveredAgentId.value) || null,
);
const pinnedAgent = computed(
  () => demo.AGENT_BY_ID.get(demo.pinnedAgentId.value) || null,
);
const avatarNodeById = computed(() => {
  const map = new Map();
  for (const node of avatarLayout.value.nodes || []) {
    const id = String(node?.id || "");
    if (!id) continue;
    map.set(id, node);
  }
  return map;
});
const avatarLayerEntries = computed(() => {
  const nodeById = avatarNodeById.value;
  const hasPin = Boolean(demo.pinnedAgentId.value);
  const highlightedSet = new Set(demo.highlightedAgentIds.value || []);
  const disabledSet = demo.disabledAgentIdSet.value;
  const orderedIds = [demo.primaryAgentId.value, ...demo.orbitAgentIds.value];
  const uniqueIds = [...new Set(orderedIds)];
  const entries = [];

  for (const agentId of uniqueIds) {
    const agent = demo.AGENT_BY_ID.get(agentId);
    const node = nodeById.get(agentId);
    if (!agent || !node) continue;

    const isDisabled = disabledSet.has(agentId);
    const isHovered = demo.hoveredAgentId.value === agentId;
    const isPinned = demo.pinnedAgentId.value === agentId;
    const isHighlighted = highlightedSet.has(agentId);
    const isDimmed = hasPin && !isPinned && !isHighlighted;
    const scaleBoost = isHovered ? 1.08 : isPinned ? 1.05 : isHighlighted ? 1.03 : 1;
    const size = clamp(
      Number(node.radius || 0) * 2.55 * scaleBoost,
      node.isCenter ? 156 : 104,
      node.isCenter ? 352 : 244,
    );

    entries.push({
      id: agentId,
      avatarSrc: String(agent.avatarSrc || ""),
      isDisabled,
      isDimmed,
      size: Math.round(size),
      particleCount: Math.round(
        clamp((node.isCenter ? 900 : 560) * (isDisabled ? 1.24 : 1), 340, 1280),
      ),
      pointSize: node.isCenter ? (isDisabled ? 1.02 : 0.94) : isDisabled ? 0.92 : 0.84,
      swirlSpeed: isDisabled ? 1.3 : 0.9,
      streamCount: isDisabled ? 4 : 3,
      transformMode: isDisabled ? "vortex" : "avatar",
      animated: demo.fxProfile.value.mode !== "off",
      ringAngleDeg: Number(node.isCenter ? 2 : 0),
      ringTiltDeg: Number(node.isCenter ? 40 : 44),
      ringYawDeg: Number(node.isCenter ? 0 : -6),
      ringRadius: Number(node.isCenter ? 1.02 : 1),
      ringBand: Number(isDisabled ? 0.14 : 0.11),
      maskStrength: Number(isDisabled ? 1.28 : 1.12),
      style: {
        left: `${Number(node.x || 0)}px`,
        top: `${Number(node.y || 0)}px`,
        width: `${Math.round(size)}px`,
        height: `${Math.round(size)}px`,
        opacity: isDimmed ? "0.34" : "1",
        zIndex: node.isCenter ? "6" : "5",
        transform: `translate(-50%, -50%) scale(${scaleBoost.toFixed(3)})`,
      },
    });
  }

  return entries;
});
const tooltipStyle = computed(() => {
  const viewportWidth =
    typeof window === "undefined" ? 1280 : window.innerWidth;
  const viewportHeight =
    typeof window === "undefined" ? 720 : window.innerHeight;
  const left = Math.min(viewportWidth - 208, tooltip.x + 14);
  const top = Math.min(viewportHeight - 110, tooltip.y + 10);
  return {
    left: `${Math.max(12, left)}px`,
    top: `${Math.max(12, top)}px`,
  };
});

const timeFormatter = new Intl.DateTimeFormat("ru-RU", {
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
});

function formatEventTime(isoTs) {
  const parsed = new Date(isoTs);
  if (Number.isNaN(parsed.getTime())) return "--:--:--";
  return timeFormatter.format(parsed);
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function handleAgentHover(payload) {
  if (!payload?.id) {
    demo.setHoveredAgent("");
    tooltip.visible = false;
    return;
  }

  demo.setHoveredAgent(payload.id);
  tooltip.x = Number(payload.clientX || 0);
  tooltip.y = Number(payload.clientY || 0);
  tooltip.visible = true;
}

function handleAgentSelect(agentId) {
  const selectedAgentId =
    typeof agentId === "string" ? agentId : String(agentId?.id || "");
  if (!selectedAgentId) return;

  if (agentId && typeof agentId === "object" && agentId.promote) {
    demo.setPrimaryAgent(selectedAgentId, { reason: "ui-shift-click" });
    return;
  }
  demo.pinAgent(selectedAgentId);
}

function handleLayoutUpdate(payload) {
  if (!payload || !Array.isArray(payload.nodes)) return;
  avatarLayout.value = {
    width: Number(payload.width || 0),
    height: Number(payload.height || 0),
    nodes: payload.nodes.map((node) => ({
      id: String(node?.id || ""),
      x: Number(node?.x || 0),
      y: Number(node?.y || 0),
      radius: Number(node?.radius || 0),
      isCenter: Boolean(node?.isCenter),
    })),
  };
}

function toggleFeed() {
  isFeedOpen.value = !isFeedOpen.value;
}

function emitClose() {
  emit("close");
}

function handlePrimaryAgentEvent(event) {
  const agentId = String(
    event?.detail?.agentId || event?.detail?.id || "",
  )
    .trim()
    .toUpperCase();
  if (!agentId) return;

  demo.setPrimaryAgent(agentId, {
    reason: String(event?.detail?.reason || "external-event"),
    durationMs: Number(event?.detail?.durationMs || 0) || undefined,
  });
}

function mountExternalApi() {
  if (typeof window === "undefined") {
    return () => {};
  }

  const previousApi = window[WINDOW_PLEIAD_API_KEY];
  const api = {
    setPrimaryAgent: (agentId, options = {}) =>
      demo.setPrimaryAgent(agentId, options),
    resetPrimaryAgent: (options = {}) => demo.resetPrimaryAgent(options),
    cyclePrimaryAgent: (step = 1, options = {}) =>
      demo.cyclePrimaryAgent(step, options),
    getState: () => ({
      primaryAgentId: demo.primaryAgentId.value,
      orbitAgentIds: [...demo.orbitAgentIds.value],
      disabledAgentIds: [...demo.disabledAgentIds.value],
      pinnedAgentId: demo.pinnedAgentId.value,
      filterKind: demo.filterKind.value,
      isPaused: demo.isPaused.value,
      isRunning: demo.isRunning.value,
    }),
  };

  window[WINDOW_PLEIAD_API_KEY] = api;
  return () => {
    if (window[WINDOW_PLEIAD_API_KEY] !== api) return;
    if (previousApi && typeof previousApi === "object") {
      window[WINDOW_PLEIAD_API_KEY] = previousApi;
      return;
    }
    delete window[WINDOW_PLEIAD_API_KEY];
  };
}

let detachExternalApi = null;

onMounted(() => {
  window.addEventListener(PLEIAD_PRIMARY_AGENT_EVENT, handlePrimaryAgentEvent);
  detachExternalApi = mountExternalApi();
});

onBeforeUnmount(() => {
  window.removeEventListener(PLEIAD_PRIMARY_AGENT_EVENT, handlePrimaryAgentEvent);
  if (typeof detachExternalApi === "function") {
    detachExternalApi();
  }
  detachExternalApi = null;
});
</script>
