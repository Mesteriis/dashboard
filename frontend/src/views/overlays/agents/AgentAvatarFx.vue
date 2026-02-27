<template>
  <div
    ref="hostRef"
    class="agent-avatar-fx"
    :style="containerStyle"
    :data-state="activeState"
    :data-mode="activeRenderMode"
    @mouseenter="handlePointerEnter"
    @mouseleave="handlePointerLeave"
  >
    <canvas
      ref="plasmaCanvasRef"
      class="fx-layer fx-layer--plasma"
      :class="{ active: activeRenderMode === 'plasma' }"
    ></canvas>

    <canvas
      ref="particlesCanvasRef"
      class="fx-layer fx-layer--particles"
      :class="{ active: activeRenderMode === 'particles' }"
    ></canvas>

    <img
      class="avatar-image"
      :src="imageSrc"
      :alt="agentAlt"
      loading="lazy"
      decoding="async"
      @error="handleImageError"
    />

    <div class="avatar-vignette"></div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, toRef, watch } from "vue";
import {
  AGENT_PLASMA_PRESETS,
  DEFAULT_AGENT_PRESET,
  normalizeAgentId,
  type AgentPlasmaPreset,
} from "@/shared/constants/agentPlasmaPresets";
import {
  useAgentActivity,
  type AgentState,
} from "@/features/composables/useAgentActivity";
import { useFxMode, type FxMode } from "@/features/composables/useFxMode";

type QualityLevel = "low" | "medium" | "high";
type IdleMode = "dim-plasma" | "particles" | "off";
type RenderMode = FxMode;

interface QualityPreset {
  octaves: number;
  particleCount: number;
  plasmaFps: number;
  particlesFps: number;
}

interface Particle {
  angle: number;
  orbit: number;
  speed: number;
  alpha: number;
  size: number;
  wobble: number;
  phase: number;
  px: number;
  py: number;
}

interface PlasmaUniformLocations {
  time: WebGLUniformLocation | null;
  resolution: WebGLUniformLocation | null;
  color: WebGLUniformLocation | null;
  power: WebGLUniformLocation | null;
  state: WebGLUniformLocation | null;
  seed: WebGLUniformLocation | null;
  octaves: WebGLUniformLocation | null;
}

interface RuntimeModeSnapshot {
  mode: RenderMode;
  power: number;
  state: AgentState;
  stateIndex: number;
}

const QUALITY_PRESETS: Record<QualityLevel, QualityPreset> = {
  low: {
    octaves: 3,
    particleCount: 35,
    plasmaFps: 30,
    particlesFps: 30,
  },
  medium: {
    octaves: 4,
    particleCount: 55,
    plasmaFps: 45,
    particlesFps: 40,
  },
  high: {
    octaves: 5,
    particleCount: 80,
    plasmaFps: 45,
    particlesFps: 45,
  },
};

const VERTEX_SHADER_SOURCE = `
attribute vec2 a_position;
void main() {
  gl_Position = vec4(a_position, 0.0, 1.0);
}
`;

