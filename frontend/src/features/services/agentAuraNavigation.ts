import { EVENT_OPEN_AGENT_AURA_DEMO, emitOkoEvent } from "@/features/services/events";

export const AGENT_AURA_DEMO_OPEN_EVENT = EVENT_OPEN_AGENT_AURA_DEMO;

export function dispatchOpenAgentAuraDemo(
  detail: Record<string, unknown> = {},
): void {
  emitOkoEvent(AGENT_AURA_DEMO_OPEN_EVENT, detail);
}
