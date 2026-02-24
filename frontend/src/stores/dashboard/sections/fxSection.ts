import type { ParticlesConfig } from "@/stores/dashboard/storeTypes";

export function createDashboardFxSection(ctx: any) {
  function fxMode(): string {
    return document.documentElement?.dataset?.fxMode || "full";
  }

  function applyMotionBudgetProfile(itemCount: number): void {
    const root = document.documentElement;
    let budget = "high";
    let scalar = "1";

    if (itemCount >= 120) {
      budget = "low";
      scalar = "0.42";
    } else if (itemCount >= 70) {
      budget = "medium";
      scalar = "0.68";
    }

    root.dataset.motionBudget = budget;
    root.style.setProperty("--motion-budget", scalar);
  }

  function tuneParticlesConfig(config: ParticlesConfig): ParticlesConfig | null {
    const mode = fxMode();
    if (mode === "off") return null;

    const tuned = JSON.parse(JSON.stringify(config)) as ParticlesConfig;
    tuned.fps_limit = mode === "lite" ? 34 : 58;
    if (mode !== "lite") return tuned;

    tuned.particles.number.value = Math.max(
      24,
      Math.round(tuned.particles.number.value * 0.56),
    );
    tuned.particles.opacity.value = Number(
      (tuned.particles.opacity.value * 0.72).toFixed(2),
    );
    tuned.particles.move.speed = Number(
      (tuned.particles.move.speed * 0.74).toFixed(2),
    );
    tuned.particles.line_linked.opacity = Number(
      (tuned.particles.line_linked.opacity * 0.56).toFixed(2),
    );
    tuned.particles.line_linked.distance = Math.max(
      80,
      Math.round(tuned.particles.line_linked.distance * 0.84),
    );
    tuned.retina_detect = false;
    return tuned;
  }

  function resetParticlesContainer(containerId: string): void {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = "";
    delete container.dataset.particlesReady;
  }

  function resetAllParticlesContainers(): void {
    resetParticlesContainer(ctx.SIDEBAR_PARTICLES_ID);
  }

  async function reinitializeParticlesByFxMode(): Promise<void> {
    if (ctx.particlesReinitRaf) {
      window.cancelAnimationFrame(ctx.particlesReinitRaf);
      ctx.particlesReinitRaf = 0;
    }

    ctx.particlesReinitRaf = window.requestAnimationFrame(async () => {
      ctx.particlesReinitRaf = 0;
      resetAllParticlesContainers();
      await initSidebarParticles();
    });
  }

  function handleFxModeChange(): void {
    reinitializeParticlesByFxMode();
  }

  async function initParticles(
    containerId: string,
    baseConfig: ParticlesConfig,
  ): Promise<void> {
    const container = document.getElementById(containerId);
    if (!container) return;

    const config = tuneParticlesConfig(baseConfig);
    if (!config) {
      container.innerHTML = "";
      delete container.dataset.particlesReady;
      return;
    }

    if (container.dataset.particlesReady === "1") return;
    const isParticlesReady = await ctx.ensureParticlesJs();
    if (!isParticlesReady || !window.particlesJS) return;
    if (!document.getElementById(containerId)) return;
    if (container.dataset.particlesReady === "1") return;

    container.innerHTML = "";
    await window.particlesJS(containerId, config);
    container.dataset.particlesReady = "1";
  }

  async function initSidebarParticles(): Promise<void> {
    await initParticles(ctx.SIDEBAR_PARTICLES_ID, ctx.SIDEBAR_PARTICLES_CONFIG);
  }

  return {
    applyMotionBudgetProfile,
    fxMode,
    handleFxModeChange,
    initParticles,
    initSidebarParticles,
    reinitializeParticlesByFxMode,
    tuneParticlesConfig,
  };
}