const FRAGMENT_SHADER_SOURCE = `
precision mediump float;

uniform float u_time;
uniform vec2 u_resolution;
uniform vec3 u_color;
uniform float u_power;
uniform float u_state;
uniform float u_seed;
uniform float u_octaves;

float hash(vec2 p) {
  p = fract(p * vec2(123.34, 456.21));
  p += dot(p, p + 45.32);
  return fract(p.x * p.y);
}

float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  float a = hash(i);
  float b = hash(i + vec2(1.0, 0.0));
  float c = hash(i + vec2(0.0, 1.0));
  float d = hash(i + vec2(1.0, 1.0));
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(a, b, u.x) +
    (c - a) * u.y * (1.0 - u.x) +
    (d - b) * u.x * u.y;
}

float fbm(vec2 p) {
  float value = 0.0;
  float amplitude = 0.5;
  vec2 shift = vec2(37.0, 17.0);

  for (int i = 0; i < 6; i++) {
    if (float(i) >= u_octaves) {
      break;
    }
    value += amplitude * noise(p);
    p = p * 2.03 + shift;
    amplitude *= 0.53;
  }

  return value;
}

void main() {
  vec2 uv = (gl_FragCoord.xy / max(u_resolution.xy, vec2(1.0))) * 2.0 - 1.0;
  uv.x *= u_resolution.x / max(u_resolution.y, 1.0);

  float t = u_time * 0.001;
  float dist = length(uv);
  float radial = smoothstep(1.16, 0.12, dist);

  float stateBoost = 0.72;
  if (u_state > 0.5) {
    stateBoost = 1.0;
  }
  if (u_state > 1.5) {
    stateBoost += 0.30;
  }
  if (u_state > 2.5) {
    stateBoost += 0.36;
  }

  vec2 q = uv * (1.8 + u_power * 0.92);
  vec2 warp = vec2(
    fbm(q + vec2(t * 0.22 + u_seed * 0.03, -t * 0.17)),
    fbm(q + vec2(-t * 0.16, t * 0.24 + u_seed * 0.05))
  );
  q += (warp - 0.5) * (0.95 + u_power * 0.35) * stateBoost;

  float base = fbm(q + u_seed * 0.1);
  float layer = fbm(q * 1.9 - vec2(t * 0.35, -t * 0.28));

  float filamentWave = abs(sin((q.x * 11.0 + q.y * 9.0 + base * 7.0 + t * 6.0) * (1.0 + stateBoost * 0.25)));
  float filaments = smoothstep(0.78 - u_power * 0.18, 1.0, filamentWave);
  filaments *= 0.35 + stateBoost * 0.45;

  float plasma = base * 0.62 + layer * 0.48 + filaments;
  plasma *= radial;

  float sparkleNoise = noise(q * 12.0 + vec2(t * 1.8, -t * 1.4) + u_seed);
  float sparkleThreshold = 0.968;
  if (u_state > 1.5) {
    sparkleThreshold -= 0.016;
  }
  if (u_state > 2.5) {
    sparkleThreshold -= 0.020;
  }
  float sparkleGate = step(sparkleThreshold, sparkleNoise);
  float sparkleBoost = 0.0;
  if (u_state > 1.5) {
    sparkleBoost = 0.70;
  }
  if (u_state > 2.5) {
    sparkleBoost = 1.20;
  }
  float sparkles = sparkleGate * radial * (0.2 + u_power * 0.8) * sparkleBoost;

  float glow = smoothstep(0.22, 1.25, plasma) * (0.42 + u_power * 0.58);
  vec3 color = u_color * (glow + plasma * 0.46 + sparkles * 1.1);
  float alpha = clamp((plasma * 0.70 + glow * 0.34 + sparkles * 0.8) * (0.55 + u_power * 0.42), 0.0, 1.0);
  alpha *= radial;

  gl_FragColor = vec4(color, alpha);
}
`;

const props = withDefaults(
  defineProps<{
    agentId: string;
    src: string;
    size?: number;
    quality?: QualityLevel;
    idleMode?: IdleMode;
    fxMode?: "" | RenderMode;
    animated?: boolean;
  }>(),
  {
    size: 160,
    quality: "medium",
    idleMode: "particles",
    fxMode: "",
    animated: true,
  },
);

const hostRef = ref<HTMLDivElement | null>(null);
const plasmaCanvasRef = ref<HTMLCanvasElement | null>(null);
const particlesCanvasRef = ref<HTMLCanvasElement | null>(null);
const imageSrc = ref(String(props.src || ""));
const activeRenderMode = ref<RenderMode>("off");
const activeState = ref<AgentState>("idle");
const hoverTarget = ref<number>(0);
const isDocumentHidden = ref(
  typeof document === "undefined" ? false : Boolean(document.hidden),
);
const isWebglUnavailable = ref(false);

const { effectiveFxMode, prefersReducedMotion } = useFxMode();
const { getFx } = useAgentActivity();
const fxSnapshot = getFx(toRef(props, "agentId"));

function isRenderMode(value: string): value is RenderMode {
  return value === "off" || value === "plasma" || value === "particles";
}

