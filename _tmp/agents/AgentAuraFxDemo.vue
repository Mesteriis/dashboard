<template>
  <section class="agent-aura-demo">
    <header class="agent-aura-demo-head">
      <div>
        <p class="agent-aura-demo-kicker">Agent Aura FX</p>
        <h3>Plasma / Particles Activity Demo</h3>
      </div>

      <div class="agent-aura-demo-actions">
        <FxModeToggle @change="handleModeChange" />
        <button class="agent-aura-demo-pulse" type="button" @click="emitRandomEvent">
          Emit Event
        </button>
      </div>
    </header>

    <div class="agent-aura-grid">
      <article v-for="agent in demoAgents" :key="agent.id" class="agent-aura-card">
        <AgentAvatarFx
          :agent-id="agent.id"
          :src="agent.src"
          :size="124"
          quality="medium"
          idle-mode="particles"
        />

        <h4>{{ agent.title }}</h4>
        <p>{{ agent.role }}</p>
      </article>
    </div>

    <section class="agent-aura-three">
      <header class="agent-aura-three-head">
        <div>
          <p class="agent-aura-demo-kicker">Three.js</p>
          <h4>Universal Masked Particle Avatar</h4>
        </div>

        <div class="agent-aura-three-head-actions">
          <div class="agent-aura-three-mode">
            <button
              class="agent-aura-three-mode-btn"
              :class="{ 'is-active': threeTransformMode === 'avatar' }"
              type="button"
              @click="setThreeTransformMode('avatar')"
            >
              Assemble
            </button>
            <button
              class="agent-aura-three-mode-btn"
              :class="{ 'is-active': threeTransformMode === 'vortex' }"
              type="button"
              @click="setThreeTransformMode('vortex')"
            >
              Vortex
            </button>
          </div>

          <button
            class="agent-aura-three-settings"
            type="button"
            @click="toggleThreeSettings"
          >
            {{ threeSettingsOpen ? "Hide settings" : "Settings" }}
          </button>
        </div>
      </header>

      <div class="agent-aura-three-stage">
        <AgentAvatarSphereParticlesThree
          :src="selectedThreeAvatarSrc"
          :size="threeSize"
          :particle-count="threeParticleCount"
          :point-size="threePointSize"
          :swirl-speed="threeSwirlSpeed"
          :stream-count="threeStreamCount"
          :transform-mode="threeTransformMode"
          :mask-src="resolvedThreeMaskSrc"
          :mask-strength="threeMaskStrength"
          :projection-mode="threeProjectionMode"
          :ring-angle-deg="threeRingAngleDeg"
          :ring-tilt-deg="threeRingTiltDeg"
          :ring-yaw-deg="threeRingYawDeg"
          :ring-radius="threeRingRadius"
          :ring-band="threeRingBand"
        />
      </div>

      <div v-if="threeSettingsOpen" class="agent-aura-three-controls">
        <label class="agent-aura-three-control">
          <span>Agent</span>
          <select v-model="selectedThreeAgentId">
            <option
              v-for="agent in AGENTS"
              :key="`three-agent-${agent.id}`"
              :value="agent.id"
            >
              {{ agent.id }}
            </option>
          </select>
        </label>

        <label class="agent-aura-three-control">
          <span>Projection</span>
          <select v-model="threeProjectionMode">
            <option value="ring2d">Ring 2D</option>
            <option value="sphere">Sphere 3D</option>
          </select>
        </label>

        <label class="agent-aura-three-control">
          <span>Mask source</span>
          <select v-model="threeMaskSourceType">
            <option value="avatar">Avatar silhouette</option>
            <option value="none">No mask</option>
            <option value="custom">Custom path</option>
          </select>
        </label>

        <label
          v-if="threeMaskSourceType === 'custom'"
          class="agent-aura-three-control agent-aura-three-control--wide"
        >
          <span>Mask path</span>
          <input
            v-model.trim="threeMaskCustomSrc"
            type="text"
            placeholder="/static/img/particles_blend.jpg"
          />
        </label>

        <label class="agent-aura-three-control">
          <span>Mask strength: {{ threeMaskStrength.toFixed(2) }}</span>
          <input
            v-model.number="threeMaskStrength"
            type="range"
            min="0.2"
            max="3"
            step="0.05"
          />
        </label>

        <label class="agent-aura-three-control">
          <span>Particles: {{ threeParticleCount }}</span>
          <input
            v-model.number="threeParticleCount"
            type="range"
            min="900"
            max="10000"
            step="200"
          />
        </label>

        <label class="agent-aura-three-control">
          <span>Point size: {{ threePointSize.toFixed(1) }}</span>
          <input
            v-model.number="threePointSize"
            type="range"
            min="0.4"
            max="3.0"
            step="0.05"
          />
        </label>

        <label class="agent-aura-three-control">
          <span>Swirl speed: {{ threeSwirlSpeed.toFixed(1) }}</span>
          <input
            v-model.number="threeSwirlSpeed"
            type="range"
            min="0.4"
            max="2.8"
            step="0.1"
          />
        </label>

        <label class="agent-aura-three-control">
          <span>Streams: {{ threeStreamCount }}</span>
          <input
            v-model.number="threeStreamCount"
            type="range"
            min="2"
            max="5"
            step="1"
          />
        </label>

        <label class="agent-aura-three-control">
          <span>Ring angle: {{ threeRingAngleDeg.toFixed(0) }}&deg;</span>
          <input
            v-model.number="threeRingAngleDeg"
            type="range"
            min="-180"
            max="180"
            step="1"
          />
        </label>

        <label class="agent-aura-three-control">
          <span>Tilt: {{ threeRingTiltDeg.toFixed(0) }}&deg;</span>
          <input
            v-model.number="threeRingTiltDeg"
            type="range"
            min="-85"
            max="85"
            step="1"
          />
        </label>

        <label class="agent-aura-three-control">
          <span>Yaw: {{ threeRingYawDeg.toFixed(0) }}&deg;</span>
          <input
            v-model.number="threeRingYawDeg"
            type="range"
            min="-180"
            max="180"
            step="1"
          />
        </label>

        <label class="agent-aura-three-control">
          <span>Ring radius: {{ threeRingRadius.toFixed(2) }}</span>
          <input
            v-model.number="threeRingRadius"
            type="range"
            min="0.35"
            max="2.2"
            step="0.01"
          />
        </label>

        <label class="agent-aura-three-control">
          <span>Ring band: {{ threeRingBand.toFixed(2) }}</span>
          <input
            v-model.number="threeRingBand"
            type="range"
            min="0.03"
            max="0.42"
            step="0.005"
          />
        </label>
      </div>
    </section>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import AgentAvatarFx from "./AgentAvatarFx.vue";
