<template>
  <div
    ref="hostRef"
    class="agent-three-sphere"
    :class="{ 'is-transparent': props.transparentShell }"
    :style="containerStyle"
  >
    <p v-if="statusText" class="agent-three-sphere-status">{{ statusText }}</p>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import * as THREE from "three";

const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";
const TAU = Math.PI * 2;

const props = defineProps({
  src: {
    type: String,
    required: true,
  },
  size: {
    type: Number,
    default: 280,
  },
  particleCount: {
    type: Number,
    default: 6200,
  },
  pointSize: {
    type: Number,
    default: 1.1,
  },
  swirlSpeed: {
    type: Number,
    default: 1,
  },
  animated: {
    type: Boolean,
    default: true,
  },
  transparentShell: {
    type: Boolean,
    default: false,
  },
  transformMode: {
    type: String,
    default: "vortex",
  },
  streamCount: {
    type: Number,
    default: 0,
  },
  maskSrc: {
    type: String,
    default: "",
  },
  maskStrength: {
    type: Number,
    default: 1,
  },
  projectionMode: {
    type: String,
    default: "sphere",
  },
  ringAngleDeg: {
    type: Number,
    default: 0,
  },
  ringTiltDeg: {
    type: Number,
    default: 42,
  },
  ringYawDeg: {
    type: Number,
    default: 0,
  },
  ringRadius: {
    type: Number,
    default: 1,
  },
  ringBand: {
    type: Number,
    default: 0.12,
  },
});

const hostRef = ref(null);
const statusText = ref("");
const isDocumentHidden = ref(
  typeof document === "undefined" ? false : Boolean(document.hidden),
);
const prefersReducedMotion = ref(false);
const isInViewport = ref(true);

const containerStyle = computed(() => {
  const size = Math.max(120, Number(props.size || 280));
  return {
    "--three-sphere-size": `${size}px`,
  };
});

const canAnimate = computed(
  () =>
    props.animated &&
    !prefersReducedMotion.value &&
    !isDocumentHidden.value &&
    isInViewport.value,
);

let renderer = null;
let scene = null;
let camera = null;
let sphereGroup = null;
let points = null;
let geometry = null;
let material = null;
let pointSpriteTexture = null;
let avatarTexture = null;
let avatarSprite = null;
let avatarSpriteMaterial = null;
let positionsBuffer = null;
let colorsBuffer = null;
let particleMeta = [];
let flowLines = null;
let flowLineGeometry = null;
let flowLineMaterial = null;
let flowLinePositionsBuffer = null;
let flowLineColorsBuffer = null;
let flowLineMeta = [];
let streamDefs = [];

let rafId = 0;
let lastTickMs = 0;
let lastDrawMs = 0;
let viewportWidth = 0;
let viewportHeight = 0;
let devicePixelRatio = 1;
let resizeObserver = null;
let fallbackResizeAttached = false;
let visibilityObserver = null;
let mediaQueryList = null;
let imageLoadToken = 0;
let flowMorph = 1;
let flowMorphTarget = 1;

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function randomFloat(min, max) {
  return min + Math.random() * (max - min);
}

function lerp(start, end, t) {
  return start + (end - start) * t;
}

function smoothstep01(value) {
  const t = clamp(value, 0, 1);
  return t * t * (3 - 2 * t);
}

function shortestAngleDistance(a, b) {
  return Math.abs(Math.atan2(Math.sin(a - b), Math.cos(a - b)));
}

