<template>
  <div ref="hostRef" class="pleiad-canvas-host">
    <canvas
      ref="canvasRef"
      class="pleiad-canvas"
      @mousemove="handlePointerMove"
      @mouseleave="handlePointerLeave"
      @click="handleCanvasClick"
    ></canvas>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

const TAU = Math.PI * 2;
type PleiadLinkKind = "info" | "action" | "warning" | "memory";

interface PleiadAgent {
  id: string;
  name: string;
  color: string;
  avatarSrc: string;
  sizeScale?: number;
  glyph?: string;
}

interface PleiadActiveLink {
  id?: string;
  trace_id: string;
  from: string;
  to: string;
  kind: PleiadLinkKind;
  importance?: number;
  createdAtMs: number;
  expiresAtMs: number;
  manual?: boolean;
}

interface PleiadFxProfile {
  mode?: string;
  glowAlpha?: number;
  linkWidthScale?: number;
  starDensity?: number;
  twinkleAmplitude?: number;
  nebulaAlpha?: number;
}

interface PleiadPrimaryTransition {
  from: string;
  to: string;
  startedAtMs: number;
  endsAtMs: number;
  durationMs: number;
}

interface CanvasLayoutNode {
  id: string;
  x: number;
  y: number;
  radius: number;
  orbitRadius: number;
  isCenter: boolean;
}

interface CanvasLayoutEmitNode {
  id: string;
  x: number;
  y: number;
  radius: number;
  isCenter: boolean;
}

interface LayoutUpdatePayload {
  width: number;
  height: number;
  nodes: CanvasLayoutEmitNode[];
}

interface HoverAgentPayload {
  id: string;
  clientX: number;
  clientY: number;
}

interface SelectAgentPayload {
  id: string;
  promote: boolean;
}

interface Star {
  x: number;
  y: number;
  radius: number;
  alpha: number;
  phase: number;
  speed: number;
}

interface CurveControlPoint {
  x: number;
  y: number;
}

interface CachedCurveShape {
  direction: number;
  factor: number;
}

interface RoleSwapTransition {
  startMs: number;
  endMs: number;
  durationMs: number;
  fromLayoutById: Map<string, CanvasLayoutNode>;
}

interface CurveCandidate {
  cpX: number;
  cpY: number;
  direction: number;
  factor: number;
  minMargin: number;
  isCollisionFree: boolean;
}

interface EvaluateCurveCandidateInput {
  sourceNode: CanvasLayoutNode;
  targetNode: CanvasLayoutNode;
  blockers: CanvasLayoutNode[];
  controlPoint: CurveControlPoint;
  clearancePadding: number;
  sampleCount?: number;
}

interface ResolveCurvedControlPointInput {
  routeKey: string;
  sourceNode: CanvasLayoutNode;
  targetNode: CanvasLayoutNode;
  fromId: string;
  toId: string;
  seed: number;
  width: number;
  baseCurvatureScale?: number;
  baseCurvatureCap?: number;
}

const KIND_COLORS: Record<PleiadLinkKind, string> = {
  info: "#6ed0f2",
  action: "#51e7b7",
  warning: "#ffbf6c",
  memory: "#a6bacc",
};

const props = withDefaults(
  defineProps<{
    agents: ReadonlyArray<PleiadAgent>;
    centerAgentId: string;
    orbitAgentIds: ReadonlyArray<string>;
    activeLinks?: PleiadActiveLink[];
    highlightedTraceId?: string;
    highlightedAgentIds?: string[];
    hoveredAgentId?: string;
    pinnedAgentId?: string;
    rotationRad?: number;
    frame?: number;
    fxProfile: PleiadFxProfile;
    avatarZoom?: number;
    primaryTransition?: PleiadPrimaryTransition | null;
    renderAgentFaces?: boolean;
  }>(),
  {
    activeLinks: () => [],
    highlightedTraceId: "",
    highlightedAgentIds: () => [],
    hoveredAgentId: "",
    pinnedAgentId: "",
    rotationRad: 0,
    frame: 0,
    avatarZoom: 1,
    primaryTransition: null,
    renderAgentFaces: true,
  },
);

const emit = defineEmits<{
  "hover-agent": [payload: HoverAgentPayload | null];
  "select-agent": [payload: SelectAgentPayload];
  "layout-update": [payload: LayoutUpdatePayload];
}>();

const canvasRef = ref<HTMLCanvasElement | null>(null);
const hostRef = ref<HTMLDivElement | null>(null);

