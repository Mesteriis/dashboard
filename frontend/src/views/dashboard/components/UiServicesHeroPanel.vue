<template>
  <UiHeroPanel
    v-if="segment === 'full'"
    :active="editMode"
    controls-class="hero-control-panel--menu service-hero-controls"
  >
    <template #title>
      <UiHeroPageTabs />
    </template>

    <template #controls>
      <UiHeroControlsAccordion
        drawer-id="hero-controls-drawer"
        :storage-key="heroControlsStorageKey"
      >
        <template #drawer>
          <UiIconButton
            button-class="hero-icon-btn hero-accordion-action"
            title="Панель настроек"
            aria-label="Открыть панель настроек"
            @click="openSettingsPanel"
          >
            <SlidersHorizontal class="ui-icon hero-action-icon" />
          </UiIconButton>

          <UiIconButton
            button-class="hero-icon-btn hero-accordion-action"
            :active="!isSidebarDetailed"
            :title="sidebarViewToggleTitle"
            :aria-label="sidebarViewToggleTitle"
            @click="toggleSidebarView"
          >
            <FolderTree class="ui-icon hero-action-icon" />
          </UiIconButton>

          <UiIconButton
            button-class="hero-icon-btn hero-accordion-action editor-toggle"
            :active="editMode"
            :title="
              editMode
                ? 'Выключить режим редактирования'
                : 'Включить режим редактирования'
            "
            :aria-label="
              editMode
                ? 'Выключить режим редактирования'
                : 'Включить режим редактирования'
            "
            @click="toggleEditMode"
          >
            <Pencil class="ui-icon hero-action-icon" />
          </UiIconButton>

          <UiIconButton
            button-class="hero-icon-btn hero-accordion-action"
            :disabled="!editMode"
            title="Добавить сущность"
            aria-label="Добавить сущность"
            @click="openCreateChooser()"
          >
            <Plus class="ui-icon hero-action-icon" />
          </UiIconButton>

          <span
            v-if="editMode"
            class="hero-save-indicator hero-accordion-status"
            :class="saveStatus"
            role="status"
            :title="saveStatusLabel"
            :aria-label="saveStatusLabel"
          >
            <Circle class="ui-icon hero-save-icon" />
          </span>
        </template>

        <template #actions>
          <UiIconButton
            button-class="hero-icon-btn hero-accordion-action hero-plugin-panel-btn"
            title="Открыть панель плагинов"
            aria-label="Открыть панель плагинов"
            @click="openPluginPanel"
          >
            <Puzzle class="ui-icon hero-action-icon" />
          </UiIconButton>

          <UiDropdownMenu
            class="hero-action-menu"
            aria-label="Системное меню"
            :items="systemActions"
            :show-caret="false"
            trigger-class="hero-icon-btn hero-accordion-action hero-system-menu-trigger"
            item-class="hero-system-menu-item"
            @action="handleSystemAction"
          >
            <template #trigger>
              <Lock class="ui-icon hero-action-icon" />
            </template>
          </UiDropdownMenu>
        </template>

        <template #footer>
          <p
            v-if="editMode && saveError"
            class="editor-error hero-editor-error"
          >
            {{ saveError }}
          </p>
        </template>
      </UiHeroControlsAccordion>
    </template>
  </UiHeroPanel>

  <UiHeroPageTabs v-else-if="segment === 'tabs'" />

  <template v-else-if="segment === 'panel.drawer'">
    <UiIconButton
      button-class="hero-icon-btn hero-accordion-action"
      title="Панель настроек"
      aria-label="Открыть панель настроек"
      @click="openSettingsPanel"
    >
      <SlidersHorizontal class="ui-icon hero-action-icon" />
    </UiIconButton>

    <UiIconButton
      button-class="hero-icon-btn hero-accordion-action"
      :active="!isSidebarDetailed"
      :title="sidebarViewToggleTitle"
      :aria-label="sidebarViewToggleTitle"
      @click="toggleSidebarView"
    >
      <FolderTree class="ui-icon hero-action-icon" />
    </UiIconButton>

    <UiIconButton
      button-class="hero-icon-btn hero-accordion-action editor-toggle"
      :active="editMode"
      :title="
        editMode
          ? 'Выключить режим редактирования'
          : 'Включить режим редактирования'
      "
      :aria-label="
        editMode
          ? 'Выключить режим редактирования'
          : 'Включить режим редактирования'
      "
      @click="toggleEditMode"
    >
      <Pencil class="ui-icon hero-action-icon" />
    </UiIconButton>

    <UiIconButton
      button-class="hero-icon-btn hero-accordion-action"
      :disabled="!editMode"
      title="Добавить сущность"
      aria-label="Добавить сущность"
      @click="openCreateChooser()"
    >
      <Plus class="ui-icon hero-action-icon" />
    </UiIconButton>

    <span
      v-if="editMode"
      class="hero-save-indicator hero-accordion-status"
      :class="saveStatus"
      role="status"
      :title="saveStatusLabel"
      :aria-label="saveStatusLabel"
    >
      <Circle class="ui-icon hero-save-icon" />
    </span>
  </template>

  <template v-else-if="segment === 'panel.actions'">
    <UiIconButton
      button-class="hero-icon-btn hero-accordion-action hero-plugin-panel-btn"
      title="Открыть панель плагинов"
      aria-label="Открыть панель плагинов"
      @click="openPluginPanel"
    >
      <Puzzle class="ui-icon hero-action-icon" />
    </UiIconButton>
  </template>

  <UiDropdownMenu
    v-else-if="segment === 'panel.menu'"
    aria-label="Системное меню"
    :items="systemActions"
    :show-caret="false"
    trigger-class="hero-icon-btn hero-accordion-action hero-system-menu-trigger"
    item-class="hero-system-menu-item"
    @action="handleSystemAction"
  >
    <template #trigger>
      <Lock class="ui-icon hero-action-icon" />
    </template>
  </UiDropdownMenu>

  <p
    v-else-if="segment === 'panel.footer' && editMode && saveError"
    class="editor-error hero-editor-error"
  >
    {{ saveError }}
  </p>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter, type RouteLocationRaw } from "vue-router";
