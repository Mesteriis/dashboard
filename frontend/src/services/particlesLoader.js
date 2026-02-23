const PARTICLES_TIMEOUT_MS = 7000;

/**
 * @type {Promise<boolean> | null}
 */
let particlesInitPromise = null;

/** @type {Readonly<Record<string, string>>} */
const LEGACY_KEY_MAP = Object.freeze({
  fps_limit: "fpsLimit",
  retina_detect: "retinaDetect",
  detect_on: "detectsOn",
  line_linked: "links",
  onhover: "onHover",
  onclick: "onClick",
  value_area: "area",
});

/**
 * @param {unknown} value
 * @returns {value is Record<string, unknown>}
 */
function isRecord(value) {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

/**
 * @param {unknown} value
 * @returns {unknown}
 */
function normalizeLegacyConfig(value) {
  if (Array.isArray(value)) {
    return value.map((entry) => normalizeLegacyConfig(entry));
  }
  if (!isRecord(value)) {
    return value;
  }

  /** @type {Record<string, unknown>} */
  const normalized = {};
  for (const [key, entry] of Object.entries(value)) {
    const nextKey = LEGACY_KEY_MAP[key] || key;
    normalized[nextKey] = normalizeLegacyConfig(entry);
  }
  return normalized;
}

/**
 * @template T
 * @param {Promise<T>} promise
 * @param {number} timeoutMs
 * @returns {Promise<T>}
 */
async function withTimeout(promise, timeoutMs) {
  return await new Promise((resolve, reject) => {
    const timeoutId = window.setTimeout(() => {
      reject(new Error("tsParticles initialization timeout"));
    }, timeoutMs);

    promise.then(
      (value) => {
        window.clearTimeout(timeoutId);
        resolve(value);
      },
      (error) => {
        window.clearTimeout(timeoutId);
        reject(error);
      },
    );
  });
}

function hasParticlesCompat() {
  const typedWindow = /** @type {{ particlesJS?: unknown }} */ (window);
  return (
    typeof typedWindow.particlesJS === "function"
  );
}

/**
 * @param {{ load: (params: any) => Promise<any> }} tsParticles
 */
function installParticlesCompat(tsParticles) {
  const typedWindow = /** @type {{ particlesJS?: ((containerId: string, config: unknown) => Promise<unknown>) }} */ (
    window
  );
  typedWindow.particlesJS = (containerId, config) => {
    const id = String(containerId || "").trim();
    if (!id) return Promise.resolve(undefined);
    const options = normalizeLegacyConfig(config);
    return tsParticles.load({ id, options });
  };
}

export async function ensureParticlesJs() {
  if (typeof window === "undefined" || typeof document === "undefined") {
    return false;
  }
  if (hasParticlesCompat()) {
    return true;
  }
  if (particlesInitPromise) {
    return particlesInitPromise;
  }

  particlesInitPromise = (async () => {
    try {
      const [{ tsParticles }, { loadSlim }] = await Promise.all([
        import("@tsparticles/engine"),
        import("@tsparticles/slim"),
      ]);
      await withTimeout(loadSlim(tsParticles), PARTICLES_TIMEOUT_MS);
      installParticlesCompat(tsParticles);
      return hasParticlesCompat();
    } catch {
      particlesInitPromise = null;
      return false;
    }
  })();

  return particlesInitPromise;
}