let canvasCtx: CanvasRenderingContext2D | null = null;
let resizeObserver: ResizeObserver | null = null;
let fallbackResizeAttached = false;
let viewportWidth = 0;
let viewportHeight = 0;
let stars: Star[] = [];
let layoutNodes: CanvasLayoutNode[] = [];
let layoutById = new Map<string, CanvasLayoutNode>();
let activityBoostByAgentId = new Map<string, number>();
let lastHoverAgentId = "";
let lastRoleSignature = "";
let roleSwapTransition: RoleSwapTransition | null = null;
let lastLayoutEmitMs = 0;
let linkCurveCache = new Map<string, CachedCurveShape>();
const avatarImageByAgentId = new Map<string, HTMLImageElement | null>();

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function toRgba(hex: string, alpha = 1): string {
  const normalized = String(hex || "")
    .replace("#", "")
    .trim();
  if (normalized.length !== 6) return `rgba(132, 180, 208, ${alpha})`;
  const r = Number.parseInt(normalized.slice(0, 2), 16);
  const g = Number.parseInt(normalized.slice(2, 4), 16);
  const b = Number.parseInt(normalized.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function hashString(value: unknown): number {
  let hash = 0;
  const text = String(value || "");
  for (let index = 0; index < text.length; index += 1) {
    hash = (hash << 5) - hash + text.charCodeAt(index);
    hash |= 0;
  }
  return Math.abs(hash);
}

function lerp(from: number, to: number, progress: number): number {
  return from + (to - from) * progress;
}

function easeInOutCubic(progress: number): number {
  const clamped = clamp(progress, 0, 1);
  if (clamped < 0.5) {
    return 4 * clamped * clamped * clamped;
  }
  return 1 - Math.pow(-2 * clamped + 2, 3) / 2;
}

function cloneLayoutMap(
  layoutMap: Map<string, CanvasLayoutNode>,
): Map<string, CanvasLayoutNode> {
  const clone = new Map<string, CanvasLayoutNode>();
  for (const [agentId, node] of layoutMap.entries()) {
    clone.set(agentId, {
      id: node.id,
      x: Number(node.x || 0),
      y: Number(node.y || 0),
      radius: Number(node.radius || 0),
      orbitRadius: Number(node.orbitRadius || 0),
      isCenter: Boolean(node.isCenter),
    });
  }
  return clone;
}

function resolveRoleSignature(): string {
  const orbitSignature = Array.isArray(props.orbitAgentIds)
    ? props.orbitAgentIds.join("|")
    : "";
  return `${String(props.centerAgentId || "")}|${orbitSignature}`;
}

function targetStarCount(width: number, height: number): number {
  const areaFactor = (width * height) / 240000;
  const density = clamp(Number(props.fxProfile?.starDensity || 1), 0.25, 1.25);
  return clamp(Math.round(140 * areaFactor * density), 34, 260);
}

function rebuildStars(): void {
  if (!viewportWidth || !viewportHeight) {
    stars = [];
    return;
  }
  const count = targetStarCount(viewportWidth, viewportHeight);
  stars = Array.from({ length: count }, () => ({
    x: Math.random() * viewportWidth,
    y: Math.random() * viewportHeight,
    radius: randomFloat(0.4, 2.1),
    alpha: randomFloat(0.18, 0.86),
    phase: Math.random() * TAU,
    speed: randomFloat(0.0002, 0.0011),
  }));
}

function randomFloat(min: number, max: number): number {
  return min + Math.random() * (max - min);
}

function drawImageCover(
  ctx: CanvasRenderingContext2D,
  image: HTMLImageElement,
  x: number,
  y: number,
  size: number,
): void {
  const safeSize = Math.max(1, Number(size || 0));
  const imageWidth = Math.max(1, Number(image?.naturalWidth || 1));
  const imageHeight = Math.max(1, Number(image?.naturalHeight || 1));
  const imageAspect = imageWidth / imageHeight;
  const boxAspect = 1;

  let drawWidth = safeSize;
  let drawHeight = safeSize;
  if (imageAspect > boxAspect) {
    drawWidth = safeSize * imageAspect;
    drawHeight = safeSize;
  } else {
    drawWidth = safeSize;
    drawHeight = safeSize / imageAspect;
  }

  ctx.drawImage(
    image,
    x - drawWidth / 2,
    y - drawHeight / 2,
    drawWidth,
    drawHeight,
  );
}

function resolveAvatarCandidates(rawSrc: unknown): string[] {
  const src = String(rawSrc || "").trim();
  if (!src) return [];

  const slashIndex = src.lastIndexOf("/");
  const lowerVariant = (() => {
    if (slashIndex < 0) return src.toLowerCase();
    const dir = src.slice(0, slashIndex + 1);
    const filename = src.slice(slashIndex + 1);
    return `${dir}${filename.toLowerCase()}`;
  })();

  const swapExt = (value: unknown, nextExt: string): string => {
    const text = String(value || "").trim();
    if (!text) return "";
    const matched = text.match(/^([^?#]+)([?#].*)?$/);
    if (!matched) return "";
    const pathname = matched[1] || "";
    const suffix = matched[2] || "";
    if (!/\.(webp|png)$/i.test(pathname)) return "";
    const replaced = pathname.replace(/\.(webp|png)$/i, `.${nextExt}`);
    if (replaced === pathname) return "";
    return `${replaced}${suffix}`;
  };

  const isWebp = /\.webp([?#].*)?$/i.test(src);
  const nextExt = isWebp ? "png" : "webp";
  const candidates: string[] = [];
  const append = (value: unknown): void => {
    const normalized = String(value || "").trim();
    if (!normalized || candidates.includes(normalized)) return;
    candidates.push(normalized);
  };

  append(src);
  append(lowerVariant);
  append(swapExt(src, nextExt));
  append(swapExt(lowerVariant, nextExt));
  return candidates;
}

function preloadAgentAvatars(): void {
  if (props.renderAgentFaces === false) {
    avatarImageByAgentId.clear();
    return;
  }
  for (const agent of props.agents) {
    const agentId = String(agent?.id || "");
    const src = String(agent?.avatarSrc || "");
    if (!agentId || !src || avatarImageByAgentId.has(agentId)) continue;

    const image = new Image();
    image.decoding = "async";
    const candidates = resolveAvatarCandidates(src);
    let candidateIndex = 0;

    function loadNextCandidate(): void {
      if (candidateIndex >= candidates.length) {
        avatarImageByAgentId.set(agentId, null);
        drawScene();
        return;
      }
      const nextCandidate = candidates[candidateIndex];
      if (!nextCandidate) {
        avatarImageByAgentId.set(agentId, null);
        drawScene();
        return;
      }
      image.src = nextCandidate;
      candidateIndex += 1;
    }

    image.onload = () => {
      drawScene();
    };
    image.onerror = () => {
      loadNextCandidate();
    };
    avatarImageByAgentId.set(agentId, image);
    loadNextCandidate();
  }
}

function computeLayout(
  width: number,
  height: number,
): Map<string, CanvasLayoutNode> {
  const nextMap = new Map<string, CanvasLayoutNode>();
  const agentById = new Map(
    props.agents.map((agent) => [String(agent?.id || ""), agent]),
  );
  const minSize = Math.min(width, height);
  const zoom = clamp(Number(props.avatarZoom || 1), 0.65, 2.2);
  const centerAgent = agentById.get(props.centerAgentId);
  const centerScale = clamp(Number(centerAgent?.sizeScale || 1), 0.75, 1.45);
  const centerRadius = clamp(minSize * 0.08 * centerScale * zoom, 40, 128);
  const orbitNodeRadiusBase = clamp(minSize * 0.041 * zoom, 22, 56);
  const orbitRadii = props.orbitAgentIds.map((agentId) => {
    const agent = agentById.get(String(agentId || ""));
    const scale = clamp(Number(agent?.sizeScale || 1), 0.75, 1.45);
    return orbitNodeRadiusBase * scale;
  });
  const maxOrbitNodeRadius = orbitRadii.length
    ? Math.max(...orbitRadii)
    : orbitNodeRadiusBase;
  const orbitRadius = clamp(
    minSize * 0.38,
    centerRadius + maxOrbitNodeRadius + 56,
    minSize * 0.58,
  );

  const cx = width * 0.5;
  const cy = height * 0.5;
  nextMap.set(props.centerAgentId, {
    id: props.centerAgentId,
    x: cx,
    y: cy,
    radius: centerRadius,
    orbitRadius,
    isCenter: true,
  });

  const orbitCount = Math.max(1, props.orbitAgentIds.length);
  for (let index = 0; index < orbitCount; index += 1) {
    const agentId = props.orbitAgentIds[index];
    const angle = props.rotationRad + (index / orbitCount) * TAU;
    nextMap.set(agentId, {
      id: agentId,
      x: cx + Math.cos(angle) * orbitRadius,
      y: cy + Math.sin(angle) * orbitRadius,
      radius: orbitRadii[index] || orbitNodeRadiusBase,
      orbitRadius,
      isCenter: false,
    });
  }

  return nextMap;
}

function resolveAnimatedLayout(
  targetLayoutById: Map<string, CanvasLayoutNode>,
  nowMs: number,
): Map<string, CanvasLayoutNode> {
  const roleSignature = resolveRoleSignature();
  if (!lastRoleSignature) {
    lastRoleSignature = roleSignature;
    roleSwapTransition = null;
    return targetLayoutById;
  }

  if (roleSignature !== lastRoleSignature) {
    const fromLayoutById = layoutById.size
      ? cloneLayoutMap(layoutById)
      : cloneLayoutMap(targetLayoutById);
    const preferredDuration = Number(
      props.primaryTransition?.durationMs || 1080,
    );
    const durationMs = clamp(preferredDuration, 260, 2600);
    roleSwapTransition = {
      startMs: nowMs,
      endMs: nowMs + durationMs,
      durationMs,
      fromLayoutById,
    };
    lastRoleSignature = roleSignature;
  }

  if (!roleSwapTransition) {
    return targetLayoutById;
  }

  const durationMs = Math.max(1, Number(roleSwapTransition.durationMs || 1));
  const progress = clamp(
    (nowMs - roleSwapTransition.startMs) / durationMs,
    0,
    1,
  );
  const eased = easeInOutCubic(progress);
  const animated = new Map<string, CanvasLayoutNode>();

  for (const [agentId, targetNode] of targetLayoutById.entries()) {
    const fromNode =
      roleSwapTransition.fromLayoutById.get(agentId) || targetNode;
    animated.set(agentId, {
      ...targetNode,
      x: lerp(fromNode.x, targetNode.x, eased),
      y: lerp(fromNode.y, targetNode.y, eased),
      radius: lerp(fromNode.radius, targetNode.radius, eased),
      orbitRadius: lerp(fromNode.orbitRadius, targetNode.orbitRadius, eased),
    });
  }

  if (progress >= 1) {
    roleSwapTransition = null;
    return targetLayoutById;
  }

  return animated;
}

function drawBackground(
  ctx: CanvasRenderingContext2D,
  nowMs: number,
  width: number,
  height: number,
): void {
  const base = ctx.createLinearGradient(0, 0, width, height);
  base.addColorStop(0, "#02060d");
  base.addColorStop(0.45, "#05131c");
  base.addColorStop(1, "#030c14");
  ctx.fillStyle = base;
  ctx.fillRect(0, 0, width, height);

  const nebulaAlpha = clamp(
    Number(props.fxProfile?.nebulaAlpha || 0.12),
    0,
    0.35,
  );
  const pulse = Math.sin(nowMs * 0.00008) * 0.5 + 0.5;

  const fogLeft = ctx.createRadialGradient(
    width * 0.18,
    height * 0.2,
    width * 0.02,
    width * 0.18,
    height * 0.2,
    width * 0.56,
  );
  fogLeft.addColorStop(
    0,
    `rgba(46, 157, 168, ${nebulaAlpha * (0.48 + pulse * 0.2)})`,
  );
  fogLeft.addColorStop(1, "rgba(4, 10, 18, 0)");
  ctx.fillStyle = fogLeft;
  ctx.fillRect(0, 0, width, height);

  const fogRight = ctx.createRadialGradient(
    width * 0.84,
    height * 0.78,
    width * 0.04,
    width * 0.84,
    height * 0.78,
    width * 0.54,
  );
  fogRight.addColorStop(0, `rgba(26, 140, 131, ${nebulaAlpha * 0.72})`);
  fogRight.addColorStop(1, "rgba(4, 10, 18, 0)");
  ctx.fillStyle = fogRight;
  ctx.fillRect(0, 0, width, height);
}

function drawStars(ctx: CanvasRenderingContext2D, nowMs: number): void {
  const twinkle = clamp(Number(props.fxProfile?.twinkleAmplitude || 0), 0, 1);
  for (const star of stars) {
    const pulse = twinkle
      ? 1 + Math.sin(star.phase + nowMs * star.speed) * twinkle
      : 1;
    const alpha = clamp(star.alpha * pulse, 0.04, 0.96);
    ctx.beginPath();
    ctx.fillStyle = `rgba(214, 237, 248, ${alpha})`;
    ctx.arc(star.x, star.y, star.radius, 0, TAU);
    ctx.fill();
  }
}

function drawOrbitGuide(ctx: CanvasRenderingContext2D): void {
  if (props.renderAgentFaces === false) return;
  const centerNode = layoutById.get(props.centerAgentId);
  if (!centerNode) return;
  ctx.save();
  ctx.beginPath();
  ctx.arc(centerNode.x, centerNode.y, centerNode.orbitRadius, 0, TAU);
  ctx.strokeStyle = "rgba(132, 170, 188, 0.2)";
  ctx.lineWidth = 1;
  ctx.setLineDash([4, 9]);
  ctx.stroke();
  ctx.setLineDash([]);
  ctx.restore();
}

function resolveCommunicationBoostMap(nowMs: number): Map<string, number> {
  const boostMap = new Map<string, number>();
  for (const link of props.activeLinks) {
    const expiresAtMs = Number(link?.expiresAtMs || 0);
    if (!Number.isFinite(expiresAtMs) || expiresAtMs <= nowMs) continue;
    const createdAtMs = Number(link?.createdAtMs || nowMs - 1);
    const duration = Math.max(1, expiresAtMs - createdAtMs);
    const life = clamp((expiresAtMs - nowMs) / duration, 0, 1);
    const importance = clamp(Number(link?.importance || 0.45), 0, 1);
    const weight = (0.18 + importance * 0.62) * (0.35 + life * 0.65);
    const deltaBoost = weight * 0.13;

    for (const agentId of [String(link?.from || ""), String(link?.to || "")]) {
      if (!agentId) continue;
      const prev = Number(boostMap.get(agentId) || 0);
      boostMap.set(agentId, clamp(prev + deltaBoost, 0, 0.16));
    }
  }
  return boostMap;
}

function resolveEffectiveNodeRadius(node: CanvasLayoutNode): number {
  const boost = Number(activityBoostByAgentId.get(node?.id) || 0);
  return Math.max(0, Number(node?.radius || 0)) * (1 + boost);
}

function sampleQuadraticPoint(
  sourceNode: CanvasLayoutNode,
  controlPoint: CurveControlPoint,
  targetNode: CanvasLayoutNode,
  t: number,
): CurveControlPoint {
  const oneMinusT = 1 - t;
  const x =
    oneMinusT * oneMinusT * sourceNode.x +
    2 * oneMinusT * t * controlPoint.x +
    t * t * targetNode.x;
  const y =
    oneMinusT * oneMinusT * sourceNode.y +
    2 * oneMinusT * t * controlPoint.y +
    t * t * targetNode.y;
  return { x, y };
}

function evaluateCurveCandidate({
  sourceNode,
  targetNode,
  blockers,
  controlPoint,
  clearancePadding,
  sampleCount = 16,
}: EvaluateCurveCandidateInput): {
  minMargin: number;
  isCollisionFree: boolean;
} {
  let minMargin = Number.POSITIVE_INFINITY;

  for (const blocker of blockers) {
    const blockerRadius =
      resolveEffectiveNodeRadius(blocker) + clearancePadding;
    let blockerMinMargin = Number.POSITIVE_INFINITY;
    for (let sampleIndex = 1; sampleIndex < sampleCount; sampleIndex += 1) {
      const t = sampleIndex / sampleCount;
      const point = sampleQuadraticPoint(
        sourceNode,
        controlPoint,
        targetNode,
        t,
      );
      const distance = Math.hypot(point.x - blocker.x, point.y - blocker.y);
      const margin = distance - blockerRadius;
      if (margin < blockerMinMargin) {
        blockerMinMargin = margin;
      }
      if (blockerMinMargin < -clearancePadding * 0.85) {
        break;
      }
    }
    if (blockerMinMargin < minMargin) {
      minMargin = blockerMinMargin;
    }
    if (minMargin < -clearancePadding * 0.85) {
      return { minMargin, isCollisionFree: false };
    }
  }

  return { minMargin, isCollisionFree: minMargin > 0 };
}

function resolveCurvedControlPoint({
  routeKey,
  sourceNode,
  targetNode,
  fromId,
  toId,
  seed,
  width,
  baseCurvatureScale = 0.24,
  baseCurvatureCap = 116,
}: ResolveCurvedControlPointInput): { cpX: number; cpY: number } {
  const dx = targetNode.x - sourceNode.x;
  const dy = targetNode.y - sourceNode.y;
  const distance = Math.max(1, Math.hypot(dx, dy));
  const nx = -dy / distance;
  const ny = dx / distance;
  const midpointX = (sourceNode.x + targetNode.x) * 0.5;
  const midpointY = (sourceNode.y + targetNode.y) * 0.5;
  const baseCurvature = Math.min(
    baseCurvatureCap,
    distance * baseCurvatureScale + (seed % 27),
  );

  const blockers = layoutNodes.filter(
    (node) => node.id !== fromId && node.id !== toId,
  );
  if (!blockers.length || baseCurvature <= 0.01) {
    const bendDirection = seed % 2 === 0 ? 1 : -1;
    return {
      cpX: midpointX + nx * baseCurvature * bendDirection,
      cpY: midpointY + ny * baseCurvature * bendDirection,
    };
  }

  const clearancePadding = 9 + width * 0.58;
  const curvatureFactors = [1, 1.18, 1.36, 1.58, 1.84, 2.14, 2.46];
  const preferredDirection = seed % 2 === 0 ? 1 : -1;
  const directionOrder = [preferredDirection, -preferredDirection];

  const cached = routeKey ? linkCurveCache.get(routeKey) : null;
  const candidateQueue: Array<{ direction: number; factor: number }> = [];
  if (
    cached &&
    Number.isFinite(cached.direction) &&
    Number.isFinite(cached.factor)
  ) {
    candidateQueue.push({
      direction: cached.direction > 0 ? 1 : -1,
      factor: clamp(cached.factor, 1, 2.6),
    });
  }

  for (const direction of directionOrder) {
    for (const factor of curvatureFactors) {
      if (
        candidateQueue.some(
          (candidate) =>
            candidate.direction === direction && candidate.factor === factor,
        )
      ) {
        continue;
      }
      candidateQueue.push({ direction, factor });
    }
  }

  let bestCandidate: CurveCandidate | null = null;
  let firstCandidate: CurveCandidate | null = null;

  for (const candidate of candidateQueue) {
    const cpX =
      midpointX + nx * baseCurvature * candidate.factor * candidate.direction;
    const cpY =
      midpointY + ny * baseCurvature * candidate.factor * candidate.direction;
    const evaluated = evaluateCurveCandidate({
      sourceNode,
      targetNode,
      blockers,
      controlPoint: { x: cpX, y: cpY },
      clearancePadding,
    });
    const candidateResult = {
      cpX,
      cpY,
      direction: candidate.direction,
      factor: candidate.factor,
      minMargin: evaluated.minMargin,
      isCollisionFree: evaluated.isCollisionFree,
    };

    if (!firstCandidate) {
      firstCandidate = candidateResult;
    }
    if (!bestCandidate || candidateResult.minMargin > bestCandidate.minMargin) {
      bestCandidate = candidateResult;
    }
    if (candidateResult.isCollisionFree) {
      if (routeKey) {
        linkCurveCache.set(routeKey, {
          direction: candidateResult.direction,
          factor: candidateResult.factor,
        });
      }
      return { cpX: candidateResult.cpX, cpY: candidateResult.cpY };
    }
  }

  const fallback = bestCandidate || firstCandidate;
  if (routeKey && fallback) {
    linkCurveCache.set(routeKey, {
      direction: fallback.direction,
      factor: fallback.factor,
    });
  }
  if (fallback) {
    return { cpX: fallback.cpX, cpY: fallback.cpY };
  }

  const bendDirection = preferredDirection;
  return {
    cpX: midpointX + nx * baseCurvature * bendDirection,
    cpY: midpointY + ny * baseCurvature * bendDirection,
  };
}

function drawLinks(ctx: CanvasRenderingContext2D, nowMs: number): void {
  const glowAlpha = clamp(Number(props.fxProfile?.glowAlpha || 0), 0, 1);
  const widthScale = clamp(
    Number(props.fxProfile?.linkWidthScale || 1),
    0.4,
    1.35,
  );
  const activeRouteKeys = new Set<string>();

  for (let index = props.activeLinks.length - 1; index >= 0; index -= 1) {
    const link = props.activeLinks[index];
    const sourceNode = layoutById.get(link.from);
    const targetNode = layoutById.get(link.to);
    if (!sourceNode || !targetNode) continue;

    const duration = Math.max(
      1,
      Number(link.expiresAtMs) - Number(link.createdAtMs),
    );
    const remaining = Number(link.expiresAtMs) - nowMs;
    if (remaining <= 0) continue;

    const life = clamp(remaining / duration, 0, 1);
    const color = KIND_COLORS[link.kind] || KIND_COLORS.info;
    const importance = clamp(Number(link.importance || 0.4), 0, 1);
    const highlighted =
      Boolean(props.highlightedTraceId) &&
      props.highlightedTraceId === link.trace_id;

    const baseAlpha = (0.1 + life * 0.8) * (0.4 + importance * 0.6);
    const strokeAlpha = highlighted ? 0.98 : clamp(baseAlpha, 0.05, 0.94);
    const width =
      (0.8 + importance * 2.4) *
      widthScale *
      (highlighted ? 1.35 : link.manual ? 1.2 : 1);

    const seed = hashString(`${link.from}:${link.to}`);
    const routeKey = String(
      link.id || link.trace_id || `${link.from}:${link.to}`,
    );
    activeRouteKeys.add(routeKey);
    const controlPoint = resolveCurvedControlPoint({
      routeKey,
      sourceNode,
      targetNode,
      fromId: String(link.from || ""),
      toId: String(link.to || ""),
      seed,
      width,
      baseCurvatureScale: 0.24,
      baseCurvatureCap: 126,
    });

    ctx.save();
    ctx.beginPath();
    ctx.moveTo(sourceNode.x, sourceNode.y);
    ctx.quadraticCurveTo(
      controlPoint.cpX,
      controlPoint.cpY,
      targetNode.x,
      targetNode.y,
    );
    ctx.lineWidth = width;
    ctx.strokeStyle = toRgba(color, strokeAlpha);
    if (glowAlpha > 0) {
      const glowStrength = highlighted ? 18 : 10 + importance * 12;
      ctx.shadowBlur = glowStrength * glowAlpha;
      ctx.shadowColor = toRgba(color, 0.86 * glowAlpha);
    } else {
      ctx.shadowBlur = 0;
    }
    ctx.stroke();
    ctx.restore();
  }

  if (linkCurveCache.size) {
    for (const key of linkCurveCache.keys()) {
      if (activeRouteKeys.has(key)) continue;
      linkCurveCache.delete(key);
    }
  }
}

function drawPrimaryTransition(
  ctx: CanvasRenderingContext2D,
  nowMs: number,
): void {
  const transition = props.primaryTransition;
  if (!transition || typeof transition !== "object") return;

  const fromAgentId = String(transition.from || "");
  const toAgentId = String(transition.to || "");
  if (!fromAgentId || !toAgentId || fromAgentId === toAgentId) return;

  const startMs = Number(transition.startedAtMs || 0);
  const fallbackDuration = Math.max(1, Number(transition.durationMs || 1));
  const endMs = Number(transition.endsAtMs || startMs + fallbackDuration);
  const durationMs = Math.max(1, endMs - startMs || fallbackDuration);
  const progress = clamp((nowMs - startMs) / durationMs, 0, 1);
  if (progress >= 1) return;

  const fromNode = layoutById.get(fromAgentId);
  const toNode = layoutById.get(toAgentId);
  if (!fromNode || !toNode) return;

  const glowAlpha = clamp(Number(props.fxProfile?.glowAlpha || 0.6), 0.15, 1);
  const eased = easeInOutCubic(progress);
  const fadeOut = clamp(1 - progress, 0, 1);
  const color = "#90ced6";

  const seed = hashString(`handoff:${fromAgentId}:${toAgentId}`);
  const controlPoint = resolveCurvedControlPoint({
    routeKey: `handoff:${fromAgentId}:${toAgentId}`,
    sourceNode: fromNode,
    targetNode: toNode,
    fromId: fromAgentId,
    toId: toAgentId,
    seed,
    width: 2.4,
    baseCurvatureScale: 0.26,
    baseCurvatureCap: 182,
  });

  ctx.save();

  ctx.beginPath();
  ctx.moveTo(fromNode.x, fromNode.y);
  ctx.quadraticCurveTo(controlPoint.cpX, controlPoint.cpY, toNode.x, toNode.y);
  ctx.setLineDash([6, 8]);
  ctx.lineDashOffset = -eased * 30;
  ctx.lineWidth = 1.1 + fadeOut * 1.5;
  ctx.strokeStyle = toRgba(color, 0.18 + fadeOut * 0.44);
  ctx.stroke();
  ctx.setLineDash([]);

  ctx.beginPath();
  ctx.arc(fromNode.x, fromNode.y, fromNode.radius + 8 + eased * 14, 0, TAU);
  ctx.lineWidth = 1.2;
  ctx.strokeStyle = toRgba(color, (0.2 + fadeOut * 0.3) * glowAlpha);
  ctx.stroke();

  ctx.beginPath();
  ctx.arc(toNode.x, toNode.y, toNode.radius + 9 + eased * 18, 0, TAU);
  ctx.lineWidth = 1.35 + (1 - eased) * 0.7;
  ctx.shadowBlur = (8 + fadeOut * 22) * glowAlpha;
  ctx.shadowColor = toRgba(color, 0.84 * glowAlpha);
  ctx.strokeStyle = toRgba(color, (0.34 + fadeOut * 0.48) * glowAlpha);
  ctx.stroke();

  ctx.restore();
}

function drawAgentNode(
  ctx: CanvasRenderingContext2D,
  agent: PleiadAgent,
  node: CanvasLayoutNode,
): void {
  const shouldRenderFaces = props.renderAgentFaces !== false;
  if (!shouldRenderFaces) return;

  const highlightedSet = new Set(props.highlightedAgentIds);
  const isHovered = props.hoveredAgentId === agent.id;
  const isPinned = props.pinnedAgentId === agent.id;
  const isHighlighted = highlightedSet.has(agent.id);
  const hasPin = Boolean(props.pinnedAgentId);
  const isDimmed = hasPin && !isPinned && !isHighlighted;
  const communicationBoost = Number(activityBoostByAgentId.get(agent.id) || 0);

  const glowAlpha = clamp(Number(props.fxProfile?.glowAlpha || 0), 0, 1);
  const interactionBoost = isHovered
    ? 1.18
    : isPinned
      ? 1.08
      : isHighlighted
        ? 1.04
        : 1;
  const ringBoost = interactionBoost * (1 + communicationBoost * 0.45);
  const radius = node.radius * (1 + communicationBoost);
  const ringRadius = radius + (isHovered || isPinned || isHighlighted ? 5 : 3);
  const avatarRadius = Math.max(6, radius * 0.88);
  const avatarImage = avatarImageByAgentId.get(agent.id);
  const hasAvatar = Boolean(
    avatarImage &&
      avatarImage.complete &&
      Number(avatarImage.naturalWidth || 0) > 0 &&
      Number(avatarImage.naturalHeight || 0) > 0,
  );

  ctx.save();
  ctx.globalAlpha = isDimmed ? 0.45 : 1;

  if (glowAlpha > 0) {
    ctx.shadowBlur = (8 + radius * 0.8) * glowAlpha * ringBoost;
    ctx.shadowColor = toRgba(agent.color, 0.72 * glowAlpha);
  }

  ctx.fillStyle = "rgba(7, 16, 26, 0.96)";
  ctx.beginPath();
  ctx.arc(node.x, node.y, radius, 0, TAU);
  ctx.fill();

  if (hasAvatar && avatarImage) {
    ctx.save();
    ctx.beginPath();
    ctx.arc(node.x, node.y, avatarRadius, 0, TAU);
    ctx.clip();
    drawImageCover(ctx, avatarImage, node.x, node.y, avatarRadius * 2);

    const shade = ctx.createLinearGradient(
      node.x,
      node.y - avatarRadius,
      node.x,
      node.y + avatarRadius,
    );
    shade.addColorStop(0, "rgba(230, 244, 250, 0.18)");
    shade.addColorStop(0.46, "rgba(10, 19, 31, 0)");
    shade.addColorStop(1, "rgba(7, 14, 24, 0.3)");
    ctx.fillStyle = shade;
    ctx.fillRect(
      node.x - avatarRadius,
      node.y - avatarRadius,
      avatarRadius * 2,
      avatarRadius * 2,
    );
    ctx.restore();
  } else {
    const gradient = ctx.createRadialGradient(
      node.x - radius * 0.3,
      node.y - radius * 0.35,
      radius * 0.2,
      node.x,
      node.y,
      radius,
    );
    gradient.addColorStop(0, "rgba(228, 243, 247, 0.94)");
    gradient.addColorStop(0.28, toRgba(agent.color, 0.9));
    gradient.addColorStop(1, "rgba(10, 17, 29, 0.95)");
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(node.x, node.y, avatarRadius, 0, TAU);
    ctx.fill();
  }

  ctx.strokeStyle = toRgba(agent.color, isHovered ? 0.98 : 0.64);
  ctx.lineWidth = isHovered ? 2.4 : 1.4;
  ctx.beginPath();
  ctx.arc(node.x, node.y, avatarRadius, 0, TAU);
  ctx.stroke();

  ctx.shadowBlur = 0;
  ctx.strokeStyle = toRgba(agent.color, isHovered || isPinned ? 0.78 : 0.32);
  ctx.lineWidth = isHovered || isPinned ? 1.8 : 1;
  ctx.beginPath();
  ctx.arc(node.x, node.y, ringRadius, 0, TAU);
  ctx.stroke();

  if (!hasAvatar) {
    ctx.fillStyle = "rgba(231, 239, 246, 0.92)";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.font = `${Math.round(radius * 0.62)}px "Space Grotesk", "Segoe UI", sans-serif`;
    ctx.fillText(
      String(agent.glyph || agent.id.slice(0, 2)),
      node.x,
      node.y + 0.5,
    );
  }

  const labelY = node.y + radius + (node.isCenter ? 19 : 14);
  ctx.textBaseline = "alphabetic";
  ctx.font = `${node.isCenter ? 13 : 11.2}px "Space Grotesk", "Segoe UI", sans-serif`;
  ctx.fillStyle = isDimmed
    ? "rgba(157, 179, 197, 0.42)"
    : "rgba(205, 220, 233, 0.9)";
  ctx.fillText(agent.name, node.x, labelY);
  ctx.restore();
}

function emitLayoutUpdate(nowMs: number): void {
  if (nowMs - lastLayoutEmitMs < 34) return;
  lastLayoutEmitMs = nowMs;
  const nodes: CanvasLayoutEmitNode[] = layoutNodes.map((node) => {
    return {
      id: node.id,
      x: node.x,
      y: node.y,
      radius: node.radius,
      isCenter: Boolean(node.isCenter),
    };
  });

  emit("layout-update", {
    width: viewportWidth,
    height: viewportHeight,
    nodes,
  });
}

function drawAgents(ctx: CanvasRenderingContext2D): void {
  const centerAgent = props.agents.find(
    (agent) => agent.id === props.centerAgentId,
  );
  if (centerAgent) {
    const node = layoutById.get(centerAgent.id);
    if (node) {
      drawAgentNode(ctx, centerAgent, node);
    }
  }

  for (const orbitAgentId of props.orbitAgentIds) {
    const agent = props.agents.find((item) => item.id === orbitAgentId);
    if (!agent) continue;
    const node = layoutById.get(agent.id);
    if (!node) continue;
    drawAgentNode(ctx, agent, node);
  }
}

function drawScene(): void {
  if (!canvasCtx || !viewportWidth || !viewportHeight) return;
  const nowMs = Number(props.frame || performance.now());
  canvasCtx.clearRect(0, 0, viewportWidth, viewportHeight);

  drawBackground(canvasCtx, nowMs, viewportWidth, viewportHeight);
  drawStars(canvasCtx, nowMs);

  const targetLayoutById = computeLayout(viewportWidth, viewportHeight);
  layoutById = resolveAnimatedLayout(targetLayoutById, nowMs);
  layoutNodes = [...layoutById.values()];
  activityBoostByAgentId = resolveCommunicationBoostMap(nowMs);

  drawOrbitGuide(canvasCtx);
  drawLinks(canvasCtx, nowMs);
  drawPrimaryTransition(canvasCtx, nowMs);
  drawAgents(canvasCtx);
  emitLayoutUpdate(nowMs);
}

function syncCanvasSize(): void {
  const host = hostRef.value;
  const canvas = canvasRef.value;
  if (!host || !canvas) return;

  const rect = host.getBoundingClientRect();
  const nextWidth = Math.max(120, Math.round(rect.width));
  const nextHeight = Math.max(120, Math.round(rect.height));
  const dpr = Math.max(1, Math.min(2, globalThis.devicePixelRatio || 1));
  const changed = nextWidth !== viewportWidth || nextHeight !== viewportHeight;

  viewportWidth = nextWidth;
  viewportHeight = nextHeight;
  canvas.width = Math.round(nextWidth * dpr);
  canvas.height = Math.round(nextHeight * dpr);
  canvas.style.width = `${nextWidth}px`;
  canvas.style.height = `${nextHeight}px`;

  canvasCtx = canvas.getContext("2d");
  if (!canvasCtx) return;
  canvasCtx.setTransform(dpr, 0, 0, dpr, 0, 0);

  if (changed || !stars.length) {
    rebuildStars();
  }
  drawScene();
}

function resolvePointerPoint(
  event: MouseEvent,
): { x: number; y: number } | null {
  const canvas = canvasRef.value;
  if (!canvas) return null;
  const rect = canvas.getBoundingClientRect();
  return {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top,
  };
}

function findHitNode(x: number, y: number): CanvasLayoutNode | null {
  if (!layoutNodes.length) return null;
  for (let index = layoutNodes.length - 1; index >= 0; index -= 1) {
    const node = layoutNodes[index];
    const communicationBoost = Number(activityBoostByAgentId.get(node.id) || 0);
    const interactiveRadius = node.radius * (1 + communicationBoost) + 7;
    const distance = Math.hypot(x - node.x, y - node.y);
    if (distance <= interactiveRadius) {
      return node;
    }
  }
  return null;
}

function handlePointerMove(event: MouseEvent): void {
  const point = resolvePointerPoint(event);
  if (!point) return;
  const hitNode = findHitNode(point.x, point.y);
  const canvas = canvasRef.value;
  if (!canvas) return;

  if (hitNode) {
    canvas.style.cursor = "pointer";
    lastHoverAgentId = hitNode.id;
    emit("hover-agent", {
      id: hitNode.id,
      clientX: event.clientX,
      clientY: event.clientY,
    });
    return;
  }

  canvas.style.cursor = "default";
  if (lastHoverAgentId) {
    lastHoverAgentId = "";
    emit("hover-agent", null);
  }
}

function handlePointerLeave(): void {
  const canvas = canvasRef.value;
  if (canvas) {
    canvas.style.cursor = "default";
  }
  if (!lastHoverAgentId) return;
  lastHoverAgentId = "";
  emit("hover-agent", null);
}

function handleCanvasClick(event: MouseEvent): void {
  const point = resolvePointerPoint(event);
  if (!point) return;
  const hitNode = findHitNode(point.x, point.y);
  if (!hitNode) return;
  emit("select-agent", {
    id: hitNode.id,
    promote: Boolean(event.shiftKey || event.altKey),
  });
}

function handleWindowResize(): void {
  syncCanvasSize();
}

onMounted(() => {
  preloadAgentAvatars();
  syncCanvasSize();
  if ("ResizeObserver" in globalThis) {
    resizeObserver = new globalThis.ResizeObserver(() => {
      syncCanvasSize();
    });
    if (hostRef.value) {
      resizeObserver.observe(hostRef.value);
    }
  } else {
    window.addEventListener("resize", handleWindowResize);
    fallbackResizeAttached = true;
  }
});

watch(
  () => props.frame,
  () => {
    drawScene();
  },
  { immediate: true },
);

watch(
  () => [props.fxProfile.starDensity, props.fxProfile.mode],
  () => {
    rebuildStars();
    drawScene();
  },
);

watch(
  () => props.activeLinks.length,
  () => {
    drawScene();
  },
);

watch(
  () => `${String(props.centerAgentId || "")}|${props.orbitAgentIds.join("|")}`,
  () => {
    drawScene();
  },
);

watch(
  () =>
    props.agents
      .map(
        (agent) =>
          `${String(agent?.id || "")}:${String(agent?.avatarSrc || "")}`,
      )
      .join("|"),
  () => {
    preloadAgentAvatars();
    drawScene();
  },
  { immediate: true },
);

watch(
  () => props.renderAgentFaces,
  () => {
    preloadAgentAvatars();
    drawScene();
  },
);

onBeforeUnmount(() => {
  if (resizeObserver) {
    resizeObserver.disconnect();
    resizeObserver = null;
  }
  if (fallbackResizeAttached) {
    window.removeEventListener("resize", handleWindowResize);
    fallbackResizeAttached = false;
  }
  roleSwapTransition = null;
  lastRoleSignature = "";
  lastLayoutEmitMs = 0;
  avatarImageByAgentId.clear();
});
</script>
