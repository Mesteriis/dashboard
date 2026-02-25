import type { LocationQuery, LocationQueryRaw, Router } from "vue-router";

export type PluginsPanelTab = "store" | "installed" | "settings";
export type PleiadOverlayMode = "route" | "screensaver";

type QueryPatch = Record<string, string | null | undefined>;

let navigationRouter: Router | null = null;

export function bindNavigationRouter(router: Router): void {
  navigationRouter = router;
}

function getRouter(): Router {
  if (!navigationRouter) {
    throw new Error("Navigation router is not bound");
  }
  return navigationRouter;
}

function mergeQuery(
  currentQuery: LocationQuery,
  patch: QueryPatch,
): LocationQueryRaw {
  const nextQuery: LocationQueryRaw = {};

  for (const [key, value] of Object.entries(currentQuery)) {
    const normalized = Array.isArray(value) ? value[value.length - 1] : value;
    if (normalized === undefined) continue;
    nextQuery[key] = String(normalized);
  }

  for (const [key, value] of Object.entries(patch)) {
    if (value === null || value === undefined || value === "") {
      delete nextQuery[key];
      continue;
    }
    nextQuery[key] = value;
  }

  return nextQuery;
}

export async function replaceQuery(patch: QueryPatch): Promise<void> {
  const router = getRouter();
  const nextQuery = mergeQuery(router.currentRoute.value.query, patch);
  await router.replace({ query: nextQuery });
}

async function pushQuery(patch: QueryPatch): Promise<void> {
  const router = getRouter();
  const nextQuery = mergeQuery(router.currentRoute.value.query, patch);
  await router.push({ query: nextQuery });
}

export async function goDashboard(): Promise<void> {
  await getRouter().push({ path: "/" });
}

export async function goSettings(): Promise<void> {
  await getRouter().push({ path: "/settings" });
}

export async function goShowcase(): Promise<void> {
  await getRouter().push({ path: "/ui" });
}

export async function goPluginsPanel(
  opts: { tab?: PluginsPanelTab } = {},
): Promise<void> {
  const query: LocationQueryRaw = {};
  if (opts.tab) {
    query.tab = opts.tab;
  }
  await getRouter().push({ path: "/plugins", query });
}

export async function goPlugin(pluginId: string): Promise<void> {
  const normalizedId = String(pluginId || "").trim();
  if (!normalizedId) return;
  await getRouter().push({
    path: `/plugins/${encodeURIComponent(normalizedId)}`,
  });
}

export async function openPleiadOverlay(
  mode: PleiadOverlayMode = "route",
): Promise<void> {
  const patch: QueryPatch = {
    overlay: "pleiad",
    mode: mode === "screensaver" ? "screensaver" : null,
  };
  await pushQuery(patch);
}

export async function closeOverlay(): Promise<void> {
  await replaceQuery({
    overlay: null,
    mode: null,
  });
}
