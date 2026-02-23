export const AGENT_AURA_DEMO_OPEN_EVENT = "oko:open-agent-aura-demo";

/**
 * @param {Record<string, unknown>} [detail]
 * @returns {void}
 */
export function dispatchOpenAgentAuraDemo(detail = {}) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent(AGENT_AURA_DEMO_OPEN_EVENT, {
      detail,
    }),
  );
}
