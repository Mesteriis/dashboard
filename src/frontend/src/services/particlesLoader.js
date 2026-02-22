const PARTICLES_SCRIPT_ID = "oko-particles-js";
const PARTICLES_SCRIPT_SRC =
  "https://cdn.jsdelivr.net/npm/particles.js@2.0.0/particles.min.js";
const PARTICLES_TIMEOUT_MS = 7000;

/**
 * @type {Promise<boolean> | null}
 */
let particlesScriptPromise = null;

function hasParticlesJs() {
  return (
    typeof (/** @type {{ particlesJS?: unknown }} */ (window).particlesJS) ===
    "function"
  );
}

/**
 * @param {HTMLScriptElement} scriptElement
 * @returns {Promise<boolean>}
 */
function resolveLoad(scriptElement) {
  return new Promise((resolve) => {
    let settled = false;

    /**
     * @param {boolean} value
     */
    const finish = (value) => {
      if (settled) return;
      settled = true;
      resolve(value);
    };

    const timeoutId = window.setTimeout(() => {
      finish(hasParticlesJs());
    }, PARTICLES_TIMEOUT_MS);

    scriptElement.addEventListener(
      "load",
      () => {
        window.clearTimeout(timeoutId);
        finish(hasParticlesJs());
      },
      { once: true },
    );
    scriptElement.addEventListener(
      "error",
      () => {
        window.clearTimeout(timeoutId);
        finish(false);
      },
      { once: true },
    );
  });
}

export async function ensureParticlesJs() {
  if (typeof window === "undefined" || typeof document === "undefined")
    return false;
  if (hasParticlesJs()) return true;
  if (particlesScriptPromise) return particlesScriptPromise;

  particlesScriptPromise = (async () => {
    /** @type {HTMLScriptElement | null} */
    let script =
      document.getElementById(PARTICLES_SCRIPT_ID) instanceof HTMLScriptElement
        ? /** @type {HTMLScriptElement} */ (
            document.getElementById(PARTICLES_SCRIPT_ID)
          )
        : null;

    if (!script) {
      script = document.createElement("script");
      script.id = PARTICLES_SCRIPT_ID;
      script.src = PARTICLES_SCRIPT_SRC;
      script.async = true;
      script.defer = true;
      document.head.appendChild(script);
    }

    const loaded = await resolveLoad(script);
    if (!loaded) {
      particlesScriptPromise = null;
    }
    return loaded;
  })();

  return particlesScriptPromise;
}