const preset = computed<AgentPlasmaPreset>(() => {
  const normalized = normalizeAgentId(props.agentId);
  if (!normalized) return DEFAULT_AGENT_PRESET;
  return AGENT_PLASMA_PRESETS[normalized] || DEFAULT_AGENT_PRESET;
});

const qualityPreset = computed<QualityPreset>(
  () => QUALITY_PRESETS[props.quality],
);

const requestedFxMode = computed<RenderMode>(() => {
  const propMode = String(props.fxMode || "")
    .trim()
    .toLowerCase();
  if (isRenderMode(propMode)) {
    return propMode;
  }
  return effectiveFxMode.value;
});

const canRunLoop = computed(
  () =>
    props.animated && !prefersReducedMotion.value && !isDocumentHidden.value,
);

const containerStyle = computed<Record<string, string>>(() => {
  const size = Math.max(56, Number(props.size || 160));
  return {
    "--avatar-size": `${size}px`,
  };
});

const agentAlt = computed(() => `${String(props.agentId || "agent")} avatar`);

let rafId = 0;
let lastTickMs = 0;
let lastDrawMs = 0;
let hoverSmoothed = 0;
let activitySmoothed = 0;
let powerSmoothed = 0;
let viewportWidth = 0;
let viewportHeight = 0;
let devicePixelRatio = 1;
let resizeObserver: ResizeObserver | null = null;
let fallbackResizeAttached = false;
let imageFallbackCandidates: string[] = [];
let imageFallbackIndex = 0;
let previousDrawMode: RenderMode = "off";

let particlesCtx: CanvasRenderingContext2D | null = null;
let particles: Particle[] = [];

let plasmaGl: WebGLRenderingContext | null = null;
let plasmaProgram: WebGLProgram | null = null;
let plasmaBuffer: WebGLBuffer | null = null;
let plasmaAttribPosition = -1;
let plasmaUniforms: PlasmaUniformLocations | null = null;

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function lerp(from: number, to: number, alpha: number): number {
  return from + (to - from) * alpha;
}

function randomFloat(min: number, max: number): number {
  return min + Math.random() * (max - min);
}

function resolveStateIndex(state: AgentState): number {
  if (state === "active") return 1;
  if (state === "alert") return 2;
  if (state === "error") return 3;
  return 0;
}

function parseRgb(colorText: unknown): [number, number, number] {
  const source = String(colorText || "").trim();
  const rgbaMatch = source.match(/rgba?\(([^)]+)\)/i);
  if (!rgbaMatch) return [120, 200, 255];
  const parts = (rgbaMatch[1] || "")
    .split(",")
    .slice(0, 3)
    .map((part) => Number.parseFloat(part.trim()));

  if (parts.length !== 3 || parts.some((value) => Number.isNaN(value))) {
    return [120, 200, 255];
  }

  return [
    clamp(parts[0] || 120, 0, 255),
    clamp(parts[1] || 200, 0, 255),
    clamp(parts[2] || 255, 0, 255),
  ];
}

function resolveImageLowercaseCandidate(src: unknown): string {
  const value = String(src || "").trim();
  if (!value) return "";

  const slashIndex = value.lastIndexOf("/");
  if (slashIndex < 0) return value.toLowerCase();

  const dir = value.slice(0, slashIndex + 1);
  const filename = value.slice(slashIndex + 1);
  return `${dir}${filename.toLowerCase()}`;
}