function hashString(value) {
  const text = String(value || "");
  let hash = 2166136261;
  for (let i = 0; i < text.length; i += 1) {
    hash ^= text.charCodeAt(i);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

function createSeededRandom(seedValue) {
  let seed = (Number(seedValue) >>> 0) || 1;
  return () => {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    return seed / 4294967296;
  };
}

function resolveStreamCount(rawCount, fallbackSeed) {
  const parsed = Number(rawCount);
  if (Number.isFinite(parsed) && parsed >= 2 && parsed <= 5) {
    return Math.round(parsed);
  }
  return 2 + (fallbackSeed % 4);
}

function buildStreamDefs(seedSource, requestedCount) {
  const seed = hashString(seedSource);
  const streamCount = resolveStreamCount(requestedCount, seed);
  const rng = createSeededRandom(seed);
  const defs = new Array(streamCount);
  const sector = TAU / streamCount;

  for (let index = 0; index < streamCount; index += 1) {
    const jitter = (rng() - 0.5) * sector * 0.22;
    const centeredIndex = index - (streamCount - 1) * 0.5;
    defs[index] = {
      angle: index * sector + jitter,
      dir: rng() < 0.5 ? -1 : 1,
      tilt: (rng() - 0.5) * 0.46,
      twist: 0.78 + rng() * 0.9,
      xScale: 0.9 + rng() * 0.22,
      yScale: 0.82 + rng() * 0.24,
      zBias: (rng() - 0.5) * 0.2,
      phase: rng() * TAU,
      ringRadius: 1.02 + centeredIndex * 0.04 + (rng() - 0.5) * 0.012,
      ringTiltX: 0.74 + (rng() - 0.5) * 0.2,
      ringTiltZ: (rng() - 0.5) * 0.28,
      clusterCount: 2 + Math.floor(rng() * 3),
    };
  }

  return defs;
}

function resolveTransformTarget(mode) {
  return String(mode || "").toLowerCase() === "avatar" ? 0 : 1;
}

function resolveProjectionMode(value) {
  const mode = String(value || "")
    .trim()
    .toLowerCase();
  return mode === "ring2d" ? "ring2d" : "sphere";
}

function resolveLowercaseCandidate(rawSrc) {
  const src = String(rawSrc || "").trim();
  if (!src) return "";

  const slashIndex = src.lastIndexOf("/");
  if (slashIndex < 0) return src.toLowerCase();

  const dir = src.slice(0, slashIndex + 1);
  const filename = src.slice(slashIndex + 1);
  return `${dir}${filename.toLowerCase()}`;
}

function swapImageExtension(rawSrc, nextExtension) {
  const src = String(rawSrc || "").trim();
  if (!src) return "";

  const matched = src.match(/^([^?#]+)([?#].*)?$/);
  if (!matched) return "";

  const pathname = matched[1];
  const suffix = matched[2] || "";
  if (!/\.(webp|png)$/i.test(pathname)) return "";
  const replaced = pathname.replace(/\.(webp|png)$/i, `.${nextExtension}`);
  if (replaced === pathname) return "";
  return `${replaced}${suffix}`;
}

function resolveImageFallbackCandidates(rawSrc) {
  const primary = String(rawSrc || "").trim();
  if (!primary) return [];

  const lower = resolveLowercaseCandidate(primary);
  const isWebp = /\.webp([?#].*)?$/i.test(primary);
  const swapExt = isWebp ? "png" : "webp";
  const candidates = [];
  const append = (value) => {
    const nextValue = String(value || "").trim();
    if (!nextValue || candidates.includes(nextValue)) return;
    candidates.push(nextValue);
  };

  append(primary);
  append(lower);
  append(swapImageExtension(primary, swapExt));
  append(swapImageExtension(lower, swapExt));
  return candidates;
}

function loadImage(url) {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.decoding = "async";
    image.crossOrigin = "anonymous";
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error(`Image load failed: ${url}`));
    image.src = url;
  });
}

async function loadImageWithFallback(rawSrc) {
  const candidates = resolveImageFallbackCandidates(rawSrc);
  if (!candidates.length) {
    throw new Error("Image src is empty");
  }

  for (const candidate of candidates) {
    try {
      return await loadImage(candidate);
    } catch {
      // Try next fallback candidate.
    }
  }

  throw new Error("Image fallback load failed");
}

function sampleImageColor(imageData, width, height, u, v) {
  const x = clamp(Math.round(u * (width - 1)), 0, width - 1);
  const y = clamp(Math.round(v * (height - 1)), 0, height - 1);
  const pixelIndex = (y * width + x) * 4;

  return {
    r: imageData[pixelIndex] || 0,
    g: imageData[pixelIndex + 1] || 0,
    b: imageData[pixelIndex + 2] || 0,
    a: imageData[pixelIndex + 3] || 0,
  };
}

function buildColorSampler(image) {
  const canvas = document.createElement("canvas");
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (!ctx) return null;

  const width = 384;
  const height = 384;
  canvas.width = width;
  canvas.height = height;
  ctx.clearRect(0, 0, width, height);
  ctx.drawImage(image, 0, 0, width, height);
  const imageData = ctx.getImageData(0, 0, width, height).data;

  return {
    canvas,
    width,
    height,
    imageData,
  };
}

function buildAvatarTextureFromSampler(sampler) {
  if (!sampler?.canvas) return null;
  const texture = new THREE.CanvasTexture(sampler.canvas);
  texture.needsUpdate = true;
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.magFilter = THREE.LinearFilter;
  texture.minFilter = THREE.LinearMipmapLinearFilter;
  return texture;
}

function getMaskWeight(maskSampler, u, v) {
  if (!maskSampler) return 1;
  const sampled = sampleImageColor(
    maskSampler.imageData,
    maskSampler.width,
    maskSampler.height,
    u,
    v,
  );
  const alpha = clamp((sampled.a || 0) / 255, 0, 1);
  const luminance = clamp(
    ((sampled.r || 0) * 0.2126 +
      (sampled.g || 0) * 0.7152 +
      (sampled.b || 0) * 0.0722) /
      255,
    0,
    1,
  );
  return clamp(alpha * 0.56 + luminance * 0.98, 0, 1);
}

function getPointSpriteTexture() {
  if (pointSpriteTexture) {
    return pointSpriteTexture;
  }

  const spriteCanvas = document.createElement("canvas");
  spriteCanvas.width = 96;
  spriteCanvas.height = 96;
  const ctx = spriteCanvas.getContext("2d");
  if (!ctx) return null;

  const center = spriteCanvas.width / 2;
  const gradient = ctx.createRadialGradient(
    center,
    center,
    0,
    center,
    center,
    center,
  );
  gradient.addColorStop(0, "rgba(255,255,255,1)");
  gradient.addColorStop(0.48, "rgba(255,255,255,0.96)");
  gradient.addColorStop(0.78, "rgba(255,255,255,0.45)");
  gradient.addColorStop(1, "rgba(255,255,255,0)");
  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, spriteCanvas.width, spriteCanvas.height);

  pointSpriteTexture = new THREE.CanvasTexture(spriteCanvas);
  pointSpriteTexture.needsUpdate = true;
  pointSpriteTexture.colorSpace = THREE.SRGBColorSpace;
  pointSpriteTexture.magFilter = THREE.LinearFilter;
  pointSpriteTexture.minFilter = THREE.LinearMipmapLinearFilter;
  return pointSpriteTexture;
}

function destroyPoints() {
  if (points && sphereGroup) {
    sphereGroup.remove(points);
  }
  if (avatarSprite && sphereGroup) {
    sphereGroup.remove(avatarSprite);
  }
  if (flowLines && sphereGroup) {
    sphereGroup.remove(flowLines);
  }
  if (geometry) {
    geometry.dispose();
  }
  if (flowLineGeometry) {
    flowLineGeometry.dispose();
  }
  if (material) {
    material.dispose();
  }
  if (flowLineMaterial) {
    flowLineMaterial.dispose();
  }
  if (avatarSpriteMaterial) {
    avatarSpriteMaterial.dispose();
  }
  if (avatarTexture) {
    avatarTexture.dispose();
  }

  points = null;
  avatarSprite = null;
  flowLines = null;
  geometry = null;
  flowLineGeometry = null;
  material = null;
  avatarSpriteMaterial = null;
  flowLineMaterial = null;
  avatarTexture = null;
  positionsBuffer = null;
  colorsBuffer = null;
  flowLinePositionsBuffer = null;
  flowLineColorsBuffer = null;
  particleMeta = [];
  flowLineMeta = [];
  streamDefs = [];
}

function destroyRenderer() {
  if (!renderer) return;

  if (renderer.domElement?.parentNode) {
    renderer.domElement.parentNode.removeChild(renderer.domElement);
  }

  renderer.dispose();
  if (typeof renderer.forceContextLoss === "function") {
    renderer.forceContextLoss();
  }

  renderer = null;
  scene = null;
  camera = null;
  sphereGroup = null;

  if (pointSpriteTexture) {
    pointSpriteTexture.dispose();
    pointSpriteTexture = null;
  }
}

function ensureRenderer() {
  if (renderer && scene && camera && sphereGroup) {
    return true;
  }

  const host = hostRef.value;
  if (!host) return false;

  try {
    renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: false,
      powerPreference: "high-performance",
      premultipliedAlpha: true,
    });
  } catch {
    statusText.value = "WebGL недоступен";
    return false;
  }

  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.setClearColor(0x000000, 0);

  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(36, 1, 0.1, 12);
  camera.position.set(0, 0, 3.35);

  sphereGroup = new THREE.Group();
  scene.add(sphereGroup);

  host.appendChild(renderer.domElement);
  statusText.value = "";
  return true;
}

function syncRendererSize() {
  const host = hostRef.value;
  if (!host || !renderer || !camera) return;

  const rect = host.getBoundingClientRect();
  const nextWidth = Math.max(120, Math.round(rect.width));
  const nextHeight = Math.max(120, Math.round(rect.height));
  const nextDpr = clamp(Number(window.devicePixelRatio || 1), 1, 1.3);

  viewportWidth = nextWidth;
  viewportHeight = nextHeight;
  devicePixelRatio = nextDpr;

  renderer.setPixelRatio(devicePixelRatio);
  renderer.setSize(viewportWidth, viewportHeight, false);

  camera.aspect = viewportWidth / Math.max(1, viewportHeight);
  camera.updateProjectionMatrix();
}

function rebuildMaterial() {
  if (!material) return;
  material.size = clamp(Number(props.pointSize || 1.1), 0.35, 2.8);
  material.needsUpdate = true;
}

function rebuildParticlesFromImage({ avatarImage, maskImage = null, sourceKey = "" }) {
  if (!ensureRenderer() || !sphereGroup) {
    return;
  }

  const sampler = buildColorSampler(avatarImage);
  if (!sampler) {
    statusText.value = "Не удалось подготовить аватар";
    return;
  }
  const maskSampler = maskImage ? buildColorSampler(maskImage) : null;
  const projectionMode = resolveProjectionMode(props.projectionMode);
  const isRing2dProjection = projectionMode === "ring2d";
  const maskStrength = clamp(Number(props.maskStrength || 1), 0, 3);

  destroyPoints();

  const baseCount = clamp(Number(props.particleCount || 6200), 900, 14000);
  const sizeScale = clamp(Math.pow(Math.max(120, Number(props.size || 280)) / 280, 1.18), 0.28, 1);
  const motionScale = prefersReducedMotion.value ? 0.42 : 1;
  const count = Math.round(clamp(baseCount * sizeScale * motionScale, 620, 14000));
  streamDefs = buildStreamDefs(
    `${sourceKey}|${count}|${Math.round(Number(props.size || 280))}|${projectionMode}`,
    props.streamCount,
  );
  const radius = 1.0;

  geometry = new THREE.BufferGeometry();
  positionsBuffer = new Float32Array(count * 3);
  colorsBuffer = new Float32Array(count * 3);
  particleMeta = new Array(count);

  for (let index = 0; index < count; index += 1) {
    const offset = index * 3;

    let accepted = false;
    let finalX = 0;
    let finalY = 0;
    let finalZ = 1;
    let finalRed = 0.08;
    let finalGreen = 0.11;
    let finalBlue = 0.16;
    let maskWeight = 0.2;

    for (let attempt = 0; attempt < 22; attempt += 1) {
      const u = Math.random();
      const v = Math.random();
      const sampled = sampleImageColor(
        sampler.imageData,
        sampler.width,
        sampler.height,
        u,
        v,
      );

      const alpha = clamp((sampled.a || 0) / 255, 0, 1);
      const red = clamp((sampled.r || 0) / 255, 0, 1);
      const green = clamp((sampled.g || 0) / 255, 0, 1);
      const blue = clamp((sampled.b || 0) / 255, 0, 1);
      const luminance = clamp(
        red * 0.2126 + green * 0.7152 + blue * 0.0722,
        0,
        1,
      );
      const avatarWeight = clamp(alpha * 0.78 + luminance * 1.38 - 0.27, 0, 1);

      let ringMaskWeight = getMaskWeight(maskSampler, u, v);
      if (!maskSampler && isRing2dProjection) {
        const radial = Math.hypot(u - 0.5, v - 0.5);
        const distanceFromRing = Math.abs(radial - 0.38);
        ringMaskWeight = clamp(1 - distanceFromRing / 0.15, 0, 1);
      }
      ringMaskWeight = clamp(Math.pow(ringMaskWeight, 1 / clamp(maskStrength, 0.3, 3)), 0, 1);

      const weight = isRing2dProjection
        ? clamp(ringMaskWeight * 1.05 + avatarWeight * 0.24, 0, 1)
        : clamp(avatarWeight * 0.86 + ringMaskWeight * 0.34, 0, 1);
      const keepChance = clamp(Math.pow(weight, isRing2dProjection ? 0.58 : 0.72) + 0.02, 0, 1);
      if (Math.random() > keepChance) {
        continue;
      }

      const mean = (red + green + blue) / 3;
      const saturationBoost = 1.14;
      finalRed = clamp(mean + (red - mean) * saturationBoost, 0, 1);
      finalGreen = clamp(mean + (green - mean) * saturationBoost, 0, 1);
      finalBlue = clamp(mean + (blue - mean) * saturationBoost, 0, 1);

      maskWeight = clamp(weight, 0, 1);

      if (isRing2dProjection) {
        const planeX = (u - 0.5) * 2;
        const planeY = (0.5 - v) * 2;
        const radial = Math.hypot(planeX, planeY);
        if (radial > 1.2) {
          continue;
        }
        finalX = planeX;
        finalY = planeY;
        finalZ = (Math.random() - 0.5) * (0.03 + (1 - ringMaskWeight) * 0.07);
      } else {
        const planeX = (u - 0.5) * 2;
        const planeY = (0.5 - v) * 2;
        const radial2 = planeX * planeX + planeY * planeY;
        if (radial2 > 1) {
          continue;
        }

        const zFront = Math.sqrt(Math.max(0, 1 - radial2));
        let z = zFront * randomFloat(0.92, 1);
        if (Math.random() < 0.06) {
          z = -zFront * randomFloat(0.05, 0.28);
        }

        let x = planeX;
        let y = planeY;
        const invLen = 1 / Math.sqrt(Math.max(1e-6, x * x + y * y + z * z));
        x *= invLen;
        y *= invLen;
        z *= invLen;

        finalX = x;
        finalY = y;
        finalZ = z;
      }

      accepted = true;
      break;
    }

    if (!accepted) {
      if (isRing2dProjection) {
        const angle = randomFloat(0, TAU);
        const ringRadius = randomFloat(0.74, 1.04);
        finalX = Math.cos(angle) * ringRadius;
        finalY = Math.sin(angle) * ringRadius;
        finalZ = randomFloat(-0.03, 0.03);
        finalRed = 0.045;
        finalGreen = 0.07;
        finalBlue = 0.11;
        maskWeight = 0.16;
      } else {
        // Fallback stays on the front hemisphere to preserve avatar silhouette.
        const angle = randomFloat(0, TAU);
        const radial = Math.sqrt(Math.random()) * 0.98;
        finalX = Math.cos(angle) * radial;
        finalY = Math.sin(angle) * radial;
        const zFront = Math.sqrt(Math.max(0, 1 - radial * radial));
        finalZ = zFront * randomFloat(0.92, 1);
        const invLen =
          1 /
          Math.sqrt(
            Math.max(
              1e-6,
              finalX * finalX + finalY * finalY + finalZ * finalZ,
            ),
          );
        finalX *= invLen;
        finalY *= invLen;
        finalZ *= invLen;
        finalRed = 0.045;
        finalGreen = 0.07;
        finalBlue = 0.11;
        maskWeight = 0.01;
      }
    }

    const depthLight = isRing2dProjection
      ? clamp(0.72 + (1 - Math.abs(finalZ)) * 0.3, 0.56, 1.12)
      : clamp(0.34 + (finalZ + 1) * 0.34, 0.18, 1);
    const energy = isRing2dProjection
      ? clamp(0.05 + maskWeight * 1.72, 0.02, 1.72)
      : clamp(0.06 + maskWeight * 1.56, 0.02, 1.62);
    colorsBuffer[offset] = clamp(finalRed * energy * depthLight, 0, 1);
    colorsBuffer[offset + 1] = clamp(finalGreen * energy * depthLight, 0, 1);
    colorsBuffer[offset + 2] = clamp(finalBlue * energy * depthLight, 0, 1);

    positionsBuffer[offset] = finalX * radius;
    positionsBuffer[offset + 1] = finalY * radius;
    positionsBuffer[offset + 2] = finalZ * radius;

    let exitX = -finalX * randomFloat(0.46, 0.88) + randomFloat(-0.24, 0.24);
    let exitY = -finalY * randomFloat(0.2, 0.56) + randomFloat(-0.42, 0.42);
    let exitZ = -Math.abs(finalZ) * randomFloat(0.84, 1.14) - randomFloat(0.12, 0.44);
    const exitInvLen = 1 / Math.sqrt(Math.max(1e-6, exitX * exitX + exitY * exitY + exitZ * exitZ));
    exitX *= exitInvLen;
    exitY *= exitInvLen;
    exitZ *= exitInvLen;

    const baseAngle = Math.atan2(finalY, finalX);
    let streamId = 0;
    if (streamDefs.length > 1) {
      let bestDistance = Infinity;
      for (let streamIndex = 0; streamIndex < streamDefs.length; streamIndex += 1) {
        const distance = shortestAngleDistance(baseAngle, streamDefs[streamIndex].angle);
        if (distance < bestDistance) {
          bestDistance = distance;
          streamId = streamIndex;
        }
      }
      if (Math.random() < 0.15) {
        const shift = Math.random() < 0.5 ? -1 : 1;
        streamId = (streamId + shift + streamDefs.length) % streamDefs.length;
      }
    }
    const streamRef = streamDefs[streamId] || streamDefs[0];
    const streamClusterCount = Math.max(2, Number(streamRef?.clusterCount || 3));

    particleMeta[index] = {
      baseX: finalX,
      baseY: finalY,
      baseZ: finalZ,
      exitX,
      exitY,
      exitZ,
      cycle: randomFloat(0, 1),
      cycleRate: randomFloat(0.22, 0.86),
      spin: randomFloat(0.72, 2.4),
      wobble: randomFloat(0.002, 0.012),
      phase: randomFloat(0, TAU),
      flow: randomFloat(0.22, 1),
      shellRadius: randomFloat(0.985, 1.03),
      coreRadius: randomFloat(0.06, 0.22),
      backRadius: randomFloat(0.84, 1.1),
      streamId,
      clusterSlot: Math.floor(Math.random() * streamClusterCount),
      clusterJitter: randomFloat(0.04, 0.24),
      clusterStickiness: randomFloat(0.66, 1.12),
      laneSpread: randomFloat(0.82, 1.18),
      lanePhase: randomFloat(0, TAU),
      avatarAngle: randomFloat(0, TAU),
      avatarSpeed: randomFloat(0.46, 1.74),
      avatarTilt: randomFloat(-0.42, 0.42),
      avatarTiltDrift: randomFloat(0.08, 0.28),
      avatarOrbitRadius: randomFloat(0.01, 0.065),
      avatarJitter: randomFloat(0.05, 0.28),
      maskWeight,
      prevX: finalX * radius,
      prevY: finalY * radius,
      prevZ: finalZ * radius,
    };
  }

  geometry.setAttribute("position", new THREE.BufferAttribute(positionsBuffer, 3));
  geometry.setAttribute("color", new THREE.BufferAttribute(colorsBuffer, 3));
  geometry.computeBoundingSphere();

  const sprite = getPointSpriteTexture();
  material = new THREE.PointsMaterial({
    size: clamp(Number(props.pointSize || 1.1), 0.35, 2.8),
    vertexColors: true,
    map: sprite,
    alphaMap: sprite,
    transparent: true,
    opacity: 0.92,
    sizeAttenuation: false,
    depthWrite: false,
    depthTest: true,
    alphaTest: 0.02,
    blending: THREE.AdditiveBlending,
    toneMapped: false,
  });

  points = new THREE.Points(geometry, material);
  sphereGroup.add(points);

  avatarTexture = buildAvatarTextureFromSampler(sampler);
  if (avatarTexture) {
    avatarSpriteMaterial = new THREE.SpriteMaterial({
      map: avatarTexture,
      transparent: true,
      opacity: 0.68,
      depthWrite: false,
      depthTest: true,
      blending: THREE.NormalBlending,
      toneMapped: false,
    });
    avatarSprite = new THREE.Sprite(avatarSpriteMaterial);
    avatarSprite.scale.set(2.03, 2.03, 1);
    avatarSprite.position.set(0, 0, 0.02);
    sphereGroup.add(avatarSprite);
  }

  const lineCount = Math.round(clamp(count * 0.09, 120, 880));
  flowLineGeometry = new THREE.BufferGeometry();
  flowLinePositionsBuffer = new Float32Array(lineCount * 6);
  flowLineColorsBuffer = new Float32Array(lineCount * 6);
  flowLineMeta = new Array(lineCount);

  for (let index = 0; index < lineCount; index += 1) {
    const mappedParticleIndex = Math.floor((index / lineCount) * count);
    const jitteredParticleIndex = clamp(
      mappedParticleIndex + Math.round(randomFloat(-42, 42)),
      0,
      count - 1,
    );
    const particleOffset = jitteredParticleIndex * 3;
    const lineOffset = index * 6;

    const px = positionsBuffer[particleOffset];
    const py = positionsBuffer[particleOffset + 1];
    const pz = positionsBuffer[particleOffset + 2];
    const cr = colorsBuffer[particleOffset];
    const cg = colorsBuffer[particleOffset + 1];
    const cb = colorsBuffer[particleOffset + 2];

    flowLinePositionsBuffer[lineOffset] = px;
    flowLinePositionsBuffer[lineOffset + 1] = py;
    flowLinePositionsBuffer[lineOffset + 2] = pz;
    flowLinePositionsBuffer[lineOffset + 3] = px;
    flowLinePositionsBuffer[lineOffset + 4] = py;
    flowLinePositionsBuffer[lineOffset + 5] = pz;

    flowLineColorsBuffer[lineOffset] = clamp(cr * 1.35, 0, 1);
    flowLineColorsBuffer[lineOffset + 1] = clamp(cg * 1.35, 0, 1);
    flowLineColorsBuffer[lineOffset + 2] = clamp(cb * 1.35, 0, 1);
    flowLineColorsBuffer[lineOffset + 3] = clamp(cr * 0.06, 0, 1);
    flowLineColorsBuffer[lineOffset + 4] = clamp(cg * 0.06, 0, 1);
    flowLineColorsBuffer[lineOffset + 5] = clamp(cb * 0.06, 0, 1);

    flowLineMeta[index] = {
      particleIndex: jitteredParticleIndex,
      trail: randomFloat(0.016, 0.074),
      pulse: randomFloat(0.5, 1.45),
      phase: randomFloat(0, TAU),
    };
  }

  const flowLinePositionAttr = new THREE.BufferAttribute(flowLinePositionsBuffer, 3);
  flowLinePositionAttr.setUsage(THREE.DynamicDrawUsage);
  flowLineGeometry.setAttribute("position", flowLinePositionAttr);
  const flowLineColorAttr = new THREE.BufferAttribute(flowLineColorsBuffer, 3);
  flowLineColorAttr.setUsage(THREE.DynamicDrawUsage);
  flowLineGeometry.setAttribute("color", flowLineColorAttr);
  flowLineGeometry.computeBoundingSphere();

  flowLineMaterial = new THREE.LineBasicMaterial({
    vertexColors: true,
    transparent: true,
    opacity: 0.62,
    depthTest: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
    toneMapped: false,
  });

  flowLines = new THREE.LineSegments(flowLineGeometry, flowLineMaterial);
  sphereGroup.add(flowLines);
}

function renderScene() {
  if (!renderer || !scene || !camera) return;
  renderer.render(scene, camera);
}

function tick(timestamp) {
  rafId = window.requestAnimationFrame(tick);

  const deltaMs = lastTickMs ? timestamp - lastTickMs : 16;
  lastTickMs = timestamp;
  const dt = clamp(deltaMs / 1000, 0.001, 0.05);
  const morphBlend = 1 - Math.exp(-dt * 5.2);
  flowMorph = lerp(flowMorph, flowMorphTarget, morphBlend);
  if (Math.abs(flowMorph - flowMorphTarget) < 0.001) {
    flowMorph = flowMorphTarget;
  }

  const shouldAnimate = canAnimate.value;
  const fpsLimit = shouldAnimate ? 32 : 8;
  const minFrameInterval = 1000 / fpsLimit;
  if (timestamp - lastDrawMs < minFrameInterval) {
    return;
  }
  lastDrawMs = timestamp;

  if (
    shouldAnimate &&
    positionsBuffer &&
    geometry &&
    geometry.attributes.position &&
    particleMeta.length
  ) {
    const speed = clamp(Number(props.swirlSpeed || 1), 0.25, 3);
    const cycleBase = 0.24 + 0.3 * speed;
    const nowS = timestamp * 0.001;
    const flowLevel = clamp(flowMorph, 0, 1);
    const driftLevel = clamp(0.08 + flowLevel * 0.92, 0.06, 1);
    const avatarLevel = 1 - flowLevel;
    const projectionMode = resolveProjectionMode(props.projectionMode);
    const isRing2dProjection = projectionMode === "ring2d";
    const ringAngleOffset =
      clamp(Number(props.ringAngleDeg || 0), -360, 360) * (Math.PI / 180);
    const ringTiltBaseX =
      clamp(Number(props.ringTiltDeg || 42), -89, 89) * (Math.PI / 180);
    const ringTiltBaseZ =
      clamp(Number(props.ringYawDeg || 0), -180, 180) * (Math.PI / 180);
    const ringRadiusScale = clamp(Number(props.ringRadius || 1), 0.32, 2.8);
    const ringBandScale = clamp(Number(props.ringBand || 0.12), 0.02, 0.5) / 0.12;

    for (let index = 0; index < particleMeta.length; index += 1) {
      const meta = particleMeta[index];
      meta.cycle += dt * meta.cycleRate * cycleBase * driftLevel;
      if (meta.cycle > 1) {
        meta.cycle -= 1;
      }

      const baseX = meta.baseX;
      const baseY = meta.baseY;
      const baseZ = meta.baseZ;
      const stream =
        streamDefs[meta.streamId] || streamDefs[0] || {
          angle: 0,
          dir: 1,
          tilt: 0,
          twist: 1,
          xScale: 1,
          yScale: 1,
          zBias: 0,
          phase: 0,
          ringRadius: 1.04,
          ringTiltX: 0.74,
          ringTiltZ: 0,
          clusterCount: 3,
        };

      const shellRadius = meta.shellRadius;
      let flowX = baseX;
      let flowY = baseY;
      let flowZ = baseZ;
      let targetRadius = shellRadius;
      let motionMix = 0;
      let normalizeToSphere = !isRing2dProjection;

      const spinTime = nowS * (0.58 + speed * 0.76) + meta.phase;
      const avatarOrbitLevel = smoothstep01(avatarLevel);
      const particleMaskBias = clamp(meta.maskWeight || 0.5, 0, 1);

      if (flowLevel < 0.14) {
        // Assemble mode: Saturn-like ring lanes that shift between clumps and a thin line.
        meta.avatarAngle +=
          dt * (0.24 + speed * 0.2) * meta.avatarSpeed * (0.74 + meta.flow * 0.44);
        if (meta.avatarAngle > TAU) {
          meta.avatarAngle -= TAU;
        }
        const streamSpin =
          nowS * (0.14 + speed * 0.2) * stream.dir * (0.84 + stream.twist * 0.34);
        const pulse = 0.5 + 0.5 * Math.sin(nowS * (0.22 + stream.twist * 0.07) + stream.phase);
        const lineSpread = smoothstep01(pulse);
        const clusterSpread = 1 - lineSpread;

        const lineAngle = streamSpin + meta.avatarAngle + stream.angle * 0.2;
        const clusterStride = TAU / Math.max(2, Number(stream.clusterCount || 3));
        const clusterCenter = streamSpin + stream.angle + clusterStride * (meta.clusterSlot || 0);
        const clusterDrift =
          Math.sin(nowS * (0.42 + meta.avatarTiltDrift * 0.8) + meta.phase) * 0.36;
        const clusterAngle =
          clusterCenter +
          clusterDrift +
          Math.sin(nowS * (0.92 + meta.avatarSpeed * 0.34) + meta.phase) *
            (meta.clusterJitter || 0.1);
        const clusterMix = smoothstep01(
          clusterSpread * (meta.clusterStickiness || 1) * (0.72 + particleMaskBias * 0.56),
        );
        const laneAngle = lerp(lineAngle, clusterAngle, clusterMix);

        const radialSpread =
          lerp(0.026, 0.0056, lineSpread) *
          (0.78 + (meta.laneSpread || 1) * 0.3) *
          ringBandScale;
        const verticalSpread =
          lerp(0.019, 0.0034, lineSpread) *
          (0.8 + (meta.laneSpread || 1) * 0.24) *
          ringBandScale;
        const ringRadius =
          (stream.ringRadius || 1.04) * ringRadiusScale +
          Math.sin(nowS * (0.76 + meta.avatarSpeed * 0.16) + meta.phase) * radialSpread;
        const ringThickness =
          Math.sin(nowS * (0.58 + meta.avatarTiltDrift) + meta.phase * 1.2) * verticalSpread;

        // Build a circle in XY, then tilt it to get Saturn-like ring perspective.
        const circleX = Math.cos(laneAngle) * ringRadius * (stream.xScale || 1);
        const circleY = Math.sin(laneAngle) * ringRadius * (stream.yScale || 1) + ringThickness;
        const circleZ = 0;

        const tiltX =
          ringTiltBaseX +
          ((stream.ringTiltX || 0.74) - 0.74) +
          Math.sin(nowS * (0.17 + meta.avatarTiltDrift * 0.36) + stream.phase) * 0.08;
        const tiltZ =
          ringTiltBaseZ +
          (stream.ringTiltZ || 0) * 0.4 +
          Math.sin(nowS * (0.14 + meta.avatarTiltDrift * 0.24) + stream.phase * 0.6) * 0.07;

        const cosX = Math.cos(tiltX);
        const sinX = Math.sin(tiltX);
        const yX = circleY * cosX - circleZ * sinX;
        const zX = circleY * sinX + circleZ * cosX;

        const cosZ = Math.cos(tiltZ);
        const sinZ = Math.sin(tiltZ);
        const xZ = circleX * cosZ - yX * sinZ;
        const yZ = circleX * sinZ + yX * cosZ;

        flowX = xZ;
        flowY = yZ;
        flowZ =
          zX +
          (stream.zBias || 0) * 0.22 +
          Math.sin(laneAngle * (1.2 + (meta.flow || 0.5) * 0.16) + meta.phase) *
            (verticalSpread * 0.58);

        motionMix = clamp(0.58 + avatarOrbitLevel * 0.4, 0.54, 0.98);
        targetRadius = ringRadius;
        normalizeToSphere = false;
      } else {
        // Cloud mode: dense rotating plume that sits in front of the avatar.
        const cloudTime = nowS * (0.44 + speed * 0.54) + meta.phase;
        const clusterStride = TAU / Math.max(2, Number(stream.clusterCount || 3));
        const clusterAnchor =
          stream.angle +
          ringAngleOffset +
          clusterStride * (meta.clusterSlot || 0) +
          Math.sin(cloudTime * (0.2 + meta.avatarTiltDrift * 0.22) + stream.phase) * 0.22;
        const spinAngle =
          clusterAnchor +
          stream.dir *
            (cloudTime * (0.82 + stream.twist * 0.28) + meta.lanePhase * 0.32);

        const cloudPulse =
          0.5 + 0.5 * Math.sin(nowS * (0.58 + meta.cycleRate * 0.74) + meta.phase);
        const clumpPulse =
          0.5 +
          0.5 *
            Math.sin(nowS * (0.4 + meta.avatarSpeed * 0.26) + stream.phase + meta.lanePhase);
        const maskBias = 0.44 + particleMaskBias * 0.62;
        const radiusBase =
          (0.14 + maskBias * 0.36 + meta.flow * 0.12) *
          (0.84 + (meta.laneSpread || 1) * 0.24);
        const radiusPulse = lerp(0.72, 1.18, cloudPulse);
        const clumpRadius = lerp(0.86, 1.16, clumpPulse);
        const laneNoise =
          Math.sin(cloudTime * (1.22 + meta.spin * 0.16) + meta.lanePhase) * 0.075 +
          Math.cos(cloudTime * (0.9 + meta.flow * 0.2) + meta.avatarAngle) * 0.055;
        const cloudRadius = clamp(radiusBase * radiusPulse * clumpRadius + laneNoise, 0.06, 0.78);

        const depthSwirl =
          Math.sin(spinAngle * 0.8 + cloudTime * 0.9) * 0.17 +
          Math.cos(cloudTime * 1.36 + meta.phase) * 0.08;

        flowX = Math.cos(spinAngle) * cloudRadius * (stream.xScale || 1) * 0.94;
        flowY =
          Math.sin(spinAngle + stream.tilt * 0.18) *
          cloudRadius *
          (stream.yScale || 1) *
          0.88;
        flowZ = depthSwirl * (0.56 + maskBias * 0.26) + (stream.zBias || 0) * 0.08;

        const inhale =
          0.5 + 0.5 * Math.sin(nowS * (0.48 + meta.avatarTiltDrift * 0.58) + meta.phase);
        const inhaleScale = lerp(0.7, 1.14, inhale);
        flowX *= inhaleScale;
        flowY *= inhaleScale;
        flowZ *= inhaleScale * 0.92;

        motionMix = clamp((0.46 + meta.flow * 0.42) * flowLevel, 0.34, 0.99);
        targetRadius = cloudRadius;
        normalizeToSphere = false;
      }

      let x = lerp(baseX, flowX, motionMix);
      let y = lerp(baseY, flowY, motionMix);
      let z = lerp(baseZ, flowZ, motionMix);

      const wobblePhase = spinTime * (0.72 + meta.spin * 0.12);
      const wobbleAmp =
        meta.wobble *
        (0.028 + avatarOrbitLevel * 0.11 + flowLevel * (0.24 + speed * 0.44));
      x += Math.cos(wobblePhase) * wobbleAmp;
      y += Math.sin(wobblePhase * 1.16 + meta.phase * 0.3) * wobbleAmp * 0.78;
      z += Math.sin(wobblePhase * 0.9 + meta.phase) * wobbleAmp;

      const radiusPulse =
        Math.sin(nowS * 1.48 + meta.phase) *
        (0.0008 + avatarOrbitLevel * 0.0012 + flowLevel * 0.0028);
      if (normalizeToSphere) {
        const invLen = 1 / Math.sqrt(Math.max(1e-6, x * x + y * y + z * z));
        const finalRadius = lerp(shellRadius, targetRadius, motionMix) + radiusPulse;
        x *= invLen * finalRadius;
        y *= invLen * finalRadius;
        z *= invLen * finalRadius;
      } else {
        const ringScale = 1 + radiusPulse * 0.5;
        x *= ringScale;
        y *= ringScale;
        z *= ringScale;
      }

      const offset = index * 3;
      meta.prevX = positionsBuffer[offset];
      meta.prevY = positionsBuffer[offset + 1];
      meta.prevZ = positionsBuffer[offset + 2];
      positionsBuffer[offset] = x;
      positionsBuffer[offset + 1] = y;
      positionsBuffer[offset + 2] = z;
    }

    geometry.attributes.position.needsUpdate = true;
    if (material) {
      material.opacity = isRing2dProjection
        ? clamp(0.84 + flowLevel * 0.14, 0.82, 1)
        : clamp(0.78 + flowLevel * 0.18, 0.74, 0.98);
    }
    if (avatarSpriteMaterial) {
      const isAssembledMode = flowLevel < 0.14;
      if (isAssembledMode) {
        avatarSpriteMaterial.opacity = isRing2dProjection
          ? clamp(0.74 + Math.pow(avatarLevel, 0.8) * 0.18, 0.72, 0.95)
          : clamp(0.72 + Math.pow(avatarLevel, 0.78) * 0.22, 0.7, 0.96);
      } else {
        avatarSpriteMaterial.opacity = isRing2dProjection
          ? clamp(0.01 + Math.pow(avatarLevel, 1.2) * 0.09, 0.01, 0.12)
          : clamp(0.015 + Math.pow(avatarLevel, 1.1) * 0.14, 0.015, 0.2);
      }
    }

    if (
      flowLineGeometry &&
      flowLinePositionsBuffer &&
      flowLineColorsBuffer &&
      flowLineMeta.length &&
      flowLevel > 0.08
    ) {
      const cloudFlowMode = flowLevel >= 0.14;
      for (let lineIndex = 0; lineIndex < flowLineMeta.length; lineIndex += 1) {
        const lineMeta = flowLineMeta[lineIndex];
        const particleIndex = lineMeta.particleIndex;
        const particleOffset = particleIndex * 3;
        const lineOffset = lineIndex * 6;

        const currX = positionsBuffer[particleOffset];
        const currY = positionsBuffer[particleOffset + 1];
        const currZ = positionsBuffer[particleOffset + 2];
        const meta = particleMeta[particleIndex];
        const prevX = meta?.prevX ?? currX;
        const prevY = meta?.prevY ?? currY;
        const prevZ = meta?.prevZ ?? currZ;

        let velX = currX - prevX;
        let velY = currY - prevY;
        let velZ = currZ - prevZ;
        let velLen = Math.sqrt(velX * velX + velY * velY + velZ * velZ);

        if (velLen < 1e-5) {
          velX = -currZ;
          velY = 0;
          velZ = currX;
          velLen = Math.sqrt(velX * velX + velY * velY + velZ * velZ);
        }

        const invVelLen = 1 / Math.max(velLen, 1e-5);
        velX *= invVelLen;
        velY *= invVelLen;
        velZ *= invVelLen;

        const pulse =
          0.66 +
          0.58 * Math.sin(nowS * (1.24 + lineMeta.pulse * 0.74) + lineMeta.phase);
        const trailLength =
          lineMeta.trail *
          (0.18 + speed * 0.86) *
          pulse *
          flowLevel *
          (cloudFlowMode ? 0.42 : 1);
        const tailX = currX - velX * trailLength;
        const tailY = currY - velY * trailLength;
        const tailZ = currZ - velZ * trailLength;

        flowLinePositionsBuffer[lineOffset] = currX;
        flowLinePositionsBuffer[lineOffset + 1] = currY;
        flowLinePositionsBuffer[lineOffset + 2] = currZ;
        flowLinePositionsBuffer[lineOffset + 3] = tailX;
        flowLinePositionsBuffer[lineOffset + 4] = tailY;
        flowLinePositionsBuffer[lineOffset + 5] = tailZ;

        const red = colorsBuffer[particleOffset];
        const green = colorsBuffer[particleOffset + 1];
        const blue = colorsBuffer[particleOffset + 2];
        const headPower = clamp(
          (cloudFlowMode ? 0.96 : 1.16) +
            speed * (cloudFlowMode ? 0.08 : 0.14) +
            pulse * 0.25,
          cloudFlowMode ? 0.65 : 0.8,
          cloudFlowMode ? 1.35 : 1.8,
        );
        flowLineColorsBuffer[lineOffset] = clamp(red * headPower, 0, 1);
        flowLineColorsBuffer[lineOffset + 1] = clamp(green * headPower, 0, 1);
        flowLineColorsBuffer[lineOffset + 2] = clamp(blue * headPower, 0, 1);
        flowLineColorsBuffer[lineOffset + 3] = clamp(red * 0.04, 0, 1);
        flowLineColorsBuffer[lineOffset + 4] = clamp(green * 0.04, 0, 1);
        flowLineColorsBuffer[lineOffset + 5] = clamp(blue * 0.04, 0, 1);
      }

      flowLineGeometry.attributes.position.needsUpdate = true;
      flowLineGeometry.attributes.color.needsUpdate = true;
      if (flowLineMaterial) {
        flowLineMaterial.opacity =
          flowLevel >= 0.14
            ? 0.01 + Math.pow(flowLevel, 1.2) * 0.2
            : 0.01 + Math.pow(flowLevel, 1.4) * 0.52;
      }
    } else if (flowLineMaterial) {
      flowLineMaterial.opacity = 0;
    }

    if (sphereGroup) {
      const rotationSpeed = isRing2dProjection
        ? 0.004 + flowLevel * 0.03
        : 0.012 + flowLevel * 0.06;
      sphereGroup.rotation.y += dt * rotationSpeed * speed;
      sphereGroup.rotation.x =
        Math.sin(timestamp * 0.00024) *
        (isRing2dProjection ? 0.003 + flowLevel * 0.012 : 0.012 + flowLevel * 0.038);
      sphereGroup.rotation.z = isRing2dProjection
        ? Math.sin(timestamp * 0.00019) * (0.002 + flowLevel * 0.008)
        : 0;
    }
  }

  renderScene();
}

function startLoop() {
  if (typeof window === "undefined") return;
  if (rafId) return;
  lastTickMs = 0;
  lastDrawMs = 0;
  rafId = window.requestAnimationFrame(tick);
}

function stopLoop() {
  if (typeof window === "undefined") return;
  if (!rafId) return;
  window.cancelAnimationFrame(rafId);
  rafId = 0;
  lastTickMs = 0;
  lastDrawMs = 0;
}

async function rebuildFromProps() {
  const source = String(props.src || "").trim();
  const maskSource = String(props.maskSrc || "").trim();
  if (!source) {
    statusText.value = "Нет изображения";
    destroyPoints();
    renderScene();
    return;
  }

  const token = ++imageLoadToken;
  statusText.value = "";

  try {
    const avatarImage = await loadImageWithFallback(source);
    if (token !== imageLoadToken) return;

    let maskImage = null;
    if (maskSource) {
      try {
        maskImage = await loadImageWithFallback(maskSource);
      } catch {
        maskImage = null;
      }
      if (token !== imageLoadToken) return;
    }

    rebuildParticlesFromImage({
      avatarImage,
      maskImage,
      sourceKey: `${source}|${maskSource || "no-mask"}`,
    });
    renderScene();
  } catch {
    if (token !== imageLoadToken) return;
    statusText.value = "Не удалось загрузить аватар";
    destroyPoints();
    renderScene();
  }
}

function handleDocumentVisibility() {
  if (typeof document === "undefined") return;
  isDocumentHidden.value = Boolean(document.hidden);
}

function handleReducedMotionChange(event) {
  prefersReducedMotion.value = Boolean(event.matches);
}

function attachResizeHandling() {
  if ("ResizeObserver" in window) {
    resizeObserver = new window.ResizeObserver(() => {
      syncRendererSize();
      renderScene();
    });
    if (hostRef.value) {
      resizeObserver.observe(hostRef.value);
    }
    return;
  }

  window.addEventListener("resize", syncRendererSize);
  fallbackResizeAttached = true;
}

function detachResizeHandling() {
  if (resizeObserver) {
    resizeObserver.disconnect();
    resizeObserver = null;
  }

  if (fallbackResizeAttached) {
    window.removeEventListener("resize", syncRendererSize);
    fallbackResizeAttached = false;
  }
}

function attachVisibilityHandling() {
  const host = hostRef.value;
  if (!host || !("IntersectionObserver" in window)) {
    isInViewport.value = true;
    return;
  }

  visibilityObserver = new window.IntersectionObserver(
    (entries) => {
      const entry = entries?.[0];
      if (!entry) return;
      isInViewport.value = entry.isIntersecting && entry.intersectionRatio > 0.02;
    },
    { threshold: [0, 0.02, 0.12] },
  );
  visibilityObserver.observe(host);
}

function detachVisibilityHandling() {
  if (!visibilityObserver) return;
  visibilityObserver.disconnect();
  visibilityObserver = null;
  isInViewport.value = true;
}

watch(
  () => [
    props.src,
    props.maskSrc,
    props.maskStrength,
    props.projectionMode,
    props.particleCount,
    props.size,
    props.streamCount,
    prefersReducedMotion.value,
  ],
  () => {
    rebuildFromProps();
  },
);

watch(
  () => [props.size, props.pointSize],
  () => {
    syncRendererSize();
    rebuildMaterial();
    renderScene();
  },
);

watch(
  () => canAnimate.value,
  (enabled) => {
    if (enabled) {
      startLoop();
      return;
    }
    stopLoop();
    renderScene();
  },
);

watch(
  () => props.transformMode,
  (mode) => {
    flowMorphTarget = resolveTransformTarget(mode);
  },
  { immediate: true },
);

onMounted(async () => {
  flowMorph = resolveTransformTarget(props.transformMode);
  flowMorphTarget = flowMorph;
  if (!ensureRenderer()) {
    return;
  }

  syncRendererSize();
  attachResizeHandling();
  attachVisibilityHandling();

  document.addEventListener("visibilitychange", handleDocumentVisibility);
  mediaQueryList = window.matchMedia?.(REDUCED_MOTION_QUERY) || null;
  prefersReducedMotion.value = Boolean(mediaQueryList?.matches);

  if (mediaQueryList?.addEventListener) {
    mediaQueryList.addEventListener("change", handleReducedMotionChange);
  } else if (mediaQueryList?.addListener) {
    mediaQueryList.addListener(handleReducedMotionChange);
  }

  await rebuildFromProps();

  if (canAnimate.value) {
    startLoop();
  }
});

onBeforeUnmount(() => {
  stopLoop();
  imageLoadToken += 1;

  document.removeEventListener("visibilitychange", handleDocumentVisibility);

  if (mediaQueryList?.removeEventListener) {
    mediaQueryList.removeEventListener("change", handleReducedMotionChange);
  } else if (mediaQueryList?.removeListener) {
    mediaQueryList.removeListener(handleReducedMotionChange);
  }
  mediaQueryList = null;

  detachResizeHandling();
  detachVisibilityHandling();
  destroyPoints();
  destroyRenderer();
});
</script>

<style scoped>
.agent-three-sphere {
  --three-sphere-size: 280px;
  position: relative;
  width: var(--three-sphere-size);
  height: var(--three-sphere-size);
  border-radius: 999px;
  overflow: hidden;
  background:
    radial-gradient(circle at 45% 32%, rgba(196, 220, 255, 0.14), transparent 44%),
    radial-gradient(circle at 62% 72%, rgba(92, 162, 255, 0.2), transparent 52%),
    linear-gradient(180deg, rgba(7, 15, 24, 0.95), rgba(5, 11, 18, 0.92));
  border: 1px solid color-mix(in oklab, var(--border), white 10%);
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.03),
    0 18px 38px rgba(2, 9, 17, 0.45);
}

.agent-three-sphere.is-transparent {
  background: transparent;
  border: 0;
  box-shadow: none;
}

.agent-three-sphere :deep(canvas) {
  width: 100%;
  height: 100%;
  display: block;
}

.agent-three-sphere-status {
  position: absolute;
  left: 50%;
  bottom: 10px;
  transform: translateX(-50%);
  margin: 0;
  font-size: 0.66rem;
  color: var(--muted);
  background: rgba(6, 14, 22, 0.72);
  border: 1px solid rgba(118, 154, 176, 0.3);
  border-radius: 999px;
  padding: 4px 8px;
  pointer-events: none;
}
</style>
