const PARTICLES_TIMEOUT_MS = 7000;

type LegacyKeyMap = Record<string, string>;
type ParticlesCompatFn = (containerId: string, config: unknown) => Promise<unknown>;

interface TsParticlesCompatLoader {
  load: (params: { id: string; options: unknown }) => Promise<unknown>;
}

let particlesInitPromise: Promise<boolean> | null = null;

const LEGACY_KEY_MAP: Readonly<LegacyKeyMap> = Object.freeze({
  fps_limit: "fpsLimit",
  retina_detect: "retinaDetect",
  detect_on: "detectsOn",
  line_linked: "links",
  onhover: "onHover",
  onclick: "onClick",
  value_area: "area",
});

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function normalizeLegacyConfig(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map((entry) => normalizeLegacyConfig(entry));
  }
  if (!isRecord(value)) {
    return value;
  }

  const normalized: Record<string, unknown> = {};
  for (const [key, entry] of Object.entries(value)) {
    const nextKey = LEGACY_KEY_MAP[key] || key;
    normalized[nextKey] = normalizeLegacyConfig(entry);
  }
  return normalized;
}

async function withTimeout<T>(promise: Promise<T>, timeoutMs: number): Promise<T> {
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

function hasParticlesCompat(): boolean {
  return typeof window.particlesJS === "function";
}

function installParticlesCompat(tsParticles: TsParticlesCompatLoader): void {
  window.particlesJS = (containerId: string, config: unknown) => {
    const id = String(containerId || "").trim();
    if (!id) return Promise.resolve(undefined);
    const options = normalizeLegacyConfig(config);
    return tsParticles.load({ id, options });
  };
}

export async function ensureParticlesJs(): Promise<boolean> {
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
      installParticlesCompat(tsParticles as unknown as TsParticlesCompatLoader);
      return hasParticlesCompat();
    } catch {
      particlesInitPromise = null;
      return false;
    }
  })();

  return particlesInitPromise;
}

declare global {
  interface Window {
    particlesJS?: ParticlesCompatFn;
  }
}