function swapImageExtension(src: unknown, nextExtension: string): string {
  const value = String(src || "").trim();
  if (!value) return "";

  const matched = value.match(/^([^?#]+)([?#].*)?$/);
  if (!matched) return "";

  const pathname = matched[1] || "";
  const suffix = matched[2] || "";
  if (!/\.(webp|png)$/i.test(pathname)) return "";

  const replaced = pathname.replace(/\.(webp|png)$/i, `.${nextExtension}`);
  if (replaced === pathname) return "";
  return `${replaced}${suffix}`;
}

function buildImageFallbackCandidates(src: unknown): string[] {
  const source = String(src || "").trim();
  if (!source) return [];

  const candidates: string[] = [];
  const append = (value: unknown): void => {
    const normalized = String(value || "").trim();
    if (!normalized || candidates.includes(normalized)) return;
    candidates.push(normalized);
  };

  const lower = resolveImageLowercaseCandidate(source);
  append(source);
  append(lower);

  const isWebp = /\.webp([?#].*)?$/i.test(source);
  const swapExt = isWebp ? "png" : "webp";
  append(swapImageExtension(source, swapExt));
  append(swapImageExtension(lower, swapExt));

  return candidates;
}

function handleImageError(): void {
  if (!imageFallbackCandidates.length) return;
  if (imageFallbackIndex >= imageFallbackCandidates.length - 1) return;
  imageFallbackIndex += 1;
  const fallbackSrc = imageFallbackCandidates[imageFallbackIndex];
  if (fallbackSrc) {
    imageSrc.value = fallbackSrc;
  }
}

function handlePointerEnter(): void {
  hoverTarget.value = 1;
}

function handlePointerLeave(): void {
  hoverTarget.value = 0;
}

function clearCanvas2d(): void {
  if (!particlesCtx || !viewportWidth || !viewportHeight) return;
  particlesCtx.clearRect(0, 0, viewportWidth, viewportHeight);
}

function clearPlasmaCanvas(): void {
  if (!plasmaGl || !plasmaCanvasRef.value) return;
  plasmaGl.viewport(
    0,
    0,
    plasmaCanvasRef.value.width,
    plasmaCanvasRef.value.height,
  );
  plasmaGl.clearColor(0, 0, 0, 0);
  plasmaGl.clear(plasmaGl.COLOR_BUFFER_BIT);
}

function clearAllLayers(): void {
  clearCanvas2d();
  clearPlasmaCanvas();
}

function buildParticles(): void {
  const count = qualityPreset.value.particleCount;
  const nextParticles: Particle[] = [];

  for (let index = 0; index < count; index += 1) {
    nextParticles.push({
      angle: randomFloat(0, Math.PI * 2),
      orbit: randomFloat(0.22, 0.96),
      speed: randomFloat(0.35, 1.15),
      alpha: randomFloat(0.28, 0.9),
      size: randomFloat(0.75, 2.9),
      wobble: randomFloat(0.2, 1.2),
      phase: randomFloat(0, Math.PI * 2),
      px: 0,
      py: 0,
    });
  }

  particles = nextParticles;
}

function ensureParticlesContext(): CanvasRenderingContext2D | null {
  if (particlesCtx) return particlesCtx;

  const canvas = particlesCanvasRef.value;
  if (!canvas) return null;

  const ctx = canvas.getContext("2d", {
    alpha: true,
    desynchronized: true,
  });
  if (!ctx) return null;

  ctx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
  particlesCtx = ctx;

  if (
    !particles.length ||
    particles.length !== qualityPreset.value.particleCount
  ) {
    buildParticles();
  }

  return particlesCtx;
}

function compileShader(
  gl: WebGLRenderingContext,
  type: number,
  source: string,
): WebGLShader | null {
  const shader = gl.createShader(type);
  if (!shader) return null;
  gl.shaderSource(shader, source);
  gl.compileShader(shader);

  const ok = gl.getShaderParameter(shader, gl.COMPILE_STATUS);
  if (ok) return shader;

  gl.deleteShader(shader);
  return null;
}

function destroyPlasmaResources(): void {
  if (!plasmaGl) {
    plasmaProgram = null;
    plasmaBuffer = null;
    plasmaAttribPosition = -1;
    plasmaUniforms = null;
    return;
  }

  if (plasmaBuffer) {
    plasmaGl.deleteBuffer(plasmaBuffer);
  }
  if (plasmaProgram) {
    plasmaGl.deleteProgram(plasmaProgram);
  }

  plasmaProgram = null;
  plasmaBuffer = null;
  plasmaAttribPosition = -1;
  plasmaUniforms = null;
  plasmaGl = null;
}

function ensurePlasmaContext(): boolean {
  if (plasmaGl && plasmaProgram) {
    return true;
  }
  if (isWebglUnavailable.value) {
    return false;
  }

  const canvas = plasmaCanvasRef.value;
  if (!canvas) return false;

  const gl = canvas.getContext("webgl", {
    alpha: true,
    antialias: true,
    premultipliedAlpha: true,
  });
  if (!gl) {
    isWebglUnavailable.value = true;
    return false;
  }

  const vertexShader = compileShader(
    gl,
    gl.VERTEX_SHADER,
    VERTEX_SHADER_SOURCE,
  );
  const fragmentShader = compileShader(
    gl,
    gl.FRAGMENT_SHADER,
    FRAGMENT_SHADER_SOURCE,
  );
  if (!vertexShader || !fragmentShader) {
    if (vertexShader) gl.deleteShader(vertexShader);
    if (fragmentShader) gl.deleteShader(fragmentShader);
    isWebglUnavailable.value = true;
    return false;
  }

  const program = gl.createProgram();
  if (!program) {
    gl.deleteShader(vertexShader);
    gl.deleteShader(fragmentShader);
    isWebglUnavailable.value = true;
    return false;
  }

  gl.attachShader(program, vertexShader);
  gl.attachShader(program, fragmentShader);
  gl.linkProgram(program);

  gl.deleteShader(vertexShader);
  gl.deleteShader(fragmentShader);

  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    gl.deleteProgram(program);
    isWebglUnavailable.value = true;
    return false;
  }

  const buffer = gl.createBuffer();
  if (!buffer) {
    gl.deleteProgram(program);
    isWebglUnavailable.value = true;
    return false;
  }

  const attribPosition = gl.getAttribLocation(program, "a_position");
  if (attribPosition < 0) {
    gl.deleteBuffer(buffer);
    gl.deleteProgram(program);
    isWebglUnavailable.value = true;
    return false;
  }

  gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
  gl.bufferData(
    gl.ARRAY_BUFFER,
    new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]),
    gl.STATIC_DRAW,
  );

  plasmaGl = gl;
  plasmaProgram = program;
  plasmaBuffer = buffer;
  plasmaAttribPosition = attribPosition;
  plasmaUniforms = {
    time: gl.getUniformLocation(program, "u_time"),
    resolution: gl.getUniformLocation(program, "u_resolution"),
    color: gl.getUniformLocation(program, "u_color"),
    power: gl.getUniformLocation(program, "u_power"),
    state: gl.getUniformLocation(program, "u_state"),
    seed: gl.getUniformLocation(program, "u_seed"),
    octaves: gl.getUniformLocation(program, "u_octaves"),
  };

  return true;
}

function renderPlasma(
  nowMs: number,
  power: number,
  stateIndex: number,
): boolean {
  const canvas = plasmaCanvasRef.value;
  if (!canvas) return false;

  const ready = ensurePlasmaContext();
  if (
    !ready ||
    !plasmaGl ||
    !plasmaProgram ||
    !plasmaBuffer ||
    !plasmaUniforms
  ) {
    return false;
  }

  plasmaGl.viewport(0, 0, canvas.width, canvas.height);
  plasmaGl.clearColor(0, 0, 0, 0);
  plasmaGl.clear(plasmaGl.COLOR_BUFFER_BIT);

  plasmaGl.useProgram(plasmaProgram);
  plasmaGl.bindBuffer(plasmaGl.ARRAY_BUFFER, plasmaBuffer);
  plasmaGl.enableVertexAttribArray(plasmaAttribPosition);
  plasmaGl.vertexAttribPointer(
    plasmaAttribPosition,
    2,
    plasmaGl.FLOAT,
    false,
    0,
    0,
  );

  const rgb = parseRgb(preset.value.color);
  const r = rgb[0] / 255;
  const g = rgb[1] / 255;
  const b = rgb[2] / 255;

  plasmaGl.uniform1f(plasmaUniforms.time, nowMs);
  plasmaGl.uniform2f(plasmaUniforms.resolution, canvas.width, canvas.height);
  plasmaGl.uniform3f(plasmaUniforms.color, r, g, b);
  plasmaGl.uniform1f(plasmaUniforms.power, clamp(power, 0, 1.6));
  plasmaGl.uniform1f(plasmaUniforms.state, stateIndex);
  plasmaGl.uniform1f(plasmaUniforms.seed, Number(preset.value.seed || 1));
  plasmaGl.uniform1f(
    plasmaUniforms.octaves,
    Number(qualityPreset.value.octaves || 4),
  );

  plasmaGl.drawArrays(plasmaGl.TRIANGLE_STRIP, 0, 4);
  return true;
}

function renderParticles(
  nowMs: number,
  dtSeconds: number,
  power: number,
  state: AgentState,
): void {
  const ctx = ensureParticlesContext();
  if (!ctx) return;

  if (particles.length !== qualityPreset.value.particleCount) {
    buildParticles();
  }

  const [r, g, b] = parseRgb(preset.value.color);
  const stateBoost =
    state === "error"
      ? 1.5
      : state === "alert"
        ? 1.28
        : state === "active"
          ? 1
          : 0.72;

  const minSize = Math.min(viewportWidth, viewportHeight);
  const cx = viewportWidth * 0.5;
  const cy = viewportHeight * 0.5;
  const maxRadius = minSize * 0.5;

  ctx.clearRect(0, 0, viewportWidth, viewportHeight);
  ctx.globalCompositeOperation = "lighter";
  ctx.lineCap = "round";

  const cometDensity =
    state === "error"
      ? 0.34
      : state === "alert"
        ? 0.24
        : clamp(0.08 + power * 0.12, 0.08, 0.2);
  const cometStride = Math.max(
    2,
    Math.round(1 / Math.max(0.001, cometDensity)),
  );

  particles.forEach((particle, index) => {
    const angularSpeed =
      dtSeconds * (0.28 + particle.speed * (0.52 + power * 0.92) * stateBoost);
    particle.angle += angularSpeed;

    const radialWave =
      Math.sin(nowMs * 0.0012 * particle.wobble + particle.phase) *
      (1.1 + stateBoost * 1.9);
    const radialShift = maxRadius * particle.orbit * (0.44 + power * 0.46);

    const x = cx + Math.cos(particle.angle + radialWave * 0.01) * radialShift;
    const y = cy + Math.sin(particle.angle + radialWave * 0.01) * radialShift;

    const particleAlpha = clamp(
      particle.alpha * (0.24 + power * 0.66),
      0.08,
      0.95,
    );
    const radius = particle.size * (0.7 + power * 0.62);

    const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius * 3.2);
    gradient.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${particleAlpha})`);
    gradient.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`);

    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(x, y, radius * 1.3, 0, Math.PI * 2);
    ctx.fill();

    if (index % cometStride === 0 && power > 0.2) {
      const trailAlpha = clamp((0.12 + power * 0.34) * stateBoost, 0.08, 0.78);
      ctx.strokeStyle = `rgba(${r}, ${g}, ${b}, ${trailAlpha})`;
      ctx.lineWidth = radius * (0.65 + power * 0.45);
      ctx.beginPath();
      ctx.moveTo(particle.px || x, particle.py || y);
      ctx.lineTo(x, y);
      ctx.stroke();
    }

    particle.px = x;
    particle.py = y;
  });

  ctx.globalCompositeOperation = "source-over";
}