import type { Component } from "vue";
import {
  Circle,
  FolderTree,
  Lock,
  Pencil,
  Plus,
  Puzzle,
  SlidersHorizontal,
} from "lucide-vue-next";
import UiHeroPageTabs from "@/views/dashboard/components/UiHeroPageTabs.vue";
import UiHeroControlsAccordion from "@/components/layout/UiHeroControlsAccordion.vue";
import UiDropdownMenu from "@/primitives/overlays/UiDropdownMenu.vue";
import UiHeroPanel from "@/components/layout/UiHeroPanel.vue";
import UiIconButton from "@/ui/actions/UiIconButton.vue";
import { goPluginsPanel, openPleiadOverlay } from "@/app/navigation/nav";
import { getRuntimeProfile } from "@/features/services/desktopRuntime";
import { useDashboardStore } from "@/features/stores/dashboardStore";

type UiServicesHeroPanelSegment =
  | "full"
  | "tabs"
  | "panel.drawer"
  | "panel.actions"
  | "panel.menu"
  | "panel.footer";

const props = withDefaults(
  defineProps<{
    segment?: UiServicesHeroPanelSegment;
  }>(),
  {
    segment: "full",
  },
);

const segment = computed(() => props.segment);
const route = useRoute();
const dashboard = useDashboardStore();

const {
  editMode,
  isSidebarDetailed,
  openCreateChooser,
  openSettingsPanel,
  saveError,
  saveStatus,
  saveStatusLabel,
  sidebarViewToggleTitle,
  toggleEditMode,
  toggleSidebarView,
} = dashboard;

const router = useRouter();

type SystemActionId = "kiosk" | "profile" | "pleiad_lock" | "exit" | "navigate";

interface SystemAction {
  id: SystemActionId | string;
  label: string;
  icon?: Component | string;
  route?: RouteLocationRaw;
  action?: () => void | Promise<void>;
  danger?: boolean;
  divider?: boolean;
}

const systemActions = computed<SystemAction[]>(() => [
  { id: "kiosk", label: "Режим киоска" },
  { id: "profile", label: "Профиль" },
  { id: "pleiad_lock", label: "Блокировка -> Плияды" },
  { id: "divider-1", label: "", divider: true },
  { id: "navigate", label: "Домой", route: "/" },
  { id: "exit", label: "Выход", danger: true },
]);

const heroControlsStorageKey = computed(() => {
  const rawPath = String(route.path || "/").trim();
  const normalizedPath =
    rawPath.length > 1 && rawPath.endsWith("/")
      ? rawPath.slice(0, -1)
      : rawPath;
  return `oko:hero-controls-open:${normalizedPath || "/"}`;
});

function openPluginPanel() {
  void goPluginsPanel();
}

async function toggleKioskMode(): Promise<void> {
  if (typeof document === "undefined") return;
  try {
    if (document.fullscreenElement) {
      await document.exitFullscreen();
      return;
    }
    await document.documentElement.requestFullscreen();
  } catch {
    // Keep UI responsive even if fullscreen API is unavailable.
  }
}

async function exitApp(): Promise<void> {
  try {
    if (getRuntimeProfile().desktop) {
      const { getCurrentWindow } = await import("@tauri-apps/api/window");
      await getCurrentWindow().close();
      return;
    }
  } catch {
    // Fall through to browser close attempt.
  }

  if (typeof window !== "undefined") {
    window.close();
  }
}

function handleSystemAction(action: SystemAction): void {
  // Обработка divider — игнорируем
  if (action.divider) return;

  // Если есть custom action — выполняем его
  if (action.action) {
    void Promise.resolve(action.action());
    return;
  }

  // Если есть route — навигируем
  if (action.route) {
    void router.push(action.route);
    return;
  }

  // Встроенные действия
  const id = action.id as SystemActionId;

  if (id === "kiosk") {
    void toggleKioskMode();
    return;
  }

  if (id === "settings" || id === "profile") {
    openSettingsPanel();
    return;
  }

  if (id === "pleiad_lock") {
    void openPleiadOverlay("route");
    return;
  }

  if (id === "logout" || id === "exit") {
    void exitApp();
  }
}
</script>
