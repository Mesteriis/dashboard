<template>
  <UiBlankLayout
    :emblem-src="EMBLEM_SRC"
    :sidebar-hidden="isSidebarHidden"
    :sidebar-particles-id="SIDEBAR_PARTICLES_ID"
    :header-panel-active="editMode"
    content-label="Dashboard content"
    @logout="handleLogout"
  >
    <template #sidebar-links>
      <section class="dashboard-sidebar-plugin-links" aria-label="Быстрые ссылки плагинов">
        <button
          v-for="link in pluginSidebarLinks"
          :key="link.key"
          class="blank-sidebar-link-btn"
          type="button"
          :title="link.title"
          :aria-label="link.title"
          @click="openPluginSidebarLink(link)"
        >
          <component :is="resolvePluginLinkIcon(link.icon)" class="ui-icon" />
        </button>
      </section>
    </template>

    <template #sidebar-mid>
      <UiSidebarTreePanel v-if="isSidebarDetailed" />
    </template>

    <template #sidebar-bottom-indicators>
      <UiSidebarIndicatorsAccordion v-if="isSidebarDetailed" />
    </template>

    <template #header-tabs>
      <UiServicesHeroPanel segment="tabs" />
    </template>

    <template #drawer>
      <UiServicesHeroPanel segment="panel.drawer" />
    </template>

    <template #drawer-footer>
      <UiServicesHeroPanel segment="panel.footer" />
    </template>

    <template #canvas-main>
      <DashboardMainView hide-hero />
    </template>
  </UiBlankLayout>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, type Component } from "vue";
import { useRouter } from "vue-router";
import { LayoutGrid, Package, Puzzle, Radar, Settings, Store } from "lucide-vue-next";
import DashboardMainView from "@/views/dashboard/DashboardMainView.vue";
import UiServicesHeroPanel from "@/views/dashboard/components/UiServicesHeroPanel.vue";
import UiSidebarIndicatorsAccordion from "@/views/dashboard/components/UiSidebarIndicatorsAccordion.vue";
import UiSidebarTreePanel from "@/views/dashboard/components/UiSidebarTreePanel.vue";
import UiBlankLayout from "@/components/layout/UiBlankLayout.vue";
import { requestJson } from "@/features/services/dashboardApi";
import {
  EMBLEM_SRC,
  SIDEBAR_PARTICLES_CONFIG,
  SIDEBAR_PARTICLES_ID,
} from "@/features/stores/ui/storeConstants";
import { useUiStore } from "@/features/stores/uiStore";
import { useSidebarParticles } from "@/features/composables/useSidebarParticles";

const dashboard = useUiStore();
const { editMode, isSidebarDetailed, isSidebarHidden } = dashboard;
const router = useRouter();

useSidebarParticles({
  containerId: SIDEBAR_PARTICLES_ID,
  baseConfig: SIDEBAR_PARTICLES_CONFIG,
  isSidebarHidden,
});

type PluginSidebarLinkTarget = "same_tab" | "new_tab";

interface PluginSidebarLink {
  key: string;
  title: string;
  icon: string;
  route: string;
  target: PluginSidebarLinkTarget;
}

const pluginsApi = ref<unknown[]>([]);

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

function asString(value: unknown): string {
  return String(value || "").trim();
}

function asTarget(value: unknown): PluginSidebarLinkTarget {
  return asString(value).toLowerCase() === "new_tab" ? "new_tab" : "same_tab";
}

const SIDEBAR_LINK_ICONS: Record<string, Component> = {
  radar: Radar,
  package: Package,
  puzzle: Puzzle,
  settings: Settings,
  store: Store,
  layoutgrid: LayoutGrid,
  grid: LayoutGrid,
};

function resolvePluginLinkIcon(iconName: string): Component {
  const key = asString(iconName)
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "");
  return SIDEBAR_LINK_ICONS[key] || Package;
}

async function loadPlugins(): Promise<void> {
  try {
    const response = await requestJson("/api/v1/plugins");
    const root = asRecord(response);
    pluginsApi.value = Array.isArray(root?.plugins) ? root.plugins : [];
  } catch {
    pluginsApi.value = [];
  }
}

const pluginSidebarLinks = computed<PluginSidebarLink[]>(() => {
  const links: PluginSidebarLink[] = [];
  const seen = new Set<string>();

  for (const raw of pluginsApi.value) {
    const entry = asRecord(raw);
    if (!entry) continue;
    const pluginId = asString(entry.id) || asString(entry.name);
    if (!pluginId) continue;

    const uiConfig = asRecord(entry.ui_config);
    const metadata = asRecord(entry.metadata);
    const pageManifestEnvelope = asRecord(metadata?.page_manifest);
    const pageManifest = asRecord(pageManifestEnvelope?.manifest);
    const page = asRecord(pageManifest?.page);
    const actionsRaw = Array.isArray(page?.sidebarActions)
      ? page.sidebarActions
      : Array.isArray(page?.sidebar_actions)
        ? page.sidebar_actions
        : [];

    for (const rawAction of actionsRaw) {
      const action = asRecord(rawAction);
      if (!action) continue;
      const route = asString(action.route);
      if (!route) continue;
      const title = asString(action.title) || pluginId;
      const icon = asString(action.icon) || asString(uiConfig?.page_icon) || "package";
      const target = asTarget(action.target);
      const key = `${pluginId}:${asString(action.id) || "open"}:${route}`;
      if (seen.has(key)) continue;
      seen.add(key);
      links.push({ key, title, icon, route, target });
    }
  }

  return links.sort((a, b) =>
    a.title.localeCompare(b.title, "ru", { sensitivity: "base" }),
  );
});

function openPluginSidebarLink(link: PluginSidebarLink): void {
  const route = asString(link.route);
  if (!route) return;
  const isExternal = /^https?:\/\//i.test(route);
  if (link.target === "new_tab") {
    const href = isExternal ? route : router.resolve(route).href;
    window.open(href, "_blank", "noopener,noreferrer");
    return;
  }
  if (isExternal) {
    window.location.assign(route);
    return;
  }
  void router.push(route);
}

onMounted(() => {
  void loadPlugins();
});

function handleLogout(): void {
  // eslint-disable-next-line no-console
  console.log("Logout requested");
}
</script>

<style scoped>
.dashboard-sidebar-plugin-links {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-content: flex-start;
}
</style>