function resolveRuntimeMode(nowMs: number): RuntimeModeSnapshot {
  const snapshot = fxSnapshot.value;
  const state: AgentState = snapshot.state || "idle";
  const stateIndex = resolveStateIndex(state);
  const lastAt = Number(snapshot.lastAt || 0);

  let mode = requestedFxMode.value;
  const isIdle = activitySmoothed < 0.08 && nowMs - lastAt > 8000;
  let powerCap = 1.6;

  if (!props.animated || prefersReducedMotion.value || isDocumentHidden.value) {
    mode = "off";
  } else if (mode !== "off" && isIdle) {
    if (props.idleMode === "off") {
      mode = "off";
    } else if (props.idleMode === "particles") {
      mode = "particles";
    } else if (props.idleMode === "dim-plasma" && mode === "plasma") {
      powerCap = 0.35;
    }
  }

  if (mode === "plasma" && isWebglUnavailable.value) {
    mode = "particles";
  }

  const basePower = clamp(
    preset.value.intensity + activitySmoothed * 0.6 + hoverSmoothed * 0.25,
    0,
    1.6,
  );
  const power = clamp(Math.min(basePower, powerCap), 0, 1.6);

  return {
    mode,
    power,
    state,
    stateIndex,
  };
}

function syncCanvasSize(): void {
  const host = hostRef.value;
  if (!host) return;

  const rect = host.getBoundingClientRect();
  const nextWidth = Math.max(48, Math.round(rect.width));
  const nextHeight = Math.max(48, Math.round(rect.height));
  const nextDpr = clamp(Number(window.devicePixelRatio || 1), 1, 2);

  const changed =
    nextWidth !== viewportWidth ||
    nextHeight !== viewportHeight ||
    nextDpr !== devicePixelRatio;

  viewportWidth = nextWidth;
  viewportHeight = nextHeight;
  devicePixelRatio = nextDpr;

  const plasmaCanvas = plasmaCanvasRef.value;
  const particlesCanvas = particlesCanvasRef.value;
  if (!plasmaCanvas || !particlesCanvas) return;

  [plasmaCanvas, particlesCanvas].forEach((canvas: HTMLCanvasElement) => {
    canvas.width = Math.round(viewportWidth * devicePixelRatio);
    canvas.height = Math.round(viewportHeight * devicePixelRatio);
    canvas.style.width = `${viewportWidth}px`;
    canvas.style.height = `${viewportHeight}px`;
  });

  if (particlesCtx) {
    particlesCtx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
  }

  if (plasmaGl && plasmaCanvasRef.value) {
    plasmaGl.viewport(
      0,
      0,
      plasmaCanvasRef.value.width,
      plasmaCanvasRef.value.height,
    );
  }

  if (changed) {
    buildParticles();
    clearAllLayers();
  }
}