import AgentAvatarSphereParticlesThree from "./AgentAvatarSphereParticlesThree.vue";
import FxModeToggle from "./FxModeToggle.vue";
import { AGENTS, type AgentDefinition } from "../../constants/agentPlasmaPresets";
import { useAgentActivity, type AgentEvent } from "../../composables/useAgentActivity";

type ThreeTransformMode = "avatar" | "vortex";
type ThreeProjectionMode = "ring2d" | "sphere";
type ThreeMaskSourceType = "avatar" | "none" | "custom";
type DemoAgentCard = AgentDefinition & { src: string };

const { ingestEvent } = useAgentActivity();

const demoAgents = computed<DemoAgentCard[]>(() =>
  AGENTS.map((agent) => ({
    ...agent,
    src: `/static/img/pleiads/${agent.id}.webp`,
  })),
);
const selectedThreeAgentId = ref<AgentDefinition["id"]>("HESTIA");
const threeSettingsOpen = ref(false);
const threeParticleCount = ref(4600);
const threePointSize = ref(1.1);
const threeSwirlSpeed = ref(1.1);
const threeStreamCount = ref(3);
const threeTransformMode = ref<ThreeTransformMode>("vortex");
const threeProjectionMode = ref<ThreeProjectionMode>("ring2d");
const threeMaskSourceType = ref<ThreeMaskSourceType>("avatar");
const threeMaskCustomSrc = ref("");
const threeMaskStrength = ref(1.2);
const threeRingAngleDeg = ref(0);
const threeRingTiltDeg = ref(44);
const threeRingYawDeg = ref(0);
const threeRingRadius = ref(1);
const threeRingBand = ref(0.12);
const threeSize = 320;

const selectedThreeAvatarSrc = computed(
  () => `/static/img/pleiads/${selectedThreeAgentId.value}.webp`,
);
const resolvedThreeMaskSrc = computed<string>(() => {
  if (threeMaskSourceType.value === "none") {
    return "";
  }
  if (threeMaskSourceType.value === "custom") {
    return String(threeMaskCustomSrc.value || "").trim();
  }
  return selectedThreeAvatarSrc.value;
});

let demoEventTimerId = 0;
let traceSequence = 0;

function randomFloat(min: number, max: number): number {
  return min + Math.random() * (max - min);
}

function randomInt(min: number, max: number): number {
  return Math.floor(randomFloat(min, max + 1));
}

function pickRandom<T>(list: readonly T[]): T | undefined {
  if (!Array.isArray(list) || !list.length) return undefined;
  return list[randomInt(0, list.length - 1)];
}

function nextTraceId(): string {
  traceSequence += 1;
  return `afx-${Date.now().toString(36)}-${traceSequence.toString(36)}`;
}

