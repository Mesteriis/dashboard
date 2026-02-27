import {
  EVENT_PLEIAD_PRIMARY_AGENT,
  emitOkoEvent,
} from "@/features/services/events";
import { openPleiadOverlay } from "@/app/navigation/nav";

export const PLEIAD_PRIMARY_AGENT_EVENT = EVENT_PLEIAD_PRIMARY_AGENT;

export function dispatchOpenPleiad(
  detail: { mode?: "screensaver" | "route" } = {},
): void {
  const mode = detail.mode === "screensaver" ? "screensaver" : "route";
  void openPleiadOverlay(mode);
}

export function dispatchPleiadPrimaryAgent(
  agentId: string,
  detail: Record<string, unknown> = {},
): void {
  const normalizedAgentId = String(agentId || "")
    .trim()
    .toUpperCase();
  if (!normalizedAgentId) return;
  emitOkoEvent(PLEIAD_PRIMARY_AGENT_EVENT, {
    ...detail,
    agentId: normalizedAgentId,
  });
}