function handleVisibilityChange(): void {
  if (typeof document === "undefined") return;
  isDocumentHidden.value = Boolean(document.hidden);
}

function step(nowMs: number): void {
  rafId = window.requestAnimationFrame(step);

  const deltaMs = lastTickMs ? nowMs - lastTickMs : 16;
  lastTickMs = nowMs;
  const dtSeconds = clamp(deltaMs / 1000, 0.001, 0.08);

  const snapshotActivity = clamp(
    Number(fxSnapshot.value.activity || 0),
    0,
    1.6,
  );
  activitySmoothed = lerp(activitySmoothed, snapshotActivity, 0.14);
  hoverSmoothed = lerp(hoverSmoothed, hoverTarget.value, 0.2);

  const runtime = resolveRuntimeMode(nowMs);
  powerSmoothed = lerp(powerSmoothed, runtime.power, 0.16);

  activeRenderMode.value = runtime.mode;
  activeState.value = runtime.state;

  const fpsLimit =
    runtime.mode === "plasma"
      ? qualityPreset.value.plasmaFps
      : runtime.mode === "particles"
        ? qualityPreset.value.particlesFps
        : 12;

  const minFrameInterval = 1000 / Math.max(1, fpsLimit);
  if (nowMs - lastDrawMs < minFrameInterval) {
    return;
  }
  lastDrawMs = nowMs;

  if (runtime.mode !== previousDrawMode) {
    clearAllLayers();
    previousDrawMode = runtime.mode;
  }

  if (runtime.mode === "off") {
    return;
  }

  if (runtime.mode === "plasma") {
    const rendered = renderPlasma(nowMs, powerSmoothed, runtime.stateIndex);
    if (rendered) return;
  }

  renderParticles(nowMs, dtSeconds, powerSmoothed, runtime.state);
}

