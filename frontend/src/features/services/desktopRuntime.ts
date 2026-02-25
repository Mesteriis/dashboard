import {
  EVENT_API_BASE_CHANGE,
  EVENT_DESKTOP_ACTION,
  emitOkoEvent,
} from "@/features/services/events";

const DEFAULT_REMOTE_BASE_URL = "http://127.0.0.1:8000";

export type RuntimeMode = "web" | "embedded" | "remote";
export type DeploymentMode = "docker" | "dev" | "app";
export type AppClientMode = "thin" | "thick" | null;

export interface RuntimeProfile {
  desktop: boolean;
  mode: RuntimeMode;
  deploymentMode: DeploymentMode;
  appClientMode: AppClientMode;
  apiBaseUrl: string;
  remoteBaseUrl: string;
  embeddedRunning: boolean;
}

type RuntimeProfilePayload = Partial<RuntimeProfile> & {
  api_base_url?: unknown;
  remote_base_url?: unknown;
  embedded_running?: unknown;
};

type InvokeBridge = (
  command: string,
  args?: Record<string, unknown>,
) => Promise<unknown>;

let runtimeProfile: RuntimeProfile = {
  desktop: false,
  mode: "web",
  deploymentMode: "docker",
  appClientMode: null,
  apiBaseUrl: "",
  remoteBaseUrl: DEFAULT_REMOTE_BASE_URL,
  embeddedRunning: false,
};

let bridgeReadyPromise: Promise<RuntimeProfile> | null = null;
let invokeBridge: InvokeBridge | null = null;

function isDesktopShell(): boolean {
  return typeof window !== "undefined" && Boolean(window.__TAURI_INTERNALS__);
}

function normalizeBaseUrl(rawValue: unknown): string {
  const value = String(rawValue || "").trim();
  if (!value) return "";
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

function resolveDeploymentMode(desktop: boolean): DeploymentMode {
  if (desktop) return "app";
  return import.meta.env.DEV ? "dev" : "docker";
}

function resolveRuntimeMode(mode: unknown): RuntimeMode {
  if (mode === "embedded" || mode === "remote" || mode === "web") return mode;
  return "web";
}

function resolveAppClientMode(mode: RuntimeMode, desktop: boolean): AppClientMode {
  if (!desktop) return null;
  return mode === "embedded" ? "thick" : "thin";
}

function readProfileField(
  payload: RuntimeProfilePayload | null | undefined,
  camelKey: keyof RuntimeProfilePayload,
  snakeKey: keyof RuntimeProfilePayload,
): unknown {
  if (!payload || typeof payload !== "object") return undefined;
  if (camelKey in payload) return payload[camelKey];
  if (snakeKey in payload) return payload[snakeKey];
  return undefined;
}

function applyRuntimeProfile(nextProfile: unknown): RuntimeProfile {
  const payload = (nextProfile as RuntimeProfilePayload | null | undefined) ?? null;
  const desktop = Boolean(readProfileField(payload, "desktop", "desktop"));
  const mode = resolveRuntimeMode(readProfileField(payload, "mode", "mode"));
  const normalized: RuntimeProfile = {
    desktop,
    mode,
    deploymentMode: resolveDeploymentMode(desktop),
    appClientMode: resolveAppClientMode(mode, desktop),
    apiBaseUrl: normalizeBaseUrl(
      readProfileField(payload, "apiBaseUrl", "api_base_url"),
    ),
    remoteBaseUrl:
      normalizeBaseUrl(
        readProfileField(payload, "remoteBaseUrl", "remote_base_url"),
      ) || DEFAULT_REMOTE_BASE_URL,
    embeddedRunning: Boolean(
      readProfileField(payload, "embeddedRunning", "embedded_running"),
    ),
  };

  runtimeProfile = normalized;

  if (typeof window !== "undefined") {
    window.__OKO_API_BASE__ = normalized.apiBaseUrl || "";
    window.__OKO_DESKTOP_RUNTIME__ = normalized;
    emitOkoEvent(EVENT_API_BASE_CHANGE, {
      apiBaseUrl: normalized.apiBaseUrl,
    });
  }

  return normalized;
}

function emitDesktopAction(actionId: unknown): void {
  emitOkoEvent(EVENT_DESKTOP_ACTION, {
    action: String(actionId || ""),
  });
}

async function loadDesktopBridge(): Promise<RuntimeProfile> {
  const [coreApi, eventApi] = await Promise.all([
    import("@tauri-apps/api/core"),
    import("@tauri-apps/api/event"),
  ]);

  invokeBridge = coreApi.invoke;

  const profile = await invokeBridge("desktop_get_runtime_profile");
  applyRuntimeProfile(profile);

  await eventApi.listen("desktop://runtime-profile", (event) => {
    applyRuntimeProfile(event.payload);
  });

  await eventApi.listen("desktop://action", (event) => {
    emitDesktopAction(event.payload);
  });

  return runtimeProfile;
}

export function getRuntimeProfile(): RuntimeProfile {
  return { ...runtimeProfile };
}

export async function initDesktopRuntimeBridge(): Promise<RuntimeProfile> {
  if (!isDesktopShell()) {
    applyRuntimeProfile({
      desktop: false,
      mode: "web",
      apiBaseUrl: "",
      remoteBaseUrl: DEFAULT_REMOTE_BASE_URL,
      embeddedRunning: false,
    });
    return runtimeProfile;
  }

  if (!bridgeReadyPromise) {
    bridgeReadyPromise = loadDesktopBridge().catch((error) => {
      bridgeReadyPromise = null;
      // Keep UI operational in browser mode if desktop bridge fails to initialize.
      void error;
      applyRuntimeProfile({
        desktop: true,
        mode: "remote",
        apiBaseUrl: DEFAULT_REMOTE_BASE_URL,
        remoteBaseUrl: DEFAULT_REMOTE_BASE_URL,
        embeddedRunning: false,
      });
      return runtimeProfile;
    });
  }

  return bridgeReadyPromise;
}

export async function setDesktopRuntimeProfile(nextProfile: {
  mode?: RuntimeMode;
  remoteBaseUrl?: string;
}): Promise<RuntimeProfile> {
  if (!invokeBridge) {
    const initialized = await initDesktopRuntimeBridge();
    if (!initialized.desktop || !invokeBridge) {
      throw new Error("Desktop runtime bridge is not available");
    }
  }

  const payload = {
    mode: String(nextProfile?.mode || runtimeProfile.mode),
    remote_base_url: normalizeBaseUrl(
      nextProfile?.remoteBaseUrl ||
        runtimeProfile.remoteBaseUrl ||
        DEFAULT_REMOTE_BASE_URL,
    ),
  };

  if (!invokeBridge) {
    throw new Error("Desktop runtime bridge is not available");
  }
  const updated = await invokeBridge("desktop_set_runtime_profile", payload);
  return applyRuntimeProfile(updated);
}

export { isDesktopShell };