function createRandomEvent(): AgentEvent {
  const from = pickRandom(AGENTS)?.id || "HESTIA";
  const targetPool = AGENTS.filter((agent) => agent.id !== from);
  const to = pickRandom(targetPool)?.id || "VELES";

  const kind = pickRandom<AgentEvent["kind"]>([
    "info",
    "warning",
    "action",
    "memory",
  ]) || "info";
  const importance = Number(randomFloat(0.2, 1).toFixed(2));

  let status: AgentEvent["status"] = "ok";
  const roll = Math.random();
  if (kind === "warning" && roll > 0.52) {
    status = "error";
  } else if (roll > 0.78) {
    status = "pending";
  }

  return {
    ts: new Date().toISOString(),
    trace_id: nextTraceId(),
    from,
    to,
    kind,
    status,
    importance,
    summary: `${from} -> ${to} ${kind}`,
  };
}

function emitRandomEvent(): void {
  ingestEvent(createRandomEvent());
}

function handleModeChange(): void {
  emitRandomEvent();
}

function toggleThreeSettings(): void {
  threeSettingsOpen.value = !threeSettingsOpen.value;
}

function setThreeTransformMode(mode: unknown): void {
  const normalized = String(mode || "").toLowerCase() === "avatar" ? "avatar" : "vortex";
  threeTransformMode.value = normalized;
}

onMounted(() => {
  demoEventTimerId = window.setInterval(() => {
    emitRandomEvent();
  }, randomInt(850, 1650));
});

onBeforeUnmount(() => {
  if (!demoEventTimerId) return;
  window.clearInterval(demoEventTimerId);
  demoEventTimerId = 0;
});
</script>

<style scoped>
.agent-aura-demo {
  display: grid;
  gap: 16px;
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 14px;
  background: linear-gradient(180deg, var(--surface-strong), var(--surface));
}

.agent-aura-demo-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.agent-aura-demo-kicker {
  margin: 0;
  color: var(--muted);
  font-size: 0.74rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.agent-aura-demo h3 {
  margin: 5px 0 0;
  font-size: 1rem;
}

.agent-aura-demo-actions {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  justify-content: flex-end;
}

.agent-aura-demo-pulse {
  height: 36px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  cursor: pointer;
}

.agent-aura-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(148px, 1fr));
  gap: 12px;
}

.agent-aura-card {
  display: grid;
  justify-items: center;
  gap: 8px;
  padding: 10px;
  border: 1px solid color-mix(in oklab, var(--border), white 8%);
  border-radius: 12px;
  background: color-mix(in oklab, var(--surface), black 6%);
}

.agent-aura-card h4 {
  margin: 0;
  font-size: 0.78rem;
  letter-spacing: 0.05em;
}

.agent-aura-card p {
  margin: 0;
  font-size: 0.72rem;
  color: var(--muted);
}

.agent-aura-three {
  display: grid;
  gap: 12px;
  border: 1px solid color-mix(in oklab, var(--border), white 8%);
  border-radius: 12px;
  padding: 12px;
  background: color-mix(in oklab, var(--surface), black 6%);
}

.agent-aura-three-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.agent-aura-three-head-actions {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.agent-aura-three-head h4 {
  margin: 5px 0 0;
  font-size: 0.95rem;
}

.agent-aura-three-mode {
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
  background: color-mix(in oklab, var(--surface), black 4%);
}

.agent-aura-three-mode-btn {
  height: 34px;
  min-width: 84px;
  padding: 0 10px;
  border: 0;
  border-right: 1px solid var(--border);
  background: transparent;
  color: var(--muted);
  cursor: pointer;
}

.agent-aura-three-mode-btn:last-child {
  border-right: 0;
}

.agent-aura-three-mode-btn.is-active {
  color: var(--text);
  background: color-mix(in oklab, var(--surface-strong), white 6%);
}

.agent-aura-three-settings {
  height: 34px;
  padding: 0 12px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  cursor: pointer;
}

.agent-aura-three-stage {
  display: grid;
  place-items: center;
  min-height: 340px;
  border-radius: 10px;
  background:
    radial-gradient(circle at 50% 28%, rgba(96, 152, 220, 0.12), transparent 56%),
    color-mix(in oklab, var(--surface-strong), black 14%);
}

.agent-aura-three-controls {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 10px;
}

.agent-aura-three-control {
  display: grid;
  gap: 6px;
  color: var(--text);
}

.agent-aura-three-control--wide {
  grid-column: 1 / -1;
}

.agent-aura-three-control span {
  font-size: 0.7rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: var(--muted);
}

.agent-aura-three-control select,
.agent-aura-three-control input[type="text"],
.agent-aura-three-control input[type="range"] {
  width: 100%;
}

.agent-aura-three-control input[type="text"] {
  height: 34px;
  border-radius: 9px;
  border: 1px solid var(--border);
  padding: 0 10px;
  background: color-mix(in oklab, var(--surface), black 2%);
  color: var(--text);
}
</style>