function startLoop(): void {
  if (typeof window === "undefined") return;
  if (rafId) return;
  lastTickMs = 0;
  lastDrawMs = 0;
  rafId = window.requestAnimationFrame(step);
}

function stopLoop(): void {
  if (!rafId || typeof window === "undefined") return;
  window.cancelAnimationFrame(rafId);
  rafId = 0;
  lastTickMs = 0;
  lastDrawMs = 0;
}

function handleWindowResize(): void {
  syncCanvasSize();
}

watch(
  () => props.src,
  (nextSrc: string) => {
    imageFallbackCandidates = buildImageFallbackCandidates(nextSrc);
    imageFallbackIndex = 0;
    imageSrc.value = imageFallbackCandidates[0] || String(nextSrc || "");
  },
  { immediate: true },
);

watch(
  () => [props.size, props.quality],
  () => {
    syncCanvasSize();
  },
);

watch(
  () => props.agentId,
  () => {
    activitySmoothed = 0;
    powerSmoothed = 0;
  },
);

watch(
  () => canRunLoop.value,
  (enabled: boolean) => {
    if (enabled) {
      startLoop();
      return;
    }
    stopLoop();
    activeRenderMode.value = "off";
    clearAllLayers();
  },
  { immediate: true },
);

onMounted(() => {
  syncCanvasSize();

  if (typeof ResizeObserver !== "undefined") {
    resizeObserver = new ResizeObserver(() => {
      syncCanvasSize();
    });
    if (hostRef.value) {
      resizeObserver.observe(hostRef.value);
    }
  } else {
    window.addEventListener("resize", handleWindowResize);
    fallbackResizeAttached = true;
  }

  if (typeof document !== "undefined") {
    document.addEventListener("visibilitychange", handleVisibilityChange);
  }
});

