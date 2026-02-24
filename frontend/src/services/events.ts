export const EVENT_FX_MODE_CHANGE = "oko:fx-mode-change" as const;
export const EVENT_AGENT_FX_MODE_CHANGE = "oko:agent-fx-mode-change" as const;
export const EVENT_API_BASE_CHANGE = "oko:api-base-change" as const;
export const EVENT_API_ERROR = "oko:api-error" as const;
export const EVENT_DESKTOP_ACTION = "oko:desktop-action" as const;
export const EVENT_OPEN_PLEIAD = "oko:open-pleiad" as const;
export const EVENT_PLEIAD_PRIMARY_AGENT = "oko:pleiad-primary-agent" as const;
export const EVENT_OPEN_PLUGIN_PANEL = "oko:open-plugin-panel" as const;
export const EVENT_OPEN_AGENT_AURA_DEMO = "oko:open-agent-aura-demo" as const;
export const EVENT_PERF_METRIC = "oko:perf-metric" as const;

export interface OkoEventDetailMap {
  [EVENT_FX_MODE_CHANGE]: { mode?: string; previousMode?: string };
  [EVENT_AGENT_FX_MODE_CHANGE]: {
    mode?: string;
    previousMode?: string;
    source?: string;
  };
  [EVENT_API_BASE_CHANGE]: { apiBaseUrl?: string };
  [EVENT_API_ERROR]: {
    message?: string;
    status?: number;
    kind?: string;
    method?: string;
    url?: string;
    source?: string;
    timestamp?: string;
  };
  [EVENT_DESKTOP_ACTION]: { action?: string };
  [EVENT_OPEN_PLEIAD]: { mode?: string };
  [EVENT_PLEIAD_PRIMARY_AGENT]: { agentId?: string };
  [EVENT_OPEN_PLUGIN_PANEL]: { tab?: string };
  [EVENT_OPEN_AGENT_AURA_DEMO]: Record<string, unknown>;
  [EVENT_PERF_METRIC]: Record<string, unknown>;
}

type OkoEventType = keyof OkoEventDetailMap;

function canDispatch(): boolean {
  return (
    typeof window !== "undefined" && typeof window.dispatchEvent === "function"
  );
}

function canListen(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.addEventListener === "function" &&
    typeof window.removeEventListener === "function"
  );
}

export function emitOkoEvent<K extends OkoEventType>(
  type: K,
  detail?: OkoEventDetailMap[K],
): boolean {
  if (!canDispatch()) return false;
  const payload = detail ?? ({} as OkoEventDetailMap[K]);
  window.dispatchEvent(
    new CustomEvent(type, {
      detail: payload,
    }),
  );
  return true;
}

export function onOkoEvent<K extends OkoEventType>(
  type: K,
  listener: (event: CustomEvent<OkoEventDetailMap[K]>) => void,
  options?: AddEventListenerOptions | boolean,
): () => void {
  if (!canListen()) {
    return () => {};
  }
  const wrappedListener = listener as unknown as EventListener;
  window.addEventListener(type, wrappedListener, options);
  return () => {
    window.removeEventListener(type, wrappedListener, options);
  };
}

export function offOkoEvent<K extends OkoEventType>(
  type: K,
  listener: (event: CustomEvent<OkoEventDetailMap[K]>) => void,
  options?: EventListenerOptions | boolean,
): void {
  if (!canListen()) return;
  const wrappedListener = listener as unknown as EventListener;
  window.removeEventListener(type, wrappedListener, options);
}
