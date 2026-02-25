export type AgentId =
  | "HESTIA"
  | "VELES"
  | "PERUN"
  | "STRIX"
  | "MORANA"
  | "DOMOVOY"
  | "YARILO"
  | "SVAROG"
  | "MAKOSH"
  | "RADOGOST"
  | "SOKOL"
  | "LADA";

export interface AgentDefinition {
  id: AgentId;
  title: string;
  role: string;
}

export interface AgentPlasmaPreset {
  color: string;
  intensity: number;
  seed: number;
}

export const AGENTS: AgentDefinition[] = [
  { id: "HESTIA", title: "HESTIA", role: "core" },
  { id: "VELES", title: "VELES", role: "infra" },
  { id: "PERUN", title: "PERUN", role: "executor" },
  { id: "STRIX", title: "STRIX", role: "analysis" },
  { id: "MORANA", title: "MORANA", role: "security" },
  { id: "DOMOVOY", title: "DOMOVOY", role: "iot/home" },
  { id: "YARILO", title: "YARILO", role: "creative" },
  { id: "SVAROG", title: "SVAROG", role: "architecture" },
  { id: "MAKOSH", title: "MAKOSH", role: "memory/rag" },
  { id: "RADOGOST", title: "RADOGOST", role: "comms" },
  { id: "SOKOL", title: "SOKOL", role: "telemetry" },
  { id: "LADA", title: "LADA", role: "social" },
];

export const AGENT_PLASMA_PRESETS = {
  HESTIA: { color: "rgba(255,210,120,1)", intensity: 0.9, seed: 7 },
  VELES: { color: "rgba(60,220,140,1)", intensity: 0.8, seed: 13 },
  PERUN: { color: "rgba(120,170,255,1)", intensity: 1, seed: 3 },
  STRIX: { color: "rgba(180,120,255,1)", intensity: 0.85, seed: 11 },
  MORANA: { color: "rgba(255,80,90,1)", intensity: 0.95, seed: 5 },
  DOMOVOY: { color: "rgba(255,160,80,1)", intensity: 0.75, seed: 9 },
  YARILO: { color: "rgba(255,190,70,1)", intensity: 0.85, seed: 17 },
  SVAROG: { color: "rgba(180,220,255,1)", intensity: 0.9, seed: 21 },
  MAKOSH: { color: "rgba(255,220,150,1)", intensity: 0.8, seed: 15 },
  RADOGOST: { color: "rgba(120,200,255,1)", intensity: 0.75, seed: 19 },
  SOKOL: { color: "rgba(150,255,120,1)", intensity: 0.8, seed: 23 },
  LADA: { color: "rgba(255,150,200,1)", intensity: 0.75, seed: 27 },
} as const satisfies Record<AgentId, AgentPlasmaPreset>;

export const DEFAULT_AGENT_PRESET: AgentPlasmaPreset = {
  color: "rgba(120,200,255,1)",
  intensity: 0.72,
  seed: 1,
};

export function normalizeAgentId(value: unknown): AgentId | "" {
  const normalized = String(value || "")
    .trim()
    .toUpperCase();
  const exists = AGENTS.some((agent) => agent.id === normalized);
  return exists ? (normalized as AgentId) : "";
}