onBeforeUnmount(() => {
  stopLoop();
  if (typeof document !== "undefined") {
    document.removeEventListener("visibilitychange", handleVisibilityChange);
  }

  if (resizeObserver) {
    resizeObserver.disconnect();
    resizeObserver = null;
  }

  if (fallbackResizeAttached) {
    window.removeEventListener("resize", handleWindowResize);
    fallbackResizeAttached = false;
  }

  destroyPlasmaResources();
  particlesCtx = null;
  particles = [];
});
</script>

<style scoped>
.agent-avatar-fx {
  --avatar-size: 160px;
  position: relative;
  width: var(--avatar-size);
  height: var(--avatar-size);
  border-radius: 999px;
  overflow: hidden;
  isolation: isolate;
  background:
    radial-gradient(
      circle at 30% 20%,
      rgba(255, 255, 255, 0.12),
      transparent 48%
    ),
    radial-gradient(
      circle at 70% 80%,
      rgba(80, 120, 180, 0.24),
      transparent 56%
    ),
    linear-gradient(170deg, rgba(6, 15, 26, 0.95), rgba(6, 13, 20, 0.92));
  border: 1px solid color-mix(in oklab, var(--border), white 12%);
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.04),
    0 10px 28px rgba(3, 11, 22, 0.38);
}

.fx-layer {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
  pointer-events: none;
  opacity: 0;
  transition: opacity 200ms ease;
}

.fx-layer.active {
  opacity: 1;
}

.fx-layer--plasma,
.fx-layer--particles {
  z-index: 1;
}

.avatar-image {
  position: absolute;
  inset: 11.5%;
  width: 77%;
  height: 77%;
  border-radius: 999px;
  object-fit: cover;
  z-index: 3;
  border: 1px solid rgba(255, 255, 255, 0.18);
  box-shadow:
    0 10px 22px rgba(1, 8, 16, 0.45),
    0 0 0 1px rgba(255, 255, 255, 0.04);
  background: rgba(5, 10, 18, 0.55);
}

.avatar-vignette {
  position: absolute;
  inset: 0;
  z-index: 4;
  pointer-events: none;
  background:
    radial-gradient(
      circle at 50% 50%,
      transparent 52%,
      rgba(1, 7, 14, 0.28) 100%
    ),
    linear-gradient(180deg, rgba(255, 255, 255, 0.1), transparent 35%);
}

.agent-avatar-fx[data-state="alert"] {
  border-color: rgba(255, 191, 108, 0.62);
}

.agent-avatar-fx[data-state="error"] {
  border-color: rgba(255, 118, 122, 0.68);
}

@media (prefers-reduced-motion: reduce) {
  .fx-layer {
    transition: none;
  }
}
</style>
